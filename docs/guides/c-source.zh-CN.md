[English](c-source.md)

# 从 C 源码给游戏接入 GXA

适用于 homebrew 和 decomp 项目，也就是游戏由你自己编译的情况。如果你只有 ROM，请看
[binary-m4a-hook.zh-CN.md](binary-m4a-hook.zh-CN.md)。

可运行的示例在 [examples/homebrew-bgm](../../examples/homebrew-bgm)：一个很小的 ROM，两个场景的音乐能用
GXA 就用 GXA，不能用就用 GBA 自己的声音。

## 1. 加入头文件

把 [include/gxa.h](../../include/gxa.h) 复制进项目。它只有一个文件，C89，不依赖 `stdint.h`。已经用 gcc 按
C89、C99 和 C++ 测试过；它也是按 agbcc（pret 系 decomp 项目用的编译器）的要求写的，但还没有用 agbcc 实测，如果编译出错请当作 bug 报告。

## 2. 找到音乐开始播放的那一处

大多数游戏的所有歌曲都通过一两个函数开始播放。m4a（Sappy）游戏的 decomp 里是 `m4aSongNumStart`，或者包着它的
`PlayBGM` 之类。自己写的引擎里，就是负责开始播放歌曲的那个函数。

把 GXA 放在这个函数前面，不要在每个调用点各加一遍。停止音乐的函数也一样处理。

## 3. 先试 GXA，不行再回落

```c
#include "gxa.h"

void bgm_start(int song) {
    unsigned short track = track_for_song(song);   // 0 = 这首歌继续用 GBA 自己的声音
    if (gxa_has_pack()) {
        if (track) {
            gxa_loop(0, track);
            if (gxa_started(0)) {
                original_stop();                     // 确保原来的音乐没有同时在播
                return;
            }
        } else {
            gxa_stop(0);                             // 没映射的歌：之前的 GXA 曲目不能继续播
        }
    }
    original_start(song);                            // 没有 GXA、没有 pack，或 pack 里没有这首
}

void bgm_stop(void) {
    if (gxa_has_pack()) {
        gxa_stop(0);
    }
    original_stop();
}
```

这段写法适用于你自己写的引擎，也就是没有别的代码会去查询音乐播放器的情况。在 m4a 的 decomp 里，游戏代码会检查播放器状态
（比如 `gMPlayInfo_BGM.status`：标题曲播完就离开标题画面），所以不能跳过原曲，而是照常开始播放，再把它静音。GXA 曲目开始播放后：

```c
m4aSongNumStart(song);                               // 游戏自己的歌，照常开始
if (gMPlayInfo_BGM.songHeader == gSongTable[song].header) {   // 播放器接受了这首歌
    gMPlayInfo_BGM.tone = gGxaSilentVoices;          // 128 个 ToneData，全部指向一个静音采样
}
```

这几行前后要关中断（`REG_IME = 0`），避免声音驱动在中间先把这首歌的乐器加载进去。
[examples/binary-hook/hook.asm](../../examples/binary-hook/hook.asm) 用汇编做了同样的事，包括静音音色表，以及暂停和继续的处理。

遵守下面三条，在任何环境下都不会出问题：

- **没有 GXA 或没有 pack**：在真机上、在不支持 GXA 的模拟器里、或者玩家没加载 pack 时，`gxa_has_pack()` 都返回 0，
  游戏和原来完全一样。
- **缺曲目**：pack 可能比 ROM 旧，也可能故意少放几首。`gxa_started()` 在播放命令之后立刻读通道状态；缺失的曲目会立刻读到
  `missing | ended`（SPEC.md §3），所以这个检查不会等待。
- **两边都要停**：所有停止或切换音乐的路径都要同时停掉 GXA 通道，否则旧曲目会在新场景底下继续播：没映射的歌、停止、全部停止、
  暂停（GXA 通道也要暂停），以及淡出（用 `gxa_fade(0, 0, ms)`，音量淡到 0 时通道会自动停止）。

## 4. 选择曲目 id

曲目 id 由你决定，范围 1–65535。最简单的做法是直接用游戏自己的歌曲编号。某个 id 一旦在发布的 ROM 里用过，就不要改变它的含义：
新增或重做的音频用新 id（SPEC.md §4 "Updating a game"）。

## 5. 语音和一次性音效

用其他通道（1–3），把 `gxa_loop` 换成 `gxa_play`。要等一句台词播完，就等 `gxa_state(ch) & GXA_ENDED`。曲目缺失或损坏时也会置
ended，所以这个等待一定会结束。

## 6. 打包和测试

打包方法见 [making-a-pack.zh-CN.md](making-a-pack.zh-CN.md)。发布前按三种方式各测一次：

| 测试方式 | 预期 |
|---|---|
| GXA 模拟器 + 完整 pack | 播 GXA 音乐，底下没有原来的音乐 |
| 同上，但 pack 里删掉一首 | 那个场景播原来的音乐 |
| 不支持 GXA 的模拟器，或不放 pack | 游戏和原来完全一样 |

示例项目里对应的命令是 `python3 make_pack.py out.gxa` 和 `python3 make_pack.py --without 2 out.gxa`。
