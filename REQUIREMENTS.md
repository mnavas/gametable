# GameTable — Self-Hosted Virtual Tabletop for D&D

> Working title. A self-hosted, multi-DM virtual tabletop (VTT) in the spirit of
> Owlbear Rodeo: run it on your own server at home or online, give each Dungeon
> Master their own account, and let players join a campaign through a shared link.

**Status:** Requirements / design draft
**Last updated:** 2026-11-12

---

## 1. Vision

GameTable is a lightweight, self-hostable VTT focused on the **in-session table
experience**: a map, tokens you can move, fog of war so players only see what the
DM reveals, and dice everyone can watch. It is not trying to be a rules engine or a
full character-sheet simulator (that's Foundry/Roll20 territory) — it's trying to be
the fast, clean shared table that Owlbear Rodeo nailed, but **self-hosted and
multi-DM** so a group can run their own server.

**Guiding principles**

- **Self-hosted first.** One binary / one `docker compose up`. No external SaaS
  dependency. Your maps, notes, and stats live on your server.
- **Multi-DM, secured.** Each DM registers an account; their campaigns, maps, and
  hidden notes are private to them. A server can host many DMs and groups.
- **DM controls visibility.** Everything defaults to hidden. The DM decides, per
  item, what players see — a map region, a token, an image, a stat block, a note.
- **Players need no account.** A player joins via a share link. Low friction:
  click link → pick/claim a token → see the table. (Optional light auth later.)
- **Fast and legible.** Minimal UI, works on a laptop at the table and on a phone
  for players.

---

## 2. Inspiration — what we borrow from existing tools

| Tool | What it does well | What we take |
|------|-------------------|--------------|
| **Owlbear Rodeo** | Dead-simple map + tokens, fog of war, measurement, instant share link, no accounts needed for players, extension system | The whole UX philosophy: minimalism, share-link for players, fog reveal, snappy token movement |
| **Foundry VTT** | Self-hosted, one license hosts many games, "Actors" (reusable creature/NPC entities), Journals with permissions, scenes, modules | Self-hosting model, reusable creature library, per-document visibility (public vs DM-only), scene concept |
| **Roll20** | Dynamic fog/line-of-sight, dice roller shared in chat, character token binding, asset library | Shared dice log with public vs private rolls, token ↔ creature binding, asset/gallery management |
| **Alchemy / Above VTT** | Gorgeous shared "handouts"/images pushed to players, atmosphere | The "push an image to all players" gallery/handout flow |
| **D&D Beyond** | Clean public stat blocks | Public creature stat blocks as shareable rich content |

**Explicit non-goals (for now)**

- No automated combat/rules engine or initiative automation (maybe later).
- No dynamic line-of-sight / vision-per-token lighting in v1 (manual fog only).
- No voice/video chat (assume Discord/other runs alongside).
- No marketplace/payments.

---

## 3. Core domain model

```
Server
 └─ User (DM account; players optional)
     └─ Campaign                     (owned by one DM)
         ├─ Members / Player seats   (invited via share link)
         ├─ Map  *                   (uploaded image + grid + fog state)
         │    └─ Token *             (placed instance on a map)
         ├─ Creature *               (reusable: creature / NPC / player char)
         │    ├─ token image
         │    ├─ display image       (public, shown on click)
         │    ├─ public stats        (rich text / image, visible to players)
         │    └─ hidden stats        (rich text / image, DM-only)
         ├─ Note *                   (rich text; public or hidden)
         └─ Gallery image *          (handouts the DM can push to players)
```

- A **Token** is a placed instance *on a map*. It usually points to a **Creature**
  (so it inherits the token image and the click-to-view public content), but a bare
  token (just a label/colour) is allowed.
- A **Creature** is the reusable library entry — "Goblin", "Innkeeper Garrett",
  "Thrain (Mario's fighter)". You can drop many tokens of the same Creature on a map.
- **Visibility is a property of content, not of the whole creature.** A Creature can
  have a public image + public stat block that players see on click, *and* a hidden
  stat block only the DM sees.
- **Public creature database (optional):** a creature can be marked
  *server-shared* so other DMs on the same server can reuse it (a shared bestiary),
  vs. campaign-private, vs. fully hidden.

---

## 4. Functional requirements

### 4.1 Accounts & authentication

- **FR-A1** A DM can register an account (email + password) on the server.
- **FR-A2** Login with session (cookie/JWT); "remember me".
- **FR-A3** Each DM sees and manages only their own campaigns. Hard isolation.
- **FR-A4** Server admin/first-run setup: configure whether registration is open,
  invite-only, or admin-created (self-hosted servers vary — a home server may be
  single-DM; a club server may host many).
- **FR-A5** Password reset (email optional; for home servers, admin reset is fine).
- **FR-A6 (optional/phase 2)** Players may optionally create light accounts to
  persist their identity across sessions; default remains link-only.

### 4.2 Campaign management

- **FR-C1** Create / rename / archive / delete a campaign.
- **FR-C2** Campaign holds: maps, creature library, notes, gallery, player seats,
  session settings.
- **FR-C3** Dashboard listing campaigns with last-played date and a "Launch session"
  button.
- **FR-C4** A campaign has an **active map/scene** — the one players currently see.
  The DM switches the active map; players' view follows.

### 4.3 Maps & scenes

- **FR-M1** Upload a map image (PNG/JPG/WebP; large images supported, tiled/zoomed).
- **FR-M2** Define a **grid**: square (default) or none/hex; cell size in px;
  offset; colour/opacity; toggle visibility.
- **FR-M3** Pan / zoom; "fit to screen"; remember last view per map.
- **FR-M4** **Fog of war (obfuscation):** the map starts fully covered for players.
  The DM reveals regions with a brush/rectangle/polygon tool; can re-hide ("cover").
  - DM sees the full map always, with revealed areas distinguished from hidden.
  - Players see only revealed areas; the rest is obscured (opaque or blurred).
  - Fog state persists per map.
- **FR-M4b (phase 2)** "Player torch" / soft reveal: a radius around player tokens
  is revealed automatically (manual fog is the v1 baseline).
- **FR-M5** Measurement tool (distance in cells/feet) — DM and optionally players.
- **FR-M6** Simple drawing/ping: temporary ping (click to point), freehand pen layer.
- **FR-M7** Multiple maps per campaign; reorder; duplicate; set thumbnails.

### 4.4 Tokens

- **FR-T1** Place a token on the active map by dragging a Creature from the library,
  or create a quick ad-hoc token (label + colour/shape).
- **FR-T2** Move tokens by drag; movement syncs live to all viewers.
  - Permission: DM moves any token; a player may move tokens assigned to them
    (their character) — configurable.
- **FR-T3** Token properties: size (1×1, 2×2, etc.), label (shown/hidden),
  rotation, border colour, status/condition markers (phase 2), lock position.
- **FR-T4** Token image comes from its Creature's token image (circular crop
  option). Ad-hoc tokens use a letter/colour.
