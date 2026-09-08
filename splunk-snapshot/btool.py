"""Running Splunk's own btool against an installation and parsing its output."""

import subprocess
import logger

from snapshot import Setting

log = logger.get_logger(__name__)


class BTool:
    def __init__(self, splunk_home="/opt/splunk"):
        self.home = splunk_home
        self.splunk_bin = f"{self.home}/bin/splunk"

    def _run(self, argv):
        return subprocess.run(argv, capture_output=True, text=True)

    def confs(self):
        """
        Get all confs in the current host
        """
        r = self._run(
            ["find", f"{self.home}/etc", "-name", "*.conf", "-printf", "%f\n"]
        )

        if r.returncode != 0 and not r.stdout:
            detail = r.stderr.strip() or f"no such directory: {self.home}/etc"
            raise RuntimeError(f"listing confs failed: {detail}")

        names = set()
        for line in r.stdout.splitlines():
            name = line.strip().removesuffix(".conf")
            if name:
                names.add(name)
        return sorted(names)

    def extract(self, conf):
        """
        Extract a conf file from the current host

        Note: derives app and scope from the last path segments, and splits on
        the first "=" to get key and value. May cause issues with windows paths.
        """
        r = self._run([self.splunk_bin, "btool", conf, "list", "--debug"])
        if r.returncode != 0:
            detail = r.stderr.strip() or f"no such conf: {conf}"
            log.error(f"extracting conf failed: {detail}")
            raise RuntimeError(f"extracting conf failed: {detail}")
        
        confs: set[Setting] = set()
        stanza = None
        pending = None          # fields of the setting still being read
        fragments: list[str] = []

        def flush():
            """Commit the setting being accumulated, if any."""
            nonlocal pending, fragments
            if pending is not None:
                value = "\n".join(fragments).strip()
                flat = value.replace("\n", "\\n")
                log.debug(f"Extracted setting: {pending['path']} "
                          f"{pending['stanza']} {pending['key']}={flat}")
                confs.add(Setting(value=value, **pending))
            pending, fragments = None, []

        for line in r.stdout.splitlines():
            parts = line.split(None, 1)

            # --debug prefixes every real setting with its source file, so a
            # line without one continues the previous value: Splunk joins conf
            # continuations into a value holding real newlines, which btool
            # then prints verbatim. Requiring the prefix to end in .conf keeps
            # a continuation that happens to start with a path (inside an
            # EXTRACT regex, say) from being mistaken for a new setting.
            if not (parts and parts[0].startswith("/") and parts[0].endswith(".conf")):
                if pending is None:
                    log.warning(f"skipping line: {line}")
                else:
                    fragments.append(line)
                continue

            # A prefixed line always ends whatever value came before it.
            flush()

            if len(parts) < 2:
                log.warning(f"no setting in line: {line}")
                raise RuntimeError(f"no setting in line: {line}")
            path, rest = parts[0], parts[1].strip()

            # The last three segments are always <app>/<scope>/<file>.conf,
            # whether the path is etc/system/local, etc/apps/<app>/local, or
            # etc/users/<user>/<app>/local -- and indexing from the end also
            # holds for a SPLUNK_HOME that isn't two segments deep.
            segs = path.split("/")
            if len(segs) < 3:
                log.warning(f"unexpected conf path: {path}")
                continue
            config, scope, app = segs[-1], segs[-2], segs[-3]

            # A stanza header applies to every setting until the next one.
            if rest.startswith("[") and rest.endswith("]"):
                stanza = rest[1:-1]
                continue

            key, sep, value = rest.partition("=")
            if not sep:
                log.warning(f"no '=' in line: {line}")
                continue

            if stanza is None:
                log.warning(f"setting before any stanza: {line}")
                continue

            pending = dict(
                config=config,
                path=path,
                app=app,
                scope=scope,
                stanza=stanza,
                key=key.strip(),
            )
            fragments = [value.strip()]

        # The last setting in the output has no successor to trigger a flush.
        flush()
        return confs

    def version(self):
        pass
