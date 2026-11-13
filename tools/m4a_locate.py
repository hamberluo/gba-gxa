#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finds the m4a (Sappy) sound engine's song functions in a GBA ROM, for hooking them (docs/guides/binary-m4a-hook.md).

usage: m4a_locate.py [--json] [--free BYTES] rom.gba

Prints ROM offsets (add 0x08000000 for the address) of m4aSongNumStart, m4aSongNumStartOrChange,
m4aSongNumStartOrContinue, m4aSongNumStop, m4aSongNumContinue, MPlayStart, MPlayStop, the song table, and
the last run of at least BYTES (default 4096) 0xFF bytes for new code. Exits 2 if the ROM is not an m4a game.

Method: the m4aSongNum* functions all begin by indexing the song table with the song number
(n << 16 >> 13 = n * 8). Among them, the most frequent call target is MPlayStart; the one that only calls
MPlayStart is m4aSongNumStart; the one calling MPlayStart behind a compare is ...OrChange; the one also
calling a second function is ...OrContinue, and that second function is MPlayContinue; the one calling
neither MPlayStart nor MPlayContinue is m4aSongNumStop, and its target is MPlayStop."""
import argparse
import json
import struct
import sys
from collections import Counter

ROM_BASE = 0x08000000


def h16(rom, off):
    return struct.unpack_from('<H', rom, off)[0] if 0 <= off and off + 2 <= len(rom) else 0


def bl_target(rom, off):
    hi, lo = h16(rom, off), h16(rom, off + 2)
    if (hi & 0xF800) != 0xF000 or (lo & 0xF800) != 0xF800:
        return None
    o = (hi & 0x7FF) << 12 | (lo & 0x7FF) << 1
    if o & 0x400000:
        o -= 0x800000
    return off + 4 + o


def lit(rom, off):
    """The literal of the Thumb `ldr rX, [pc, #imm]` at off, or None."""
    op = h16(rom, off)
    if (op >> 11) != 0x09:
        return None
    at = ((off + 4) & ~3) + (op & 0xFF) * 4
    return struct.unpack_from('<I', rom, at)[0] if at + 4 <= len(rom) else None


def is_end(op):
    return (op & 0xFF87) == 0x4700 or (op & 0xFF00) == 0xBD00   # bx rX, pop {.., pc}


def song_functions(rom):
    """Entries of functions that start with `lsls r0,r0,#16 ... lsrs rX,r0,#13`, with their body facts."""
    found = {}
    for off in range(0, len(rom) - 2, 2):
        if h16(rom, off) != 0x0400:                       # lsls r0, r0, #16
            continue
        if not any((h16(rom, off + d) & 0xFFF8) == 0x0B40 for d in (2, 4, 6)):   # lsrs rX, r0, #13
            continue
        entry = next((off - d for d in (2, 4) if (h16(rom, off - d) & 0xFF00) == 0xB500), None)   # push {.., lr}
        if entry is None or entry in found:
            continue
        calls, cond, lits = [], False, []
        p = off
        while p < off + 0x60 and not is_end(h16(rom, p)):
            t = bl_target(rom, p)
            if t is not None:
                calls.append(t)
                p += 4
                continue
            op = h16(rom, p)
            cond |= (op & 0xF000) == 0xD000 and (op & 0x0F00) < 0x0E00
            v = lit(rom, p)
            if v is not None:
                lits.append(v)
            p += 2
        if calls:
            found[entry] = {'calls': calls, 'cond': cond, 'lits': lits}
    return found


def is_song_table(rom, off):
    """Song entries: (header pointer in ROM, u16 player, u16 player) for the first 4 entries."""
    if off < 0 or off + 32 > len(rom):
        return False
    for i in range(4):
        hdr, ms, me = struct.unpack_from('<IHH', rom, off + 8 * i)
        if not (ROM_BASE <= hdr < ROM_BASE + len(rom)) or ms > 32 or me > 32:
            return False
    return True


def free_space(rom, need):
    """(offset, length) of the 0xFF run that ends the ROM, if at least need bytes, else None."""
    end = len(rom)
    start = len(rom.rstrip(b'\xFF'))
    start = (start + 3) & ~3
    return (start, end - start) if end - start >= need else None


def locate(rom):
    fns = song_functions(rom)
    if not fns:
        raise LookupError('not an m4a game, or its m4a library was modified (no stock m4aSongNum* functions); '
                          'for a decomp-based hack, add GXA in C: docs/guides/c-source.md')
    # The library's m4aSongNum* functions sit next to each other; a hack's own code may look alike elsewhere.
    runs, run = [], []
    for entry in sorted(fns):
        if run and entry - run[-1] > 0x60:
            runs.append(run)
            run = []
        run.append(entry)
    runs.append(run)
    fns = {e: fns[e] for e in max(runs, key=len)}
    mplay_start = Counter(t for f in fns.values() for t in f['calls']).most_common(1)[0][0]
    out = {'MPlayStart': mplay_start}
    rest = []
    for entry, f in sorted(fns.items()):
        others = sorted(set(f['calls']) - {mplay_start})
        if mplay_start in f['calls']:
            name = ('m4aSongNumStartOrContinue' if others else
                    'm4aSongNumStartOrChange' if f['cond'] else 'm4aSongNumStart')
            if others:
                out['MPlayContinue'] = others[0]
            out.setdefault(name, entry)
        else:
            rest.append((entry, f))
    for entry, f in rest:
        if out.get('MPlayContinue') in f['calls']:
            out.setdefault('m4aSongNumContinue', entry)
        elif len(set(f['calls'])) == 1:
            out.setdefault('m4aSongNumStop', entry)
            out.setdefault('MPlayStop', f['calls'][0])
    start = out.get('m4aSongNumStart')
    if start is None:
        raise LookupError('found m4aSongNum* functions but not m4aSongNumStart')
    table = [v - ROM_BASE for v in fns[start]['lits'] if is_song_table(rom, v - ROM_BASE)]
    if table:
        out['song_table'] = table[0]
    return out


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument('--json', action='store_true')
    a.add_argument('--free', type=int, default=4096)
    a.add_argument('rom')
    args = a.parse_args()
    rom = open(args.rom, 'rb').read()
    try:
        out = locate(rom)
    except LookupError as e:
        print('%s: %s' % (args.rom, e), file=sys.stderr)
        return 2
    fs = free_space(rom, args.free)
    if args.json:
        res = {k: '0x%X' % v for k, v in out.items()}
        res['free_space'] = ['0x%X' % fs[0], fs[1]] if fs else None
        print(json.dumps(res, indent=1))
    else:
        for k, v in out.items():
            print('%-26s 0x%07X  (0x%08X)' % (k, v, v + ROM_BASE))
        print('%-26s %s' % ('free_space', '0x%07X, %d bytes' % fs if fs else 'none at the end of the ROM'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
