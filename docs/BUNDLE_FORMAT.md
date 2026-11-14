# GameTable bundle format

A **bundle** is a plain `.zip` that holds one campaign — maps, tokens, a creature
library, notes, and gallery handouts — plus its images. Export a campaign to a
bundle, carry the file anywhere, and import it into any GameTable server as a new
campaign. The layout is deliberately simple so you can also **build one by hand**.

Portability use case: build a campaign at home, export the `.zip`, bring it to the
game, and import it on the server at the table.

## Layout

```
bundle.json            the manifest — everything textual about the campaign
maps/<file>            battlemap images                 (public)
tokens/<file>          creature token art               (public)
portraits/<file>       creature "display" images        (public, shown on click)
secret/<file>          creature DM-only images          (protected)
handouts/<file>        gallery images / player handouts (public)
```

Images are referenced from `bundle.json` by their path relative to the manifest.
Any folder names work for images as long as the manifest points at them; the names
above are just the convention export uses. Allowed image types: PNG, JPEG, WebP, GIF
(≤ 25 MB each).

The manifest may sit at the zip root (`bundle.json`) or one level down inside a single
top folder (`the-sunless-shrine/bundle.json`) — import finds it either way.

## `bundle.json`

```jsonc
{
  "format": "gametable-bundle",   // required, must be exactly this
  "version": 1,                   // required
  "campaign": { "name": "…", "description": "…" },

  "creatures": [
    {
      "key": "goblin",            // bundle-local id; tokens reference this
      "name": "Goblin",
      "type": "creature",         // creature | npc | player
      "visibility": "campaign_public",  // hidden | campaign_public | server_shared
      "public_stats": "What players see when they click the token.",
      "hidden_stats": "DM-only notes / full stat block.",
      "token_image":   "tokens/goblin.png",     // or null
      "display_image": "portraits/goblin.png",  // or null  (public)
      "hidden_image":  "secret/goblin.png"      // or null  (DM-only, protected)
    }
  ],

  "maps": [
    {
      "name": "Cragmaw Cave",
      "image": "maps/cave.png",
      "width": 2100, "height": 1540,
      "active": true,             // which map players start on
      "grid": { "type": "square", "size": 70, "offset_x": 0, "offset_y": 0,
                "color": "#2a2d36", "unit_per_cell": 5 },
      "fog": { "revealed": [], "hidden": [] },   // empty = whole map fogged
      "tokens": [
        {
          "creature": "goblin",   // a creature key, or null for a bare token
          "label": "Goblin A",
          "x": 665, "y": 175,     // map pixel coords (cell*size + size/2 centers it)
          "size": 1,              // in cells (a Large creature = 2)
          "color": "#8a9a5b",
          "border_color": null,
          "hidden_from_players": true,   // DM reveals it when the fight starts
          "locked": false,
          "z_index": 0
        }
      ]
    }
  ],

  "notes": [
    { "title": "Running this", "body": "…", "visibility": "hidden", "sort_order": 0 }
    // visibility: hidden (DM-only) | public (a handout players can read)
  ],

  "gallery": [
    { "name": "Player map", "image": "handouts/player-map.png", "is_shared": false }
  ]
}
```

Everything except `format`, `version`, and `campaign.name` is optional. Omit a
section and it's simply empty.

### Token placement math

Token `x`/`y` are **map pixel coordinates**. To drop a 1-cell token on the center
of grid cell `(col, row)` with grid size `S`:

```
x = col * S + S / 2
y = row * S + S / 2
```

## Building a bundle by hand

1. Make a folder with a `bundle.json` and your image sub-folders.
2. Zip it (the `bundle.json` must be at the root of the zip, or one folder deep):
   ```bash
   # from inside the folder
   zip -r ../my-campaign.zip .
   # …or use the bundled packer (validates the JSON first):
   python -m app.bundle pack path/to/folder my-campaign.zip   # run in backend/
   ```
3. In GameTable: **Campaigns → Import bundle** → choose the `.zip`.

See [`content/adventures/the-sunless-shrine/`](../content/adventures/the-sunless-shrine)
for a complete, hand-editable example (and `build_assets.py`, which draws all of its
art from scratch).

## Import guarantees & safety

- Import always creates a **new** campaign owned by the importer. It never
  overwrites or touches existing campaigns.
- Hidden creature content (`hidden_stats`, `hidden_image`) stays DM-only: hidden
  images go to the protected media bucket, exactly as in normal use.
- Import reads only the image paths named in the manifest, each sanitized against
  path traversal, with per-file (25 MB) and total-size (200 MB) caps.
- `share_links`, player seats, and dice history are **not** exported — a bundle is
  content, not a live session. Generate fresh share links after importing.
