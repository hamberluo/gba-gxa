#!/bin/sh
# SPDX-License-Identifier: MIT
# Builds gxa-conformance.gba and its pack gxa-conformance.gxa here (both committed).
# PY: a python with soundfile and numpy (tools/requirements.txt).
set -e
cd "$(dirname "$0")"
PY=${PY:-python3}
T=$(mktemp -d)
arm-none-eabi-gcc -mcpu=arm7tdmi -mthumb -mthumb-interwork -O2 -ffreestanding -nostdlib -Wall \
	-I../include -T gba.ld -o "$T/rom.elf" crt0.s main.c -lgcc
arm-none-eabi-objcopy -O binary "$T/rom.elf" gxa-conformance.gba
"$PY" ../tools/gba_header.py gxa-conformance.gba
"$PY" make_pack.py "$T/pack"
"$PY" ../tools/gxa_pack.py "$T/pack" gxa-conformance.gxa
rm -rf "$T"
ls -l gxa-conformance.gba gxa-conformance.gxa
