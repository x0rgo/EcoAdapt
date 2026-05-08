"""
Web Push notifications for EcoAdapt.

Uses VAPID + the browser Push API + a service worker to deliver
notifications even when the page/tab is closed (works on Android Chrome
out of the box, and on iOS as an installed PWA on iOS 16.4+).

VAPID keys: prefer env vars VAPID_PRIVATE_KEY (PEM) and VAPID_PUBLIC_KEY
(base64url of the raw uncompressed point). If absent, a key pair is
generated and persisted to instance/vapid.json.
"""

import os
import json
import time
import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from pywebpush import webpush, WebPushException

from lib.db import get_db

INSTANCE_DIR = Path(os.environ.get("INSTANCE_DIR", "instance"))
VAPID_FILE = INSTANCE_DIR / "vapid.json"
VAPID_SUB = os.environ.get("VAPID_SUB", "mailto:admin@ecoadapt.local")

# Min seconds between push notifications of the same type to the same user
# — same idea as the threshold debounce; prevents spam.
PUSH_DEBOUNCE_S = 6 * 3600  # 6 hours
_last_push = {}  # (user_id, type) -> ts


def _generate_keys():
    priv = ec.generate_private_key(ec.SECP256R1())
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    pub_b64 = base64.urlsafe_b64encode(pub_bytes).rstrip(b"=").decode()
    return priv_pem, pub_b64


def _load_keys():
    pri = os.environ.get("VAPID_PRIVATE_KEY")
    pub = os.environ.get("VAPID_PUBLIC_KEY")
    if pri and pub:
        return pri.replace("\\n", "\n"), pub

    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)
    if VAPID_FILE.exists():
        d = json.loads(VAPID_FILE.read_text())
        return d["private_key"], d["public_key"]

    pri_pem, pub_b64 = _generate_keys()
    VAPID_FILE.write_text(json.dumps({
        "private_key": pri_pem,
        "public_key":  pub_b64,
    }))
    print(f"[PUSH] generated VAPID keys -> {VAPID_FILE}")
    return pri_pem, pub_b64


_VAPID_PRIVATE, VAPID_PUBLIC = _load_keys()


def init_push_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS push_subscriptions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            endpoint    TEXT UNIQUE NOT NULL,
            p256dh      TEXT NOT NULL,
            auth        TEXT NOT NULL,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_push_user ON push_subscriptions(user_id);
    """)
    conn.commit()
    conn.close()


def subscribe(user_id, subscription):
    """subscription: {"endpoint": str, "keys": {"p256dh": str, "auth": str}}"""
    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys", {})
    if not endpoint or not keys.get("p256dh") or not keys.get("auth"):
        return False
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO push_subscriptions(user_id,endpoint,p256dh,auth) VALUES (?,?,?,?)",
        (user_id, endpoint, keys["p256dh"], keys["auth"]),
    )
    conn.commit()
    conn.close()
    return True


def unsubscribe(user_id, endpoint):
    conn = get_db()
    conn.execute(
        "DELETE FROM push_subscriptions WHERE user_id=? AND endpoint=?",
        (user_id, endpoint),
    )
    conn.commit()
    conn.close()


def _drop(endpoint):
    conn = get_db()
    conn.execute("DELETE FROM push_subscriptions WHERE endpoint=?", (endpoint,))
    conn.commit()
    conn.close()


def send_to_user(user_id, title, body, *, kind="generic", url="/", tag=None):
    """Fan out to every subscription for this user. Auto-prunes 404/410."""
    key = (user_id, kind)
    now = time.time()
    if now - _last_push.get(key, 0) < PUSH_DEBOUNCE_S:
        return 0
    _last_push[key] = now

    conn = get_db()
    rows = conn.execute(
        "SELECT endpoint,p256dh,auth FROM push_subscriptions WHERE user_id=?",
        (user_id,),
    ).fetchall()
    conn.close()

    payload = json.dumps({
        "title": title,
        "body":  body,
        "url":   url,
        "tag":   tag or kind,
    })

    sent = 0
    for r in rows:
        sub = {
            "endpoint": r["endpoint"],
            "keys": {"p256dh": r["p256dh"], "auth": r["auth"]},
        }
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=_VAPID_PRIVATE,
                vapid_claims={"sub": VAPID_SUB},
                ttl=3600,
            )
            sent += 1
        except WebPushException as e:
            code = getattr(e.response, "status_code", 0) if e.response else 0
            if code in (404, 410):
                _drop(r["endpoint"])
            else:
                print(f"[PUSH] send error to {r['endpoint'][:40]}…: {e}")
        except Exception as e:
            print(f"[PUSH] unexpected error: {e}")
    return sent
