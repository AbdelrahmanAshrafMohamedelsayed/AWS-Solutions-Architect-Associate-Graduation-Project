#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
PACKAGE_DIR="$ROOT_DIR/build/lambda_package"
ZIP_FILE="$ROOT_DIR/build/lambda-package.zip"

rm -rf "$PACKAGE_DIR" "$ZIP_FILE"
mkdir -p "$PACKAGE_DIR"

cp -R "$ROOT_DIR/lambda_src/." "$PACKAGE_DIR/"

"$PYTHON_BIN" -m pip install \
  --upgrade \
  --requirement "$ROOT_DIR/lambda_src/requirements.txt" \
  --target "$PACKAGE_DIR"

find "$PACKAGE_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$PACKAGE_DIR" -name "*.pyc" -delete

(cd "$PACKAGE_DIR" && zip -qr "$ZIP_FILE" .)

echo "Created $ZIP_FILE"

