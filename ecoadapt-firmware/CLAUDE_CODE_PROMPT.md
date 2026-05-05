# Integrate EcoAdapt firmware flasher into the existing repo

You are working in the EcoAdapt Python/Flask repo (https://github.com/x0rgo/EcoAdapt). Your job is to integrate a new firmware auto-flash system into the existing codebase **without breaking any existing functionality**.

## What you have access to

A folder called `ecoadapt-firmware/` (sibling to the repo, or pasted in by the user) containing:
- `pod/pod.ino` — Pod firmware
- `bridge/bridge.ino` — Bridge firmware (3-tier WiFi provisioning: NVS-staged, BLE, captive portal)
- `web_flasher/flash.html` — Web Serial flasher page (browser flashes ESP32 over USB)
- `web_flasher/pair.html` — Web Bluetooth pairing page
- `web_flasher/flash_routes.py` — Flask blueprint with `/flash`, `/pair`, `/api/firmware/*` endpoints
- `build_scripts/setup.sh` and `build.sh` — arduino-cli build pipeline
- `INTEGRATION.md` — high-level integration guide

## Core principle

**One universal firmware .bin per device type. Per-user data (API key, server URL, optional WiFi credentials) is written to a separate NVS partition image generated server-side at flash time.** This means we never recompile firmware per user.

## Tasks (do them in this order)

### 1. Inventory the existing repo first
Before touching anything, read these files and report back what you find:
- `main.py` — confirm it's a Flask app factory
- `api.py` — list all existing routes; specifically check whether `/api/sensor/data` and `/api/commands/pending` already exist
- `db.py` — find the function that fetches a user by ID, and confirm the column name for the API key (likely `api_key` or `apiKey`)
- `auth.py` — confirm sessions use `session['user_id']` (the new code assumes this)
- `static/index.html` — find a sensible spot to add a "Flash my bridge" link

Do not modify anything yet. Tell me what you found and flag any mismatches with the assumptions in `flash_routes.py`.

### 2. Copy firmware files into the repo
- Create `firmware/` directory at repo root
- Copy `pod/`, `bridge/`, and `build_scripts/` into it verbatim
- Copy `INTEGRATION.md` into `firmware/`
- Copy `flash.html` and `pair.html` into `static/` (Flask serves these directly)
- Copy `flash_routes.py` into the repo root (next to `api.py`, `db.py`, etc.)

### 3. Adapt `flash_routes.py` to match the existing codebase
The blueprint assumes:
- `from db import get_user_by_id` — if your function is named differently (e.g. `get_user`, `find_user_by_id`), update the import in `_get_user_api_key`
- The user record has a key called `api_key` — if your column is called something else (e.g. `apiKey`, `api_token`), update `_get_user_api_key`
- Sessions use `session['user_id']` — if you use `session['uid']` or similar, update `_require_user`

Make the smallest possible changes. Do not refactor.

### 4. Register the blueprint in `main.py`
Add a single line to the Flask app factory:
```python
from flash_routes import flash_bp
app.register_blueprint(flash_bp)
```

### 5. Verify required endpoints exist (do not create them yet, just check)
The bridge firmware POSTs to `/api/sensor/data` (with `X-API-Key` header) and GETs `/api/commands/pending`. If these already exist in `api.py`, confirm they:
- Authenticate via `X-API-Key` header (not session cookie)
- Resolve the API key to a `user_id` and scope reads/writes to that user

If they don't exist or don't auth via API key, **stop and tell me before generating new endpoints**. The way you implement these has implications for the rest of the system.

### 6. Add the dashboard link
In `static/index.html`, add a "Flash my bridge" button somewhere logical — settings page, account dropdown, or near the API key display. Keep the styling consistent with what's already in the page.

### 7. Set up the firmware build directory
Create `instance/firmware/` and add a `.gitkeep` file. Add `instance/firmware/*.bin` to `.gitignore` if user wants .bins out of git, OR leave them tracked if they want them deployed via Render. Ask the user which.

### 8. Run a smoke test
Boot the Flask app locally if possible. Verify:
- `/flash` returns the flasher page (HTML)
- `/pair` returns the pairing page (HTML)
- `/api/me/flash-config` returns 401 when not logged in, returns the user's API key when logged in
- `/firmware/bridge.bin` returns 404 with message about running build.sh (expected — we haven't built firmware yet)

### 9. Document next steps
At the end, summarize for the user:
- What you changed and where
- What still needs to happen (build the firmware via arduino-cli before `/flash` actually works end-to-end)
- Any TODOs you discovered (mismatched function names, missing endpoints, etc.)

## Constraints

- **Do not modify any existing route logic.** Only add new files and add the one blueprint registration line. If you need to change something existing, stop and ask first.
- **Do not regenerate the firmware .ino files or the HTML.** They are correct as-is. If you find a bug, flag it but don't auto-fix.
- **Do not run `pip install`** unless explicitly asked. Note any new dependencies (this integration adds none — Flask, Werkzeug, etc. are already used).
- **Do not commit anything.** Show me the diff first.
- **The hand-rolled NVS partition writer in `flash_routes.py` is intentional.** It builds a 24KB ESP-IDF NVS v2 image with one namespace ('ecoadapt') and 2-4 string keys. Don't try to "improve" it by importing esp-idf tools — those don't run on Render.

## Definition of done

- All 8 numbered tasks above are complete
- The Flask app starts without errors
- Existing functionality is unchanged (verify by hitting the existing dashboard)
- A diff/summary is shown to the user with everything that changed
- A clear "what's next" list is provided

If anything is ambiguous, **ask before guessing**. The cost of a wrong assumption here is breaking a working multi-user dashboard with one week to science fair.
