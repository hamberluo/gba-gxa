// SPDX-License-Identifier: MIT
// GXA conformance ROM (SPEC.md). Each case draws a 16 px row, green on pass and red on fail, and sets
// its bit in the result block at 0x02000100 (magic "GXAR", pass bits, done, case count) for automated runs.
// Needs its pack (gxa-conformance.gxa): track 1 is 1.0 s, track 2 a 0.5 s loop, track 7 is listed nowhere.
#include <stdint.h>

#include "gxa.h"

#define REG16(a) (*(volatile uint16_t*) (a))
#define REG32(a) (*(volatile uint32_t*) (a))
#define GXA(off) GXA_REG(off)
#define GXA32(off) REG32(GXA_BASE + (off))   // the store-order case needs a real 32-bit store
#define CH(n, off) (GXA_CH(n) + (off))
enum { TRACK = GXA_TRACK, CTRL = GXA_CTRL, VOL = GXA_VOL, FADE = GXA_FADE, STATE = GXA_STATE, POS = GXA_POS };
enum { PLAYING = GXA_PLAYING, PAUSED = GXA_PAUSED, ENDED = GXA_ENDED, MISSING = GXA_MISSING };

#define DISPCNT REG16(0x04000000)
#define VCOUNT REG16(0x04000006)
#define VRAM ((volatile uint16_t*) 0x06000000)
#define RESULT ((volatile uint32_t*) 0x02000100)
#define CASES 8

static void frame(void) {
	while (VCOUNT >= 160) {}
	while (VCOUNT < 160) {}
}

static void frames(int n) {
	while (n--) {
		frame();
	}
}

static void row(int i, uint16_t color) {
	volatile uint16_t* p = &VRAM[i * 16 * 240];
	int y, x;
	for (y = 1; y < 15; ++y) {
		for (x = 4; x < 236; ++x) {
			p[y * 240 + x] = color;
		}
	}
}

static void report(int i, int pass) {
	if (pass) {
		RESULT[1] |= 1u << i;
	}
	row(i, pass ? 0x03E0 : 0x001F);
}

static uint32_t pos(int ch) {
	return gxa_pos(ch);
}

static int handshake(void) {
	return gxa_detect() && GXA(GXA_ID0) == 0x5847 && GXA(GXA_ID1) == 0x3141 && GXA(GXA_VERSION) == 0x0100;
}

static int status(void) {
	return gxa_has_pack() && GXA(GXA_STATUS) == 0x0401;
}

static int length(void) {
	gxa_play(0, 1);
	int n = 0;
	while (GXA(CH(0, STATE)) & PLAYING && n < 120) {
		frame();
		++n;
	}
	// 1.000 s is 59.7 frames of 16.74 ms: within 50 ms
	return GXA(CH(0, STATE)) == ENDED && n >= 57 && n <= 63;
}

static int missing(void) {
	gxa_play(1, 7);
	return GXA(CH(1, STATE)) == (MISSING | ENDED) && !gxa_started(1);
}

static int loop(void) {
	gxa_loop(2, 2);
	int started = gxa_started(2);
	frames(72);   // 1.2 s: past twice the track
	int ok = started && GXA(CH(2, STATE)) == PLAYING && pos(2) >= 1100;
	gxa_stop(2);
	return ok && GXA(CH(2, STATE)) == 0;
}

static int pause(void) {
	gxa_play(3, 1);
	frames(10);
	GXA(CH(3, CTRL)) = 4;
	uint32_t held = pos(3);
	frames(10);
	int ok = GXA(CH(3, STATE)) == PAUSED && pos(3) == held && held > 100;
	GXA(CH(3, CTRL)) = 5;
	frames(5);
	ok = ok && GXA(CH(3, STATE)) == PLAYING && pos(3) > held;
	gxa_stop(3);
	return ok;
}

static int volumes(void) {
	GXA(0xA) = 200;
	GXA(0xC) = 64;
	int ok = GXA(0xA) == 200 && GXA(0xC) == 64;
	GXA(0xA) = 256;
	GXA(0xC) = 256;
	return ok && GXA(0xA) == 256;
}

static int store32(void) {
	GXA32(CH(0, TRACK)) = (1u << 16) | 1;   // TRACK, then CTRL = play
	int ok = GXA(CH(0, STATE)) == PLAYING && GXA(CH(0, TRACK)) == 1;
	GXA(CH(0, CTRL)) = 3;
	return ok;
}

int main(void) {
	DISPCNT = 0x0403;   // mode 3, BG2
	RESULT[0] = 0x52415847;   // "GXAR"
	RESULT[1] = 0;
	RESULT[2] = 0;
	RESULT[3] = CASES;
	int i;
	for (i = 0; i < CASES; ++i) {
		row(i, 0x4210);
	}
	int (*const cases[CASES])(void) = { handshake, status, length, missing, loop, pause, volumes, store32 };
	for (i = 0; i < CASES; ++i) {
		// without GXA the rest cannot pass: report them failed at once
		report(i, (i == 0 || (RESULT[1] & 1)) && cases[i]());
	}
	row(CASES, 0x7FFF);
	RESULT[2] = 1;
	for (;;) {
		frame();
	}
}
