"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export default function Home() {
  const [status, setStatus] = useState<string>("checking…");

  useEffect(() => {
    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((d) => setStatus(`${d.service} v${d.version} — ${d.status}`))
      .catch(() => setStatus("API unreachable"));
  }, []);

  return (
    <main style={{ maxWidth: 720, margin: "0 auto", padding: "4rem 1.5rem" }}>
      <h1 style={{ fontSize: "2.5rem", marginBottom: "0.25rem" }}>🎲 GameTable</h1>
      <p style={{ color: "#9aa0ad", marginTop: 0 }}>
        Self-hosted virtual tabletop for D&amp;D — scaffold stub.
      </p>
      <p style={{ marginTop: "2rem", padding: "0.75rem 1rem", background: "#1b1e27", borderRadius: 8 }}>
        API: <strong>{status}</strong>
      </p>
      <p style={{ color: "#9aa0ad", fontSize: "0.9rem" }}>
        Next: DM login, campaign dashboard, and the map canvas (PixiJS). See{" "}
        <code>REQUIREMENTS.md</code> and <code>docs/WEBSOCKET_PROTOCOL.md</code>.
      </p>
    </main>
  );
}
