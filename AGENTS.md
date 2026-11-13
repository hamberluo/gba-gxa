# AGENTS.md: adding GXA to a GBA game

You are probably here because a person asked you to make their GBA game or hack play audio from a GXA pack:
voice lines, arranged music, better sound effects. This file is your map. Follow it in order.

## 1. Read

1. [SPEC.md](SPEC.md) §1–§4: registers, detection, playback, packs. It is short and normative.
2. Then one integration path:

| The person has | Path | Read |
|---|---|---|
| The game's C source (homebrew, or a decomp such as pret's) | C | [include/gxa.h](include/gxa.h), [docs/guides/c-source.md](docs/guides/c-source.md), [examples/homebrew-bgm](examples/homebrew-bgm) |
| Only the ROM, and `python3 tools/m4a_locate.py rom.gba` finds the m4a functions | Binary hook | [asm/gxa.s](asm/gxa.s), [docs/guides/binary-m4a-hook.md](docs/guides/binary-m4a-hook.md), [examples/binary-hook](examples/binary-hook) |
| Only the ROM, and `m4a_locate.py` exits 2, or its last line is not `hook: ok` | Neither guide fits | Tell the person: the game does not use the stock m4a engine. Finding its sound driver's entry points is reverse-engineering work the guides do not cover. |

3. [docs/guides/making-a-pack.md](docs/guides/making-a-pack.md) for the pack.

## 2. Rules that keep the ROM safe

The ROM will also run on hardware and on emulators without GXA. Breaking those is the worst outcome.

- **Detect first.** Touch no other GXA register before the handshake passes (`gxa_has_pack()`, or
  `gxa_detect` in `asm/gxa.s`). Without GXA, run the original code path unchanged.
- **Fall back per track.** After a play command, check that it started (`gxa_started()`, or r0 from
  `gxa_play_track`). A missing or broken track must play the original sound.
- **Stop on every stop path.** Whatever stops or changes the music (song stop, stop-all, fade-out, scene
  change, a new song starting) must also stop the GXA channel. Otherwise two musics play at once. The binary
  hook covers song starts, stops, and pausing/continuing the BGM player, but not fade-outs; tell the person
  (see the guide's Limits).
- **Keep the game's own state.** Do not skip or stop the original song when GXA plays instead; mute it
  (the binary hook swaps in a silent voice table). Games poll their music player: one went back to its
  intro when the title song looked stopped.
- **Never wait on GXA alone.** Waits on a channel end on `ended`; missing tracks set it at once. Do not spin
  on `playing`.
- **16-bit or 32-bit accesses only.** No `strb`/`ldrb` on `0x04FFFA00`–`0x04FFFA7F`.
- **Binary patches:** put new code only where `m4a_locate.py --armips` says (free space at the end, or past
  the end of a full ROM); re-run the displaced instructions exactly; run
  `python3 tools/gba_header.py --check rom.gba` after patching.
- **Song numbers and the BGM player are per game.** Find song numbers with a debugger breakpoint on
  `m4aSongNumStart` (r0), and the BGM player with `m4a_locate.py --song N` (or let
  `--armips --bgm-song N` write it into `defs.asm`). If you cannot run a debugger,
  ask the person for the song numbers instead of guessing.
- **Track ids:** once a released ROM uses an id, it keeps its meaning. New or changed audio takes a new id.

## 3. Verify before you report done

Build the pack (`tools/gxa_pack.py`), inspect it (`tools/gxa_info.py`), then run the ROM three ways:

| Run | Must see |
|---|---|
| GXA emulator, full pack | GXA audio where intended, no original music underneath |
| GXA emulator, pack with one used track removed | that spot plays the original sound; nothing hangs |
| Emulator without GXA (or no pack) | the game behaves exactly like the unmodified one |

If you cannot run an emulator, say so plainly in your report and list these three checks for the person.

## 4. Report to the person

- What you changed (files, or ROM offsets and the free space used).
- The song → track id table.
- Which of the three checks you ran, and their results.
- Anything you guessed (for example which song ids are music and which are sound effects).
