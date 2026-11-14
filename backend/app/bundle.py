"""Campaign bundles: export a campaign to a .zip, and import one back.

A bundle is a plain .zip with a human-authorable layout, so a DM can build one
at home (or by hand) and import it at the table on another server:

    bundle.json            manifest (campaign + maps + creatures + notes + gallery)
    maps/<file>            battlemap images                 (public)
    tokens/<file>          creature token art               (public)
    portraits/<file>       creature display images          (public, shown on click)
    secret/<file>          creature DM-only images          (protected)
    handouts/<file>        gallery images / player handouts (public)

Media are referenced from bundle.json by their relative path. Tokens reference a
creature by its bundle-local `key`. See docs/BUNDLE_FORMAT.md for the full spec.

Security note: import only ever reads the media paths named in the manifest, each
sanitized against path traversal, with per-file and total-size caps. Hidden
creature content stays in the protected bucket, exactly as in normal use.
"""
from __future__ import annotations

import io
import json
import os
import posixpath
import re
import uuid
import zipfile
from datetime import datetime, timezone

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # avoid importing the DB stack for the stdlib-only CLI (`pack`)
    from sqlalchemy.orm import Session
    from .models import Campaign, User

BUNDLE_FORMAT = "gametable-bundle"
BUNDLE_VERSION = 1
MANIFEST_NAME = "bundle.json"

# Import guardrails.
_MAX_UNCOMPRESSED = 200 * 1024 * 1024   # 200 MB total
_MAX_FILE_BYTES = 25 * 1024 * 1024       # 25 MB per media file
_MAX_ENTITIES = 2000                      # maps+creatures+tokens+notes+gallery

_MEDIA_FOLDERS = ("maps", "tokens", "portraits", "secret", "handouts")


# --- shared helpers ---------------------------------------------------------

def _slug(text: str, fallback: str = "item") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or fallback


def _ext_of(ref: str) -> str:
    ext = os.path.splitext(ref)[1].lower()
    return ext or ".png"


# --- export -----------------------------------------------------------------

class _MediaWriter:
    """Copies a stored media file into the zip under a friendly, unique name."""

    def __init__(self, zf: zipfile.ZipFile, resolve):
        self.zf = zf
        self.resolve = resolve  # url -> filesystem path (or None)
        self._used: set[str] = set()

    def add(self, folder: str, url: str | None, display: str) -> str | None:
        fs = self.resolve(url)
        if not fs or not os.path.isfile(fs):
            return None
        ext = os.path.splitext(fs)[1].lower() or ".png"
        base = _slug(display, folder[:-1] if folder.endswith("s") else folder)
        name = f"{base}{ext}"
        i = 2
        while f"{folder}/{name}" in self._used:
            name = f"{base}-{i}{ext}"
            i += 1
        ref = f"{folder}/{name}"
        self._used.add(ref)
        with open(fs, "rb") as fh:
            self.zf.writestr(ref, fh.read())
        return ref


def export_campaign(db: "Session", campaign: "Campaign") -> bytes:
    """Serialize a campaign (and all its media) into a .zip, returned as bytes."""
    from sqlalchemy import select

    from . import storage
    from .models import Creature, GalleryImage, Map, Note, Token

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        media = _MediaWriter(zf, storage.fs_path_for_url)

        creatures = db.scalars(
            select(Creature).where(Creature.campaign_id == campaign.id).order_by(Creature.created_at)
        ).all()
        # Assign stable bundle-local keys for token references.
        keys: dict[uuid.UUID, str] = {}
        used_keys: set[str] = set()
        for c in creatures:
            k = _slug(c.name, "creature")
            kk, i = k, 2
            while kk in used_keys:
                kk = f"{k}-{i}"
                i += 1
            used_keys.add(kk)
            keys[c.id] = kk

        creatures_j = []
        for c in creatures:
            creatures_j.append({
                "key": keys[c.id],
                "name": c.name,
                "type": c.type,
                "visibility": c.visibility,
                "public_stats": c.public_stats,
                "hidden_stats": c.hidden_stats,
                "token_image": media.add("tokens", c.token_image_path, c.name),
                "display_image": media.add("portraits", c.display_image_path, c.name),
                "hidden_image": media.add("secret", c.hidden_image_path, c.name),
            })

        maps = db.scalars(
            select(Map).where(Map.campaign_id == campaign.id).order_by(Map.sort_order, Map.created_at)
        ).all()
        maps_j = []
        for m in maps:
            tokens = db.scalars(
                select(Token).where(Token.map_id == m.id).order_by(Token.z_index, Token.created_at)
            ).all()
            maps_j.append({
                "name": m.name,
                "image": media.add("maps", m.image_path, m.name),
                "width": m.width,
                "height": m.height,
                "active": campaign.active_map_id == m.id,
                "grid": {
                    "type": m.grid_type,
                    "size": m.grid_size,
                    "offset_x": m.grid_offset_x,
                    "offset_y": m.grid_offset_y,
                    "color": m.grid_color,
                    "unit_per_cell": m.unit_per_cell,
                },
                "fog": m.fog or {"revealed": [], "hidden": []},
                "tokens": [{
                    "creature": keys.get(t.creature_id) if t.creature_id else None,
                    "label": t.label,
                    "x": t.x, "y": t.y,
                    "size": t.size,
                    "rotation": t.rotation,
                    "color": t.color,
                    "border_color": t.border_color,
                    "hidden_from_players": t.hidden_from_players,
                    "locked": t.locked,
                    "z_index": t.z_index,
                } for t in tokens],
            })

        notes = db.scalars(
            select(Note).where(Note.campaign_id == campaign.id).order_by(Note.sort_order, Note.created_at)
        ).all()
        notes_j = [{
            "title": n.title, "body": n.body,
            "visibility": n.visibility, "sort_order": n.sort_order,
        } for n in notes]

        gallery = db.scalars(
            select(GalleryImage).where(GalleryImage.campaign_id == campaign.id).order_by(GalleryImage.created_at)
        ).all()
        gallery_j = []
        for g in gallery:
            gallery_j.append({
                "name": g.name,
                "image": media.add("handouts", g.image_path, g.name),
                "is_shared": g.is_shared,
            })

        manifest = {
            "format": BUNDLE_FORMAT,
            "version": BUNDLE_VERSION,
            "generator": "GameTable",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "campaign": {"name": campaign.name, "description": campaign.description},
            "creatures": creatures_j,
            "maps": maps_j,
            "notes": notes_j,
            "gallery": gallery_j,
        }
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, ensure_ascii=False))

    return buf.getvalue()


