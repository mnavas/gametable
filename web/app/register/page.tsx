"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import { api, setToken } from "../../lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.register(email, password, displayName);
      setToken(res.access_token);
      router.push("/campaigns");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main style={wrap}>
      <form onSubmit={submit} style={card}>
        <h1 style={{ marginTop: 0 }}>🎲 Create your DM account</h1>
        {error && <div style={errBox}>{error}</div>}
        <input style={input} placeholder="Display name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
        <input style={input} type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input style={input} type="password" placeholder="Password (min 8 chars)" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} required />
        <button style={primary} disabled={busy}>{busy ? "…" : "Create account"}</button>
        <p style={{ fontSize: 13, color: "#9aa0ad" }}>
          Have an account? <Link href="/login" style={{ color: "#7aa2ff" }}>Sign in</Link>
        </p>
      </form>
    </main>
  );
}

const wrap: React.CSSProperties = { minHeight: "100vh", display: "grid", placeItems: "center", padding: "1rem" };
const card: React.CSSProperties = { width: "min(360px, 100%)", display: "flex", flexDirection: "column", gap: 10, background: "#171a22", padding: 24, borderRadius: 12, border: "1px solid #242a36" };
const input: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 8, padding: "10px 12px", fontSize: 15 };
const primary: React.CSSProperties = { background: "#3b5bdb", color: "#fff", border: "none", borderRadius: 8, padding: "11px", fontSize: 15, cursor: "pointer" };
const errBox: React.CSSProperties = { background: "#3a1d24", color: "#ffb4b4", padding: "8px 12px", borderRadius: 8, fontSize: 13 };
