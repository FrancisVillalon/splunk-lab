from client import Splunk
import os
import json
from rules import ENDPOINTS, IGNORE_ALWAYS
import pandas as pd

SNAPSHOT_DIR = os.path.join("snapshots")

# [apps][app-local]
# [inputs_outputs_indexes][indexes]
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)  # don't wrap to 80 chars
pd.set_option("display.max_colwidth", 40)  # truncate long cell values

with Splunk.from_env() as splunk:
    for category in ENDPOINTS:
        for endpoint in ENDPOINTS[category]:
            print(f"-- Capturing ENDPOINTS[{category}][{endpoint}] --")
            api_response: list[dict] = splunk.get(ENDPOINTS[category][endpoint][0])
            df = pd.DataFrame(api_response)
            content_df = pd.json_normalize(df["content"])
            content_df.index = df.index
            content_df = content_df.add_prefix("content.")
            df = df.drop(columns="content").join(content_df)
            print(df.columns)
            break
