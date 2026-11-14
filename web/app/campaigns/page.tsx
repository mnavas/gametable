"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, getToken, setToken } from "../../lib/api";
import type { Campaign, User } from "../../lib/types";

export default function CampaignsPage() {
  const router = useRouter();
  const [me, setMe] = useState<User | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!getToken()) {
      router.push("/login");
      return;
    }
    (async () => {
      try {
        setMe(await api.me());
        setCampaigns(await api.listCampaigns());
      } catch {
        setToken(null);
        router.push("/login");
      } finally {
        setLoading(false);
      }
    })();
  }, [router]);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const c = await api.createCampaign(name.trim());
    setCampaigns((prev) => [c, ...prev]);
    setName("");
  };

  const onImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = ""; // allow re-selecting the same file
    if (!file) return;
    setError(null);
    setBusy("import");
    try {
      const c = await api.importBundle(file);
      setCampaigns((prev) => [c, ...prev]);
      router.push(`/campaigns/${c.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(null);
    }
  };

  const onExport = async (id: string) => {
    setError(null);
    setBusy(`export:${id}`);
    try {
      await api.exportBundle(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    } finally {
      setBusy(null);
    }
  };

  const logout = () => {
    setToken(null);
    router.push("/login");
  };

  if (loading) return <main style={{ padding: 40 }}>Loading…</main>;

  return (
    <main style={{ maxWidth: 820, margin: "0 auto", padding: "2rem 1.5rem" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>🎲 Campaigns</h1>
        <div style={{ color: "#9aa0ad", fontSize: 14 }}>
          {me?.display_name} · <button onClick={logout} style={linkBtn}>Log out</button>
        </div>
      </header>

      <div style={{ display: "flex", gap: 8, margin: "1.5rem 0", flexWrap: "wrap" }}>
        <form onSubmit={create} style={{ display: "flex", gap: 8, flex: 1, minWidth: 260 }}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New campaign name" style={{ ...input, flex: 1 }} />
          <button style={primary}>Create</button>
        </form>
        <input ref={fileRef} type="file" accept=".zip,application/zip" onChange={onImportFile} style={{ display: "none" }} />
        <button onClick={() => fileRef.current?.click()} disabled={busy === "import"} style={secondary} title="Import a .zip campaign bundle">
          {busy === "import" ? "Importing…" : "⬆ Import bundle"}
        </button>
      </div>

      <p style={{ color: "#6b7280", fontSize: 12, marginTop: -8 }}>
        Build a campaign at home, export it as a .zip, and import it anywhere — try the free{" "}
        <em>Sunless Shrine</em> one-shot from the repo&apos;s <code>content/adventures</code> folder.
      </p>

      {error && <p style={{ color: "#f87171", fontSize: 13 }}>{error}</p>}

      {campaigns.length === 0 && <p style={{ color: "#9aa0ad" }}>No campaigns yet. Create your first above, or import a bundle.</p>}
      <div style={{ display: "grid", gap: 12 }}>
        {campaigns.map((c) => (
          <div key={c.id} style={{ display: "flex", alignItems: "stretch", gap: 8 }}>
            <Link href={`/campaigns/${c.id}`} style={{ ...cardLink, flex: 1 }}>
              <strong style={{ fontSize: 17 }}>{c.name}</strong>
              <div style={{ color: "#9aa0ad", fontSize: 13 }}>
                {c.description || "No description"} · created {new Date(c.created_at).toLocaleDateString()}
              </div>
            </Link>
            <button
              onClick={() => onExport(c.id)}
              disabled={busy === `export:${c.id}`}
              style={exportBtn}
              title="Export this campaign as a .zip bundle"
            >
              {busy === `export:${c.id}` ? "…" : "⬇ Export"}
            </button>
          </div>
        ))}
      </div>
    </main>
  );
}

const input: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 8, padding: "10px 12px" };
const primary: React.CSSProperties = { background: "#3b5bdb", color: "#fff", border: "none", borderRadius: 8, padding: "10px 16px", cursor: "pointer" };
const secondary: React.CSSProperties = { background: "#232838", color: "#e8e8ea", border: "1px solid #2f3647", borderRadius: 8, padding: "10px 16px", cursor: "pointer" };
const exportBtn: React.CSSProperties = { background: "#171a22", color: "#9aa0ad", border: "1px solid #242a36", borderRadius: 10, padding: "0 14px", cursor: "pointer", fontSize: 13, whiteSpace: "nowrap" };
const cardLink: React.CSSProperties = { display: "block", background: "#171a22", border: "1px solid #242a36", borderRadius: 10, padding: "14px 16px", color: "#e8e8ea", textDecoration: "none" };
const linkBtn: React.CSSProperties = { background: "none", border: "none", color: "#7aa2ff", cursor: "pointer", fontSize: 14 };
