#!/usr/bin/env bash
# EcoAdapt firmware build script
# Compiles pod.ino and bridge.ino into .bin files using arduino-cli.
# Output goes to instance/firmware/ which is served by the Flask app.
#
# Prerequisites:
#   - arduino-cli   (https://arduino.github.io/arduino-cli/installation/)
#   - The ESP32 board package, ArduinoJson, Adafruit ADS1X15,
#     Adafruit VEML7700, OneWire, DallasTemperature
#
# Run once: ./setup.sh   (installs all deps)
# Run to build: ./build.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIRMWARE_DIR="$ROOT_DIR/firmware"
OUT_DIR="$ROOT_DIR/instance/firmware"

# Seeed XIAO ESP32-C3 FQBN
FQBN="esp32:esp32:XIAO_ESP32C3"

mkdir -p "$OUT_DIR"

build_one () {
  local name="$1"        # pod | bridge
  local sketch_dir="$FIRMWARE_DIR/$name"
  local build_dir="/tmp/ecoadapt-build-$name"

  echo ""
  echo "=== Building $name ==="
  rm -rf "$build_dir"
  mkdir -p "$build_dir"

  arduino-cli compile \
    --fqbn "$FQBN" \
    --build-path "$build_dir" \
    --build-property "build.partitions=min_spiffs" \
    --build-property "upload.maximum_size=1966080" \
    "$sketch_dir"

  # arduino-cli output naming: <sketch>.ino.bin
  cp "$build_dir/$name.ino.bin"           "$OUT_DIR/$name.bin"

  # Bootloader and partitions are the same for both targets — copy from
  # whichever build we just did.
  if [ -f "$build_dir/$name.ino.bootloader.bin" ]; then
    cp "$build_dir/$name.ino.bootloader.bin" "$OUT_DIR/bootloader.bin"
  fi
  if [ -f "$build_dir/$name.ino.partitions.bin" ]; then
    cp "$build_dir/$name.ino.partitions.bin" "$OUT_DIR/partitions.bin"
  fi

  echo "  -> $OUT_DIR/$name.bin"
  ls -l "$OUT_DIR/$name.bin"
}

build_one pod
build_one bridge

echo ""
echo "✓ Build complete. Output:"
ls -l "$OUT_DIR"
