#!/usr/bin/env python3
"""
protect.py — bundle the static site into one file and encrypt it with a password.

    pip install cryptography
    python3 protect.py --src . --out dist --password 'correct horse battery staple'

Produces dist/index.html: a small plaintext loader carrying the ciphertext.
Nothing else needs to be published.

Crypto: AES-256-GCM, key derived with PBKDF2-HMAC-SHA256. Both are available in
the browser through WebCrypto, so the loader needs no library. The iteration
count is the only thing standing between an attacker with the blob and your
content — keep it high and pick a real passphrase.
"""

import argparse
import base64
import json
import mimetypes
import os
import re
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITERATIONS = 600_000


# --------------------------------------------------------------- inlining
def data_uri(path):
    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"
    with open(path, "rb") as fh:
        return "data:%s;base64,%s" % (mime, base64.b64encode(fh.read()).decode())


def inline(src_dir):
    """Fold styles.css, app.js and every local image into one HTML string."""
    html = open(os.path.join(src_dir, "index.html"), encoding="utf-8").read()

    def read(rel):
        return open(os.path.join(src_dir, rel), encoding="utf-8").read()

    # <link rel="stylesheet" href="styles.css">  ->  <style>...</style>
    def css_sub(m):
        href = m.group(1)
        if href.startswith(("http://", "https://", "//")):
            return m.group(0)          # leave Google Fonts alone
        return "<style>\n%s\n</style>" % read(href)

    html = re.sub(
        r'<link[^>]+rel=["\']stylesheet["\'][^>]*href=["\']([^"\']+)["\'][^>]*>',
        css_sub, html)

    # <script src="app.js"></script>  ->  <script>...</script>
    def js_sub(m):
        src = m.group(1)
        if src.startswith(("http://", "https://", "//")):
            return m.group(0)
        return "<script>\n%s\n</script>" % read(src)

    html = re.sub(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>\s*</script>',
                  js_sub, html)

    # every local src="..." -> data URI
    def img_sub(m):
        attr, url = m.group(1), m.group(2)
        if url.startswith(("http://", "https://", "//", "data:", "#", "mailto:")):
            return m.group(0)
        path = os.path.join(src_dir, url)
        if not os.path.isfile(path):
            print("  ! missing asset, left as-is: %s" % url, file=sys.stderr)
            return m.group(0)
        return '%s="%s"' % (attr, data_uri(path))

    html = re.sub(r'\b(src)=["\']([^"\']+)["\']', img_sub, html)
    return html


# --------------------------------------------------------------- crypto
def encrypt(plaintext, password):
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                     salt=salt, iterations=ITERATIONS).derive(password.encode())
    blob = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode()
    return {"salt": b64(salt), "nonce": b64(nonce),
            "data": b64(blob), "iter": ITERATIONS}


# --------------------------------------------------------------- loader
LOADER = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Protected</title>
<style>
  :root { color-scheme: light; }
  body { margin:0; min-height:100vh; display:grid; place-items:center;
         font:400 15px/1.5 ui-sans-serif,system-ui,sans-serif;
         background:#f8fafc; color:#111625; }
  form { width:min(360px,90vw); background:#fff; padding:32px;
         border:1px solid #eaecf0; border-radius:14px;
         box-shadow:0 2px 8px rgba(0,0,0,.04); }
  h1 { margin:0 0 6px; font-size:16px; font-weight:700; }
  p  { margin:0 0 20px; font-size:13px; color:#64748b; }
  label { display:block; font-size:13px; font-weight:600; margin-bottom:8px; }
  input { width:100%; box-sizing:border-box; padding:10px 12px; font:inherit;
          border:1px solid #e2e8f0; border-radius:8px; background:#fff; }
  input:focus { outline:2px solid #00A3E0; outline-offset:1px; }
  button { width:100%; margin-top:16px; padding:12px; font:inherit;
           font-weight:700; color:#fff; background:#0054A6;
           border:0; border-radius:8px; cursor:pointer; }
  button:disabled { opacity:.6; cursor:progress; }
  .err { margin:12px 0 0; font-size:13px; color:#b42318; min-height:1.2em; }
</style>
</head>
<body>
<form id="gate" autocomplete="off">
  <h1>This page is password protected</h1>
  <p>Enter the passphrase to decrypt it in your browser.</p>
  <label for="pw">Passphrase</label>
  <input id="pw" type="password" autocomplete="current-password" autofocus>
  <button id="go" type="submit">Unlock</button>
  <p class="err" id="err" role="alert"></p>
</form>

<script>
const PAYLOAD = __PAYLOAD__;

const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));

async function unlock(password) {
  const enc = new TextEncoder();
  const base = await crypto.subtle.importKey(
    'raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']);
  const key = await crypto.subtle.deriveKey(
    { name:'PBKDF2', salt:b64(PAYLOAD.salt),
      iterations:PAYLOAD.iter, hash:'SHA-256' },
    base, { name:'AES-GCM', length:256 }, false, ['decrypt']);
  const plain = await crypto.subtle.decrypt(
    { name:'AES-GCM', iv:b64(PAYLOAD.nonce) }, key, b64(PAYLOAD.data));
  return new TextDecoder().decode(plain);
}

document.getElementById('gate').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('go');
  const err = document.getElementById('err');
  err.textContent = '';
  btn.disabled = true;
  btn.textContent = 'Decrypting\\u2026';
  // let the browser paint before the KDF blocks the main thread
  await new Promise(r => setTimeout(r, 30));
  try {
    const html = await unlock(document.getElementById('pw').value);
    document.open();
    document.write(html);
    document.close();
  } catch (_) {
    err.textContent = 'Wrong passphrase.';
    btn.disabled = false;
    btn.textContent = 'Unlock';
    document.getElementById('pw').select();
  }
});
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=".", help="folder holding index.html")
    ap.add_argument("--out", default="dist", help="output folder")
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    if len(args.password) < 12:
        print("Refusing: passphrase under 12 characters. The blob is "
              "brute-forceable offline; length is your only defence.",
              file=sys.stderr)
        return 1

    print("Inlining assets...")
    html = inline(args.src)
    print("  bundled: %.1f KB" % (len(html.encode()) / 1024))

    print("Encrypting (PBKDF2 %d iterations)..." % ITERATIONS)
    payload = encrypt(html, args.password)

    os.makedirs(args.out, exist_ok=True)
    out = os.path.join(args.out, "index.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(LOADER.replace("__PAYLOAD__", json.dumps(payload)))

    print("Wrote %s (%.1f KB)" % (out, os.path.getsize(out) / 1024))
    print("\nPublish ONLY this file. Do not commit the plaintext source "
          "to a public repo — git history keeps it forever.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
