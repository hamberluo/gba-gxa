#!/bin/bash
# SPDX-License-Identifier: MIT
# Tests hook.asm on fake_m4a.s, a stand-in for the m4a library. Needs arm-none-eabi-gcc, armips (ARMIPS),
# a Python with tools/requirements.txt (PY), and a headless GXA emulator (PROBE) that prints
# "f <frame> ch <n> track <id> state <bits> pos <ms>" on every GXA channel change.
#   song 1 -> track 1 plays; MPlayStop on the BGM player pauses it; MPlayContinue resumes it;
#   unmapped song 2 (priority 10) stops it; song 3 (priority 0, mapped) is refused by MPlayStart, so GXA
#   must not play track 3 and the m4a player must not be muted.
set -u
cd "$(dirname "$0")"
ARMIPS=${ARMIPS:?set ARMIPS}; PY=${PY:-python3}; PROBE=${PROBE:?set PROBE}
O=out; rm -rf $O; mkdir -p $O
arm-none-eabi-gcc -mcpu=arm7tdmi -mthumb -mthumb-interwork -nostdlib -T ../../../test-rom/gba.ld \
	-o $O/fake.elf crt0.s fake_m4a.s || exit 1
arm-none-eabi-objcopy -O binary $O/fake.elf $O/fake.gba && "$PY" ../../../tools/gba_header.py $O/fake.gba || exit 1
"$PY" ../../../tools/m4a_locate.py --armips --bgm-song 1 $O/fake.gba > $O/defs.asm || exit 1
printf '.gba\n.open "%s", "%s", 0x08000000\n.include "%s"\n.include "hook.asm"\ngxa_song_tracks:\n.halfword 1, 1\n.halfword 3, 3\n.halfword 0xFFFF\n.close\n' \
	"$PWD/$O/fake.gba" "$PWD/$O/hooked.gba" "$PWD/$O/defs.asm" > $O/main.asm
"$ARMIPS" -root "$PWD/.." "$PWD/$O/main.asm" || exit 1
mkdir -p $O/pack
"$PY" - $O/pack <<'PYEOF' || exit 1
import json, sys, numpy as np, soundfile as sf
d = sys.argv[1]
for i in (1, 3):
    sf.write('%s/t%d.wav' % (d, i), np.zeros(32000 * 4, dtype=np.float32), 32000)
json.dump({'spec': 1, 'title': 'fake m4a', 'author': 'GXA', 'version': '1', 'license': 'CC0-1.0',
           'match': [{'code': 'GXAM', 'title': 'GXA FAKE M4A'}],
           'tracks': {'1': {'file': 't1.wav', 'loop': 0}, '3': {'file': 't3.wav', 'loop': 0}}}, open(d + '/manifest.json', 'w'))
PYEOF
"$PY" ../../../tools/gxa_pack.py $O/pack $O/hooked.gxa > /dev/null || exit 1
ROM=$PWD/$O/hooked.gba FRAMES=200 "$PROBE" > $O/probe.txt
# channel 0's state at the end of each step (the step number is reported in channel 3)
"$PY" - $O/probe.txt <<'PYEOF'
import re, sys
step, st, track, report, at = 0, {}, {}, None, {}
rows = [tuple(map(int, m.groups())) for m in
        (re.match(r'f (\d+) ch (\d) track (\d+) state (\d+)', l) for l in open(sys.argv[1])) if m]
rows.sort(key=lambda r: (r[0], -r[1]))   # within a frame, the step marker (channel 3) first
for f, ch, tr, s in rows:
    if ch == 0:
        st, track = s, tr
    if ch == 3 and tr & 0x100:
        step = tr & 0xFF
    if ch == 3 and tr & 0x200:   # the final report replaces step 5's marker in the same frame
        step, report = 5, tr & 1
    at[step] = (track, st)
want = {1: (1, 1), 2: (1, 2), 3: (1, 1), 4: (1, 0)}
bad = 0
for k, v in want.items():
    ok = at.get(k) == v
    bad += not ok
    print('%s step %d: channel 0 (track, state) %s, want %s' % ('PASS' if ok else 'FAIL', k, at.get(k), v))
ok = at.get(5, (0, 0))[1] & 1 == 0 or at.get(5, (0, 0))[0] != 3
bad += not ok
print('%s step 5: refused song 3 does not play on GXA: %s' % ('PASS' if ok else 'FAIL', at.get(5)))
ok = report == 1
bad += not ok
print('%s step 5: the m4a player is not muted (report %s)' % ('PASS' if ok else 'FAIL', report))
sys.exit(1 if bad else 0)
PYEOF
