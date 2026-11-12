"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, getToken, setToken } from "../../lib/api";
import type { Campaign, User } from "../../lib/types";

export default function CampaignsPage() {
  const router = useRouter();
  const [me, setMe] = useState<User | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);

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

      <form onSubmit={create} style={{ display: "flex", gap: 8, margin: "1.5rem 0" }}>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="New campaign name" style={{ ...input, flex: 1 }} />
        <button style={primary}>Create</button>
      </form>

      {campaigns.length === 0 && <p style={{ color: "#9aa0ad" }}>No campaigns yet. Create your first above.</p>}
      <div style={{ display: "grid", gap: 12 }}>
        {campaigns.map((c) => (
          <Link key={c.id} href={`/campaigns/${c.id}`} style={cardLink}>
            <strong style={{ fontSize: 17 }}>{c.name}</strong>
            <div style={{ color: "#9aa0ad", fontSize: 13 }}>
              {c.description || "No description"} · created {new Date(c.created_at).toLocaleDateString()}
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}

const input: React.CSSProperties = { background: "#0f1218", border: "1px solid #2a2f3c", color: "#e8e8ea", borderRadius: 8, padding: "10px 12px" };
const primary: React.CSSProperties = { background: "#3b5bdb", color: "#fff", border: "none", borderRadius: 8, padding: "10px 16px", cursor: "pointer" };
const cardLink: React.CSSProperties = { display: "block", background: "#171a22", border: "1px solid #242a36", borderRadius: 10, padding: "14px 16px", color: "#e8e8ea", textDecoration: "none" };
const linkBtn: React.CSSProperties = { background: "none", border: "none", color: "#7aa2ff", cursor: "pointer", fontSize: 14 };
