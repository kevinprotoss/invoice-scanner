import base64
import getpass
import hashlib
import os

password = getpass.getpass("Password: ")
if not password:
    raise SystemExit("empty password")

iterations = 200_000
salt = os.urandom(16)
digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)

s = base64.urlsafe_b64encode(salt).decode().rstrip("=")
h = base64.urlsafe_b64encode(digest).decode().rstrip("=")
print(f"pbkdf2_sha256${iterations}${s}${h}")