"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import DicePanel from "../../../components/DicePanel";
import { api, getToken, mediaUrl } from "../../../lib/api";
import type { Campaign, Creature, DiceRoll, GalleryImage, GameMap, Token } from "../../../lib/types";
import { dmSocketUrl, useWS, type WSMessage } from "../../../lib/useWS";

const TableCanvas = dynamic(() => import("../../../components/TableCanvas"), { ssr: false });

function upsert<T extends { id: string }>(list: T[], item: T): T[] {
  const i = list.findIndex((x) => x.id === item.id);
  if (i === -1) return [...list, item];
  const copy = [...list];
  copy[i] = item;
  return copy;
}

function readImageSize(file: File): Promise<{ w: number; h: number }> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = () => resolve({ w: 0, h: 0 });
    img.src = URL.createObjectURL(file);
  });
}

export default function DMSessionPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const campaignId = params.id;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [maps, setMaps] = useState<GameMap[]>([]);
  const [activeMap, setActiveMap] = useState<GameMap | null>(null);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [creatures, setCreatures] = useState<Creature[]>([]);
  const [gallery, setGallery] = useState<GalleryImage[]>([]);
  const [rolls, setRolls] = useState<DiceRoll[]>([]);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [fogMode, setFogMode] = useState(false);

  const creatureById = useMemo(() => new Map(creatures.map((c) => [c.id, c])), [creatures]);
  const jwt = getToken();

  // Live sync.
  const onMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case "token_upsert":
      case "token_move": {
        const t = msg.token as Token;
        setActiveMap((m) => {
          if (m && (!t.map_id || t.map_id === m.id)) setTokens((prev) => upsert(prev, t));
          return m;
        });
        break;
      }
      case "token_delete":
        setTokens((prev) => prev.filter((t) => t.id !== msg.token_id));
        break;
      case "dice_roll":
        setRolls((prev) => [msg.roll as DiceRoll, ...prev]);
        break;
      case "fog":
        setActiveMap((m) => (m && m.id === msg.map_id ? { ...m, fog: msg.fog as GameMap["fog"] } : m));
        break;
    }
  }, []);
  useWS(jwt ? dmSocketUrl(campaignId, jwt) : null, onMessage);

  // Initial load.
  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    (async () => {
      try {
        const [c, ms, cr, gal, dice] = await Promise.all([
          api.getCampaign(campaignId),
          api.listMaps(campaignId),
          api.listCreatures(campaignId),
          api.listGallery(campaignId),
          api.dmDiceLog(campaignId),
        ]);
        setCampaign(c);
        setMaps(ms);
        setCreatures(cr);
        setGallery(gal);
        setRolls(dice);
        const am = ms.find((m) => m.id === c.active_map_id) ?? null;
        if (am) await selectMap(am);
      } catch {
        router.push("/campaigns");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [campaignId]);

  async function selectMap(m: GameMap) {
    setActiveMap(m);
    setTokens(await api.listTokens(m.id));
    const c = await api.updateCampaign(campaignId, { active_map_id: m.id });
    setCampaign(c);
  }

  async function onUploadMap(file: File) {
    const { w, h } = await readImageSize(file);
    const m = await api.uploadMap(campaignId, file.name.replace(/\.[^.]+$/, ""), file, w, h);
    setMaps((prev) => [...prev, m]);
    if (!activeMap) await selectMap(m);
  }

  async function addToken(cr: Creature) {
    if (!activeMap) return;
    const t = await api.createToken(activeMap.id, {
      creature_id: cr.id,
      label: cr.name,
      x: (activeMap.width || 600) / 2,
      y: (activeMap.height || 600) / 2,
      size: 1,
      color: "#6b7bd6",
    });
    setTokens((prev) => upsert(prev, t));
  }

  async function onTokenMove(id: string, x: number, y: number) {
    setTokens((prev) => prev.map((t) => (t.id === id ? { ...t, x, y } : t)));
    await api.updateToken(id, { x, y });
  }

  async function toggleHidden(t: Token) {
    const upd = await api.updateToken(t.id, { hidden_from_players: !t.hidden_from_players });
    setTokens((prev) => upsert(prev, upd));
  }

  async function onFogRect(x: number, y: number, w: number, h: number) {
    if (!activeMap || w < 2 || h < 2) return;
    const m = await api.fog(activeMap.id, "reveal", { type: "rect", x, y, w, h });
    setActiveMap(m);
  }

  async function resetFog() {
    if (!activeMap) return;
    setActiveMap(await api.fog(activeMap.id, "reset"));
  }

  async function makeShareLink() {
    const link = await api.createShareLink(campaignId, "Table link");
    setShareUrl(`${window.location.origin}/play/${link.token}`);
  }

  async function pushImage(img: GalleryImage) {
    if (img.is_shared) {
      await api.unshareImage(campaignId, img.id);
      setGallery((prev) => prev.map((g) => ({ ...g, is_shared: false })));
    } else {
      await api.shareImage(campaignId, img.id);
      setGallery((prev) => prev.map((g) => ({ ...g, is_shared: g.id === img.id })));
    }
  }

  if (!campaign) return <main style={{ padding: 40 }}>Loading…</main>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr 300px", height: "100vh" }}>
      {/* Left: maps, creatures, gallery */}
      <aside style={side}>
        <Link href="/campaigns" style={{ color: "#7aa2ff", fontSize: 13 }}>← Campaigns</Link>
        <h2 style={{ fontSize: 18, margin: "8px 0" }}>{campaign.name}</h2>

        <Section title="Maps">
          <FileButton label="＋ Upload map" accept="image/*" onFile={onUploadMap} />
          {maps.map((m) => (
            <button key={m.id} onClick={() => selectMap(m)} style={{ ...rowBtn, fontWeight: activeMap?.id === m.id ? 700 : 400 }}>
              {m.name}
            </button>
          ))}
        </Section>

        <Section title="Creatures">
          <CreatureCreator campaignId={campaignId} onCreated={(c) => setCreatures((p) => [...p, c])} />
          {creatures.map((cr) => (
            <div key={cr.id} style={rowBtn}>
              <span>{cr.name}</span>
              <button onClick={() => addToken(cr)} disabled={!activeMap} style={miniBtn} title="Place on map">
                ＋
              </button>
            </div>
          ))}
        </Section>

        <Section title="Gallery">
          <FileButton
            label="＋ Upload image"
            accept="image/*"
            onFile={async (f) => {
              const img = await api.uploadGallery(campaignId, f.name, f);
              setGallery((p) => [img, ...p]);
            }}
          />
          {gallery.map((g) => (
            <div key={g.id} style={rowBtn}>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{g.name}</span>
              <button onClick={() => pushImage(g)} style={{ ...miniBtn, background: g.is_shared ? "#3b5bdb" : "#232838" }}>
                {g.is_shared ? "Showing" : "Show"}
              </button>
            </div>
          ))}
        </Section>
      </aside>

      {/* Center: canvas + toolbar */}
      <main style={{ position: "relative", background: "#0c0e14" }}>
        <div style={toolbar}>
          <button onClick={() => setFogMode((v) => !v)} style={{ ...toolBtn, background: fogMode ? "#3b5bdb" : "#232838" }}>
            {fogMode ? "Fog: reveal (drag)" : "Fog tool"}
          </button>
          <button onClick={resetFog} style={toolBtn}>Reset fog</button>
          <button onClick={makeShareLink} style={toolBtn}>Share link</button>
          {shareUrl && (
            <span style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input readOnly value={shareUrl} style={{ ...toolInput, width: 260 }} onFocus={(e) => e.target.select()} />
              <button style={toolBtn} onClick={() => navigator.clipboard?.writeText(shareUrl)}>Copy</button>
            </span>
          )}
        </div>
        {activeMap ? (
          <TableCanvas
            map={activeMap}
            tokens={tokens}
            isDM
            fogMode={fogMode}
            tokenImage={(t) => (t.creature_id ? creatureById.get(t.creature_id)?.token_image_path ?? null : null)}
            canMoveToken={() => !fogMode}
            onTokenMove={onTokenMove}
            onTokenClick={(t) => toggleHidden(t)}
            onFogRect={onFogRect}
          />
        ) : (
          <div style={{ display: "grid", placeItems: "center", height: "100%", color: "#6b7280" }}>
            Upload a map to begin. Click a token to hide/reveal it from players.
          </div>
        )}
      </main>

      {/* Right: dice */}
      <aside style={side}>
        <Section title="Dice">
          <DicePanel rolls={rolls} onRoll={(f, v) => api.dmRoll(campaignId, f, v)} />
        </Section>
        <p style={{ color: "#6b7280", fontSize: 12 }}>
          Private (🤫) rolls are shown only to you. Click a token on the map to toggle it hidden from players.
        </p>
      </aside>
    </div>
  );
}

