import time
import json
import hashlib
from datetime import datetime, timedelta

import bcrypt
from fastapi.testclient import TestClient

from main import app
from database import SessionLocal, init_db
from models.user import User


def sample(obj):
    try:
        return json.dumps(obj)[:240]
    except Exception:
        return str(obj)[:240]


results = []
issues = []

init_db()
client = TestClient(app)

stamp = int(time.time() * 1000)
email = f"qa_reset_{stamp}@example.com"
old_password = "OldPass123!"
new_password = "NewPass123!"

with SessionLocal() as db:
    user = User(
        name="QA Reset User",
        email=email,
        password_hash=bcrypt.hashpw(old_password.encode(), bcrypt.gensalt()).decode(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id

# TEST 1: FORGOT PASSWORD
r1 = client.post("/forgot-password", json={"email": email})
b1 = r1.json() if r1.headers.get("content-type", "").startswith("application/json") else {"raw": r1.text}
token = b1.get("token") if isinstance(b1, dict) else None

with SessionLocal() as db:
    u = db.query(User).filter(User.id == user_id).first()
    db_hash = u.reset_token_hash
    db_expiry = u.reset_token_expiry

token_plain_match = bool(token and db_hash == token)
token_hash_matches_sha256 = bool(token and db_hash == hashlib.sha256(token.encode()).hexdigest())

pass_t1 = (
    r1.status_code == 200
    and bool(token)
    and bool(db_hash)
    and bool(db_expiry)
)
if not pass_t1:
    issues.append("TEST 1 failed required token/DB update checks")

results.append({
    "test": "TEST 1: FORGOT PASSWORD",
    "pass": pass_t1,
    "status": r1.status_code,
    "response": sample(b1),
    "db_reset_token_hash_exists": bool(db_hash),
    "db_reset_token_expiry_exists": bool(db_expiry),
    "db_hash_equals_plain_token": token_plain_match,
    "db_hash_equals_sha256_token": token_hash_matches_sha256,
    "issue": None if pass_t1 else "token missing or DB fields not set",
})

# TEST 2: RESET PASSWORD
r2 = client.post("/reset-password", json={"token": token, "new_password": new_password})
b2 = r2.json() if r2.headers.get("content-type", "").startswith("application/json") else {"raw": r2.text}
pass_t2 = (r2.status_code == 200)
if not pass_t2:
    issues.append("TEST 2 failed: valid token reset did not return 200")

results.append({
    "test": "TEST 2: RESET PASSWORD",
    "pass": pass_t2,
    "status": r2.status_code,
    "response": sample(b2),
    "issue": None if pass_t2 else "valid reset failed or server error",
})

# TEST 3: LOGIN WITH NEW PASSWORD
r3_new = client.post("/login", json={"email": email, "password": new_password})
b3_new = r3_new.json() if r3_new.headers.get("content-type", "").startswith("application/json") else {"raw": r3_new.text}
r3_old = client.post("/login", json={"email": email, "password": old_password})
b3_old = r3_old.json() if r3_old.headers.get("content-type", "").startswith("application/json") else {"raw": r3_old.text}

pass_t3 = (r3_new.status_code == 200 and r3_old.status_code != 200)
if not pass_t3:
    issues.append("TEST 3 failed: new password login or old password invalidation failed")

results.append({
    "test": "TEST 3: LOGIN WITH NEW PASSWORD",
    "pass": pass_t3,
    "status": f"new={r3_new.status_code}, old={r3_old.status_code}",
    "response": f"new={sample(b3_new)} | old={sample(b3_old)}",
    "issue": None if pass_t3 else "new login failed or old password still valid",
})

# TEST 4: TOKEN EXPIRY
r4_forgot = client.post("/forgot-password", json={"email": email})
b4_forgot = r4_forgot.json() if r4_forgot.headers.get("content-type", "").startswith("application/json") else {"raw": r4_forgot.text}
expired_token = b4_forgot.get("token") if isinstance(b4_forgot, dict) else None

with SessionLocal() as db:
    u = db.query(User).filter(User.id == user_id).first()
    u.reset_token_expiry = datetime.utcnow() - timedelta(minutes=5)
    db.commit()

r4 = client.post("/reset-password", json={"token": expired_token, "new_password": "AnotherPass123!"})
b4 = r4.json() if r4.headers.get("content-type", "").startswith("application/json") else {"raw": r4.text}
msg4 = sample(b4).lower()
expiry_message_ok = ("expired" in msg4)
pass_t4 = (r4.status_code == 400 and expiry_message_ok)
if not pass_t4:
    issues.append("TEST 4 failed: expired token not blocked correctly")

results.append({
    "test": "TEST 4: TOKEN EXPIRY",
    "pass": pass_t4,
    "status": r4.status_code,
    "response": sample(b4),
    "issue": None if pass_t4 else "expired token accepted or wrong error/possible datetime handling bug",
})

# TEST 5: SECURITY CHECKS
# 5a) Reuse original token after successful reset should fail
r5_reuse = client.post("/reset-password", json={"token": token, "new_password": "ReuseAttempt123!"})
b5_reuse = r5_reuse.json() if r5_reuse.headers.get("content-type", "").startswith("application/json") else {"raw": r5_reuse.text}

# 5b) Fake token should fail
fake_token = "this.is.not.a.valid.reset.token"
r5_fake = client.post("/reset-password", json={"token": fake_token, "new_password": "FakeAttempt123!"})
b5_fake = r5_fake.json() if r5_fake.headers.get("content-type", "").startswith("application/json") else {"raw": r5_fake.text}

reuse_blocked = (r5_reuse.status_code >= 400)
fake_blocked = (r5_fake.status_code >= 400)

# Hash validation evidence uses TEST1 pre-reset DB checks
token_stored_hashed = bool(db_hash and token and db_hash != token)
hash_validation_ok = token_hash_matches_sha256

pass_t5 = (reuse_blocked and fake_blocked and token_stored_hashed and hash_validation_ok)
if not pass_t5:
    issues.append("TEST 5 failed: token reuse/fake-token/hash-validation checks failed")

results.append({
    "test": "TEST 5: SECURITY CHECKS",
    "pass": pass_t5,
    "status": f"reuse={r5_reuse.status_code}, fake={r5_fake.status_code}",
    "response": f"reuse={sample(b5_reuse)} | fake={sample(b5_fake)}",
    "token_reuse_blocked": reuse_blocked,
    "fake_token_blocked": fake_blocked,
    "token_stored_hashed": token_stored_hashed,
    "token_hash_validation_matches_sha256": hash_validation_ok,
    "issue": None if pass_t5 else "security checks failed",
})

all_pass = all(r["pass"] for r in results)
verdict = "STABLE" if all_pass else ("PARTIALLY STABLE" if len(issues) <= 2 else "UNSTABLE")

print("=== INDEPENDENT QA RESULTS ===")
for r in results:
    print(json.dumps(r, default=str))
print("=== FINAL VERDICT ===")
print(verdict)
if issues:
    print("=== ISSUES ===")
    for i in issues:
        print(i)
