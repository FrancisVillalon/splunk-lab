from client import Splunk
import os
import json
from rules import ENDPOINTS, IGNORE_ALWAYS

SNAPSHOT_DIR = os.path.join("snapshots")

# [apps][app-local]
# [inputs_outputs_indexes][indexes]
#

with Splunk.from_env() as splunk:
    entries = splunk.get(ENDPOINTS["kvstore"]["collections"][0])
    entries = [x["name"] for x in entries]
    print(json.dumps(entries, indent=2))
