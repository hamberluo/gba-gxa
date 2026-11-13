/* SPDX-License-Identifier: MIT
 * A stand-in for the m4a library, for testing hook.asm without a commercial ROM.
 * The song functions, MPlayStop and MPlayContinue begin with the same instructions as the real library
 * (what m4a_locate.py looks for and hook.asm relocates); their bodies only keep the state the test needs:
 * MPlayStart refuses a song of lower priority than a playing one, MPlayStop/MPlayContinue set and clear
 * the pause bit. Songs: 1 (player 0, priority 0), 2 (player 0, priority 10), 3 (player 0, priority 0),
 * 4 and 5 (player 1).
 *
 * main runs a script, one step every 30 frames: it writes the step number to GXA channel 3's TRACK register
 * (0x100 | step), waits a frame, then acts. Step 10 reports 0x200 | bits: 1 = player 0's voice table is
 * song 2's own (not muted), 2 = player 1 was paused by the original m4aSongNumStop.
 */
	.thumb
	.equ	ID, 0x68736D53
	.equ	INFO0, 0x02000200
	.equ	INFO1, 0x02000300
	.equ	VCOUNT, 0x04000006

	.global	main
	.thumb_func
main:
	ldr	r1, =ID
	ldr	r0, =INFO0
	str	r1, [r0, #0x34]		/* ident */
	ldr	r0, =INFO1
	str	r1, [r0, #0x34]
	mov	r0, #1
	bl	step			/* 1: start song 1 */
	mov	r0, #1
	bl	m4aSongNumStart
	mov	r0, #2
	bl	step			/* 2: pause the BGM player */
	ldr	r0, =INFO0
	bl	MPlayStop
	mov	r0, #3
	bl	step			/* 3: continue it */
	ldr	r0, =INFO0
	bl	MPlayContinue
	mov	r0, #4
	bl	step			/* 4: start song 2 (priority 10, unmapped) */
	mov	r0, #2
	bl	m4aSongNumStart
	mov	r0, #5
	bl	step			/* 5: start song 3 (priority 0, mapped): MPlayStart refuses it */
	mov	r0, #3
	bl	m4aSongNumStart
	mov	r0, #6
	bl	step			/* 6: song 4 on player 1 (a voice line, mapped) */
	mov	r0, #4
	bl	m4aSongNumStart
	mov	r0, #7
	bl	step			/* 7: song 5 on player 1 (unmapped) interrupts it */
	mov	r0, #5
	bl	m4aSongNumStart
	mov	r0, #8
	bl	step			/* 8: song 4 again */
	mov	r0, #4
	bl	m4aSongNumStart
	mov	r0, #9
	bl	step			/* 9: m4aSongNumStop(4) */
	mov	r0, #4
	bl	m4aSongNumStop
	mov	r0, #10
	bl	step			/* 10: report */
	ldr	r0, =INFO0		/* bit 0: is player 0's voice table still song 2's? */
	ldr	r1, [r0, #0x30]
	ldr	r2, =song2
	ldr	r2, [r2, #4]
	mov	r3, #0
	cmp	r1, r2
	bne	1f
	mov	r3, #1
1:	ldr	r0, =INFO1		/* bit 1: did the original m4aSongNumStop(4) pause player 1? */
	ldr	r1, [r0, #4]
	lsr	r1, r1, #31
	lsl	r1, r1, #1
	orr	r3, r1
	mov	r0, #2
	lsl	r0, r0, #8
	orr	r0, r3
	ldr	r1, =0x04FFFA40
	strh	r0, [r1]
2:	b	2b

/* waits 30 frames, reports step r0 in channel 3's TRACK, then waits one more frame */
	.thumb_func
step:
	push	{r4, lr}
	mov	r4, #30
	bl	frames
	mov	r1, #1
	lsl	r1, r1, #8
	orr	r0, r1
	ldr	r1, =0x04FFFA40
	strh	r0, [r1]
	mov	r4, #1
	bl	frames
	pop	{r4}
	pop	{r0}
	bx	r0

/* waits r4 frames; keeps r0 */
	.thumb_func
frames:
1:	ldr	r1, =VCOUNT
2:	ldrh	r2, [r1]
	cmp	r2, #160
	bge	2b
3:	ldrh	r2, [r1]
	cmp	r2, #160
	blt	3b
	sub	r4, #1
	bne	1b
	bx	lr
	.pool

/* ---- the library ---- */
	.align	2
	.thumb_func
m4aSongNumStart:
	push	{lr}
	lsl	r0, r0, #16
	ldr	r2, =players
	ldr	r1, =songs
	lsr	r0, r0, #13
	add	r0, r0, r1
	ldrh	r3, [r0, #4]
	lsl	r1, r3, #1
	add	r1, r1, r3
	lsl	r1, r1, #2
	add	r1, r1, r2
	ldr	r2, [r1]
	ldr	r1, [r0]
	add	r0, r2, #0
	bl	MPlayStart
	pop	{r0}
	bx	r0
	.pool

	.align	2
	.thumb_func
m4aSongNumStartOrChange:
	push	{lr}
	lsl	r0, r0, #16
	ldr	r2, =players
	ldr	r1, =songs
	lsr	r0, r0, #13
	add	r0, r0, r1
	ldrh	r3, [r0, #4]
	lsl	r1, r3, #1
	add	r1, r1, r3
	lsl	r1, r1, #2
	add	r1, r1, r2
	ldr	r1, [r1]
	ldr	r3, [r1]
	ldr	r2, [r0]
	cmp	r3, r2
	beq	1f
	add	r0, r1, #0
	add	r1, r2, #0
	bl	MPlayStart
1:	pop	{r0}
	bx	r0
	.pool

	.align	2
	.thumb_func
m4aSongNumStartOrContinue:
	push	{lr}
	lsl	r0, r0, #16
	ldr	r2, =players
	ldr	r1, =songs
	lsr	r0, r0, #13
	add	r0, r0, r1
	ldrh	r3, [r0, #4]
	lsl	r1, r3, #1
	add	r1, r1, r3
	lsl	r1, r1, #2
	add	r1, r1, r2
	ldr	r1, [r1]
	ldr	r3, [r1]
	ldr	r2, [r0]
	cmp	r3, r2
	beq	1f
	add	r0, r1, #0
	add	r1, r2, #0
	bl	MPlayStart
	b	2f
1:	add	r0, r1, #0
	bl	MPlayContinue
2:	pop	{r0}
	bx	r0
	.pool

	.align	2
	.thumb_func
m4aSongNumStop:
	push	{lr}
	lsl	r0, r0, #16
	ldr	r2, =players
	ldr	r1, =songs
	lsr	r0, r0, #13
	add	r0, r0, r1
	ldrh	r3, [r0, #4]
	lsl	r1, r3, #1
	add	r1, r1, r3
	lsl	r1, r1, #2
	add	r1, r1, r2
	ldr	r2, [r1]
	ldr	r1, [r2]
	ldr	r0, [r0]
	cmp	r1, r0
	bne	1f
	add	r0, r2, #0
	bl	MPlayStop
1:	pop	{r0}
	bx	r0
	.pool

	.align	2
	.thumb_func
m4aSongNumContinue:
	push	{lr}
	lsl	r0, r0, #16
	ldr	r2, =players
	ldr	r1, =songs
	lsr	r0, r0, #13
	add	r0, r0, r1
	ldrh	r3, [r0, #4]
	lsl	r1, r3, #1
	add	r1, r1, r3
	lsl	r1, r1, #2
	add	r1, r1, r2
	ldr	r2, [r1]
	ldr	r1, [r2]
	ldr	r0, [r0]
	cmp	r1, r0
	bne	1f
	add	r0, r2, #0
	bl	MPlayContinue
1:	pop	{r0}
	bx	r0
	.pool

/* MPlayStart(info, header): refuses a lower-priority song while one plays */
	.align	2
	.thumb_func
MPlayStart:
	ldr	r2, [r0, #4]
	cmp	r2, #0
	beq	1f
	ldrb	r2, [r1, #2]
	ldrb	r3, [r0, #9]
	cmp	r2, r3
	blt	2f
1:	str	r1, [r0, #0]
	mov	r2, #1
	str	r2, [r0, #4]
	ldrb	r2, [r1, #2]
	strb	r2, [r0, #9]
	ldr	r2, [r1, #4]
	str	r2, [r0, #0x30]
2:	bx	lr

	.align	2
	.thumb_func
MPlayStop:
	push	{r4-r6, lr}
	add	r6, r0, #0
	ldr	r1, [r6, #0x34]
	ldr	r0, =ID
	cmp	r1, r0
	bne	1f
	ldr	r0, [r6, #4]
	mov	r1, #0x80
	lsl	r1, r1, #24
	orr	r0, r1
	str	r0, [r6, #4]
1:	pop	{r4-r6}
	pop	{r0}
	bx	r0
	.pool

	.align	2
	.thumb_func
MPlayContinue:
	add	r2, r0, #0
	ldr	r3, [r2, #0x34]
	ldr	r0, =ID
	cmp	r3, r0
	bne	1f
	ldr	r0, [r2, #4]
	ldr	r1, =0x7FFFFFFF
	and	r0, r1
	str	r0, [r2, #4]
1:	bx	lr
	.pool

/* ---- data ---- */
	.align	2
players:
	.word	INFO0, 0x02000400, 0x00000004
	.word	0x02000300, 0x02000500, 0x00000004
songs:
	.word	song0
	.hword	0, 0
	.word	song1
	.hword	0, 0
	.word	song2
	.hword	0, 0
	.word	song3
	.hword	0, 0
	.word	song4
	.hword	1, 1
	.word	song5
	.hword	1, 1
song0:	.byte	1, 0, 0, 0
	.word	voices0
song1:	.byte	1, 0, 0, 0
	.word	voices1
song2:	.byte	1, 0, 10, 0
	.word	voices2
song3:	.byte	1, 0, 0, 0
	.word	voices3
song4:	.byte	1, 0, 0, 0
	.word	voices4
song5:	.byte	1, 0, 0, 0
	.word	voices5
voices4: .word 4
voices5: .word 5
voices0: .word 0
voices1: .word 1
voices2: .word 2
voices3: .word 3
