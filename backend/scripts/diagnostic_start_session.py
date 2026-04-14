"""
Diagnostic test for start_session 500 error
"""
import requests
import json

BACKEND_URL = "http://127.0.0.1:8000"

# Use real user/resume from previous test
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIzIn0.5jqrUYFlJu0bqj_QoL7sCDZlGb07_8t-3pf-B0L3EwE"  # Will need to get fresh
RESUME_ID = 3  # From previous test
USER_ID = 3

# Get fresh JWT first
print("Getting fresh JWT token...")
response = requests.post(
    f"{BACKEND_URL}/login",
    json={
        "email": "test_user_1776155915.636662@test.com",
        "password": "TestPassword123!"
    }
)
if response.status_code == 200:
    JWT_TOKEN = response.json().get("access_token")
    print(f"✓ JWT obtained: {JWT_TOKEN[:50]}...")
else:
    print(f"✗ Failed to get JWT: {response.status_code}")
    print(response.text)
    exit(1)

# Try to start session
print("\nAttempting to start session...")
headers = {"Authorization": f"Bearer {JWT_TOKEN}"}
payload = {"resume_id": RESUME_ID}

print(f"Request: POST /start_session")
print(f"Payload: {json.dumps(payload, indent=2)}")
print(f"Headers: {headers}")

response = requests.post(
    f"{BACKEND_URL}/start_session",
    headers=headers,
    json=payload
)

print(f"\nResponse Status: {response.status_code}")
print(f"Response Body:")
print(json.dumps(response.json(), indent=2))

if response.status_code >= 400:
    print(f"\n❌ ERROR: Status {response.status_code}")
    print("Response indicates server error. Check backend logs.")
