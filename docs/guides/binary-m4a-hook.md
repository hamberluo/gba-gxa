[中文](binary-m4a-hook.zh-CN.md)

# Adding GXA to an m4a game you only have as a ROM

Most commercial GBA games play music with Nintendo's m4a engine (also called Sappy or MusicPlayer2000).
Every song starts through `m4aSongNumStart` or one of its siblings, with the song number in `r0`. This guide
patches those functions so that a song you choose plays from a GXA pack instead, and everything else stays
as it was.

You need: Python 3 with `tools/requirements.txt`, [armips](https://github.com/Kingcom/armips) v0.11
(`sh tools/get_armips.sh` builds it), and an emulator with a debugger, such as mGBA, to find song numbers.

If you build the game from source (a decomp), read [c-source.md](c-source.md) instead.

## 1. Check the ROM

```sh
python3 tools/m4a_locate.py game.gba
```

The last line must read `hook: ok`. It prints the addresses of the song functions, the song table, and
where new code will go. If it exits with "not an m4a game", the game uses another sound engine, or a
modified m4a (common in decomp-based hacks); the template below does not apply.

## 2. Find the song numbers

Open the ROM in mGBA, open the debugger, and set a breakpoint at the `m4aSongNumStart` address that
`m4a_locate.py` printed (and at `m4aSongNumStartOrChange` and `m4aSongNumStartOrContinue`, which many games
use for map music). Play to the scene you want. When the breakpoint hits, `r0` is the song number.

Write down each song you want to replace, then find the player that plays it:

```sh
python3 tools/m4a_locate.py --song 413 game.gba
# song 413: player 0 (header 0x08...)
```

The player of your title or field music is the game's BGM player. It is 0 in many games but not all; one
game we tested uses 31.

## 3. Write the patch

```sh
cd examples/binary-hook
python3 ../../tools/m4a_locate.py --armips /path/to/game.gba > defs.asm
cp example.asm my-hack.asm
```

In `my-hack.asm`, set the input and output file names, `BGM_PLAYER`, and the table:

```
gxa_song_tracks:
	.halfword 413, 1     ; song 413 -> GXA track 1
	.halfword 414, 2
	.halfword 0xFFFF     ; end
```

Songs not in the table play as before.

## 4. Build

```sh
armips my-hack.asm                   # run it from examples/binary-hook: armips resolves includes there
python3 ../../tools/gba_header.py --check game-gxa.gba
```

When the ROM has no free space at its end, `defs.asm` says so and the patch grows the ROM past its end;
emulators and flash carts accept that.

## 5. Make the pack

Follow [making-a-pack.md](making-a-pack.md). Track ids are the numbers on the right of your table. Match the
pack by the SHA-1 of the patched ROM if you release the ROM or a patch for one base ROM.

## 6. Test three ways

| Run | Expect |
|---|---|
| GXA emulator, full pack | your tracks play; the original music is not heard under them |
| Same, with one mapped track removed from the pack | that scene plays its original music |
| Emulator without GXA, or no pack | the game exactly as before |

## How the hook works

- The first 8 bytes of `m4aSongNumStart`, `...OrChange`, `...OrContinue` and `m4aSongNumStop` become a jump
  to new code in free space. `m4a_locate.py` checks that these 8 bytes are the stock m4a prologue, and the
  hook re-runs them exactly when it falls back.
- Without GXA or without a pack, the hook runs the original function at once.
- The game's own song **always starts**, so anything the game checks about its music (is it playing, has it
  ended) behaves as before. When GXA plays a track for it, the hook gives that m4a player a silent voice
  table, so the song runs without sound. The next song started on that player gets its own voices back.
  An earlier version stopped the m4a player instead; one game then thought its title music had ended and
  went back to the intro.
- A song on the BGM player loops on GXA channel 0. `...OrChange` and `...OrContinue` do not restart a track
  that already plays. A song on another player plays once on channel 1, for voice lines and jingles.
- An unmapped song on the BGM player stops channel 0, so old GXA music never plays under new game music.
- A missing or broken track reads `missing` or `error` at once (SPEC.md §3), and the original song is heard.

## Limits

- **Fade-outs.** When the game fades its music out (`m4aMPlayFadeOut`), the GXA track keeps playing until
  the next song starts or stops. Map songs whose scenes end with a new song, or extend the hook to the fade
  function of your game.
- **Modified m4a.** Decomp-based hacks often change the m4a library; `m4a_locate.py` then refuses. Add GXA in
  C instead.
- **Other engines.** Games with their own sound driver need their own hook point; the rules in
  [AGENTS.md](../../AGENTS.md) still apply.
