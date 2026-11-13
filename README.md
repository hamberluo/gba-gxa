[中文](README.zh-CN.md)

# GXA: external audio for GBA ROMs

Created by [GoGBA](https://gogba.xyz/); open to every emulator and every ROM.

GXA lets a Game Boy Advance ROM play audio stored outside the ROM: voiced dialogue, arranged soundtracks,
high-quality effects. It is the GBA's counterpart to the SNES's MSU-1. A ROM writes a few registers; a GXA
emulator plays the tracks from a `.gxa` pack beside the ROM. On hardware and other emulators the ROM runs as
before, with its own sound.

The standard is [SPEC.md](SPEC.md) (GXA 1.0).

## What it sounds like

The Langrisser II voice hack runs on GoGBA with fully voiced story scenes from a GXA pack.

![conformance ROM: every row green](test-rom/conformance.png)

## Where to start

| You are | Read |
|---|---|
| Making a hack of a game you only have as a ROM | [Binary hook guide](docs/guides/binary-m4a-hook.md) (m4a/Sappy games), then [Making a pack](docs/guides/making-a-pack.md) |
| Making homebrew, or a hack from a decomp (C source) | [C source guide](docs/guides/c-source.md) and [include/gxa.h](include/gxa.h), then [Making a pack](docs/guides/making-a-pack.md) |
| Writing an emulator | [SPEC.md](SPEC.md), the [reference implementation](#for-emulator-authors), and the [conformance ROM](test-rom) |
| Playing | Put `game.gxa` beside `game.gba` and open the ROM in an emulator from the list below |

## Using an AI coding agent?

Point it at [AGENTS.md](AGENTS.md). It tells the agent what to read, the rules that keep the ROM safe on
every emulator, and how to verify the result.

## Emulators

| Emulator | GXA | Conformance |
|---|---|---|
| [GoGBA](https://gogba.xyz/) (iOS, Android), core: [libretro-mgba](https://github.com/hamberluo/libretro-mgba) | 1.0 | all pass |

Implemented GXA? Open an [emulator support issue](https://github.com/hamberluo/gba-gxa/issues/new?template=emulator-support.yml)
with a screenshot of the conformance ROM.

Works that use GXA are listed in [SHOWCASE.md](SHOWCASE.md).

## For emulator authors

- **Spec:** [SPEC.md](SPEC.md). Registers at `0x04FFFA00`, a handshake, four channels, zip packs of Ogg Vorbis.
- **Reference implementation (C, MPL 2.0):** [hamberluo/libretro-mgba](https://github.com/hamberluo/libretro-mgba):
  `src/gba/gxa.c` (registers, channels, rendering, state), `src/gba/gxa-pack.c` (pack reading, ROM matching),
  hooks in `src/gba/io.c`, `src/gba/audio.c`, `src/gba/core.c`, libretro glue in
  `src/platform/libretro/libretro.c` and `libretro_gxa.h`.
- **Conformance:** run [test-rom/gxa-conformance.gba](test-rom/gxa-conformance.gba) with
  `test-rom/gxa-conformance.gxa` beside it. Every row must turn green; automated runs read the result block
  (SPEC.md §6).
- **Spec check:** `python3 tools/check_spec.py <your-tree>` compares SPEC.md's register table with constants
  in an mGBA-based tree.

## Tools

```sh
pip install -r tools/requirements.txt
python3 tools/gxa_pack.py my-pack-dir my-game.gxa   # build a pack
python3 tools/gxa_info.py my-game.gxa               # inspect a pack
python3 tools/m4a_locate.py my-game.gba             # find m4a song functions to hook
python3 tools/gba_header.py my-game.gba             # fix the header checksum after patching
```

## Copyright

This repository contains no game audio or ROMs. Pack authors are responsible for having the rights to the
audio they distribute.

## Contributing and licences

See [CONTRIBUTING.md](CONTRIBUTING.md). Spec changes start as an issue.

- Specification text: CC BY 4.0 ([LICENSE-SPEC](LICENSE-SPEC)).
- Tools, header, examples and the conformance ROM: MIT ([LICENSE-TOOLS](LICENSE-TOOLS)).
- The reference implementation follows mGBA: MPL 2.0.
