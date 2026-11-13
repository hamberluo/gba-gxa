#!/bin/bash
# SPDX-License-Identifier: MIT
# Tests hook.asm on fake_m4a.s, a stand-in for the m4a library. Needs arm-none-eabi-gcc, armips (ARMIPS),
# a Python with tools/requirements.txt (PY), and a headless GXA emulator (PROBE) that prints
# "f <frame> ch <n> track <id> state <bits> pos <ms>" on every GXA channel change.
#   song 1 -> track 1 plays; MPlayStop on the BGM player pauses it; MPlayContinue resumes it;
#   unmapped song 2 (priority 10) stops it; song 3 (priority 0, mapped) is refused by MPlayStart, so GXA
#   must not play track 3 and the m4a player must not be muted; song 4 on player 1 plays on channel 2
#   (1 + player % 3), and unmapped song 5 on that player stops it; m4aSongNumStop(4) stops channel 2 and
#   still runs the original stop.
set -u
cd "$(dirname "$0")"
ARMIPS=${ARMIPS:?set ARMIPS}; PY=${PY:-python3}; PROBE=${PROBE:?set PROBE}
O=out; rm -rf $O; mkdir -p $O
arm-none-eabi-gcc -mcpu=arm7tdmi -mthumb -mthumb-interwork -nostdlib -T ../../../test-rom/gba.ld \
	-o $O/fake.elf crt0.s fake_m4a.s || exit 1
arm-none-eabi-objcopy -O binary $O/fake.elf $O/fake.gba && "$PY" ../../../tools/gba_header.py $O/fake.gba || exit 1
"$PY" ../../../tools/m4a_locate.py --armips --bgm-song 1 $O/fake.gba > $O/defs.asm || exit 1
printf '.gba\n.open "%s", "%s", 0x08000000\n.include "%s"\n.include "hook.asm"\ngxa_song_tracks:\n.halfword 1, 1\n.halfword 3, 3\n.halfword 4, 4\n.halfword 0xFFFF\n.close\n' \
	"$PWD/$O/fake.gba" "$PWD/$O/hooked.gba" "$PWD/$O/defs.asm" > $O/main.asm
"$ARMIPS" -root "$PWD/.." "$PWD/$O/main.asm" || exit 1
mkdir -p $O/pack
"$PY" - $O/pack <<'PYEOF' || exit 1
import json, sys, numpy as np, soundfile as sf
d = sys.argv[1]
for i in (1, 3, 4):
    sf.write('%s/t%d.wav' % (d, i), np.zeros(32000 * 4, dtype=np.float32), 32000)
json.dump({'spec': 1, 'title': 'fake m4a', 'author': 'GXA', 'version': '1', 'license': 'CC0-1.0',
           'match': [{'code': 'GXAM', 'title': 'GXA FAKE M4A'}],
           'tracks': {str(i): {'file': 't%d.wav' % i, 'loop': 0} for i in (1, 3, 4)}}, open(d + '/manifest.json', 'w'))
PYEOF
"$PY" ../../../tools/gxa_pack.py $O/pack $O/hooked.gxa > /dev/null || exit 1
ROM=$PWD/$O/hooked.gba FRAMES=400 "$PROBE" > $O/probe.txt
# each channel's (track, state) at the end of each step (the step number is reported in channel 3)
"$PY" - $O/probe.txt <<'PYEOF'
import re, sys
step, ch_now, at, report = 0, {}, {}, None
for line in open(sys.argv[1]):
    m = re.match(r'f \d+ ch (\d) track (\d+) state (\d+)', line)
    if not m:
        continue
    ch, tr, s = map(int, m.groups())
    if ch == 3 and tr & 0x100:
        step = tr & 0xFF
    elif ch == 3 and tr & 0x200:
        report = tr & 3
    else:
        ch_now[ch] = (tr, s)
    at[step] = dict(ch_now)
want = [(1, 0, (1, 1)), (2, 0, (1, 2)), (3, 0, (1, 1)), (4, 0, (1, 0)), (6, 2, (4, 1)), (7, 2, (4, 0)),
        (8, 2, (4, 1)), (9, 2, (4, 0))]
bad = 0
for step, ch, v in want:
    got = at.get(step, {}).get(ch)
    bad += got != v
    print('%s step %d: channel %d (track, state) %s, want %s' % ('PASS' if got == v else 'FAIL', step, ch, got, v))
got = at.get(5, {}).get(0)
ok = got is None or got[0] != 3 or not got[1] & 1
bad += not ok
print('%s step 5: refused song 3 does not play on GXA: %s' % ('PASS' if ok else 'FAIL', got))
ok = report is not None and report & 1
bad += not ok
print('%s report: the m4a player that refused song 3 is not muted (%s)' % ('PASS' if ok else 'FAIL', report))
ok = report is not None and report & 2
bad += not ok
print('%s report: the original m4aSongNumStop(4) ran (%s)' % ('PASS' if ok else 'FAIL', report))
sys.exit(1 if bad else 0)
PYEOF
