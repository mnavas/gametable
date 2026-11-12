"use client";

import { useEffect, useState } from "react";
import { API_URL, api, getToken, mediaUrl } from "../lib/api";
import type { Creature } from "../lib/types";

interface Props {
  creature: Creature;
  onChange: (c: Creature) => void;
  onClose: () => void;
  onDelete: (id: string) => void;
}

/** Loads a protected (DM-only) image by fetching with the auth header. */
function AuthImage({ path, alt }: { path: string; alt: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    let revoked: string | null = null;
    (async () => {
      try {
        const res = await fetch(`${API_URL}${path}`, { headers: { Authorization: `Bearer ${getToken()}` } });
        if (!res.ok) return;
        const blob = await res.blob();
        revoked = URL.createObjectURL(blob);
        setUrl(revoked);
      } catch {
        /* ignore */
      }
    })();
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [path]);
  if (!url) return <div style={thumbEmpty}>loading…</div>;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={url} alt={alt} style={thumb} />;
}

function ImageSlot({
  label,
  path,
  protectedAsset,
  onUpload,
}: {
  label: string;
  path: string | null | undefined;
  protectedAsset?: boolean;
  onUpload: (f: File) => void;
}) {
  return (
    <div style={{ textAlign: "center" }}>
      <div style={{ fontSize: 11, color: "#7b8494", marginBottom: 4 }}>{label}</div>
      {path ? (
        protectedAsset ? (
          <AuthImage path={path} alt={label} />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={mediaUrl(path) ?? ""} alt={label} style={thumb} />
        )
      ) : (
        <div style={thumbEmpty}>none</div>
      )}
      <label style={uploadBtn}>
        Upload
        <input
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = "";
          }}
        />
      </label>
    </div>
  );
}

export default function CreatureEditor({ creature, onChange, onClose, onDelete }: Props) {
  const [c, setC] = useState<Creature>(creature);
  const [saving, setSaving] = useState(false);
  useEffect(() => setC(creature), [creature]);

  const set = (patch: Partial<Creature>) => setC((prev) => ({ ...prev, ...patch }));

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.updateCreature(c.id, {
        name: c.name,
        type: c.type,
        visibility: c.visibility,
        public_stats: c.public_stats,
        hidden_stats: c.hidden_stats,
      });
      onChange(updated);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  const upload = async (kind: "token" | "display" | "hidden", f: File) => {
    const updated = await api.uploadCreatureImage(c.id, kind, f);
    setC(updated);
    onChange(updated);
  };

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>Edit creature</h2>
          <button onClick={onClose} style={ghost}>✕</button>
        </div>

        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <input value={c.name} onChange={(e) => set({ name: e.target.value })} placeholder="Name" style={{ ...input, flex: 1 }} />
          <select value={c.type} onChange={(e) => set({ type: e.target.value })} style={input}>
            <option value="creature">Creature</option>
            <option value="npc">NPC</option>
            <option value="player">Player</option>
          </select>
        </div>

        <label style={fieldLabel}>Visibility</label>
        <select value={c.visibility ?? "hidden"} onChange={(e) => set({ visibility: e.target.value })} style={{ ...input, width: "100%" }}>
          <option value="hidden">Hidden — DM only</option>
          <option value="campaign_public">Campaign public — players can see public content</option>
          <option value="server_shared">Server shared — add public content to the server bestiary</option>
        </select>

        <div style={{ display: "flex", gap: 14, justifyContent: "space-around", margin: "16px 0" }}>
          <ImageSlot label="Token (public)" path={c.token_image_path} onUpload={(f) => upload("token", f)} />
          <ImageSlot label="Display (public)" path={c.display_image_path} onUpload={(f) => upload("display", f)} />
          <ImageSlot label="Hidden (DM only)" path={c.hidden_image_path} protectedAsset onUpload={(f) => upload("hidden", f)} />
        </div>

        <label style={fieldLabel}>Public stats — players see this on click</label>
        <textarea value={c.public_stats} onChange={(e) => set({ public_stats: e.target.value })} style={textarea} rows={3} placeholder="AC, visible description…" />

        <label style={{ ...fieldLabel, color: "#e0a0a0" }}>Hidden stats — DM only 🔒</label>
        <textarea value={c.hidden_stats ?? ""} onChange={(e) => set({ hidden_stats: e.target.value })} style={{ ...textarea, borderColor: "#5a3a3a" }} rows={4} placeholder="HP, tactics, secret identity…" />

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
          <button onClick={() => { onDelete(c.id); onClose(); }} style={danger}>Delete</button>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={onClose} style={ghost}>Cancel</button>
            <button onClick={save} disabled={saving} style={primary}>{saving ? "…" : "Save"}</button>
          </div>
        </div>
      </div>
    </div>
  );
}

const overlay: React.CSSProperties = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center", zIndex: 50, padding: 20 };
const modal: React.CSSProperties = { background: "#171a22", border: "1px solid #2a2f3c", borderRadius: 12, padding: 22, width: "min(560px, 100%)", maxHeight: "90vh", overflowY: "auto" };
const input: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "8px 10px", fontSize: 14 };
const textarea: React.CSSProperties = { ...input, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "inherit" };
const fieldLabel: React.CSSProperties = { display: "block", fontSize: 12, color: "#7b8494", margin: "12px 0 4px" };
const thumb: React.CSSProperties = { width: 84, height: 84, objectFit: "cover", borderRadius: 8, border: "1px solid #2a2f3c" };
const thumbEmpty: React.CSSProperties = { width: 84, height: 84, display: "grid", placeItems: "center", borderRadius: 8, border: "1px dashed #2a2f3c", color: "#6b7280", fontSize: 11 };
const uploadBtn: React.CSSProperties = { display: "inline-block", marginTop: 6, fontSize: 12, color: "#7aa2ff", cursor: "pointer" };
const ghost: React.CSSProperties = { background: "#232838", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "7px 12px", cursor: "pointer" };
const primary: React.CSSProperties = { background: "#3b5bdb", border: "none", color: "#fff", borderRadius: 7, padding: "7px 16px", cursor: "pointer" };
const danger: React.CSSProperties = { background: "#3a1d24", border: "1px solid #5a3a3a", color: "#ffb4b4", borderRadius: 7, padding: "7px 12px", cursor: "pointer" };
