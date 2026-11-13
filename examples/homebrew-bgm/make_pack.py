#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Builds the example's pack: two generated looping tunes as tracks 1 (title) and 2 (field).

usage: make_pack.py out.gxa [--without ID]   (--without leaves a track out, to try the fallback)"""
import argparse
import json
import pathlib
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf

RATE = 32000
TUNES = {1: (262, 330, 392, 330), 2: (392, 494, 587, 494)}   # C-major and G-major arpeggios, 0.5 s a note

a = argparse.ArgumentParser()
a.add_argument('out')
a.add_argument('--without', type=int, action='append', default=[])
args = a.parse_args()
with tempfile.TemporaryDirectory() as d:
    d = pathlib.Path(d)
    tracks = {}
    for tid, notes in TUNES.items():
        if tid in args.without:
            continue
        t = np.arange(RATE // 2) / RATE
        x = np.concatenate([0.3 * np.sin(2 * np.pi * f * t) * np.minimum(1, (RATE // 2 - np.arange(RATE // 2)) / 800)
                            for f in notes]).astype(np.float32)
        sf.write(d / ('bgm%d.wav' % tid), np.stack([x, x], 1), RATE)
        tracks[str(tid)] = {'file': 'bgm%d.wav' % tid, 'loop': 0}
    (d / 'manifest.json').write_text(json.dumps({
        'spec': 1, 'title': 'GXA homebrew-bgm example', 'author': 'GXA', 'version': '1', 'license': 'CC0-1.0',
        'match': [{'code': 'GXAB', 'title': 'GXA BGM DEMO'}], 'tracks': tracks}, indent=1))
    tool = pathlib.Path(__file__).resolve().parents[2] / 'tools' / 'gxa_pack.py'
    sys.exit(subprocess.call([sys.executable, str(tool), str(d), args.out]))