- **FR-T5** **Token visibility to players:** a token can be hidden from players
  (DM-only, e.g., an ambush) and revealed later.
- **FR-T6** **Click a token** → shows the Creature's *public* display image and/or
  public stat block in a panel (see 4.6). Players only ever get public content.
- **FR-T7** Z-order / bring-to-front; delete; multi-select move (phase 2).
- **FR-T8** Snap-to-grid toggle.

### 4.5 Creature / NPC / Player library

- **FR-E1** Create a library entry with: name, type (Creature / NPC / Player),
  token image, optional larger display image.
- **FR-E2** **Public content** (what players see on click): display image and/or a
  rich-text public stat block (name, description, visible stats). Optional.
- **FR-E3** **Hidden content** (DM-only): rich-text notes and/or an image (e.g., the
  real stat block, tactics, secret identity). Never sent to player clients.
- **FR-E4** Visibility scope per entry:
  - **Hidden** — DM-only, nothing public.
  - **Campaign-public** — public content visible to this campaign's players.
  - **Server-shared** — the entry (public content) is added to the server's shared
    bestiary other DMs can copy/reference. *Never shares hidden content.*
- **FR-E5** Assign a Player-type entry to a specific player seat (so that player can
  move their own token and is identified).
- **FR-E6** Duplicate / import from server bestiary into a campaign.
- **FR-E7** Search/filter the library by name/type.

> **Security note:** Hidden stats and images must be enforced server-side. A player
> client must never receive hidden content in any API response or websocket message
> — not merely hidden in the UI.

### 4.6 Player share link & player view

- **FR-P1** The DM generates a **share link** (and/or short join code) for the
  campaign. Options: single shared link, or per-player links/seats.
- **FR-P2** Opening the link gives a player the **player view**, no account required
  (optional password on the link).
- **FR-P3** Player view shows the **active map with fog applied** — only revealed
  regions, grid if enabled, and visible tokens.
- **FR-P4** Players can: pan/zoom, see token movement live, click a visible token to
  see its **public** image/text, place pings, and move **their own** token (if
  allowed).
- **FR-P5** **Mode switch** in the player view: toggle between
  - **Map mode** (the tabletop), and
  - **Gallery / handout mode** (the image the DM is currently sharing — see 4.8).
  The DM can also *force* all players to the shared image ("push to players").
- **FR-P6** Players never receive hidden tokens, hidden fog areas, or hidden
  creature content over the wire.
- **FR-P7** Player identity: pick/claim a seat on join; display name; colour.
- **FR-P8** Revoke / rotate share link; kick a player.

### 4.7 Dice roller

