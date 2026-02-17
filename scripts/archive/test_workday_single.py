import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def check(slug):
    url = f"https://{slug}.myworkdayjobs.com"
    try:
        r = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        print(f"✅ {slug}: {r.status_code}")
        # If it redirects to /w/tm/0/jobs or similar, print that
        if r.is_redirect or r.history:
              print(f"   -> Redirected to: {r.url}")

    except requests.exceptions.ConnectionError:
        print(f"❌ {slug}: NXDOMAIN (Does not exist)")
    except Exception as e:
        print(f"⚠️ {slug}: {e}")

slugs = ["netflix", "target", "walmart", "nike", "nvidia", "salesforce", "visa", "mastercard"]
for s in slugs:
    check(s)
