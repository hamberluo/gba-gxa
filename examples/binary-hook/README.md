# binary-hook

An armips patch that makes an m4a (Sappy) game play chosen songs from a GXA pack. Read with
[docs/guides/binary-m4a-hook.md](../../docs/guides/binary-m4a-hook.md)
([中文](../../docs/guides/binary-m4a-hook.zh-CN.md)).

- `hook.asm`: the hook itself. Game-independent; it reads every address from `defs.asm`.
- `example.asm`: the file you copy and edit: file names, `BGM_PLAYER`, the song → track table.

```sh
cd examples/binary-hook
python3 ../../tools/m4a_locate.py --armips /path/to/game.gba > defs.asm
cp example.asm my-hack.asm            # edit names, BGM_PLAYER, gxa_song_tracks
armips my-hack.asm
python3 ../../tools/gba_header.py --check game-gxa.gba
```

`defs.asm` holds one game's addresses; it is ignored by git here.
