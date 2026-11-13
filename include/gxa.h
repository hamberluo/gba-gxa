/* SPDX-License-Identifier: MIT */
/*
 * gxa.h: GXA 1.0 for GBA ROMs, in one header. See SPEC.md for the standard.
 *
 * Works with gcc, clang and agbcc (decomp projects): C89, no stdint.h.
 *
 *     #include "gxa.h"
 *
 *     if (gxa_has_pack()) {            // GXA emulator with this ROM's pack
 *         gxa_loop(0, 42);              // track 42 on channel 0, looped
 *         if (!gxa_started(0)) {
 *             play_original_music();    // track missing: keep the old sound
 *         }
 *     } else {
 *         play_original_music();        // hardware, or no GXA: as before
 *     }
 */
#ifndef GXA_H
#define GXA_H

typedef unsigned short gxa_u16;
typedef unsigned long gxa_u32;

#define GXA_BASE 0x04FFFA00UL
#define GXA_REG(off) (*(volatile gxa_u16 *) (GXA_BASE + (unsigned long) (off)))

/* Global registers */
#define GXA_ID0 0x00
#define GXA_ID1 0x02
#define GXA_HANDSHAKE 0x04
#define GXA_VERSION 0x06
#define GXA_STATUS 0x08
#define GXA_GAMEVOL 0x0A
#define GXA_DUCK 0x0C

/* Channel n (0-3) registers: GXA_REG(GXA_CH(n) + GXA_TRACK) */
#define GXA_CHANNELS 4
#define GXA_CH(n) (0x10 + 0x10 * (n))
#define GXA_TRACK 0x0
#define GXA_CTRL 0x2
#define GXA_VOL 0x4
#define GXA_FADE 0x6
#define GXA_STATE 0x8
#define GXA_POS 0xC

/* CTRL commands */
#define GXA_PLAY 1
#define GXA_LOOP 2
#define GXA_STOP 3
#define GXA_PAUSE 4
#define GXA_RESUME 5

/* STATE bits */
#define GXA_PLAYING 1
#define GXA_PAUSED 2
#define GXA_ENDED 4
#define GXA_MISSING 8
#define GXA_ERROR 16

/* Volumes: 0-256, 256 = unchanged */
#define GXA_UNITY 256

#if defined(__GNUC__)
#define GXA_FN static __attribute__((unused))
#else
#define GXA_FN static
#endif

/* 1 on a GXA 1.x emulator, else 0 (hardware, other emulators). */
GXA_FN int gxa_detect(void) {
	GXA_REG(GXA_HANDSHAKE) = 0x1234;
	return GXA_REG(GXA_HANDSHAKE) == (0x1234 ^ 0x5847) && (GXA_REG(GXA_VERSION) >> 8) == 1;
}

/* 1 when GXA is there and a pack for this ROM is loaded. Treat 0 like no GXA. */
GXA_FN int gxa_has_pack(void) {
	return gxa_detect() && (GXA_REG(GXA_STATUS) & 1);
}

GXA_FN void gxa_play(int ch, gxa_u16 track) {
	GXA_REG(GXA_CH(ch) + GXA_TRACK) = track;
	GXA_REG(GXA_CH(ch) + GXA_CTRL) = GXA_PLAY;
}

GXA_FN void gxa_loop(int ch, gxa_u16 track) {
	GXA_REG(GXA_CH(ch) + GXA_TRACK) = track;
	GXA_REG(GXA_CH(ch) + GXA_CTRL) = GXA_LOOP;
}

GXA_FN void gxa_stop(int ch) {
	GXA_REG(GXA_CH(ch) + GXA_CTRL) = GXA_STOP;
}

/* Ramp the channel's volume to vol over ms milliseconds. A ramp to 0 stops it. */
GXA_FN void gxa_fade(int ch, gxa_u16 vol, gxa_u16 ms) {
	GXA_REG(GXA_CH(ch) + GXA_FADE) = ms;
	GXA_REG(GXA_CH(ch) + GXA_VOL) = vol;
}

GXA_FN gxa_u16 gxa_state(int ch) {
	return GXA_REG(GXA_CH(ch) + GXA_STATE);
}

/* Milliseconds played since the last play command. */
GXA_FN gxa_u32 gxa_pos(int ch) {
	gxa_u32 lo = GXA_REG(GXA_CH(ch) + GXA_POS);
	return lo | (gxa_u32) GXA_REG(GXA_CH(ch) + GXA_POS + 2) << 16;
}

/* Right after gxa_play/gxa_loop: 1 if the track is playing, 0 if it is missing or
 * broken (the ROM should then play its own sound instead). */
GXA_FN int gxa_started(int ch) {
	gxa_u16 s = gxa_state(ch);
	return (s & GXA_PLAYING) && !(s & (GXA_MISSING | GXA_ERROR));
}

#endif
