#!/bin/sh
# SPDX-License-Identifier: MIT
# Builds armips (pinned) into $ARMIPS_DIR (default .cache/armips) once, and prints its path.
# Needs git, cmake and a C++ compiler.
set -e
VER=v0.11.0
ROOT=$(cd "$(dirname "$0")/.." && pwd)
DIR=${ARMIPS_DIR:-$ROOT/.cache/armips}
BIN=$DIR/build/armips
if [ ! -x "$BIN" ]; then
	rm -rf "$DIR"
	git clone -q --depth 1 --branch "$VER" --recursive https://github.com/Kingcom/armips.git "$DIR" >&2
	cmake -S "$DIR" -B "$DIR/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 >&2
	cmake --build "$DIR/build" --target armips -j 4 >&2
fi
echo "$BIN"
