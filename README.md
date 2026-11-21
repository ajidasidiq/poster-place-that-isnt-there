# AETHORIA — The Poster for a Place That Isn't There

A make.fun bounty entry: a program that draws a travel poster for an
invented place, the floating isles of **Aethoria**, and writes it to
`/output/entry.png`.

## What it draws

Golden-hour sky over a sea of cloud, with green-topped islands adrift in
the air — the main isle carries a little lit lighthouse and pine trees,
waterfalls spill off the islands' edges into the clouds below, a small
red-and-cream airship crosses the sun, and birds drift in the distance.
The place name **AETHORIA** is set large across the cloud sea in a
hand-built geometric deco face, flanked by thin gold rules. No quotes, no
star ratings, no other copy — just the name.

## How it works

`main.py` is pure Python 3 standard library — no images, no fonts, no
network, nothing to install. It paints the poster pixel by pixel into an
RGB buffer (gradient sky, soft radial glows, scanline-filled islands and
letterforms with 3x supersampling for smooth edges) and writes its own
PNG with `zlib`.

## Run it

```sh
python3 main.py        # writes /output/entry.png
```

The image is 1024x1024 and well under the 1 MiB limit (about 320 KB).
It runs in roughly 2 seconds.

## License

MIT — see LICENSE.
