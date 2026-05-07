"""
EcoAdapt firmware flasher backend.

Adds these endpoints (mount as a Flask Blueprint):

  GET  /flash                          — the web flasher page (HTML)
  GET  /firmware/<kind>.bin            — serves prebuilt firmware (bridge.bin / pod.bin)
  GET  /firmware/bootloader.bin        — ESP32-C3 bootloader
  GET  /firmware/partitions.bin        — partition table
  GET  /api/me/flash-config            — returns the logged-in user's API key + server URL
  POST /api/firmware/nvs-image         — builds an NVS partition image with the user's config
  GET  /api/firmware/bundle.zip        — downloads a zip with .bins + esptool flash script

IMPORTANT — building the universal firmware:
  Compile pod.ino and bridge.ino once (Arduino IDE or arduino-cli) and place the
  resulting binaries at:
     instance/firmware/bridge.bin
     instance/firmware/pod.bin
     instance/firmware/bootloader.bin
     instance/firmware/partitions.bin

The same .bin files work for every user — per-user config is written to the
NVS partition at flash time by the web flasher.
"""

import io
import os
import struct
import zipfile
import hashlib
import functools
from pathlib import Path
from flask import (
    Blueprint, send_file, send_from_directory, jsonify, request,
    abort, render_template_string, make_response, current_app, session
)

flash_bp = Blueprint("flash", __name__)

FIRMWARE_DIR = Path(os.environ.get("FIRMWARE_DIR", "instance/firmware"))
NVS_NAMESPACE = "ecoadapt"
NVS_PARTITION_SIZE = 20 * 1024  # 20 KB — matches partitions.bin (0x5000)

# --------------------------------------------------------------------------
# NVS partition builder
# --------------------------------------------------------------------------
# We construct a minimal NVS image with one namespace ("ecoadapt") containing:
#   - api_key       (string)
#   - server_url    (string)
#
# The full NVS format is documented in ESP-IDF; we use the well-known helper
# `nvs_partition_gen.py` shipped with the ESP-IDF tools when available. If
# it's not on PATH we fall back to a pre-built template approach: we read a
# blank 24KB NVS image and overlay our values using esp_idf_nvs writer.
#
# For Render.com (which can't run arbitrary tools), we vendor a small pure-
# Python NVS writer below. It supports the subset we need.

def _crc32(data: bytes) -> int:
    """ESP-IDF's esp_rom_crc32_le: reflected CRC-32, init=0xFFFFFFFF, no final XOR.
    Python's binascii.crc32 applies a final XOR with 0xFFFFFFFF, so we invert."""
    import binascii
    return (binascii.crc32(data) ^ 0xFFFFFFFF) & 0xFFFFFFFF


