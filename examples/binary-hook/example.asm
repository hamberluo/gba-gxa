; SPDX-License-Identifier: MIT
; Copy this file, set the file names and the song table, then:
;   python3 tools/m4a_locate.py --armips game.gba > examples/binary-hook/defs.asm
;   armips examples/binary-hook/example.asm
;   python3 tools/gba_header.py game-gxa.gba
.gba
.open "game.gba", "game-gxa.gba", 0x08000000

.include "defs.asm"
.definelabel BGM_PLAYER, 0		; the player index of the game's music (see the guide)

.include "hook.asm"

; song number -> GXA track id. Songs not listed play as before.
gxa_song_tracks:
	.halfword 1, 1
	.halfword 2, 2
	.halfword 0xFFFF

.close
