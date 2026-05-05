#!/usr/bin/env bash
# One-time setup: install arduino-cli + ESP32 board package + libraries.
# Run this once on the machine that will build firmware.

set -euo pipefail

if ! command -v arduino-cli >/dev/null 2>&1; then
  echo "arduino-cli not found. Install from:"
  echo "  https://arduino.github.io/arduino-cli/latest/installation/"
  exit 1
fi

echo "Updating index…"
arduino-cli core update-index \
  --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json

echo "Installing ESP32 board package…"
arduino-cli core install esp32:esp32 \
  --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json

echo "Installing libraries…"
arduino-cli lib install \
  "ArduinoJson" \
  "Adafruit ADS1X15" \
  "Adafruit VEML7700 Library" \
  "OneWire" \
  "DallasTemperature" \
  "NimBLE-Arduino"

echo ""
echo "✓ Setup complete. Run ./build.sh to compile firmware."
