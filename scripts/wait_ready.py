"""Wait for the test API after Docker starts."""
import time
import httpx

for attempt in range(120):
    try:
        if httpx.get('http://127.0.0.1:5512/api/health', timeout=2).status_code == 200:
            break
    except httpx.HTTPError:
        pass
    time.sleep(1)
else:
    raise RuntimeError('The test API did not become ready.')
