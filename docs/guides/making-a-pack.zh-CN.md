[English](making-a-pack.md)

# 制作 GXA pack

pack 是玩家放在 ROM 旁边的 `.gxa` 文件，本质是一个 zip，里面是 Ogg Vorbis 音频加一个 `manifest.json`（SPEC.md §4）。
用 `tools/gxa_pack.py` 打包，它会检查所有规则。

## 1. 准备目录

```
my-pack/
  manifest.json
  bgm/title.wav
  bgm/field.flac
  voice/0001.ogg
```

WAV 和 FLAC 会被编码成 Ogg Vorbis，Ogg 文件原样放入。单声道、立体声都可以，采样率不限。

## 2. 编写 manifest.json

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

- `tracks`：曲目 id（和 ROM 里用的一致）→ 文件。`loop` 是循环命令跳回的采样帧，按文件自身的采样率计；不写（或写 `0`）时循环从头开始。
  `gain` 的单位是 dB。背景音乐通常用循环命令播放，记得给 BGM 曲目设置 loop 点。
- `match`：哪些 ROM 会加载这个 pack，二选一：

| 规则 | 适用场景 |
|---|---|
| `{"sha1": "..."}` | 精确对应某一个 ROM 文件，比如打好补丁的发布版。改动任何一个字节都会匹配不上。 |
| `{"code": "...", "title": "..."}` + `version` | 你自己的 ROM，每次发布都递增文件头的版本字节（`0xBC`）。`"version": 1` 表示 1 及以后的所有版本。 |

code 是 `0xAC` 处的 4 个字节，title 是 `0xA0` 处的 12 个字节。hack 会沿用原游戏的 code 和 title，所以应该用 `sha1` 匹配；
如果你会递增版本字节，也可以用 `version` 匹配。最终 ROM 的 SHA-1 用 `shasum -a 1 game.gba` 获取（Windows：`certutil -hashfile game.gba SHA1`）。

## 3. 打包并检查

```sh
pip install -r tools/requirements.txt
python3 tools/gxa_pack.py my-pack my-game.gxa            # --quality 0-1，默认 0.4
python3 tools/gxa_info.py my-game.gxa
```

`gxa_pack.py` 会列出所有问题（文件缺失、loop 超出曲目长度、id 不合法、`match` 为空），只要还有问题就不会生成文件。

## 4. 发布

pack 的文件名和 ROM 保持一致：`my-game.gba` 会自动加载同目录下的 `my-game.gxa`（SPEC.md §5）。把 pack 和补丁或 ROM 放在一起发布。
不要放入你没有权利分发的音频。

## 更新

一个游戏只有一个 pack。音频有改动时，重新发布整个 pack。曲目 id 一旦在已发布的 ROM 里用过，含义就不能再变：重做的台词和新音乐都用新 id。
新版 ROM 配旧版 pack 也能正常运行：pack 里没有的曲目会读到 missing，ROM 对这些曲目回落到原来的声音。