def build_nvs_image(values: dict) -> bytes:
    """
    Build a 24KB NVS partition with one namespace 'ecoadapt' containing the
    given string values.

    Format (per ESP-IDF docs):
      Page = 4096 bytes.
      Page header (32 bytes):
        state (4)  : 0xFFFFFFFE = ACTIVE
        seqnum (4) : 0
        version(1) : 0xFE (NVS v2)
        unused(19) : 0xFF
        crc32  (4) : crc of bytes 4..27
      Entry state bitmap (32 bytes): two bits per entry (126 entries),
        0b11 = empty, 0b10 = written, 0b00 = erased.
      126 entries × 32 bytes = 4032 bytes of data.

    Entry header (32 bytes for primitive types or for the FIRST entry of a blob):
        ns (1)        : namespace index
        type (1)      : 0x21 = string, 0x01 = u8, etc.
        span (1)      : how many entries this record spans
        chunk_idx(1)  : 0xFF for non-blob
        crc32 (4)     : crc of entry (with crc field zeroed)
        key  (16)     : zero-padded UTF-8
        data (8)      : for strings -> {size:u16, _pad:u16, crc32_data:u32}
                        the actual string bytes follow in span-1 more entries

    We write namespace records first (assigning index 1 to 'ecoadapt'), then
    one string record per value.
    """
    PAGE_SIZE = 4096
    ENTRY_SIZE = 32
    ENTRIES_PER_PAGE = 126

    # ---- Build entries ----
    entries = []  # list of 32-byte chunks

    # Namespace record: ns=0, type=u8, key='ecoadapt', data=index 1
    def make_entry(ns, etype, span, chunk_idx, key, data8):
        assert len(data8) == 8
        kb = key.encode('utf-8')[:15] + b'\x00' * (16 - min(len(key), 15))
        # zero CRC first to compute, then fill
        body = struct.pack('<BBBB', ns, etype, span, chunk_idx) \
             + b'\x00\x00\x00\x00' \
             + kb \
             + data8
        crc = _crc32(body[0:4] + body[8:32])
        return body[0:4] + struct.pack('<I', crc) + body[8:]

    NS_INDEX = 1
    # Namespace entry: ns=0, type=0x01 (u8), span=1, chunk=0xFF, key='ecoadapt'
    ns_data = struct.pack('<BBBBBBBB', NS_INDEX, 0, 0, 0, 0, 0, 0, 0)
    entries.append(make_entry(0, 0x01, 1, 0xFF, NVS_NAMESPACE, ns_data))

    written_states = []  # 1 = written, 0 = empty (we fill all written ones first)
    written_states.append(1)  # namespace entry

    # String entries — each value spans (1 header + ceil(len/32)) entries
    for key, value in values.items():
        if not isinstance(value, str):
            value = str(value)
        vb = value.encode('utf-8') + b'\x00'  # NUL-terminated as ESP-IDF does
        size = len(vb)
        # pad to multiple of 32
        pad = (-size) % ENTRY_SIZE
        vb_padded = vb + b'\x00' * pad
        n_data_entries = len(vb_padded) // ENTRY_SIZE
        span = 1 + n_data_entries

        # data8 = size (u16), reserved (u16=0xFFFF), crc32 of the string data
        data_crc = _crc32(vb_padded)
        data8 = struct.pack('<HHI', size, 0xFFFF, data_crc)

        entries.append(make_entry(NS_INDEX, 0x21, span, 0xFF, key, data8))
        written_states.append(1)

        for i in range(n_data_entries):
            chunk = vb_padded[i*ENTRY_SIZE:(i+1)*ENTRY_SIZE]
            entries.append(chunk)
            written_states.append(1)

    # ---- Pad to fit on page 0 ----
    while len(entries) < ENTRIES_PER_PAGE:
        entries.append(b'\xFF' * ENTRY_SIZE)
        written_states.append(0)

    # ---- Build state bitmap (32 bytes) ----
    # Two bits per entry, little-endian. 0b11 = empty, 0b10 = written.
    bitmap_bytes = bytearray(b'\xFF' * 32)
    for i, st in enumerate(written_states):
        byte_idx = i // 4
        bit_idx = (i % 4) * 2
        if st == 1:
            # Clear the low bit of the pair: 0b10
            bitmap_bytes[byte_idx] &= ~(1 << bit_idx) & 0xFF

    # ---- Page header ----
    state = 0xFFFFFFFE  # ACTIVE
    seq = 0
    version = 0xFE  # v2
    header_body = struct.pack('<II', state, seq) + struct.pack('<B', version) + b'\xFF' * 19
    header_crc = _crc32(header_body[4:28])
    page_header = header_body + struct.pack('<I', header_crc)
    assert len(page_header) == 32

    page0 = page_header + bytes(bitmap_bytes) + b''.join(entries)
    assert len(page0) == PAGE_SIZE

    # ---- Remaining pages: empty/uninitialized ----
    n_pages = NVS_PARTITION_SIZE // PAGE_SIZE
    image = bytearray(NVS_PARTITION_SIZE)
    image[:PAGE_SIZE] = page0
    for i in range(1, n_pages):
        # Empty pages: state UNINITIALIZED = 0xFFFFFFFF, all 0xFF
        image[i*PAGE_SIZE:(i+1)*PAGE_SIZE] = b'\xFF' * PAGE_SIZE

    return bytes(image)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _require_user():
    user_id = session.get("user_id")
    if not user_id:
        abort(401, description="Login required")
    return user_id


