"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import DicePanel from "../../../components/DicePanel";
import { api, mediaUrl } from "../../../lib/api";
import type { Creature, DiceRoll, GalleryImage, GameMap, Note, Seat, SeatClaim, Token, Viewer } from "../../../lib/types";
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
  const [notes, setNotes] = useState<Note[]>([]);
  const [view, setView] = useState<"map" | "image" | "notes">("map");
  const [detail, setDetail] = useState<Creature | null>(null);
  const [playerName, setPlayerName] = useState("Player");
  const [viewers, setViewers] = useState<Viewer[]>([]);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [claim, setClaim] = useState<SeatClaim | null>(null);
  const [showPicker, setShowPicker] = useState(false);
  const claimRef = useRef<SeatClaim | null>(null);

  const seatStoreKey = `gametable_seat_${token}`;
  const storeClaim = useCallback((c: SeatClaim | null) => {
    claimRef.current = c;
    setClaim(c);
    try {
      if (c) window.localStorage.setItem(seatStoreKey, JSON.stringify(c));
      else window.localStorage.removeItem(seatStoreKey);
    } catch {
      /* private mode — in-memory only */
    }
  }, [seatStoreKey]);

  const reloadState = useCallback(async () => {
    const s = await api.playerState(token, claimRef.current?.claim_token);
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
      case "seats": {
        // Merge live claim state in; keep the thumbnails from the initial fetch.
        const incoming = (msg.seats as Seat[]) ?? [];
        setSeats((prev) => {
          const byId = new Map(prev.map((s) => [s.id, s]));
          return incoming.map((s) => ({ ...byId.get(s.id), ...s }));
        });
        break;
      }
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

  const { send } = useWS(playerSocketUrl(token, claim?.claim_token), onMessage);

  useEffect(() => {
    (async () => {
      // Restore a character this browser already claimed (survives refresh).
      try {
        const saved = window.localStorage.getItem(seatStoreKey);
        if (saved) {
          const c = JSON.parse(saved) as SeatClaim;
          claimRef.current = c;
          setClaim(c);
        }
      } catch {
        /* ignore */
      }
      try {
        await reloadState();
        setRolls(await api.playerDiceLog(token));
        try {
          setNotes(await api.playerNotes(token));
        } catch {
          /* notes are optional */
        }
        try {
          const ss = await api.playerSeats(token);
          setSeats(ss);
          // Offer the picker on arrival if there are characters and none is ours yet.
          if (ss.length > 0 && !claimRef.current) setShowPicker(true);
        } catch {
          /* seats are optional */
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "This link is invalid or expired.");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, reloadState]);

  async function pickSeat(seat: Seat) {
    if (seat.claimed) return;
    try {
      const c = await api.claimSeat(token, seat.id, playerName);
      storeClaim(c);
      setShowPicker(false);
      if (playerName === "Player") setPlayerName(c.name);
      await reloadState();
    } catch {
      // Someone grabbed it first — refresh the list so it shows as taken.
      try {
        setSeats(await api.playerSeats(token));
      } catch {
        /* ignore */
      }
    }
  }

  async function leaveSeat() {
    const c = claimRef.current;
    if (c) {
      try {
        await api.releaseSeat(token, c.claim_token);
      } catch {
        /* ignore */
      }
    }
    storeClaim(null);
    await reloadState();
    try {
      setSeats(await api.playerSeats(token));
    } catch {
      /* ignore */
    }
  }

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
          <button
            onClick={() => setView("notes")}
            disabled={notes.length === 0}
            style={{ ...toolBtn, background: view === "notes" ? "#3b5bdb" : "#232838", opacity: notes.length ? 1 : 0.5 }}
          >
            Notes{notes.length ? ` (${notes.length})` : ""}
          </button>
        </div>

        {view === "notes" ? (
          <div style={{ position: "absolute", inset: 0, overflowY: "auto", padding: "56px 24px 24px" }}>
            <div style={{ maxWidth: 680, margin: "0 auto" }}>
              {notes.map((n) => (
                <article key={n.id} style={{ marginBottom: 28 }}>
                  <h2 style={{ margin: "0 0 8px", color: "#e8e8ea" }}>{n.title}</h2>
                  <div style={{ whiteSpace: "pre-wrap", color: "#c4c9d4", lineHeight: 1.6 }}>{n.body}</div>
                </article>
              ))}
            </div>
          </div>
        ) : view === "image" && activeImage ? (
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

        {showPicker && (
          <div style={modalWrap} onClick={() => setShowPicker(false)}>
            <div style={{ ...modal, maxWidth: 540 }} onClick={(e) => e.stopPropagation()}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2 style={{ margin: 0 }}>Choose your character</h2>
                <button onClick={() => setShowPicker(false)} style={toolBtn}>✕</button>
              </div>
              <p style={{ color: "#9aa3b2", fontSize: 13, marginTop: 6 }}>
                Pick the hero you&apos;re playing. Once taken, a character is greyed out for everyone else.
              </p>
              <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
                {seats.map((s) => {
                  const mine = claim?.seat_id === s.id;
                  const taken = s.claimed && !mine;
                  return (
                    <button
                      key={s.id}
                      onClick={() => pickSeat(s)}
                      disabled={taken}
                      style={{
                        display: "flex", alignItems: "center", gap: 12, textAlign: "left",
                        background: mine ? "#1d2a24" : "#0f1218",
                        border: `1px solid ${mine ? "#3a6b55" : taken ? "#2a2f3c" : "#39507e"}`,
                        color: "#e8e8ea", borderRadius: 10, padding: "10px 12px",
                        cursor: taken ? "not-allowed" : "pointer", opacity: taken ? 0.55 : 1,
                      }}
                    >
                      {s.token_image_path ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={mediaUrl(s.token_image_path) ?? ""} alt={s.name} style={{ width: 44, height: 44, borderRadius: "50%", objectFit: "cover", border: `2px solid ${s.color}` }} />
                      ) : (
                        <span style={{ width: 44, height: 44, borderRadius: "50%", background: s.color, display: "inline-block" }} />
                      )}
                      <span style={{ flex: 1 }}>
                        <span style={{ display: "block", fontSize: 15, fontWeight: 600 }}>{s.name}</span>
                        <span style={{ fontSize: 12, color: taken ? "#c98b8b" : mine ? "#7fe0b0" : "#8a93a2" }}>
                          {mine ? "Yours" : taken ? `Taken${s.claimed_by ? ` by ${s.claimed_by}` : ""}` : "Available"}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </main>

      <aside style={{ background: "#13161d", borderLeft: "1px solid #222834", padding: 14, overflowY: "auto" }}>
        <h3 style={label}>You</h3>
        <input value={playerName} onChange={(e) => setPlayerName(e.target.value)} style={input} placeholder="Your name" />

        {seats.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <h3 style={label}>Your character</h3>
            {claim ? (
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: claim.color, display: "inline-block" }} />
                <span style={{ flex: 1, fontSize: 14 }}>{claim.name}</span>
                <button onClick={leaveSeat} style={{ ...toolBtn, fontSize: 12, padding: "5px 9px" }}>Leave</button>
              </div>
            ) : (
              <button onClick={() => setShowPicker(true)} style={{ ...toolBtn, width: "100%" }}>
                🎭 Pick a character
              </button>
            )}
          </div>
        )}

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
