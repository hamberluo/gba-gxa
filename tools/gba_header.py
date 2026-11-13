#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fills a GBA ROM's header logo and complement checksum in place, as hardware and some emulators need.
Run it after building or patching a ROM.

usage: gba_header.py [--check] rom.gba    (--check: report only; exit 1 if the logo or checksum is wrong)"""
import argparse
import sys
import zlib

LOGO = bytes.fromhex(
    '24FFAE51699AA2213D84820A84E409AD11248B98C0817F21A352BE199309CE2010464A4AF82731EC58C7E83382E3CEBF85F4DF94CE4B'
    '09C194568AC01372A7FC9F844D73A3CA9A615897A327FC039876231DC7610304AE56BF38840040A70EFDFF52FE036F9530F197FBC085'
    '60D68025A963BE03014E38E2F9A234FFBB3E0344780090CB88113A9465C07C6387F03CAFD625E48B380AAC7221D4F807')
assert zlib.crc32(LOGO) == 0xD0BEB55E


def checksum(d):
    return (-(sum(d[0xA0:0xBD]) + 0x19)) & 0xFF


def main():
    a = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    a.add_argument('--check', action='store_true')
    a.add_argument('rom')
    args = a.parse_args()
    d = bytearray(open(args.rom, 'rb').read())
    if len(d) < 0xC0:
        print('%s: too short for a GBA header' % args.rom, file=sys.stderr)
        return 2
    if args.check:
        bad = [what for what, ok in (('logo', d[4:160] == LOGO), ('checksum', d[0xBD] == checksum(d))) if not ok]
        print('%s: %s' % (args.rom, 'bad ' + ', '.join(bad) if bad else 'ok'))
        return 1 if bad else 0
    d[4:160] = LOGO
    d[0xBD] = checksum(d)
    open(args.rom, 'wb').write(d)
    return 0


if __name__ == '__main__':
    sys.exit(main())
