// Typed REST client for the GameTable API.
import type {
  BestiaryEntry,
  Campaign,
  Creature,
  DiceRoll,
  GalleryImage,
  GameMap,
  Note,
  PlayerState,
  Seat,
  SeatClaim,
  ShareLink,
  Token,
  User,
} from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

const TOKEN_KEY = "gametable_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore storage errors (private mode etc.) */
  }
}

/** Resolve a stored media path (e.g. "/media/<cid>/<file>") to a full URL. */
export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  return path.startsWith("http") ? path : `${API_URL}${path}`;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, opts: RequestInit = {}, auth = true): Promise<T> {
  const headers = new Headers(opts.headers);
  if (auth) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }
  const isForm = opts.body instanceof FormData;
  if (!isForm && opts.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...opts, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail ?? detail;
    } catch {
      /* non-JSON error */
    }
    throw new ApiError(res.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

interface AuthResponse {
  access_token: string;
  user: User;
}

export const api = {
  // --- Auth ---
  async register(email: string, password: string, display_name: string): Promise<AuthResponse> {
    return request("/auth/register", { method: "POST", body: JSON.stringify({ email, password, display_name }) }, false);
  },
  async login(email: string, password: string): Promise<AuthResponse> {
    return request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }, false);
  },
  async me(): Promise<User> {
    return request("/auth/me");
  },

  // --- Campaigns ---
  listCampaigns: () => request<Campaign[]>("/campaigns"),
  createCampaign: (name: string, description = "") =>
    request<Campaign>("/campaigns", { method: "POST", body: JSON.stringify({ name, description }) }),
  getCampaign: (id: string) => request<Campaign>(`/campaigns/${id}`),
  updateCampaign: (id: string, data: Partial<Campaign>) =>
    request<Campaign>(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCampaign: (id: string) => request<void>(`/campaigns/${id}`, { method: "DELETE" }),

  // --- Bundles (export / import as a .zip) ---
  /** Download a campaign as a .zip bundle (authorized fetch -> browser save). */
  async exportBundle(campaignId: string): Promise<void> {
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`${API_URL}/campaigns/${campaignId}/export`, { headers });
    if (!res.ok) throw new ApiError(res.status, "Export failed");
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition") ?? "";
    const m = cd.match(/filename="?([^"]+)"?/);
    const fname = m ? m[1] : "campaign.gtbundle.zip";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = fname;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
  /** Import a .zip bundle into a brand-new campaign. */
  importBundle: (file: File, name?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (name) fd.append("name", name);
    return request<Campaign>("/campaigns/import", { method: "POST", body: fd });
  },

  // --- Maps ---
  listMaps: (campaignId: string) => request<GameMap[]>(`/campaigns/${campaignId}/maps`),
  uploadMap: (campaignId: string, name: string, file: File, width = 0, height = 0) => {
    const fd = new FormData();
    fd.append("name", name);
    fd.append("file", file);
    fd.append("width", String(width));
    fd.append("height", String(height));
    return request<GameMap>(`/campaigns/${campaignId}/maps`, { method: "POST", body: fd });
  },
  updateMap: (mapId: string, data: Partial<GameMap>) =>
    request<GameMap>(`/maps/${mapId}`, { method: "PATCH", body: JSON.stringify(data) }),
  fog: (mapId: string, op: string, shape?: unknown) =>
    request<GameMap>(`/maps/${mapId}/fog`, { method: "POST", body: JSON.stringify({ op, shape }) }),

  // --- Tokens ---
  listTokens: (mapId: string) => request<Token[]>(`/maps/${mapId}/tokens`),
  createToken: (mapId: string, data: Partial<Token>) =>
    request<Token>(`/maps/${mapId}/tokens`, { method: "POST", body: JSON.stringify(data) }),
  updateToken: (tokenId: string, data: Partial<Token>) =>
    request<Token>(`/tokens/${tokenId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteToken: (tokenId: string) => request<void>(`/tokens/${tokenId}`, { method: "DELETE" }),

  // --- Creatures ---
  listCreatures: (campaignId: string) => request<Creature[]>(`/campaigns/${campaignId}/creatures`),
  createCreature: (campaignId: string, data: Partial<Creature>) =>
    request<Creature>(`/campaigns/${campaignId}/creatures`, { method: "POST", body: JSON.stringify(data) }),
  updateCreature: (creatureId: string, data: Partial<Creature>) =>
    request<Creature>(`/creatures/${creatureId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCreature: (creatureId: string) => request<void>(`/creatures/${creatureId}`, { method: "DELETE" }),
  uploadCreatureImage: (creatureId: string, kind: "token" | "display" | "hidden", file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<Creature>(`/creatures/${creatureId}/${kind}-image`, { method: "PUT", body: fd });
  },

  // --- Notes (DM-authored; hidden = DM-only, public = player handout) ---
  listNotes: (campaignId: string) => request<Note[]>(`/campaigns/${campaignId}/notes`),
  createNote: (campaignId: string, data: Partial<Note>) =>
    request<Note>(`/campaigns/${campaignId}/notes`, { method: "POST", body: JSON.stringify(data) }),
  updateNote: (campaignId: string, noteId: string, data: Partial<Note>) =>
    request<Note>(`/campaigns/${campaignId}/notes/${noteId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteNote: (campaignId: string, noteId: string) =>
    request<void>(`/campaigns/${campaignId}/notes/${noteId}`, { method: "DELETE" }),

  // --- Bestiary (cross-DM shared creature library) ---
  listBestiary: (q?: string) =>
    request<BestiaryEntry[]>(`/bestiary${q && q.trim() ? `?q=${encodeURIComponent(q.trim())}` : ""}`),
  copyFromBestiary: (creatureId: string, campaignId: string) =>
    request<Creature>(`/bestiary/${creatureId}/copy`, {
      method: "POST",
      body: JSON.stringify({ campaign_id: campaignId }),
    }),

  // --- Dice ---
  dmRoll: (campaignId: string, formula: string, visibility: string) =>
    request<DiceRoll>(`/campaigns/${campaignId}/roll`, { method: "POST", body: JSON.stringify({ formula, visibility }) }),
  dmDiceLog: (campaignId: string) => request<DiceRoll[]>(`/campaigns/${campaignId}/dice`),

  // --- Seats (DM view: who has claimed which character) ---
  listSeats: (campaignId: string) => request<Seat[]>(`/campaigns/${campaignId}/seats`),
  resetSeat: (campaignId: string, seatId: string) =>
    request<Seat>(`/campaigns/${campaignId}/seats/${seatId}/reset`, { method: "POST" }),

  // --- Share links ---
  listShareLinks: (campaignId: string) => request<ShareLink[]>(`/campaigns/${campaignId}/share-links`),
  createShareLink: (campaignId: string, label = "") =>
    request<ShareLink>(`/campaigns/${campaignId}/share-links`, { method: "POST", body: JSON.stringify({ label, kind: "shared" }) }),
  revokeShareLink: (campaignId: string, linkId: string) =>
    request<void>(`/campaigns/${campaignId}/share-links/${linkId}`, { method: "DELETE" }),

  // --- Gallery ---
  listGallery: (campaignId: string) => request<GalleryImage[]>(`/campaigns/${campaignId}/gallery`),
  uploadGallery: (campaignId: string, name: string, file: File) => {
    const fd = new FormData();
    fd.append("name", name);
    fd.append("file", file);
    return request<GalleryImage>(`/campaigns/${campaignId}/gallery`, { method: "POST", body: fd });
  },
  shareImage: (campaignId: string, imageId: string) =>
    request<GalleryImage>(`/campaigns/${campaignId}/gallery/${imageId}/share`, { method: "POST" }),
  unshareImage: (campaignId: string, imageId: string) =>
    request<void>(`/campaigns/${campaignId}/gallery/${imageId}/unshare`, { method: "POST" }),

  // --- Player (share-token scoped) ---
  playerState: (shareToken: string, claimToken?: string | null) =>
    request<PlayerState>(
      `/play/state?share_token=${encodeURIComponent(shareToken)}` +
        (claimToken ? `&claim_token=${encodeURIComponent(claimToken)}` : ""),
      {},
      false,
    ),
  // Seats: list the table's characters, claim one, or release it.
  playerSeats: (shareToken: string) =>
    request<Seat[]>(`/play/seats?share_token=${encodeURIComponent(shareToken)}`, {}, false),
  claimSeat: (shareToken: string, seatId: string, playerName: string) =>
    request<SeatClaim>(`/play/seats/${seatId}/claim?share_token=${encodeURIComponent(shareToken)}`, {
      method: "POST",
      body: JSON.stringify({ player_name: playerName }),
    }, false),
  releaseSeat: (shareToken: string, claimToken: string) =>
    request<{ ok: boolean }>(`/play/seats/release?share_token=${encodeURIComponent(shareToken)}`, {
      method: "POST",
      body: JSON.stringify({ claim_token: claimToken }),
    }, false),
  playerCreature: (shareToken: string, creatureId: string) =>
    request<Creature>(`/play/creatures/${creatureId}?share_token=${encodeURIComponent(shareToken)}`, {}, false),
  playerNotes: (shareToken: string) => request<Note[]>(`/play/notes?share_token=${encodeURIComponent(shareToken)}`, {}, false),
  playerDiceLog: (shareToken: string) => request<DiceRoll[]>(`/play/dice?share_token=${encodeURIComponent(shareToken)}`, {}, false),
  playerRoll: (shareToken: string, formula: string, visibility: string, player_name: string) =>
    request<DiceRoll>(`/play/roll?share_token=${encodeURIComponent(shareToken)}`, {
      method: "POST",
      body: JSON.stringify({ formula, visibility, player_name }),
    }, false),
};
