"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import DicePanel from "../../../components/DicePanel";
import { api, mediaUrl } from "../../../lib/api";
import type { Creature, DiceRoll, GalleryImage, GameMap, Token, Viewer } from "../../../lib/types";
import { playerSocketUrl, useWS, type WSMessage } from "../../../lib/useWS";

const TableCanvas = dynamic(() => import("../../../components/TableCanvas"), { ssr: false });

function upsert<T extends { id: string }>(list: T[], item: T): T[] {
  const i = list.findIndex((x) => x.id === item.id);
  if (i === -1) return [...list, item];
  const copy = [...list];
  copy[i] = item;
  return copy;
}

export default function PlayerPage() {
  const { token } = useParams<{ token: string }>();

  const [error, setError] = useState<string | null>(null);
  const [campaignName, setCampaignName] = useState("");
  const [map, setMap] = useState<GameMap | null>(null);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [activeImage, setActiveImage] = useState<GalleryImage | null>(null);
  const [seatId, setSeatId] = useState<string | null>(null);
  const [rolls, setRolls] = useState<DiceRoll[]>([]);
  const [view, setView] = useState<"map" | "image">("map");
  const [detail, setDetail] = useState<Creature | null>(null);
  const [playerName, setPlayerName] = useState("Player");
  const [viewers, setViewers] = useState<Viewer[]>([]);

  const reloadState = useCallback(async () => {
    const s = await api.playerState(token);
    setCampaignName(s.campaign_name);
    setMap(s.active_map);
    setTokens(s.tokens);
    setActiveImage(s.active_image);
    setSeatId(s.seat_id);
  }, [token]);

  const onMessage = useCallback((msg: WSMessage) => {
    switch (msg.type) {
      case "state":
        setMap((msg.map as GameMap | null) ?? null);
        setTokens((msg.tokens as Token[]) ?? []);
        setActiveImage((msg.active_image as GalleryImage | null) ?? null);
        break;
      case "presence":
        setViewers((msg.viewers as Viewer[]) ?? []);
        break;
      case "token_upsert":
      case "token_move":
        setTokens((prev) => upsert(prev, msg.token as Token));
        break;
      case "token_delete":
        setTokens((prev) => prev.filter((t) => t.id !== msg.token_id));
        break;
      case "dice_roll":
        setRolls((prev) => [msg.roll as DiceRoll, ...prev]);
        break;
      case "fog":
        setMap((m) => (m && m.id === msg.map_id ? { ...m, fog: msg.fog as GameMap["fog"] } : m));
        break;
      case "active_image":
        reloadState();
        setView(msg.image_id ? "image" : "map");
        break;
      case "active_map":
        reloadState();
        break;
    }
  }, [reloadState]);

  const { send } = useWS(playerSocketUrl(token), onMessage);

  useEffect(() => {
    (async () => {
      try {
        await reloadState();
        setRolls(await api.playerDiceLog(token));
      } catch (e) {
        setError(e instanceof Error ? e.message : "This link is invalid or expired.");
      }
    })();
  }, [token, reloadState]);

  // Announce the player's chosen name to the table.
  useEffect(() => {
    send({ type: "presence", name: playerName });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerName]);

  const canMove = (t: Token) => !!seatId && t.owner_seat_id === seatId;

  async function onTokenClick(t: Token) {
    if (!t.creature_id) return;
    try {
      setDetail(await api.playerCreature(token, t.creature_id));
    } catch {
      /* no public info */
    }
  }

  if (error) return <main style={{ display: "grid", placeItems: "center", height: "100vh", color: "#ffb4b4" }}>{error}</main>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 280px", height: "100vh" }}>
      <main style={{ position: "relative", background: "#0c0e14" }}>
        <div style={toolbar}>
          <strong style={{ marginRight: 8 }}>{campaignName}</strong>
          <button onClick={() => setView("map")} style={{ ...toolBtn, background: view === "map" ? "#3b5bdb" : "#232838" }}>Map</button>
          <button
            onClick={() => setView("image")}
            disabled={!activeImage}
            style={{ ...toolBtn, background: view === "image" ? "#3b5bdb" : "#232838", opacity: activeImage ? 1 : 0.5 }}
          >
            Handout{activeImage ? " •" : ""}
          </button>
        </div>

        {view === "image" && activeImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={mediaUrl(activeImage.image_path) ?? ""} alt={activeImage.name} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
        ) : (
          <TableCanvas
            map={map}
            tokens={tokens}
            isDM={false}
            canMoveToken={canMove}
            onTokenMove={(id, x, y) => send({ type: "token_move", token_id: id, x, y })}
            onTokenClick={onTokenClick}
          />
        )}

        {detail && (
          <div style={modalWrap} onClick={() => setDetail(null)}>
            <div style={modal} onClick={(e) => e.stopPropagation()}>
              <button onClick={() => setDetail(null)} style={{ ...toolBtn, float: "right" }}>✕</button>
              <h2 style={{ marginTop: 0 }}>{detail.name}</h2>
              {detail.display_image_path && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={mediaUrl(detail.display_image_path) ?? ""} alt={detail.name} style={{ maxWidth: "100%", borderRadius: 8 }} />
              )}
              {detail.public_stats && <p style={{ whiteSpace: "pre-wrap", color: "#d4d8e0" }}>{detail.public_stats}</p>}
            </div>
          </div>
        )}
      </main>

      <aside style={{ background: "#13161d", borderLeft: "1px solid #222834", padding: 14, overflowY: "auto" }}>
        <h3 style={label}>You</h3>
        <input value={playerName} onChange={(e) => setPlayerName(e.target.value)} style={input} placeholder="Your name" />

        <h3 style={{ ...label, marginTop: 18 }}>At the table ({viewers.length})</h3>
        {viewers.map((v, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginBottom: 2 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: v.color, display: "inline-block" }} />
            {v.name}
            {v.is_dm && <span style={{ color: "#f0c060" }}> (DM)</span>}
          </div>
        ))}

        <h3 style={{ ...label, marginTop: 18 }}>Dice</h3>
        <DicePanel rolls={rolls} onRoll={(f, v) => api.playerRoll(token, f, v, playerName)} />
      </aside>
    </div>
  );
}

const toolbar: React.CSSProperties = { position: "absolute", top: 10, left: 10, zIndex: 5, display: "flex", gap: 8, alignItems: "center" };
const toolBtn: React.CSSProperties = { background: "#232838", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "7px 11px", cursor: "pointer", fontSize: 13 };
const label: React.CSSProperties = { fontSize: 12, textTransform: "uppercase", color: "#7b8494", letterSpacing: 0.5 };
const input: React.CSSProperties = { width: "100%", boxSizing: "border-box", background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 6, padding: "8px 10px" };
const modalWrap: React.CSSProperties = { position: "absolute", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center", zIndex: 10, padding: 20 };
const modal: React.CSSProperties = { background: "#171a22", border: "1px solid #2a2f3c", borderRadius: 12, padding: 20, maxWidth: 480, maxHeight: "80vh", overflowY: "auto" };
