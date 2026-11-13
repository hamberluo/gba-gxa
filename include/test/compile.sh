#!/bin/sh
# SPDX-License-Identifier: MIT
# Compiles use.c against gxa.h as C89 (agbcc-era code), C99 and C++, warnings as errors.
set -e
cd "$(dirname "$0")"
CC=${CC:-arm-none-eabi-gcc}
O=$(mktemp -d)
trap 'rm -rf "$O"' EXIT
for std in "-std=c89 -pedantic" "-std=c99" "-x c++"; do
	# shellcheck disable=SC2086
	$CC -mthumb -mcpu=arm7tdmi -O2 -Wall -Wextra -Werror $std -I.. -c use.c -o "$O/use.o"
	echo "ok: $std"
done