// --- Small UI helpers -------------------------------------------------------

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <h3 style={{ fontSize: 12, textTransform: "uppercase", color: "#7b8494", letterSpacing: 0.5 }}>{title}</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>{children}</div>
    </div>
  );
}

function FileButton({ label, accept, onFile }: { label: string; accept: string; onFile: (f: File) => void }) {
  return (
    <label style={{ ...rowBtn, cursor: "pointer", justifyContent: "center" }}>
      {label}
      <input
        type="file"
        accept={accept}
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(f);
          e.target.value = "";
        }}
      />
    </label>
  );
}

function CreatureCreator({ campaignId, onCreated }: { campaignId: string; onCreated: (c: Creature) => void }) {
  const [name, setName] = useState("");
  const create = async () => {
    if (!name.trim()) return;
    const c = await api.createCreature(campaignId, { name: name.trim(), type: "creature", visibility: "campaign_public" });
    onCreated(c);
    setName("");
  };
  return (
    <div style={{ display: "flex", gap: 6 }}>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New creature" style={{ ...toolInput, flex: 1 }} onKeyDown={(e) => e.key === "Enter" && create()} />
      <button onClick={create} style={miniBtn}>＋</button>
    </div>
  );
}

const side: React.CSSProperties = { background: "#13161d", borderRight: "1px solid #222834", padding: 14, overflowY: "auto" };
const rowBtn: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", gap: 6, background: "#1b1f28", border: "1px solid #272d3a", color: "#e8e8ea", borderRadius: 7, padding: "8px 10px", fontSize: 14, cursor: "pointer", textAlign: "left" };
const miniBtn: React.CSSProperties = { background: "#232838", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 6, padding: "2px 8px", cursor: "pointer" };
const toolbar: React.CSSProperties = { position: "absolute", top: 10, left: 10, zIndex: 5, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" };
const toolBtn: React.CSSProperties = { background: "#232838", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "7px 11px", cursor: "pointer", fontSize: 13 };
const toolInput: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 6, padding: "6px 8px", fontSize: 13 };
