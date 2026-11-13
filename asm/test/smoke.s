/* SPDX-License-Identifier: MIT
 * Runs asm/gxa.s on a GXA emulator with the conformance pack (track 1 exists, track 7 does not) and reports
 * through GXA itself: channel 3's TRACK register (RW) ends as 0x100 | detect | started(1) << 1 | started(7) << 2,
 * so 0x103 (259) with the pack, 0x100 (256) without. Channel 0 loops track 1; channel 1 asked for track 7. */
	.thumb
	.global main
	.thumb_func
main:
	push	{r4, lr}
	bl	gxa_detect
	mov	r4, r0
	cmp	r0, #0
	beq	smoke_report
	mov	r0, #0
	mov	r1, #1
	mov	r2, #1
	bl	gxa_play_track
	lsl	r0, r0, #1
	orr	r4, r0
	mov	r0, #1
	mov	r1, #7
	mov	r2, #0
	bl	gxa_play_track
	lsl	r0, r0, #2
	orr	r4, r0
smoke_report:
	mov	r0, #1
	lsl	r0, r0, #8
	orr	r4, r0
	ldr	r3, =0x04FFFA40		/* channel 3 TRACK */
	strh	r4, [r3, #0]
smoke_wait:
	b	smoke_wait
	.pool

	.include "gxa.s"
