# The Sunless Shrine — a free GameTable one-shot

A ready-to-run **Dungeons & Dragons 5e** one-shot for **four 2nd-level characters**
(about 2–3 hours). A buried shrine's light has been snuffed and a death cult feeds
the dark that crept in — put the dead sun's cold fire out before the blight reaches
the valley.

It ships as a **GameTable bundle**: import the `.zip` and you get the battlemap (with
fog), pre-placed and pre-hidden monster tokens, four pre-gen player tokens, a reusable
creature library with SRD stat blocks in the DM-only notes, two player handouts, and
full room-by-room DM notes.

## Import it

- **In the app:** DM dashboard → **Import bundle** → choose `the-sunless-shrine.zip`.
- It lands as a new campaign you own; nothing else in your account is touched.

## What's inside

```
bundle.json         the whole adventure (campaign, maps, creatures, notes, gallery)
maps/               the battlemap
tokens/             monster + pre-gen PC token art
portraits/          public "shown on click" images
secret/             DM-only reveal images
handouts/           player map + the warning glyph
build_assets.py     regenerates all the art with Pillow — tweak it to reskin the map
```

Everything here is **hand-editable**. Open `bundle.json`, change the text, drop in
your own PNGs under the folders, and re-zip (`python -m app.bundle pack <folder> out.zip`
from the backend, or just zip the folder with `bundle.json` at its root).

## License

Original text and art: **CC BY 4.0**. Rules and monster stat blocks: **SRD 5.1**
(Wizards of the Coast), used under CC BY 4.0. See [NOTICE.md](NOTICE.md) for the
required attribution. Unofficial, compatible-with-5E fan content — not affiliated
with or endorsed by Wizards of the Coast.
