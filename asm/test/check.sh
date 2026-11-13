#!/bin/sh
# SPDX-License-Identifier: MIT
# Static checks for asm/gxa.s: assembles with GNU as (and with armips when ARMIPS is set), no 8-bit accesses.
# Builds asm/test/out/gxa-smoke.gba (conformance header, so the conformance pack loads) for running on an emulator.
set -e
cd "$(dirname "$0")"
if grep -nE '\b(strb|ldrb)\b' ../gxa.s; then
	echo "gxa.s: 8-bit access to GXA registers is undefined"; exit 1
fi
# the handshake reply is 0x1234 ^ 0x5847
grep -q "=0x$(printf '%X' $((0x1234 ^ 0x5847)))" ../gxa.s || { echo "gxa.s: wrong handshake reply"; exit 1; }
mkdir -p out
arm-none-eabi-gcc -mcpu=arm7tdmi -mthumb -mthumb-interwork -nostdlib -I.. -Wa,-I.. \
	-T ../../test-rom/gba.ld -o out/smoke.elf ../../test-rom/crt0.s smoke.s
arm-none-eabi-objcopy -O binary out/smoke.elf out/gxa-smoke.gba
python3 ../../tools/gba_header.py out/gxa-smoke.gba
if [ -n "$ARMIPS" ]; then
	printf '.gba\n.create "out/armips.bin", 0x08000000\n.include "../gxa.s"\n.close\n' > out/armips.asm
	"$ARMIPS" out/armips.asm
	arm-none-eabi-as -mthumb -mcpu=arm7tdmi -o out/gas.o ../gxa.s
	arm-none-eabi-objcopy -O binary out/gas.o out/gas.bin
	cmp out/gas.bin out/armips.bin || { echo "gxa.s: armips and GNU as disagree"; exit 1; }
	echo "ok: armips (same bytes as GNU as)"
fi
echo "ok: gxa.s"
