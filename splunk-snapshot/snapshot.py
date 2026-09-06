"""Snapshots as data: the settings model, how they are stored, how they differ.

Nothing here touches a Splunk host -- it works against files on disk, so a
diff runs on a machine that has never had Splunk installed.
"""

import json
import logger
from dataclasses import dataclass, asdict
from pathlib import Path

log = logger.get_logger(__name__)

BASE_SNAPSHOT_DIR = Path("./snapshots")


@dataclass(frozen=True)
class Setting:
    """One resolved conf setting and the file it was resolved from."""

    __slots__ = ('config', 'path', 'app', 'scope', 'stanza', 'key', 'value')
    config: str
    path: str
    app: str
    scope: str
    stanza: str
    key: str
    value: str

    @property
    def identity(self):
        """The fields naming the same knob across two snapshots.

        Deliberately excludes value (what changed) and path/app/scope (where it
        came from), so a diff can tell those two kinds of change apart.
        """
        return (self.config, self.stanza, self.key)

    def __str__(self):
        return f"{self.config} {self.path} {self.app} {self.scope} {self.stanza} {self.key}={self.value}"


@dataclass(frozen=True)
class Change:
    kind: str                       # added | removed | modified | moved
    identity: tuple[str, str, str]
    old: Setting | None
    new: Setting | None


def write_settings(path, settings):
    """Serialize settings as JSON Lines.

    Sorted because a set has no order of its own: without it, two snapshots of
    an unchanged instance differ on every line. JSON rather than a delimited
    format because stanzas and values both contain spaces and '='.
    """
    with open(path, "w") as f:
        for s in sorted(settings, key=lambda s: (s.config, s.stanza, s.key, s.scope, s.path)):
            f.write(json.dumps(asdict(s), sort_keys=True) + "\n")


def read_settings(path):
    """Load a JSON Lines snapshot back into Settings."""
    settings = set()
    with open(path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            settings.add(Setting(**json.loads(line)))
    return settings


def diff_settings(old: set, new: set) -> list[Change]:
    """Compare two sets of settings, keyed on identity.

    Keyed rather than differenced: whole-object set difference reports a value
    change as one removal plus one addition, which is indistinguishable from a
    genuine delete plus a genuine add.
    """
    a: dict[tuple[str, str, str], Setting] = {s.identity: s for s in old}
    b: dict[tuple[str, str, str], Setting] = {s.identity: s for s in new}
    changes: list[Change] = []

    for k in a.keys() - b.keys():
        changes.append(Change(kind="removed", identity=k, old=a[k], new=None))
    for k in b.keys() - a.keys():
        changes.append(Change(kind="added", identity=k, old=None, new=b[k]))

    for k in a.keys() & b.keys():
        if a[k].value != b[k].value:
            changes.append(Change(kind="modified", identity=k, old=a[k], new=b[k]))
        elif a[k].scope != b[k].scope or a[k].path != b[k].path:
            # Same effective value, different file winning -- a precedence
            # shift that a value-only comparison would miss entirely.
            changes.append(Change(kind="moved", identity=k, old=a[k], new=b[k]))
    return changes


def list_snapshots(base=BASE_SNAPSHOT_DIR) -> list[Path]:
    """Snapshot directories, oldest first.

    Ordered numerically rather than lexically: sorted as strings, snapshot_10
    lands before snapshot_2 and "the last two" quietly becomes the wrong pair.
    Returns [] for a missing directory so callers never have to guard it.
    """
    base = Path(base)
    if not base.is_dir():
        return []

    found = []
    for p in base.iterdir():
        if not (p.is_dir() and p.name.startswith("snapshot_")):
            continue
        suffix = p.name.split("_", 1)[1]
        if not suffix.isdigit():
            log.warning(f"ignoring oddly named snapshot: {p.name}")
            continue
        found.append((int(suffix), p))

    return [p for _, p in sorted(found, key=lambda t: t[0])]


def diff_snapshots(dir_a, dir_b):
    """
    Compare two snapshot directories and return a list of changes.

    Walks the union of the .snapshot files on both sides rather than a fixed
    conf list, so a conf present in only one snapshot -- outputs.conf appearing
    after a migration, say -- is reported as added/removed settings instead of
    being skipped. The absent side reads as an empty set, so it needs no
    special case.
    """
    names = {p.name for p in Path(dir_a).glob("*.snapshot")}
    names |= {p.name for p in Path(dir_b).glob("*.snapshot")}

    changes = []
    for name in sorted(names):
        file_a, file_b = Path(dir_a) / name, Path(dir_b) / name
        settings_a = read_settings(file_a) if file_a.exists() else set()
        settings_b = read_settings(file_b) if file_b.exists() else set()
        changes.extend(diff_settings(settings_a, settings_b))
    return changes
