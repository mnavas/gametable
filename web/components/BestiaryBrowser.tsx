"use client";

import { useEffect, useState } from "react";
import { api, mediaUrl } from "../lib/api";
import type { BestiaryEntry, Creature } from "../lib/types";

interface Props {
  campaignId: string;
  onClose: () => void;
  onAdded: (c: Creature) => void;
}

/** Browse creatures other DMs have shared to the server, and copy one in. */
export default function BestiaryBrowser({ campaignId, onClose, onAdded }: Props) {
  const [q, setQ] = useState("");
  const [entries, setEntries] = useState<BestiaryEntry[] | null>(null);
  const [adding, setAdding] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const rows = await api.listBestiary(q);
        if (!cancelled) setEntries(rows);
      } catch {
        if (!cancelled) setError("Couldn't load the bestiary.");
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [q]);

  async function add(entry: BestiaryEntry) {
    setAdding(entry.id);
    try {
      const created = await api.copyFromBestiary(entry.id, campaignId);
      onAdded(created);
    } catch {
      setError("Couldn't add that creature.");
    } finally {
      setAdding(null);
    }
  }

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>📚 Shared bestiary</h2>
          <button onClick={onClose} style={ghost}>✕</button>
        </div>
        <p style={{ color: "#9aa3b2", fontSize: 13, margin: "6px 0 12px" }}>
          Creatures other DMs have shared. Add one to <strong>this campaign</strong> — you get the public
          content (name, stats, art); add your own secret stats afterward.
        </p>
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by name…"
          style={{ ...input, width: "100%", boxSizing: "border-box" }}
        />

        {error && <div style={{ color: "#ffb4b4", fontSize: 13, marginTop: 10 }}>{error}</div>}

        <div style={{ marginTop: 12, display: "grid", gap: 10 }}>
          {entries === null ? (
            <div style={{ color: "#6b7280", fontSize: 13 }}>Loading…</div>
          ) : entries.length === 0 ? (
            <div style={{ color: "#6b7280", fontSize: 13 }}>
              Nothing shared yet. Mark one of your creatures <em>Server shared</em> in its editor to add it here.
            </div>
          ) : (
            entries.map((e) => (
              <div key={e.id} style={card}>
                {e.token_image_path ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={mediaUrl(e.token_image_path) ?? ""} alt={e.name} style={avatar} />
                ) : (
                  <span style={{ ...avatar, display: "grid", placeItems: "center", background: "#2a2f3c", color: "#8a93a2" }}>
                    {e.name.slice(0, 1)}
                  </span>
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 15, fontWeight: 600 }}>
                    {e.name}
                    <span style={{ fontSize: 11, color: "#8a93a2", fontWeight: 400 }}> · {e.type}</span>
                    {e.mine && <span style={{ fontSize: 11, color: "#7fe0b0", fontWeight: 400 }}> · yours</span>}
                  </div>
                  {e.public_stats && (
                    <div style={{ fontSize: 12, color: "#9aa3b2", maxHeight: 34, overflow: "hidden" }}>
                      {e.public_stats}
                    </div>
                  )}
                  <div style={{ fontSize: 11, color: "#6b7280", marginTop: 2 }}>shared by {e.contributor}</div>
                </div>
                <button onClick={() => add(e)} disabled={adding === e.id} style={primary}>
                  {adding === e.id ? "…" : "Add"}
                </button>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

const overlay: React.CSSProperties = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "grid", placeItems: "center", zIndex: 50, padding: 20 };
const modal: React.CSSProperties = { background: "#171a22", border: "1px solid #2a2f3c", borderRadius: 12, padding: 22, width: "min(600px, 100%)", maxHeight: "90vh", overflowY: "auto" };
const input: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "8px 10px", fontSize: 14 };
const card: React.CSSProperties = { display: "flex", alignItems: "center", gap: 12, background: "#0f1218", border: "1px solid #272d3a", borderRadius: 10, padding: 10 };
const avatar: React.CSSProperties = { width: 46, height: 46, borderRadius: "50%", objectFit: "cover", border: "1px solid #2a2f3c", flexShrink: 0 };
const ghost: React.CSSProperties = { background: "#232838", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "7px 12px", cursor: "pointer" };
const primary: React.CSSProperties = { background: "#3b5bdb", border: "none", color: "#fff", borderRadius: 7, padding: "7px 14px", cursor: "pointer", flexShrink: 0 };
