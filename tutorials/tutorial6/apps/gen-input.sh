#!/bin/sh
# gen-input.sh — run on the SENDER container to create a test file
# Usage: sh /apps/gen-input.sh [size_kb]
# Default: 32 KB

SIZE_KB=${1:-50}
OUTPUT="/tmp/input.txt"

echo "[setup] Generating ${SIZE_KB} KB test file at ${OUTPUT} ..."

# Generate printable ASCII content (easier to diff-check)
python3 -c "
import random, string
size = ${SIZE_KB} * 1024
chars = string.ascii_letters + string.digits + ' \n'
print(''.join(random.choices(chars, k=size)), end='')
" > ${OUTPUT}

ACTUAL=$(wc -c < ${OUTPUT})
echo "[setup] Done — ${ACTUAL} bytes written to ${OUTPUT}"
