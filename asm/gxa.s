/* SPDX-License-Identifier: MIT
 *
 * gxa.s: GXA 1.0 routines for binary hacks (SPEC.md). Thumb code, written in the syntax that armips and
 * GNU as both accept, so it can be .include'd from an armips patch or assembled with arm-none-eabi-as.
 *
 * Call them with bl. They use only r0-r3 and return with bx lr.
 *
 *   gxa_detect       -> r0 = 1 when a GXA emulator has a pack for this ROM loaded, else 0.
 *                       Treat 0 as "no GXA": run the game's original code.
 *   gxa_play_track   r0 = channel (0-3), r1 = track id, r2 = 1 to loop / 0 to play once
 *                    -> r0 = 1 if the track started, 0 if it is missing or broken (then fall back).
 *   gxa_stop         r0 = channel (0-3).
 *
 * All register accesses are 16-bit (strh/ldrh), as SPEC.md §1 requires.
 */

	.thumb
	.align 2

gxa_detect:
	ldr	r3, =0x04FFFA00
	ldr	r0, =0x1234
	strh	r0, [r3, #4]		/* HANDSHAKE = 0x1234 */
	ldrh	r1, [r3, #4]
	ldr	r2, =0x4A73		/* 0x1234 ^ 0x5847 */
	mov	r0, #0
	cmp	r1, r2
	bne	gxa_detect_done
	ldrh	r1, [r3, #6]		/* VERSION: major 1 */
	lsr	r1, r1, #8
	cmp	r1, #1
	bne	gxa_detect_done
	ldrh	r1, [r3, #8]		/* STATUS bit 0: a pack is loaded */
	mov	r0, #1
	and	r0, r1
gxa_detect_done:
	bx	lr

gxa_play_track:
	ldr	r3, =0x04FFFA10
	lsl	r0, r0, #4
	add	r3, r3, r0		/* r3 = channel registers */
	strh	r1, [r3, #0]		/* TRACK */
	mov	r0, #1			/* play */
	cmp	r2, #0
	beq	gxa_play_track_cmd
	mov	r0, #2			/* loop */
gxa_play_track_cmd:
	strh	r0, [r3, #2]		/* CTRL */
	ldrh	r1, [r3, #8]		/* STATE */
	mov	r0, #0x18		/* missing | error */
	tst	r1, r0
	bne	gxa_play_track_no
	mov	r0, #1			/* playing */
	and	r0, r1
	bx	lr
gxa_play_track_no:
	mov	r0, #0
	bx	lr

gxa_stop:
	ldr	r3, =0x04FFFA10
	lsl	r0, r0, #4
	add	r3, r3, r0
	mov	r0, #3			/* stop */
	strh	r0, [r3, #2]
	bx	lr

	.pool
