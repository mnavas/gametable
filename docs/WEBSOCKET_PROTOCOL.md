# GameTable — Realtime WebSocket Protocol (draft)

Live table state syncs over WebSocket. The **server is authoritative and the
permission gate**: it validates every inbound message and fans out to each
connection only what that role may see. Hidden tokens, hidden fog, and private
rolls are filtered *per connection* — a player's socket never receives them.

## Connections

| Endpoint | Auth | Trust |
|---|---|---|
| `GET /ws/dm?campaign_id=<uuid>&token=<jwt>` | DM JWT (query param) | full |
| `GET /ws/player?share_token=<token>` | Share token | public events only |

Close codes: `4401` bad JWT · `4403` not the owner · `4404` bad share link ·
`4410` expired link.

All messages are JSON objects with a `type` field.

## Client → Server

| type | Sender | Payload | Notes |
|---|---|---|---|
| `ping` | DM, player | `{x, y}` | transient pointer ping |
| `token_move` | DM, player | `{token_id, x, y}` | player may move only `owner_seat_id == self` and not `locked` |
| `token_create` | DM | `{map_id, creature_id?, x, y, ...}` | DM only |
| `token_update` | DM | `{token_id, ...props}` | size/rotation/label/hidden/locked |
| `token_delete` | DM | `{token_id}` | DM only |
| `fog_update` | DM | `{map_id, op, shape}` | op = `reveal` \| `hide`; DM only |
| `active_map` | DM | `{map_id}` | switch the scene players see |
| `active_image` | DM | `{image_id\|null}` | push/clear a gallery handout |
| `player_roll` | player | `{formula, visibility}` | visibility = `public` \| `private` |
| `presence` | DM, player | `{name, color}` | join/update seat presence |

Any message a role isn't allowed to send is rejected (and ignored), never applied.

## Server → Client

| type | Sent to | Payload |
|---|---|---|
| `state` | on connect | full current snapshot (role-filtered: DM gets `MapDM`+all tokens; player gets `MapPublic`+visible tokens) |
| `ping` | all | `{x, y}` |
| `token_move` | all* | `{token_id, x, y}` — *DM-only if the token is hidden |
| `token_upsert` | all* | role-filtered token (`TokenDM` vs `TokenPublic`); hidden tokens → DM only |
| `token_delete` | all | `{token_id}` |
| `fog` | all | DM gets full shapes; players get only the **revealed** regions |
| `active_map` | all | `{map_id}` |
| `active_image` | all | `{image_id\|null}` |
| `dice_roll` | all* | `{roll: DiceRollOut}` — *private rolls go to DM connections only |
| `presence` | all | `{seats: [...], viewers: [...]}` |

## Enforcement rules (non-negotiable)

1. **Never serialize hidden fields to a player.** Use `*Public` schemas for every
   player-bound message (`CreaturePublic`, `TokenPublic`, `MapPublic`).
2. **Hidden tokens / hidden fog** are omitted from player payloads entirely, not
   merely flagged.
3. **Private (silent) rolls** broadcast with `dm_only=True`.
4. **Player-originated writes** are authorized server-side (own token, not locked)
   before persist + rebroadcast.
5. The **snapshot on connect** is built with the same role filter as live events,
   so a reconnecting player can't see more than they could live.

> Transport implemented in `backend/app/routers/ws.py`; fan-out + filtering in
> `backend/app/realtime.py`. Handlers marked `TODO` there are filled as the
> maps/tokens/creatures routers land.
