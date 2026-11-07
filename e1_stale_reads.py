import requests

BASE = "http://127.0.0.1:5000"
stale = 0
for i in range(100):
    requests.post(f"{BASE}/counter/increment")
    a = requests.get(f"{BASE}/counter?from=primary").json()["value"]
    b = requests.get(f"{BASE}/counter?from=replica").json()["value"]
    if a != b:
        stale += 1
print("stale reads from the replica:", stale, "out of 100")