- **FR-D1** Roll standard dice: d4, d6, d8, d10, d12, d20, d100, with counts and
  modifiers (e.g., `2d6+3`, `1d20+5`). Text formula input + quick buttons.
- **FR-D2** **Shared roll log** visible to everyone: who rolled, formula, individual
  dice, total, timestamp.
- **FR-D3** **Roll visibility modes (both DM and players can choose per roll):**
  - **Public** — result shown to everyone in the shared log.
  - **Private / silent** — result shown only to the roller (DM rolls behind the
    screen; a player can roll privately too). DM option to see all private rolls.
- **FR-D4** DM "roll as" a creature/NPC (phase 2, with saved stat shortcuts).
- **FR-D5** Advantage/disadvantage helper (roll 2d20 keep highest/lowest) — nice to
  have.
- **FR-D6 (optional)** Simple 3D/animated dice; otherwise clean numeric results.
- **FR-D7** Roll results sync in real time; private rolls are server-filtered so
  other clients never receive them.

### 4.8 Gallery & shared images (handouts)

- **FR-G1** Upload images into a campaign gallery (character art, maps-as-handouts,
  item cards, letters, scenery).
- **FR-G2** DM can **share/push** a gallery image to players → appears in the
  players' Gallery mode (and optionally auto-switches their view to it).
- **FR-G3** Gallery images have visibility (private to DM vs shared). Stop sharing
  returns players to the map.
- **FR-G4** Re-use: a gallery image can be set as a creature's display image or as a
  map.

### 4.9 Notes

- **FR-N1** Rich-text notes per campaign (sessions, lore, plot, recaps).
- **FR-N2** Visibility: **hidden** (DM-only) or **public** (shared handout to
  players, e.g., a prophecy or quest text).
- **FR-N3** Organise with titles/folders or tags; search.
- **FR-N4** Public notes appear to players (in Gallery/handout area). Hidden notes
  never leave the server to player clients.

### 4.10 Real-time synchronisation

- **FR-S1** All table state (token positions, fog reveals, active map, shared image,
  dice log, pings) syncs live to connected clients via WebSocket.
- **FR-S2** Server is the source of truth and the **permission gate**: every message
  is authorised server-side; player clients are only sent content they may see.
- **FR-S3** Reconnect handling: a client that reconnects gets current state.
- **FR-S4** Reasonable latency target for token drag (<150 ms perceived on LAN).

---

## 5. Roles & permissions matrix

| Capability | DM (owner) | Player (seat) | Other DM (server) |
|---|---|---|---|
| See full map (no fog) | ✅ | ❌ | ❌ |
| See fogged/revealed map | ✅ | ✅ (revealed only) | ❌ |
| Move any token | ✅ | ❌ | ❌ |
| Move own character token | ✅ | ✅ (if allowed) | ❌ |
| See hidden tokens | ✅ | ❌ | ❌ |
| View public creature content | ✅ | ✅ | ✅ (if server-shared) |
| View hidden creature content | ✅ | ❌ | ❌ |
| Reveal/hide fog, switch map | ✅ | ❌ | ❌ |
| Push gallery image to players | ✅ | ❌ | ❌ |
| Roll public dice | ✅ | ✅ | — |
| Roll private/silent dice | ✅ | ✅ | — |
| See others' private rolls | ✅ (optional) | ❌ | ❌ |
| Edit notes / creatures / maps | ✅ | ❌ | ❌ |
| Copy server-shared creature | ✅ | — | ✅ |

---

## 6. Non-functional requirements

- **NFR-1 Self-hosting:** ship as Docker Compose (app + DB) and/or a single binary.
  Simple first-run setup. Runs on a modest home server or a cheap VPS.
- **NFR-2 Storage:** uploaded images on local disk (configurable path) or S3-compatible
  bucket; DB stores metadata and state.
- **NFR-3 Security:**
  - Hidden content enforced server-side; never serialised to unauthorised clients.
  - Auth with hashed passwords (argon2/bcrypt), CSRF protection, secure cookies.
  - Signed/expiring share links; ability to revoke.
  - Per-request authorization checks on every campaign resource (no IDOR).
  - Uploaded image validation (type/size), served from a sandboxed path.
- **NFR-4 Performance:** handle large map images (progressive/zoomable), ~6–8
  concurrent players per session smoothly.
- **NFR-5 Offline/local-first friendly:** works fully on a LAN with no internet
  (home game night). Internet only needed if hosting publicly.
- **NFR-6 Responsive:** DM on desktop; players usable on tablet/phone.
- **NFR-7 Backups:** simple export/backup of a campaign (DB rows + assets).
- **NFR-8 Browser-based client:** no install for players; modern evergreen browsers.

---

## 7. Tech stack (decided — mirrors QuizBuilder)

