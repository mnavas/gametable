# Dungeon Master's Guide

How to run a session in GameTable — from creating a campaign to sharing the table
with your players. If you haven't set up the server yet, start with the
[installation guide](installation.md).

---

## 1. Your account and campaigns

- Open the web app and **register** (the first account on a fresh server becomes the
  admin). Log in any time afterward.
- From the dashboard, **create a campaign** — one per game/group. Everything below
  lives inside a campaign and is private to you.

Each campaign holds its **maps**, a **creature library**, **notes**, a **gallery**,
and the **share links** you give players.

---

## 2. Maps & fog of war

- In the campaign, open the **Maps** panel and **upload a map image** (PNG/JPG/WebP).
  The first map you upload becomes the active scene; click any map to switch to it.
- A square **grid** is drawn over the map. (Grid size, colour, and feet-per-square
  are configurable per map.)
- **Fog of war:** players start seeing nothing. Turn on the **Fog tool** and drag a
  rectangle to **reveal** an area; use **Reset fog** to cover everything again.
  You always see the whole map (fog shows as a dim tint); players see only the
  revealed regions.

Pan with drag, zoom with the scroll wheel.

---

## 3. Creatures: public vs hidden

Open the **Creatures** panel to build your library — monsters, NPCs, and the
players' characters. Click a creature to open its editor, where you set:

- **Name & type** (creature / NPC / player).
- **Visibility:** *Hidden* (DM-only), *Campaign public* (players can see the public
  parts), or *Server shared*.
- **Public stats** — rich text players see when they click the token.
- **Hidden stats** — DM-only text (HP, tactics, secret identity). **Never sent to
  players.**
- **Three images:** a **token** image (shown on the map), a **display** image
  (public, shown to players on click), and a **hidden** image (DM-only — e.g. the
  real stat block).

> The split is enforced on the server: hidden stats and the hidden image are never
> delivered to a player's browser, not merely hidden in their UI.

---

## 4. Tokens on the map

- With a map active, click the **＋** next to a creature to **drop a token** onto it.
- **Drag** tokens to move them — every connected player sees the move live.
- **Click a token** (as the DM) to toggle it **hidden from players** — perfect for an
  ambush. Hidden tokens show for you with a dashed red border; players don't receive
  them at all until you reveal them.
- Players can move **their own** character token if it's assigned to their seat;
  everything else is yours to move.

---

## 5. Dice — open or secret

Use the **Dice** panel:

- Type a formula (`1d20`, `2d6+3`, `1d20+5`) or tap a quick die, then **Roll**.
- **Public** rolls appear in the shared log everyone sees.
- The **🤫 (silent)** button rolls privately — only you see the result. Players can
  roll privately too; their secret rolls come to you but not to the rest of the table.

---

## 6. Handouts from the gallery

- Upload character art, item cards, or reveal images to the **Gallery**.
- Click **Show** on an image to **push it to your players** — their view can switch
  to the handout. Click again to stop showing it and send them back to the map.

---

## 7. Notes

Keep lore, plot, and session recaps as **notes**. Each note is either **hidden**
(DM-only) or **public** (a handout your players can read) — your call, per note.

---

## 8. Share the table with players

- Open the share-link control and **create a share link**. You get a URL like
  `https://your-server/play/<token>`.
- Send it to your players. They open it — **no account, no install** — and land in
  the player view, seeing only the revealed map, visible tokens, and whatever you're
  showing.
- You can give **one link for the whole table** or per-player links, add an optional
  **password** or **expiry**, and **revoke** a link at any time to cut access.

See the [player guide](player-guide.md) for what your players will see.

## 9. Take your game anywhere (export / import)

A whole campaign — maps, fog, tokens, your creature library (hidden stats and all),
notes, and gallery — can travel as a single `.zip` **bundle**.

- **Export:** on the Campaigns page, click **⬇ Export** on a campaign. Your browser
  downloads `that-campaign.gtbundle.zip`.
- **Import:** click **⬆ Import bundle** and pick a `.zip`. It comes in as a brand-new
  campaign you own — nothing else in your account is touched. Create fresh share links
  afterwards (links and live-session data don't travel in a bundle).

This is how you prep at home and run at the table: build it on your home server,
export, and import on the laptop at game night.

**Try the included one-shot:** import `content/adventures/the-sunless-shrine.zip` from
the repo for a complete, ready-to-run adventure. You can also **hand-author** a bundle
(or edit that one) — the layout is documented in the [bundle format](BUNDLE_FORMAT.md).

---

## Quick reference

| I want to… | Do this |
|---|---|
| Change the scene players see | Click a different map |
| Reveal part of the map | Fog tool → drag a rectangle |
| Hide the whole map again | Reset fog |
| Put a monster on the board | ＋ next to the creature |
| Spring an ambush | Add it as a hidden token, then click to reveal |
| Show players a picture | Gallery → Show |
| Roll behind the screen | Dice → 🤫 |
| Let players in | Create a share link, send the URL |
| Kick everyone off a link | Revoke the share link |
| Back up / move a campaign | ⬇ Export it as a `.zip` |
| Load a campaign or adventure | ⬆ Import bundle → pick the `.zip` |
