# Contributing

Chinese and English are both welcome in issues. 中文、英文提 issue 都可以。

## Spec changes

GXA keeps old ROMs working, so the spec changes slowly.

1. Open a [spec change issue](https://github.com/hamberluo/gba-gxa/issues/new?template=spec-change.yml):
   the problem, the proposed registers or behavior, and what existing ROMs and emulators would see.
2. Discussion happens in the issue. A change needs a working implementation in at least one emulator and a
   conformance case before it lands.
3. Minor versions (1.x) only add: new registers in the reserved range or new commands. Nothing existing
   changes meaning. Breaking changes need a new major version, decided by the maintainer.

Typo and wording fixes to SPEC.md can go straight to a pull request.

## Listing an emulator

Open an [emulator support issue](https://github.com/hamberluo/gba-gxa/issues/new?template=emulator-support.yml)
with a screenshot of `test-rom/gxa-conformance.gba` showing every row green, and a link to the source or
release.

## Listing a work

Open a [showcase issue](https://github.com/hamberluo/gba-gxa/issues/new?template=showcase.yml).

## Pull requests

- Docs: `README.md` and `docs/guides/*.md` have Chinese translations (`*.zh-CN.md`). Change both in the same
  pull request; `python3 tools/check_docs.py` checks that their headings line up and that links resolve.
- Tools: `pip install -r tools/requirements.txt && python3 -m pytest tools`.
- Header: `sh include/test/compile.sh` (needs `arm-none-eabi-gcc`).
- Assembly: `sh asm/test/check.sh` (set `ARMIPS` to also check armips). The hook: `examples/binary-hook/test/run.sh`
  (needs armips and a headless GXA emulator; see the script).
- No game audio, ROMs or copyrighted game code in this repository.

## Pitfalls (never repeat)

Each one cost a wrong result once. Add new ones here when they happen.

- **Constants from the spec are derived, not typed.** `asm/gxa.s` once shipped `0x4573` for the handshake reply
  `0x1234 ^ 0x5847` (it is `0x4A73`); `asm/test/check.sh` now computes it.
- **Never stop the game's own m4a song to make room for GXA.** Games poll their music player; one went back
  to its intro when the title song looked stopped. Mute it instead (the hook's silent voice table).
- **Muting through a track's `volX` does not last.** The driver resets every track on the first tick after
  `MPlayStart`; the voice table pointer (`MusicPlayerInfo+0x30`) is what survives.
- **`MPlayStart` can refuse a song** of lower priority than the playing one. Act on GXA only after checking
  the player's `songHeader`.
- **Keep interrupts off from the original call to the mute,** or the driver can load the real instruments in
  between.
- **A hook keeps its arguments.** The song number lives in a saved register for the call to the original;
  a scratch use of that register once made `m4aSongNumStop` stop the wrong song. Test every hooked function
  with the original actually running (`examples/binary-hook/test`).
- **armips** resolves `.include` from the working folder (or `-root`), has no `.rept`, and its executable is
  the CMake target `armips-bin`, not `armips`.
- **A test pack matched by SHA-1 stops loading when the ROM is rebuilt,** silently. Match test packs by code
  and title, and check the emulator reports the pack loaded before comparing two runs.
- **ROM data can end in 0xFF bytes** (a 0xFFFF terminator, a tile of colour 15); free space starts 0x100
  after the last other byte.
- **Ogg encoders pick a random stream serial;** `gxa_pack.py` fixes it so the same input gives the same pack.
