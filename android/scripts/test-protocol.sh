#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS_DIR="${TRANSFER_TOOLS_DIR:-/home/vhehdhkd/work/personal-ledger/.tools}"
mkdir -p "$PROJECT_DIR/build/protocol-tests"
"$TOOLS_DIR/jdk/bin/javac" -encoding UTF-8 -d "$PROJECT_DIR/build/protocol-tests" \
    "$PROJECT_DIR/app/src/main/java/app/base64transfer/Transfer.java" "$PROJECT_DIR/tests/ProtocolTest.java" \
    "$PROJECT_DIR/app/src/main/java/app/base64transfer/CompactText15.java" "$PROJECT_DIR/tests/CompactText15Test.java"
"$TOOLS_DIR/jdk/bin/java" -cp "$PROJECT_DIR/build/protocol-tests" ProtocolTest "$@"
