import urllib.request
url = 'http://127.0.0.1:8000/'
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        print(resp.status)
        print(resp.read().decode('utf-8', errors='ignore'))
except Exception as exc:
    print(type(exc).__name__, exc)
