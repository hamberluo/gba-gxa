// SPDX-License-Identifier: MIT
// GXA example: a game with its own (PSG) background music hands it to GXA when it can.
//
// Two scenes: the title (track 1) and, after START, the field (track 2). Every BGM change goes through
// bgm_start(), which tries GXA first and falls back to the game's own music when there is no GXA, no pack,
// or no such track in the pack. Every BGM stop goes through bgm_stop(), which stops both.
#include "gxa.h"

#define REG16(a) (*(volatile unsigned short*) (a))
#define DISPCNT REG16(0x04000000)
#define VCOUNT REG16(0x04000006)
#define KEYINPUT REG16(0x04000130)
#define KEY_START 0x0008
#define VRAM ((volatile unsigned short*) 0x06000000)

// PSG channel 1 (square), the game's own music
#define SOUND1CNT_L REG16(0x04000060)
#define SOUND1CNT_H REG16(0x04000062)
#define SOUND1CNT_X REG16(0x04000064)
#define SOUNDCNT_L REG16(0x04000080)
#define SOUNDCNT_H REG16(0x04000082)
#define SOUNDCNT_X REG16(0x04000084)

#define BGM_CH 0   // the GXA channel used for music
#define NOTE_FRAMES 15

enum { SCENE_TITLE, SCENE_FIELD };

// The GXA track for each scene's music (the pack's manifest maps these ids to files)
static const unsigned short bgm_track[] = { 1, 2 };

// Rates for SOUND1CNT_X: 2048 - 131072 / Hz
static const unsigned short tune_title[] = { 1797, 1849, 1881, 1899, 1881, 1849, 0 };   // C5 E5 G5 A5 G5 E5
static const unsigned short tune_field[] = { 1923, 1881, 1849, 1881, 1923, 1936, 0 };   // C6 G5 E5 G5 C6 D6

static const unsigned short* psg_tune;
static int psg_note, psg_wait;

static void psg_play(int scene) {
	SOUNDCNT_X = 0x0080;      // sound on
	SOUNDCNT_L = 0x1177;      // PSG channel 1 left and right, full volume
	SOUNDCNT_H = 0x0002;      // PSG at 100 %
	SOUND1CNT_L = 0;          // no sweep
	SOUND1CNT_H = 0xA080;     // envelope 10, duty 50 %
	psg_tune = scene == SCENE_TITLE ? tune_title : tune_field;
	psg_note = 0;
	psg_wait = 0;
}

static void psg_stop(void) {
	psg_tune = 0;
	SOUND1CNT_H = 0;          // envelope 0: silent
	SOUND1CNT_X = 0x8000;
}

static void psg_tick(void) {
	if (!psg_tune || psg_wait--) {
		return;
	}
	if (!psg_tune[psg_note]) {
		psg_note = 0;         // loop
	}
	SOUND1CNT_X = 0x8000 | psg_tune[psg_note++];
	psg_wait = NOTE_FRAMES - 1;
}

static void bgm_start(int scene) {
	if (gxa_has_pack()) {
		gxa_loop(BGM_CH, bgm_track[scene]);
		if (gxa_started(BGM_CH)) {
			psg_stop();
			return;
		}
	}
	psg_play(scene);          // no GXA, no pack, or the track is missing
}

static void bgm_stop(void) {
	if (gxa_has_pack()) {
		gxa_stop(BGM_CH);
	}
	psg_stop();
}

static void frame(void) {
	while (VCOUNT >= 160) {}
	while (VCOUNT < 160) {}
}

static void fill(unsigned short color) {
	int i;
	for (i = 0; i < 240 * 160; ++i) {
		VRAM[i] = color;
	}
}

int main(void) {
	DISPCNT = 0x0403;         // mode 3, BG2
	fill(0x5000);             // title: blue
	bgm_start(SCENE_TITLE);
	for (;;) {
		frame();
		psg_tick();
		if (!(KEYINPUT & KEY_START)) {
			break;
		}
	}
	bgm_stop();
	fill(0x0280);             // field: green
	bgm_start(SCENE_FIELD);
	for (;;) {
		frame();
		psg_tick();
	}
}
