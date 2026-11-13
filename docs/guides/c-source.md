[中文](c-source.zh-CN.md)

# Adding GXA to a game you build from C source

For homebrew and decomp projects: anything where you compile the game yourself. If you only have the ROM,
read [binary-m4a-hook.md](binary-m4a-hook.md) instead.

The working example is [examples/homebrew-bgm](../../examples/homebrew-bgm): a tiny ROM whose two scenes
play their music from GXA when they can and from the GBA's own sound when they cannot.

## 1. Add the header

Copy [include/gxa.h](../../include/gxa.h) into your project. It is one file, C89, with no `stdint.h`. It is
tested with gcc as C89, C99 and C++; it is written for agbcc (the compiler of the pret decomp projects) too,
but not yet tested with it, so report a build error there as a bug.

## 2. Find the one place your music starts

Most games start every song through one or two functions. In a decomp of an m4a (Sappy) game that is
`m4aSongNumStart`, or a wrapper around it such as `PlayBGM`. In your own engine it is whatever starts a song.

Put GXA in front of that function, not next to every call. Do the same for the function that stops music.

## 3. Try GXA, fall back to the original

```c
#include "gxa.h"

void bgm_start(int song) {
    unsigned short track = track_for_song(song);   // 0 = this song stays on the GBA's own sound
    if (gxa_has_pack()) {
        if (track) {
            gxa_loop(0, track);
            if (gxa_started(0)) {
                original_stop();                     // make sure the old music is not playing too
                return;
            }
        } else {
            gxa_stop(0);                             // unmapped song: the previous GXA track must not go on
        }
    }
    original_start(song);                            // no GXA, no pack, or the pack lacks this track
}

void bgm_stop(void) {
    if (gxa_has_pack()) {
        gxa_stop(0);
    }
    original_stop();
}
```

This is for your own engine, where nothing else looks at the music player. In an m4a decomp, game code
checks the player (`gMPlayInfo_BGM.status`, for example to leave the title screen when its song ends), so
do not skip the original song there: start it as before, then mute it. With the GXA track started:

```c
m4aSongNumStart(song);                               // the game's own song, as before
if (gMPlayInfo_BGM.songHeader == gSongTable[song].header) {   // the player took it
    gMPlayInfo_BGM.tone = gGxaSilentVoices;          // 128 ToneData entries of a silent sample
}
```

Turn interrupts off (`REG_IME = 0`) around those lines so the sound driver does not start the song's
instruments in between. [examples/binary-hook/hook.asm](../../examples/binary-hook/hook.asm) does the same
in assembly, including the silent voice table and the pause and continue paths.

Three rules make this safe everywhere:

- **No GXA, no pack:** `gxa_has_pack()` is 0 on hardware, on emulators without GXA, and when the player has
  not loaded a pack. The game then runs exactly as before.
- **Missing track:** a pack may be older than the ROM, or leave some songs out. `gxa_started()` reads the
  channel right after the play command; a missing track reads `missing | ended` at once (SPEC.md §3), so
  the check never waits.
- **Stop both:** every path that stops or changes music must stop the GXA channel as well, or the old track
  keeps playing under the new scene: a song with no track, a stop, stop-all, a pause (pause the channel too)
  and a fade-out (`gxa_fade(0, 0, ms)`; a fade to 0 stops the channel).

## 4. Choose track ids

Track ids are yours, 1–65535. Using the game's own song numbers as track ids is the simplest mapping. Once a
released ROM plays an id, keep its meaning: new or rewritten audio takes a new id (SPEC.md §4, "Updating a
game").

## 5. Voice and one-shot sounds

Use another channel (1–3) and `gxa_play` instead of `gxa_loop`. To wait for a line to finish, wait for
`gxa_state(ch) & GXA_ENDED`. A missing or broken track also sets ended, so the wait always ends.

## 6. Build a pack and test

See [making-a-pack.md](making-a-pack.md). Test three ways before release:

| Run | Expect |
|---|---|
| GXA emulator with the full pack | GXA music, no original music underneath |
| Same, pack with one track removed | that scene plays its original music |
| Emulator without GXA, or no pack | the game exactly as before |

The example does this with `python3 make_pack.py out.gxa` and `python3 make_pack.py --without 2 out.gxa`.
