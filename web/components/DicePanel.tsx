"use client";

import { useState } from "react";
import type { DiceRoll } from "../lib/types";

const QUICK = ["d20", "d12", "d10", "d8", "d6", "d4", "d100"];

interface Props {
  rolls: DiceRoll[];
  onRoll: (formula: string, visibility: "public" | "private") => void;
}

export default function DicePanel({ rolls, onRoll }: Props) {
  const [formula, setFormula] = useState("1d20");

  const roll = (vis: "public" | "private") => {
    const f = formula.trim();
    if (f) onRoll(f, vis);
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 8 }}>
        {QUICK.map((d) => (
          <button key={d} onClick={() => setFormula(d)} style={chip}>
            {d}
          </button>
        ))}
      </div>
      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
        <input
          value={formula}
          onChange={(e) => setFormula(e.target.value)}
          placeholder="2d6+3"
          style={{ ...input, flex: 1 }}
          onKeyDown={(e) => e.key === "Enter" && roll("public")}
        />
        <button onClick={() => roll("public")} style={btnPrimary}>
          Roll
        </button>
        <button onClick={() => roll("private")} style={btn} title="Only you (and the DM) see this">
          🤫
        </button>
      </div>
      <div style={{ maxHeight: 220, overflowY: "auto", fontSize: 13 }}>
        {rolls.length === 0 && <div style={{ color: "#6b7280" }}>No rolls yet.</div>}
        {rolls.map((r) => (
          <div key={r.id} style={{ padding: "6px 8px", borderBottom: "1px solid #1f2430" }}>
            <strong>{r.roller_name}</strong> {r.formula}{" "}
            {r.visibility === "private" && <span title="private">🤫</span>}
            <span style={{ float: "right", fontWeight: 700 }}>{r.total}</span>
            <div style={{ color: "#8b93a3", fontSize: 11 }}>
              [{r.detail?.rolls?.join(", ")}]
              {r.detail?.modifier ? ` ${r.detail.modifier > 0 ? "+" : ""}${r.detail.modifier}` : ""}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const input: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 6, padding: "6px 8px" };
const btn: React.CSSProperties = { background: "#232838", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 6, padding: "6px 10px", cursor: "pointer" };
const btnPrimary: React.CSSProperties = { ...btn, background: "#3b5bdb", borderColor: "#3b5bdb" };
const chip: React.CSSProperties = { ...btn, padding: "4px 8px", fontSize: 12 };
