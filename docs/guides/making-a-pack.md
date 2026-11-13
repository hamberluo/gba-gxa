[中文](making-a-pack.zh-CN.md)

# Making a GXA pack

A pack is the `.gxa` file players put beside the ROM. It is a zip of Ogg Vorbis files plus a
`manifest.json` (SPEC.md §4). `tools/gxa_pack.py` builds it and checks every rule.

## 1. Lay out a directory

```
my-pack/
  manifest.json
  bgm/title.wav
  bgm/field.flac
  voice/0001.ogg
```

WAV and FLAC are encoded to Ogg Vorbis; Ogg files are copied as they are. Mono or stereo, any sample rate.

## 2. Write manifest.json

```json
{
  "spec": 1,
  "title": "My Hack arranged soundtrack",
  "author": "you",
  "version": "1.0",
  "license": "CC BY-NC 4.0",
  "match": [{ "code": "ABCE", "title": "MY GAME", "version": 1 }],
  "tracks": {
    "1": { "file": "bgm/title.wav", "loop": 88200 },
    "2": { "file": "bgm/field.flac", "loop": 0, "gain": -3 },
    "1001": { "file": "voice/0001.ogg" }
  }
}
```

- `tracks`: track id (as in your ROM) → file. `loop` is the sample frame a loop command returns to, in the
  file's own rate; without it (or with `0`) a loop starts over from the beginning. `gain` is in dB. Background music is
  usually played with the loop command, so give BGM tracks a loop point.
- `match`: which ROMs load this pack. Pick one:

| Rule | Use it when |
|---|---|
| `{"sha1": "..."}` | One exact ROM file, for example a patched release. Any byte change breaks the match. |
| `{"code": "...", "title": "..."}` + `version` | Your own ROM, where you bump the header's version byte (`0xBC`) on each release. `"version": 1` covers 1 and later. |

The code is the 4 bytes at `0xAC` and the title the 12 bytes at `0xA0`. A hack keeps the original game's code
and title, so it should match by `sha1`, or by `version` if it bumps the version byte. Get the SHA-1 of the
final ROM with `shasum -a 1 game.gba` (Windows: `certutil -hashfile game.gba SHA1`).

## 3. Build and inspect

```sh
pip install -r tools/requirements.txt
python3 tools/gxa_pack.py my-pack my-game.gxa            # --quality 0-1, default 0.4
python3 tools/gxa_info.py my-game.gxa
```

`gxa_pack.py` prints every problem (missing file, loop outside the track, bad id, empty `match`) and writes
nothing until there are none.

## 4. Ship it

Name the pack like the ROM: `my-game.gba` loads `my-game.gxa` from the same folder (SPEC.md §5). Release
the pack next to your patch or ROM. Do not include audio you do not have the rights to distribute.

## Updating

One game, one pack. When you change audio, release the whole pack again. A track id keeps its meaning once
a released ROM uses it: rewritten lines and new music take new ids. A newer ROM with an older pack still
works: the tracks the pack lacks read missing, and the ROM falls back for those.
