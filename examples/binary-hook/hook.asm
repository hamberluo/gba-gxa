; SPDX-License-Identifier: MIT
;
; hook.asm: GXA for m4a (Sappy) games you only have as a ROM. armips v0.11.
; Guide: docs/guides/binary-m4a-hook.md. Start from example.asm, which includes this file; run armips from
; this directory (or pass -root with it), since armips resolves .include paths from there.
;
; Before including it, define (python3 tools/m4a_locate.py --armips game.gba > defs.asm does all but the last):
;   m4aSongNumStart, m4aSongNumStartOrChange, m4aSongNumStartOrContinue, m4aSongNumStop,
;   PlayerTable, SongTable, PLAYER_REG (2 or 3), FreeSpace, and BGM_PLAYER (the music player's index, usually 0).
; After including it, define the table gxa_song_tracks: .halfword song, track pairs, ended by .halfword 0xFFFF.
;
; The game's own song always starts as before, so everything the game checks about its music (is it playing,
; has it ended) stays true. When GXA plays a track instead, the hook mutes that m4a player.
; On a GXA emulator with a pack:
;   - a song that maps to a track, on the BGM player: GXA channel 0 loops the track; the m4a song is muted.
;     ...OrChange / ...OrContinue do not restart channel 0 when it already plays that track;
;   - a song on the BGM player with no track: channel 0 stops, the original song is heard;
;   - a song that maps to a track, on another player: channel 1 plays it once (voice, jingles), the m4a song
;     is muted;
;   - a missing or broken track: the original song is heard;
;   - m4aSongNumStop of a mapped song: the channel playing its track stops.
; Without GXA or without a pack, nothing changes.

.thumb

