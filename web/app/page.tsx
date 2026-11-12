"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { getToken } from "../lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    router.replace(getToken() ? "/campaigns" : "/login");
  }, [router]);
  return <main style={{ display: "grid", placeItems: "center", height: "100vh", color: "#9aa0ad" }}>🎲 Loading GameTable…</main>;
}
