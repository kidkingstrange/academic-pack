import urllib.request
import urllib.error
import json
import time

url = "https://edgepack.thescaleconference.com/api/admin/marketing/dispatch-preview-test"
payload = json.dumps({
    "recipient": "daviditoyaa@gmail.com",
    "product_slug": "quitting-the-handjob",
    "campaign_type": "direct_response"
}).encode("utf-8")

headers = {
    "Content-Type": "application/json",
    "User-Agent": "ScaleMarketingEngine/1.0"
}

print("Monitoring Render build deployment for commit 157b5c9...")
deployed = False
for attempt in range(1, 25):
    try:
        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            print("\n🎉 SUCCESS! LIVE EMAIL DISPATCHED!")
            print(json.dumps(data, indent=2))
            deployed = True
            break
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode()
        if status == 404:
            print(f"[{attempt}/24] Render building... (HTTP 404: route not live yet)")
        elif status == 500:
            print(f"[{attempt}/24] Route live, but SMTP error: {body}")
            break
        else:
            print(f"[{attempt}/24] HTTP {status}: {body}")
            break
    except Exception as e:
        print(f"[{attempt}/24] Connection error: {e}")
    time.sleep(6)

if not deployed:
    print("Deployment timed out or failed.")
