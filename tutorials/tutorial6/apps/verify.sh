#!/bin/sh

SENDER="clab-rdt-lab-sender"
RECEIVER="clab-rdt-lab-receiver"

INPUT="/tmp/input.txt"
OUTPUT="/tmp/output.txt"

echo "=== Transfer Verification ==="

docker exec "$SENDER" test -f "$INPUT" || {
    echo "ERROR: $INPUT not found in sender"
    exit 1
}

docker exec "$RECEIVER" test -f "$OUTPUT" || {
    echo "ERROR: $OUTPUT not found in receiver"
    exit 1
}

INPUT_HASH=$(docker exec "$SENDER" md5sum "$INPUT" | awk '{print $1}')
OUTPUT_HASH=$(docker exec "$RECEIVER" md5sum "$OUTPUT" | awk '{print $1}')

INPUT_SIZE=$(docker exec "$SENDER" sh -c "wc -c < '$INPUT'")
OUTPUT_SIZE=$(docker exec "$RECEIVER" sh -c "wc -c < '$OUTPUT'")

echo "Input  : ${INPUT_SIZE} bytes  md5=${INPUT_HASH}"
echo "Output : ${OUTPUT_SIZE} bytes  md5=${OUTPUT_HASH}"

if [ "$INPUT_HASH" = "$OUTPUT_HASH" ]; then
    echo "Result : ✓ MATCH — transfer was reliable"
else
    echo "Result : ✗ MISMATCH — data was corrupted or lost"
fi