# --- import -----------------------------------------------------------------

class BundleError(ValueError):
    """Raised for a malformed or unsafe bundle (-> HTTP 422)."""


def _find_manifest(zf: zipfile.ZipFile) -> str:
    names = [n for n in zf.namelist() if posixpath.basename(n) == MANIFEST_NAME]
    if not names:
        raise BundleError("No bundle.json found in the archive")
    # Prefer the shallowest (root) manifest.
    return min(names, key=lambda n: n.count("/"))


def _safe_member(base: str, ref: str) -> str:
    if not isinstance(ref, str) or not ref:
        raise BundleError("Invalid media reference")
    name = posixpath.normpath(posixpath.join(base, ref))
    if name.startswith("/") or name.startswith("..") or ".." in name.split("/"):
        raise BundleError(f"Unsafe path in bundle: {ref}")
    return name


def _read_member(zf: zipfile.ZipFile, name: str) -> bytes:
    try:
        info = zf.getinfo(name)
    except KeyError:
        raise BundleError(f"Bundle references a missing file: {name}")
    if info.file_size > _MAX_FILE_BYTES:
        raise BundleError(f"Media file too large: {name}")
    return zf.read(name)


def import_bundle(db: "Session", user: "User", data: bytes, name_override: str | None = None) -> "Campaign":
    """Create a brand-new campaign owned by `user` from a bundle .zip."""
    from . import storage
    from .models import Campaign, Creature, GalleryImage, Map, Note, Token

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise BundleError("Not a valid .zip archive")

    if sum(i.file_size for i in zf.infolist()) > _MAX_UNCOMPRESSED:
        raise BundleError("Bundle is too large")

    manifest_name = _find_manifest(zf)
    base = posixpath.dirname(manifest_name)
    try:
        manifest = json.loads(zf.read(manifest_name))
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise BundleError("bundle.json is not valid JSON")

    if not isinstance(manifest, dict) or manifest.get("format") != BUNDLE_FORMAT:
        raise BundleError("Not a GameTable bundle")
    if int(manifest.get("version", 0)) > BUNDLE_VERSION:
        raise BundleError("Bundle was made by a newer GameTable version")

    camp_j = manifest.get("campaign") or {}
    creatures_j = manifest.get("creatures") or []
    maps_j = manifest.get("maps") or []
    notes_j = manifest.get("notes") or []
    gallery_j = manifest.get("gallery") or []
    total = len(creatures_j) + len(maps_j) + len(notes_j) + len(gallery_j) + sum(
        len(m.get("tokens") or []) for m in maps_j if isinstance(m, dict)
    )
    if total > _MAX_ENTITIES:
        raise BundleError("Bundle has too many objects")

    name = (name_override or camp_j.get("name") or "Imported campaign").strip()[:200]
    campaign = Campaign(owner_id=user.id, name=name, description=str(camp_j.get("description", ""))[:10000])
    db.add(campaign)
    db.flush()  # need campaign.id for media buckets

    def pub(ref: str | None) -> str | None:
        if not ref:
            return None
        raw = _read_member(zf, _safe_member(base, ref))
        return storage.save_public_bytes(raw, _ext_of(ref), campaign.id)

    def prot(ref: str | None) -> str | None:
        if not ref:
            return None
        raw = _read_member(zf, _safe_member(base, ref))
        return storage.save_protected_bytes(raw, _ext_of(ref), campaign.id)

    # Creatures first (tokens reference them by key).
    key_to_id: dict[str, uuid.UUID] = {}
    for cj in creatures_j:
        if not isinstance(cj, dict):
            continue
        c = Creature(
            campaign_id=campaign.id,
            name=str(cj.get("name", "Creature"))[:200],
            type=str(cj.get("type", "creature"))[:20],
            visibility=str(cj.get("visibility", "hidden"))[:20],
            public_stats=str(cj.get("public_stats", "")),
            hidden_stats=str(cj.get("hidden_stats", "")),
            token_image_path=pub(cj.get("token_image")),
            display_image_path=pub(cj.get("display_image")),
            hidden_image_path=prot(cj.get("hidden_image")),
        )
        db.add(c)
        db.flush()
        key = cj.get("key")
        if isinstance(key, str) and key:
            key_to_id[key] = c.id

    # Maps + tokens.
    active_target: uuid.UUID | None = None
    for order, mj in enumerate(maps_j):
        if not isinstance(mj, dict):
            continue
        grid = mj.get("grid") or {}
        m = Map(
            campaign_id=campaign.id,
            name=str(mj.get("name", "Map"))[:200],
            image_path=pub(mj.get("image")) or "",
            width=int(mj.get("width", 0) or 0),
            height=int(mj.get("height", 0) or 0),
            grid_type=str(grid.get("type", "square"))[:20],
            grid_size=int(grid.get("size", 70) or 70),
            grid_offset_x=int(grid.get("offset_x", 0) or 0),
            grid_offset_y=int(grid.get("offset_y", 0) or 0),
            grid_color=str(grid.get("color", "#000000"))[:32],
            unit_per_cell=float(grid.get("unit_per_cell", 5.0) or 5.0),
            fog=mj.get("fog") or {"revealed": [], "hidden": []},
            sort_order=order,
        )
        db.add(m)
        db.flush()
        if mj.get("active") and active_target is None:
            active_target = m.id
        for tj in (mj.get("tokens") or []):
            if not isinstance(tj, dict):
                continue
            db.add(Token(
                map_id=m.id,
                creature_id=key_to_id.get(tj.get("creature")) if tj.get("creature") else None,
                label=str(tj.get("label", ""))[:120],
                x=float(tj.get("x", 0) or 0),
                y=float(tj.get("y", 0) or 0),
                size=int(tj.get("size", 1) or 1),
                rotation=float(tj.get("rotation", 0) or 0),
                color=str(tj.get("color", "#888888"))[:32],
                border_color=(str(tj["border_color"])[:32] if tj.get("border_color") else None),
                hidden_from_players=bool(tj.get("hidden_from_players", False)),
                locked=bool(tj.get("locked", False)),
                z_index=int(tj.get("z_index", 0) or 0),
            ))

    for nj in notes_j:
        if not isinstance(nj, dict):
            continue
        db.add(Note(
            campaign_id=campaign.id,
            title=str(nj.get("title", "Note"))[:200],
            body=str(nj.get("body", "")),
            visibility=str(nj.get("visibility", "hidden"))[:20],
            sort_order=int(nj.get("sort_order", 0) or 0),
        ))

    for gj in gallery_j:
        if not isinstance(gj, dict):
            continue
        db.add(GalleryImage(
            campaign_id=campaign.id,
            name=str(gj.get("name", "Image"))[:200],
            image_path=pub(gj.get("image")) or "",
            is_shared=bool(gj.get("is_shared", False)),
        ))

    if active_target:
        campaign.active_map_id = active_target

    db.commit()
    db.refresh(campaign)
    return campaign


# --- CLI: pack a folder into a bundle .zip -----------------------------------

def pack_folder(src_dir: str, out_zip: str) -> None:
    """Zip a bundle source folder (must contain bundle.json) into out_zip."""
    manifest_path = os.path.join(src_dir, MANIFEST_NAME)
    if not os.path.isfile(manifest_path):
        raise SystemExit(f"No {MANIFEST_NAME} in {src_dir}")
    with open(manifest_path, encoding="utf-8") as fh:
        json.load(fh)  # validate JSON early
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(src_dir):
            for fn in sorted(files):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, src_dir).replace(os.sep, "/")
                zf.write(full, rel)
    print(f"Wrote {out_zip}")


def _cli() -> None:
    import argparse

    p = argparse.ArgumentParser(prog="python -m app.bundle", description="GameTable bundle tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    pk = sub.add_parser("pack", help="zip a bundle source folder into a .zip")
    pk.add_argument("src_dir")
    pk.add_argument("out_zip")
    args = p.parse_args()
    if args.cmd == "pack":
        pack_folder(args.src_dir, args.out_zip)


if __name__ == "__main__":
    _cli()