; Overwrites a function's first 8 bytes (the stock prologue, checked by m4a_locate.py) with a jump to hook.
.macro gxa_entry, fn, hook
	.org fn
	.halfword 0x4B00		; ldr r3, [pc, #0]
	bx	r3
	.word	hook + 1
.endmacro

; Runs the 8 bytes gxa_entry replaced, then continues in the original function, which returns to lr.
; Expects r0 = the song number.
.macro gxa_reenter, fn
	push	{lr}
	lsl	r0, r0, #16
	.if PLAYER_REG == 2
		ldr	r2, =PlayerTable
		ldr	r1, =SongTable
		ldr	r3, =fn + 8 + 1
		bx	r3
	.else
		ldr	r3, =PlayerTable
		ldr	r1, =SongTable
		ldr	r2, =fn + 8 + 1
		bx	r2
	.endif
.endmacro

; A start hook. keep = 1: do not restart channel 0 when it already plays the track.
.macro gxa_start_hook, name, fn, keep
name:
	push	{r4-r7, lr}
	mov	r4, r0			; song
	mov	r7, #0			; 1 when GXA plays it: mute the m4a player afterwards
	bl	gxa_detect
	cmp	r0, #0
	beq	@@original
	mov	r0, r4
	bl	gxa_lookup
	mov	r5, r0			; track, 0 = none
	mov	r6, r1			; the song's player
	cmp	r6, #BGM_PLAYER
	bne	@@other
	cmp	r5, #0
	beq	@@unmapped
	.if keep
		ldr	r3, =0x04FFFA10
		ldrh	r0, [r3, #0]	; channel 0 TRACK
		cmp	r0, r5
		bne	@@play
		ldrh	r0, [r3, #8]	; channel 0 STATE
		mov	r1, #1
		tst	r0, r1
		bne	@@playing
	.endif
@@play:
	mov	r0, #0
	mov	r1, r5
	mov	r2, #1
	bl	gxa_play_track
	cmp	r0, #0
	beq	@@original
@@playing:
	mov	r7, #1
	b	@@original
@@unmapped:
	mov	r0, #0
	bl	gxa_stop
	b	@@original
@@other:
	cmp	r5, #0
	beq	@@original
	mov	r0, #1
	mov	r1, r5
	mov	r2, #0
	bl	gxa_play_track
	mov	r7, r0
@@original:
	mov	r0, r4
	bl	@@call
	cmp	r7, #0
	beq	@@done
	mov	r0, r6
	bl	gxa_mute
@@done:
	pop	{r4-r7}
	pop	{r0}
	bx	r0
@@call:
	gxa_reenter fn
	.pool
.endmacro

gxa_entry m4aSongNumStart, gxa_hook_start
gxa_entry m4aSongNumStartOrChange, gxa_hook_start_or_change
gxa_entry m4aSongNumStartOrContinue, gxa_hook_start_or_continue
gxa_entry m4aSongNumStop, gxa_hook_stop

.org FreeSpace
.align 4

gxa_start_hook gxa_hook_start, m4aSongNumStart, 0
gxa_start_hook gxa_hook_start_or_change, m4aSongNumStartOrChange, 1
gxa_start_hook gxa_hook_start_or_continue, m4aSongNumStartOrContinue, 1

gxa_hook_stop:
	push	{r4, lr}
	mov	r4, r0
	bl	gxa_detect
	cmp	r0, #0
	beq	@@original
	mov	r0, r4
	bl	gxa_lookup
	cmp	r0, #0
	beq	@@original
	ldr	r3, =0x04FFFA10
	mov	r2, #3			; stop
	ldrh	r1, [r3, #0x00]		; channel 0 TRACK
	cmp	r1, r0
	bne	@@ch1
	strh	r2, [r3, #0x02]
@@ch1:
	ldrh	r1, [r3, #0x10]		; channel 1 TRACK
	cmp	r1, r0
	bne	@@original
	strh	r2, [r3, #0x12]
@@original:
	mov	r0, r4
	pop	{r4}
	pop	{r3}
	mov	lr, r3
	gxa_reenter m4aSongNumStop
	.pool

; r0 = song number -> r0 = its track (0 = none), r1 = its player index. Uses r2, r3.
gxa_lookup:
	lsl	r0, r0, #16
	lsr	r0, r0, #16
	ldr	r2, =SongTable
	lsl	r1, r0, #3
	add	r1, r1, r2
	ldrh	r1, [r1, #4]
	ldr	r2, =gxa_song_tracks
@@next:
	ldrh	r3, [r2]
	cmp	r3, r0
	beq	@@found
	add	r3, #1			; 0xFFFF ends the table
	lsl	r3, r3, #16
	beq	@@none
	add	r2, #4
	b	@@next
@@found:
	ldrh	r0, [r2, #2]
	bx	lr
@@none:
	mov	r0, #0
	bx	lr

; Mutes m4a player r0 (an index into PlayerTable) for the rest of its current song: its voice table becomes
; gxa_silent_voices, so every note it plays from now on is silent, while the song still runs, loops and ends as
; the game expects. The next MPlayStart on the player sets the song's own voice table again.
gxa_mute:
	ldr	r1, =PlayerTable
	lsl	r2, r0, #1
	add	r2, r2, r0
	lsl	r2, r2, #2
	add	r1, r1, r2
	ldr	r0, [r1]		; MusicPlayerInfo
	ldr	r1, =gxa_silent_voices
	str	r1, [r0, #0x30]		; MusicPlayerInfo.tone
	bx	lr

	.pool

.include "../../asm/gxa.s"

; 128 voices (ToneData: type, key, length, pan, wave, attack, decay, sustain, release), all a silent sample
.macro gxa_silent_voice8
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
	.byte	0, 60, 0, 0
	.word	gxa_silent_wave
	.byte	0xFF, 0, 0xFF, 0
.endmacro
.align 4
gxa_silent_voices:
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
	gxa_silent_voice8
gxa_silent_wave:			; WaveData: type, status (no loop), frequency, loop start, size, one sample
	.halfword 0, 0
	.word	0x4000, 0, 1
	.byte	0, 0, 0, 0

.align 2
