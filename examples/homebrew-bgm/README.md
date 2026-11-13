# homebrew-bgm

A tiny ROM that hands its background music to GXA and falls back to its own PSG music. Read with
[docs/guides/c-source.md](../../docs/guides/c-source.md) ([中文](../../docs/guides/c-source.zh-CN.md)).

- Title screen (blue): track 1. Press START for the field (green): track 2.
- `main.c`: `bgm_start()` and `bgm_stop()` are the whole integration.

```sh
sh build.sh                                   # homebrew-bgm.gba (needs arm-none-eabi-gcc)
python3 make_pack.py homebrew-bgm.gxa         # full pack (needs tools/requirements.txt)
python3 make_pack.py --without 2 homebrew-bgm.gxa   # track 2 missing: the field falls back to PSG
```

Put `homebrew-bgm.gba` and `homebrew-bgm.gxa` in one folder and open the ROM in a GXA emulator.
Without the pack, or in any other emulator, you hear the PSG tune.
