import base64
import getpass
import hashlib
import hmac
import os


def b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


stored = os.environ.get("APP_PASSWORD_HASH", "")

has_cr = "\r" in stored
has_lf = "\n" in stored
has_space = " " in stored

print(f"[env] length = {len(stored)}")
print(f"[env] segments = {stored.count('$') + 1}")
print(f"[env] prefix = {stored[:20]!r}")
print(f"[env] has CR = {has_cr}")
print(f"[env] has LF = {has_lf}")
print(f"[env] has space = {has_space}")

if not stored.startswith("pbkdf2_sha256$"):
    raise SystemExit("ERROR: APP_PASSWORD_HASH missing or wrong prefix")

parts = stored.split("$")
if len(parts) != 4:
    raise SystemExit(f"ERROR: expected 4 segments, got {len(parts)}")

_, iters_s, salt_s, hash_s = parts
try:
    iterations = int(iters_s)
except ValueError:
    raise SystemExit(f"ERROR: bad iteration count {iters_s!r}")

try:
    salt = b64d(salt_s)
    expected = b64d(hash_s)
except Exception as e:
    raise SystemExit(f"ERROR: base64 decode failed: {e}")

print(f"[env] iterations = {iterations}")
print(f"[env] salt bytes = {len(salt)}")
print(f"[env] hash bytes = {len(expected)}")

password = getpass.getpass("Password to verify: ")
actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
ok = hmac.compare_digest(actual, expected)
print("MATCH" if ok else "NO MATCH")
raise SystemExit(0 if ok else 1)