def _firmware_path(filename: str) -> Path:
    p = (FIRMWARE_DIR / filename).resolve()
    if not str(p).startswith(str(FIRMWARE_DIR.resolve())):
        abort(404)
    if not p.is_file():
        abort(404, description=f"{filename} not built yet — run firmware/build_scripts/build.sh")
    return p


def _get_user_api_key(user_id):
    """Pull the user's API key from your existing auth/db layer."""
    from lib.auth import get_user_by_id
    u = get_user_by_id(user_id)
    if not u:
        abort(404)
    return u.get("api_key") or u.get("apiKey")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@flash_bp.route("/flash")
def flash_page():
    """Serve the Web Serial flasher page."""
    static_path = Path(current_app.root_path) / "static" / "flash.html"
    if static_path.is_file():
        return send_from_directory(static_path.parent, static_path.name)
    # Fallback: render from the firmware/web_flasher dir during development
    dev = Path(current_app.root_path) / "firmware" / "web_flasher" / "flash.html"
    if dev.is_file():
        return send_from_directory(dev.parent, dev.name)
    abort(404, description="flash.html not deployed")


@flash_bp.route("/pair")
def pair_page():
    """Serve the Web Bluetooth pairing page."""
    static_path = Path(current_app.root_path) / "static" / "pair.html"
    if static_path.is_file():
        return send_from_directory(static_path.parent, static_path.name)
    dev = Path(current_app.root_path) / "firmware" / "web_flasher" / "pair.html"
    if dev.is_file():
        return send_from_directory(dev.parent, dev.name)
    abort(404, description="pair.html not deployed")


@flash_bp.route("/firmware/<path:filename>")
def serve_firmware(filename):
    """Serve raw .bin files from the firmware build dir."""
    if not filename.endswith(".bin"):
        abort(404)
    p = _firmware_path(filename)
    return send_file(
        p, mimetype="application/octet-stream",
        as_attachment=False, download_name=filename
    )


@flash_bp.route("/api/firmware/version")
def firmware_version():
    """Return MD5 hash of the requested firmware binary for OTA version checks."""
    kind = request.args.get("kind", "bridge")
    if kind not in ("bridge", "pod"):
        abort(400)
    try:
        data = _firmware_path(f"{kind}.bin").read_bytes()
        h = hashlib.md5(data).hexdigest()
        return jsonify({"version": h, "kind": kind, "size": len(data)})
    except Exception:
        abort(404, description=f"{kind}.bin not built yet")


@flash_bp.route("/api/me/flash-config")
def me_flash_config():
    user_id = _require_user()
    api_key = _get_user_api_key(user_id)
    server_url = request.host_url.rstrip("/")
    return jsonify({"api_key": api_key, "server_url": server_url})


