"use client";

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Note } from "../lib/types";

interface Props {
  campaignId: string;
  note: Note;
  onChange: (n: Note) => void;
  onClose: () => void;
  onDelete: (id: string) => void;
}

/** Read / edit a single campaign note, and flip it between DM-only and a player handout. */
export default function NotesEditor({ campaignId, note, onChange, onClose, onDelete }: Props) {
  const [n, setN] = useState<Note>(note);
  const [saving, setSaving] = useState(false);
  useEffect(() => setN(note), [note]);

  const set = (patch: Partial<Note>) => setN((prev) => ({ ...prev, ...patch }));
  const isPublic = (n.visibility ?? "hidden") === "public";

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.updateNote(campaignId, n.id, {
        title: n.title,
        body: n.body,
        visibility: n.visibility ?? "hidden",
      });
      onChange(updated);
      onClose();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={overlay} onClick={onClose}>
      <div style={modal} onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>Edit note</h2>
          <button onClick={onClose} style={ghost}>✕</button>
        </div>

        <input
          value={n.title}
          onChange={(e) => set({ title: e.target.value })}
          placeholder="Title"
          style={{ ...input, width: "100%", boxSizing: "border-box", marginTop: 12, fontWeight: 600 }}
        />

        <div style={{ display: "flex", gap: 8, margin: "12px 0" }}>
          <button
            onClick={() => set({ visibility: "hidden" })}
            style={{ ...toggle, ...(isPublic ? {} : toggleOn) }}
            title="Only you can read this"
          >
            🔒 DM-only
          </button>
          <button
            onClick={() => set({ visibility: "public" })}
            style={{ ...toggle, ...(isPublic ? toggleOnPublic : {}) }}
            title="Players can read this as a handout"
          >
            👁 Player handout
          </button>
        </div>

        <textarea
          value={n.body}
          onChange={(e) => set({ body: e.target.value })}
          style={textarea}
          rows={14}
          placeholder="Write freely — area descriptions, read-aloud text, tactics…"
        />

        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
          <button onClick={() => { onDelete(n.id); onClose(); }} style={danger}>Delete</button>
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
const modal: React.CSSProperties = { background: "#171a22", border: "1px solid #2a2f3c", borderRadius: 12, padding: 22, width: "min(620px, 100%)", maxHeight: "90vh", overflowY: "auto" };
const input: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "8px 10px", fontSize: 14 };
const textarea: React.CSSProperties = { ...input, width: "100%", boxSizing: "border-box", resize: "vertical", fontFamily: "inherit", lineHeight: 1.5 };
const ghost: React.CSSProperties = { background: "#232838", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 7, padding: "7px 12px", cursor: "pointer" };
const primary: React.CSSProperties = { background: "#3b5bdb", border: "none", color: "#fff", borderRadius: 7, padding: "7px 16px", cursor: "pointer" };
const danger: React.CSSProperties = { background: "#3a1d24", border: "1px solid #5a3a3a", color: "#ffb4b4", borderRadius: 7, padding: "7px 12px", cursor: "pointer" };
const toggle: React.CSSProperties = { flex: 1, background: "#0f1218", border: "1px solid #2a2f3c", color: "#9aa3b2", borderRadius: 7, padding: "8px 10px", cursor: "pointer", fontSize: 13 };
const toggleOn: React.CSSProperties = { background: "#2a2320", borderColor: "#6b5a3a", color: "#f0c060" };
const toggleOnPublic: React.CSSProperties = { background: "#1d2a24", borderColor: "#3a6b55", color: "#7fe0b0" };
