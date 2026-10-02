import ssl
import time
from datetime import datetime
import urllib.error
import urllib.request

# Splunk endpoints to check, as seen from inside the docker network
TARGETS = {
    "sh1_web": "https://sh1:8000",
    "hf1_web": "https://hf1:8000",
    "ds1_web": "https://ds1:8000",
    "ds1_mgmt": "https://ds1:8089",
    "idx1_mgmt": "https://idx1:8089",
}

TIMEOUT = 5

# Every instance uses splunk's self-signed cert
ctx = ssl._create_unverified_context()

for name, url in TARGETS.items():
    # Local time with offset, e.g. Oct 02 14:03:11 +0800
    timestamp = datetime.now().astimezone().strftime("%b %d %H:%M:%S %z")
    start = time.time()
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT, context=ctx) as resp:
            status = resp.status
        error = "none"
    except urllib.error.HTTPError as e:
        # Endpoint responded, just not with a 2xx (e.g. 401 on the mgmt port)
        status = e.code
        error = "none"
    except Exception as e:
        # No response at all: connection refused, timeout, DNS failure
        status = 0
        error = type(e).__name__
    time_ms = int((time.time() - start) * 1000)
    print(
        f"{timestamp} target={name} url={url} status={status} time_ms={time_ms} error={error}"
    )
