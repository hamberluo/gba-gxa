; SPDX-License-Identifier: MIT
; Copy this file, set the file names, BGM_PLAYER and the song table, then, in examples/binary-hook:
;   python3 ../../tools/m4a_locate.py --armips /path/to/game.gba > defs.asm
;   armips my-hack.asm
;   python3 ../../tools/gba_header.py --check game-gxa.gba
; Guide: docs/guides/binary-m4a-hook.md
.gba
.open "game.gba", "game-gxa.gba", 0x08000000

.include "defs.asm"
.definelabel BGM_PLAYER, 0		; the music's player: m4a_locate.py --song <title song> (not always 0)

.include "hook.asm"

; song number -> GXA track id. Songs not listed play as before.
gxa_song_tracks:
	.halfword 1, 1
	.halfword 2, 2
	.halfword 0xFFFF

.close