@flash_bp.route("/api/firmware/nvs-image", methods=["POST"])
def make_nvs_image():
    user_id = _require_user()
    body = request.get_json(force=True) or {}
    api_key = body.get("api_key", "").strip()
    server_url = body.get("server_url", "").strip()
    wifi_ssid = body.get("wifi_ssid", "").strip()
    wifi_pass = body.get("wifi_pass", "")  # do NOT strip — passwords may have spaces

    # Defense: never let a user write someone else's API key by trusting the
    # request body. Pull the canonical key from the session.
    real_key = _get_user_api_key(user_id)
    if api_key and api_key != real_key:
        abort(403, description="API key in request does not match your account")
    api_key = real_key

    if not server_url:
        server_url = request.host_url.rstrip("/")

    # Build the NVS dict. Only include WiFi keys if SSID is set — empty
    # values in NVS are still readable by the firmware as empty strings.
    nvs_values = {
        "api_key":    api_key,
        "server_url": server_url,
    }
    if wifi_ssid:
        nvs_values["wifi_ssid"] = wifi_ssid
        nvs_values["wifi_pass"] = wifi_pass  # may be empty for open networks

    try:
        image = build_nvs_image(nvs_values)
    except Exception as e:
        import traceback
        print("NVS BUILD ERROR:", traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    resp = make_response(image)
    resp.headers["Content-Type"] = "application/octet-stream"
    resp.headers["Content-Disposition"] = 'attachment; filename="nvs.bin"'
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    resp.headers["Pragma"] = "no-cache"
    return resp


@flash_bp.route("/api/firmware/bundle.zip")
def bundle_zip():
    user_id = _require_user()
    kind = request.args.get("kind", "bridge")
    if kind not in ("bridge", "pod"):
        abort(400)

    api_key = _get_user_api_key(user_id)
    server_url = request.args.get("server_url") or request.host_url.rstrip("/")

    nvs = build_nvs_image({"api_key": api_key, "server_url": server_url})

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{kind}.bin", _firmware_path(f"{kind}.bin").read_bytes())
        z.writestr("bootloader.bin", _firmware_path("bootloader.bin").read_bytes())
        z.writestr("partitions.bin", _firmware_path("partitions.bin").read_bytes())
        z.writestr("nvs.bin", nvs)
        z.writestr("flash.sh", _flash_script(kind, "linux"))
        z.writestr("flash.bat", _flash_script(kind, "win"))
        z.writestr("README.txt", _readme(kind))
    buf.seek(0)
    return send_file(
        buf, mimetype="application/zip",
        as_attachment=True, download_name=f"ecoadapt-{kind}-firmware.zip"
    )


def _flash_script(kind: str, os_kind: str) -> str:
    if os_kind == "linux":
        return f"""#!/usr/bin/env bash
# EcoAdapt firmware flash script (Linux/macOS)
# Usage: ./flash.sh /dev/ttyUSB0   (or /dev/cu.usbserial-* on macOS)
set -e
PORT="${{1:-/dev/ttyUSB0}}"
echo "Flashing {kind} firmware to $PORT…"
pip install --quiet esptool
esptool.py --chip esp32c3 --port "$PORT" --baud 460800 \\
  write_flash --flash_mode dio --flash_size 4MB \\
  0x0000  bootloader.bin \\
  0x8000  partitions.bin \\
  0x9000  nvs.bin \\
  0x10000 {kind}.bin
echo "Done. Reset your board to start."
"""
    return f"""@echo off
REM EcoAdapt firmware flash script (Windows)
REM Usage: flash.bat COM3
set PORT=%1
if "%PORT%"=="" set PORT=COM3
echo Flashing {kind} firmware to %PORT%...
pip install esptool
esptool.py --chip esp32c3 --port %PORT% --baud 460800 ^
  write_flash --flash_mode dio --flash_size 4MB ^
  0x0000  bootloader.bin ^
  0x8000  partitions.bin ^
  0x9000  nvs.bin ^
  0x10000 {kind}.bin
echo Done. Reset your board to start.
"""


def _readme(kind: str) -> str:
    return f"""EcoAdapt {kind} firmware
=========================

This bundle contains:
  bootloader.bin   ESP32-C3 bootloader
  partitions.bin   partition table
  nvs.bin          your personal config (API key + server URL)
  {kind}.bin       the application firmware
  flash.sh         Linux/macOS flash script
  flash.bat        Windows flash script

Quick start
-----------
1. Plug the XIAO ESP32-C3 into USB.
2. Hold BOOT, tap RESET, release BOOT to enter download mode.
3. Run the appropriate script with your serial port:
     macOS/Linux:  ./flash.sh /dev/ttyUSB0
     Windows:      flash.bat COM3

If esptool is not installed, the script will install it via pip first.
"""
