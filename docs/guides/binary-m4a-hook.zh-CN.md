[English](binary-m4a-hook.md)

# 只有 ROM 时，给 m4a 游戏接入 GXA

大部分 GBA 商业游戏用任天堂的 m4a 引擎（也叫 Sappy、MusicPlayer2000）放音乐。所有歌曲都通过 `m4aSongNumStart`
或它的几个同类函数开始播放，歌曲编号放在 `r0` 里。本指南给这几个函数打补丁：你指定的歌改为从 GXA pack 播放，其余一切保持原样。

需要准备：装好 `tools/requirements.txt` 依赖的 Python 3；[armips](https://github.com/Kingcom/armips) v0.11（运行
`sh tools/get_armips.sh` 会自动编译）；一个带调试器的模拟器（比如 mGBA），用来找歌曲编号。

如果你是从源码（decomp）编译游戏，请看 [c-source.zh-CN.md](c-source.zh-CN.md)。

## 1. 检查 ROM

```sh
python3 tools/m4a_locate.py game.gba
```

最后一行必须是 `hook: ok`。它会列出各个歌曲函数和歌曲表的地址，以及新代码要放的位置。如果报 "not an m4a game"，说明游戏用的是别的声音引擎，
或者 m4a 被改过（基于 decomp 的 hack 常见这种情况），下面的模板不适用。

## 2. 找到歌曲编号

用 mGBA 打开 ROM，打开调试器，在 `m4a_locate.py` 给出的 `m4aSongNumStart` 地址下断点（很多游戏的地图音乐走
`m4aSongNumStartOrChange` 和 `m4aSongNumStartOrContinue`，这两个也一起下断点）。玩到你想替换音乐的场景，断点触发时 `r0` 就是歌曲编号。

记下每一首要替换的歌，再查它由哪个播放器播放：

```sh
python3 tools/m4a_locate.py --song 413 game.gba
# song 413: player 0 (header 0x08...)
```

标题画面或大地图音乐所用的播放器，就是这个游戏的 BGM 播放器。很多游戏是 0，但不全是；我们测试过的一个游戏是 31。

## 3. 编写补丁

```sh
cd examples/binary-hook
python3 ../../tools/m4a_locate.py --armips /path/to/game.gba > defs.asm
cp example.asm my-hack.asm
```

在 `my-hack.asm` 里填好输入、输出文件名，`BGM_PLAYER` 和映射表：

```
gxa_song_tracks:
	.halfword 413, 1     ; 413 号歌 -> GXA 曲目 1
	.halfword 414, 2
	.halfword 0xFFFF     ; 表结束
```

表里没有的歌照原样播放。

## 4. 编译

```sh
armips my-hack.asm                   # 要在 examples/binary-hook 目录里运行：armips 从这里解析 include 路径
python3 ../../tools/gba_header.py --check game-gxa.gba
```

如果 ROM 末尾没有空闲区，`defs.asm` 里会注明，补丁会把 ROM 往后延长；模拟器和烧录卡都能正常运行。

## 5. 制作 pack

按 [making-a-pack.zh-CN.md](making-a-pack.zh-CN.md) 操作。曲目 id 就是映射表右边那一列。如果你发布的是针对某一个原版 ROM 的补丁或成品
ROM，用打完补丁后 ROM 的 SHA-1 来匹配 pack。

## 6. 三种方式各测一次

| 测试方式 | 预期 |
|---|---|
| GXA 模拟器 + 完整 pack | 播放你的曲目，底下听不到原来的音乐 |
| 同上，但 pack 里删掉一首已映射的曲目 | 那个场景播原来的音乐 |
| 不支持 GXA 的模拟器，或不放 pack | 游戏和原来完全一样 |

## hook 的工作原理

- `m4aSongNumStart`、`...OrChange`、`...OrContinue` 和 `m4aSongNumStop` 开头的 8 个字节被改成一条跳转，跳到空闲区里的新代码。
  `m4a_locate.py` 会先确认这 8 个字节是原版 m4a 的开头；hook 回落时会原样重新执行它们。
- 没有 GXA 或没有 pack 时，hook 直接执行原函数。
- 游戏自己的歌**总是照常开始播放**，所以游戏对音乐的所有判断（是否在播、是否已经播完）都和原来一样。当 GXA 替它播放曲目时，
  hook 会给这个 m4a 播放器换上一张静音音色表，原曲照常推进但没有声音。这个播放器下一次开始播放别的歌时，会自动换回那首歌自己的音色。
  早期版本是直接停掉 m4a 播放器，结果有个游戏以为标题音乐已经播完，又退回了开场动画。
- BGM 播放器上的歌在 GXA 通道 0 循环播放。`...OrChange` 和 `...OrContinue` 遇到正在播的同一首不会重新开始。其他播放器上的歌在通道 1
  播一次，用于语音和短乐句。
- BGM 播放器上没有映射的歌会先停掉通道 0，避免旧的 GXA 音乐叠在新的游戏音乐底下。
- 曲目缺失或损坏时会立刻读到 `missing` 或 `error`（SPEC.md §3），玩家听到的是原曲。

## 限制

- **淡出**：游戏淡出音乐（`m4aMPlayFadeOut`）时，GXA 曲目会一直播到下一首歌开始或停止。尽量映射那些"场景结束时会换歌"的音乐，
  或者把 hook 扩展到你这个游戏的淡出函数上。
- **m4a 被改过**：基于 decomp 的 hack 经常改 m4a 库，这时 `m4a_locate.py` 会拒绝处理。请改用 C 的方式接入。
- **其他声音引擎**：使用自研声音驱动的游戏需要另找 hook 点；[AGENTS.md](../../AGENTS.md) 里的规则同样适用。
