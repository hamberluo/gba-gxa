/* SPDX-License-Identifier: MIT */
/* Compile check: calls every gxa.h function. Built by compile.sh, never run. */
#include "gxa.h"

int use(void) {
	int r = 0;
	if (gxa_detect() && gxa_has_pack()) {
		gxa_play(0, 1);
		gxa_loop(1, 2);
		gxa_fade(1, 128, 500);
		r += gxa_started(0);
		r += (int) gxa_state(1);
		r += (int) (gxa_pos(1) & 1);
		gxa_stop(0);
	}
	GXA_REG(GXA_GAMEVOL) = 256;
	GXA_REG(GXA_CH(2) + GXA_VOL) = GXA_UNITY;
	return r + (GXA_PLAYING | GXA_PAUSED | GXA_ENDED | GXA_MISSING | GXA_ERROR) + GXA_PAUSE + GXA_RESUME
		+ GXA_ID0 + GXA_ID1 + GXA_HANDSHAKE + GXA_VERSION + GXA_STATUS + GXA_DUCK + GXA_TRACK + GXA_CTRL + GXA_FADE
		+ GXA_STATE + GXA_POS;
}