GameTable reuses the self-hosted stack from **QuizBuilder**
(see `project_quizbuilder_context`): **FastAPI + PostgreSQL + Next.js, in Docker**.
A custom Python backend (not Supabase) — the server owns auth, realtime, and the
permission filtering that keeps hidden content away from players.

- **Backend:** **FastAPI** (Python 3) — REST API + native **WebSocket** endpoints.
  SQLAlchemy + Alembic migrations. **Pydantic** schemas define exactly what each
  role receives (public vs DM-only), so hidden content is filtered **in the
  serializer**, not just the UI.
- **Database:** **PostgreSQL** (Docker). Enforcement of public/hidden/DM-only/
  server-shared lives in the **API/application layer** (the server never serialises
  hidden fields into a player response). Plain Postgres — no Supabase/RLS.
- **Auth (DMs):** FastAPI-issued **JWT** (or session cookie), passwords hashed with
  **argon2/bcrypt**. Each DM sees only their own campaigns (ownership checks on
  every resource — no IDOR).
- **Players (link-only, no account):** join via a **share token** (a signed,
  revocable token embedded in the link, optionally a short join code). A dedicated
  player API + WebSocket namespace validates the token and returns only public,
  permitted data. Players are **not** user accounts in v1.
- **Realtime sync:** **FastAPI WebSockets** carry token moves, fog reveals,
  active-map switches, pushed images, pings, presence ("who's at the table"), and
  the dice log. The server is authoritative and the permission gate: it fans out to
  each client only the messages they may see (hidden tokens/fog/rolls are filtered
  per connection). This implements §4.10. (Redis pub/sub can back multi-worker
  fan-out later; single-process in-memory is fine for v1.)
- **Frontend:** **Next.js** (TypeScript) web app. The tabletop is a **canvas/WebGL
  surface** — **PixiJS** (preferred for many moving sprites) or **Konva** — for
  smooth pan/zoom and token dragging. Lightweight state store (Zustand); talks to
  the FastAPI REST + WebSocket.
- **Storage:** uploaded images (maps, token/display images, gallery) on a Docker
  **media volume** (mirrors QuizBuilder's `media-data`), served by the API with
  authorization checks; DM-only images never get a public URL. S3/MinIO optional
  later.
- **Packaging:** **Docker Compose** — `api` (FastAPI), `db` (Postgres), `web`
  (Next.js), optional `redis`. `.env` config; a Python/Make one-command helper for
  install/start/stop/migrate, consistent with QuizBuilder's workflow.
- **Mobile:** none planned — players use the browser. (QuizBuilder's Expo/Android
  app has no analogue here; the share link is the player client.)
- **Open-core (optional, confirm):** public server repo on GitHub following your
  pattern; decide MIT vs private when ready.

---

## 8. MVP scope (phase 1)

The smallest thing that's fun to play on:

1. DM account + login; create a campaign.
2. Upload a map; square grid.
3. Manual fog of war (reveal/hide rectangles).
4. Creature library with token image + public display image/text.
5. Drag tokens onto the map; move them; hide/reveal tokens; click shows public info.
6. Player share link → player view with fog-applied map, live token movement,
   click-for-public-info.
7. Shared dice roller with public vs private rolls and a shared log.
8. Live sync over WebSocket with server-side permission filtering.
9. Docker Compose deploy.

**Phase 2:** gallery push/handouts, public notes, server-shared bestiary, hidden
stat images, measurement, player-moves-own-token, link rotation/kick.

**Phase 3:** soft/auto fog around player tokens, conditions/status markers, 3D dice,
"roll as creature", per-player seats with light accounts, initiative tracker,
extensions/plugins.

---

## 9. Open questions

1. ~~**Backend language**~~ — **Decided:** FastAPI + Next.js, mirroring QuizBuilder (§7).
2. ~~**Default DB**~~ — **Decided:** PostgreSQL (Docker), per QuizBuilder (§7).
3. **Player auth** — pure link-only forever, or optional light player accounts in v2?
4. **Registration policy default** — open / invite-only / admin-created DMs?
5. **Fog model** — rectangle/polygon manual only for v1, confirm (auto line-of-sight
   is a big feature — defer)?
6. **Grid/measurement units** — D&D 5e default (5 ft / square), configurable?
7. **Server-shared bestiary** — in scope for v1 or later? (adds cross-DM data model
   and moderation questions.)
8. **Mobile DM** — must the DM tools work on tablet, or desktop-only for v1?

---

## 10. Suggested next steps

- Confirm the open questions in §9 (especially stack + DB).
- Lock the MVP (§8) and turn each item into tickets.
- Draft the data schema (tables for users, campaigns, maps, tokens, creatures,
  notes, gallery, share_links, dice_rolls) and the WebSocket message contract.
- Scaffold the repo (client + server + docker-compose) and build the map+token
  render loop first — it's the core risk.
