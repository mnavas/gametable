// Mirrors the backend Pydantic schemas (app/schemas.py).

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_admin: boolean;
}

export interface Campaign {
  id: string;
  name: string;
  description: string;
  active_map_id: string | null;
  active_image_id: string | null;
  archived_at: string | null;
  created_at: string;
}

export interface FogState {
  revealed?: FogShape[];
  hidden?: FogShape[];
}

export interface FogShape {
  type: "rect";
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface GameMap {
  id: string;
  campaign_id?: string;
  name: string;
  image_path: string;
  width: number;
  height: number;
  grid_type: string;
  grid_size: number;
  grid_offset_x: number;
  grid_offset_y: number;
  grid_color: string;
  unit_per_cell: number;
  fog: FogState;
  sort_order?: number;
}

export interface Token {
  id: string;
  map_id?: string;
  creature_id: string | null;
  owner_seat_id: string | null;
  label: string;
  x: number;
  y: number;
  size: number;
  rotation: number;
  color: string;
  border_color: string | null;
  hidden_from_players?: boolean;
  locked?: boolean;
  z_index: number;
}

export interface Creature {
  id: string;
  name: string;
  type: string;
  token_image_path: string | null;
  display_image_path: string | null;
  public_stats: string;
  hidden_stats?: string;
  hidden_image_path?: string | null;
  visibility?: string;
}

export interface CreaturePublic {
  id: string;
  name: string;
  type: string;
  token_image_path: string | null;
  display_image_path: string | null;
  public_stats: string;
}

export interface DiceRoll {
  id: string;
  roller_type: string;
  roller_name: string;
  formula: string;
  detail: { rolls: number[]; modifier: number; total: number; [k: string]: unknown };
  total: number;
  visibility: string;
  created_at: string;
}

export interface ShareLink {
  id: string;
  token: string;
  label: string;
  kind: string;
  seat_id: string | null;
  revoked: boolean;
  expires_at: string | null;
  created_at: string;
}

export interface GalleryImage {
  id: string;
  name: string;
  image_path: string;
  is_shared: boolean;
  created_at: string;
}

export interface PlayerState {
  campaign_name: string;
  active_map: GameMap | null;
  tokens: Token[];
  active_image: GalleryImage | null;
  seat_id: string | null;
}
