#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS_DIR="${TRANSFER_TOOLS_DIR:-/home/vhehdhkd/work/personal-ledger/.tools}"
export JAVA_HOME="$TOOLS_DIR/jdk"
export ANDROID_HOME="$TOOLS_DIR/sdk"
export ANDROID_USER_HOME="$PROJECT_DIR/.android"
export GRADLE_USER_HOME="$PROJECT_DIR/.gradle-home"
export PATH="$JAVA_HOME/bin:$PATH"
mkdir -p "$ANDROID_USER_HOME" "$PROJECT_DIR/build/tmp"
export TMPDIR="$PROJECT_DIR/build/tmp"
export JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=$TMPDIR -Duser.home=$PROJECT_DIR"
cd "$PROJECT_DIR"
"$TOOLS_DIR/gradle/bin/gradle" --offline --no-daemon --console=plain "$@"
