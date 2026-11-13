#!/bin/sh
# SPDX-License-Identifier: MIT
# Builds homebrew-bgm.gba here. Needs arm-none-eabi-gcc. The pack: python3 make_pack.py homebrew-bgm.gxa
set -e
cd "$(dirname "$0")"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
arm-none-eabi-gcc -mcpu=arm7tdmi -mthumb -mthumb-interwork -O2 -ffreestanding -nostdlib -Wall -Wextra \
	-I../../include -T gba.ld -o "$T/rom.elf" crt0.s main.c -lgcc
arm-none-eabi-objcopy -O binary "$T/rom.elf" homebrew-bgm.gba
python3 ../../tools/gba_header.py homebrew-bgm.gba
