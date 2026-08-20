import urllib3
import os
import requests
from dotenv import load_dotenv
from urllib.parse import quote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SplunkError(Exception):
    pass


def env():
    """Read connection details from .env"""
    load_dotenv()
    try:
        return (
            os.environ["SPLUNK_URL"].rstrip("/"),
            os.environ["SPLUNK_USER"],
            os.environ["SPLUNK_PASSWORD"],
        )
    except KeyError as e:
        raise SplunkError(f"missing env var: {e.args[0]}") from None


class Splunk:
    def __init__(self, url, user, password):
        self.url = url
        self.user = user
        self.password = password
        self.s = requests.Session()
        self.s.verify = False  # self-signed management cert
        self._login(user, password)

    # auth
    @classmethod
    def from_env(cls):
        return cls(*env())

    def _login(self, user, password):
        """Sets sessionKey in authorization headers"""
        # Get session key
        r = self.s.post(
            self.url + "/services/auth/login",
            data={"username": user, "password": password, "output_mode": "json"},
            timeout=30,
        )
        # Set session key in authorization header
        if r.status_code != 200:
            raise SplunkError(f"login failed ({r.status_code}): {r.text[:200]}")
        self.s.headers["Authorization"] = f"Splunk {r.json()['sessionKey']}"

    def logout(self):
        """Invalidate the session key server-side by supplying session key to httpauth-tokens endpoint"""
        auth = self.s.headers.get("Authorization", "")
        session_key = auth.removeprefix("Splunk ")
        try:
            if session_key:
                r = self.s.delete(
                    f"{self.url}/services/authentication/httpauth-tokens/{quote(session_key, safe='')}",
                    timeout=30,
                )
                if r.status_code != 200:
                    print(f"logout failed ({r.status_code}): {self._why(r)}")
        except requests.RequestException as e:
            print(e)
        finally:
            self.s.headers.pop("Authorization", None)

    # methods
    def get(self, path, params=None, page_size=500):
        """Return all entries for a REST path, following pagination"""
        entries, offset = [], 0
        while True:
            # Set default params, add additional params
            q = {"output_mode": "json", "count": page_size, "offset": offset}
            if params:
                q.update(params)
            # Perform the request
            r = self.s.get(self.url + path, params=q, timeout=60)
            # Handle http errors
            if r.status_code != 200:
                raise SplunkError(f"{path} -> {r.status_code}: {self._why(r)}")
            # Add entry to entries
            body = r.json()
            batch = body.get("entry", [])
            entries.extend(batch)
            total = body.get("paging", {}).get("total")
            if len(batch) < page_size:
                if total is not None and len(entries) != total:
                    raise SplunkError(
                        f"{path}: got {len(entries)} entries, servers reports {total}"
                    )
                break
            offset += page_size
        return entries

    # Not robust, check
    def search(self, spl, earliest="-24@h", latest="now"):
        """Run SPL via oneshot, return list of result dicts."""
        if not spl.lstrip().startswith("|"):
            spl = f"search {spl}"
        r = self.s.post(
            self.url + "/services/search/jobs",
            data={
                "search": spl,
                "exec_mode": "oneshot",
                "output_mode": "json",
                "earliest_time": earliest,
                "latest_time": latest,
                "count": 0,
            },
            timeout=300,
        )
        if r.status_code != 200:
            raise SplunkError(f"search -> {r.status_code}: {self._why(r)}")
        return r.json().get("results", [])

    # Context
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.logout()
        return False

    # static
    @staticmethod
    def _why(r):
        try:
            msgs = r.json().get("messages", [])
            return "; ".join(m.get("text", "") for m in msgs) or r.text[:200]
        except ValueError:
            return r.text[:200]
