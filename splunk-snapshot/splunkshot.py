import argparse
import os
import sys
import logger

from collections import Counter

from btool import BTool
from snapshot import (
    BASE_SNAPSHOT_DIR,
    diff_snapshots,
    list_snapshots,
    write_settings,
)

CONFS = ["inputs", "props", "transforms", "outputs", "indexes", "server"]

# Exit codes. Drift is deliberately distinct from failure, so a caller can tell
# "the configs differ" from "the tool could not run".
EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_FAIL = 2

log = logger.get_logger(__name__)


def cmd_clear(args):
    """
    Clear all snapshots in the snapshots directory.
    """
    if os.path.exists(BASE_SNAPSHOT_DIR):
        for item in os.listdir(BASE_SNAPSHOT_DIR):
            item_path = os.path.join(BASE_SNAPSHOT_DIR, item)
            if os.path.isdir(item_path) and item.startswith("snapshot_"):
                log.info(f"Removing snapshot: {item_path}")
                for root, dirs, files in os.walk(item_path, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(item_path)
    else:
        log.info(f"No snapshots found in {BASE_SNAPSHOT_DIR}.")

def cmd_snapshot(args):
    """
    Snapshot the current configuration of the Splunk instance.
    """
    # Number one past the highest existing snapshot. list_snapshots() returns
    # [] for a missing or empty directory, so there is no listdir guard and no
    # max() over a possibly-empty sequence here.
    snaps = list_snapshots()
    n = int(snaps[-1].name.split("_")[1]) + 1 if snaps else 1
    SNAPSHOT_DIR = BASE_SNAPSHOT_DIR / f"snapshot_{n}"

    log.info(f"Creating snapshot directory: {SNAPSHOT_DIR}")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Snapshotting configurations...")
    btool_instance = BTool()
    available_confs = btool_instance.confs()
    for conf in CONFS:
        if conf not in available_confs:
            log.warning(f"{conf}.conf is not found in {btool_instance.home}/etc")
            continue
        conf_data = btool_instance.extract(conf)
        write_settings(f"{SNAPSHOT_DIR}/{conf}.snapshot", conf_data)
    log.info(f"Snapshot completed. Snapshot saved in {SNAPSHOT_DIR}.")

def _render(c) -> str:
    """One line for one change.

    Values are flattened: a multi-line EVAL would otherwise wrap across the
    report and break the one-change-per-line reading.
    """
    stanza, key = c.identity[1], c.identity[2]
    old = c.old.value.replace("\n", "\\n") if c.old else None
    new = c.new.value.replace("\n", "\\n") if c.new else None

    if c.kind == "added":
        return f"  + [{stanza}] {key} = {new}"
    if c.kind == "removed":
        return f"  - [{stanza}] {key} = {old}"
    if c.kind == "modified":
        return f"  ~ [{stanza}] {key}: {old} -> {new}"
    # moved: the value is what did NOT change, so show the source instead --
    # same effective config now winning from a different file.
    return f"  > [{stanza}] {key}: {c.old.path} -> {c.new.path}"


def cmd_diff(args):
    """
    Compare the two most recent snapshots and report what differs.
    """
    snaps = list_snapshots()
    if len(snaps) < 2:
        log.error(f"need two snapshots to diff, found {len(snaps)}")
        return EXIT_FAIL
    dir_a, dir_b = snaps[-2], snaps[-1]

    log.info(f"Comparing {dir_a} -> {dir_b}")
    changes = diff_snapshots(dir_a, dir_b)

    if not changes:
        log.info("No differences found.")
        return EXIT_OK

    # The report goes to stdout while progress goes to the logger (stderr), so
    # the diff can be piped or redirected without status lines mixed into it.
    current = None
    for c in sorted(changes, key=lambda c: (c.identity, c.kind)):
        if c.identity[0] != current:
            current = c.identity[0]
            print(f"\n{current}")
        print(_render(c))

    counts = Counter(c.kind for c in changes)
    summary = ", ".join(f"{n} {kind}" for kind, n in sorted(counts.items()))
    log.info(f"{len(changes)} difference(s): {summary}")
    return EXIT_DRIFT

def cmd_list(args):
    log.info("Listing all snapshots...")
    if os.path.exists(BASE_SNAPSHOT_DIR):
        for item in os.listdir(BASE_SNAPSHOT_DIR):
            item_path = os.path.join(BASE_SNAPSHOT_DIR, item)
            if os.path.isdir(item_path) and item.startswith("snapshot_"):
                log.info(f" - {item}")

def build_parser() -> argparse.ArgumentParser:
    """Assemble the CLI.

    Separate from main() so the grammar can be exercised in a test without
    dispatching to a handler that talks to a host.
    """
    parser = argparse.ArgumentParser(prog="splunkshot")

    # Global flags
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="enable verbose logging"
    )

    sub = parser.add_subparsers(dest="command", required=True)
    # Commands
    snapshot = sub.add_parser(
        "snapshot", help="take a snapshot of the current configuration"
    )
    snapshot.set_defaults(func=cmd_snapshot)

    clear = sub.add_parser(
        "clear", help="clear all snapshots"
    )
    clear.set_defaults(func=cmd_clear)

    # Named list_parser, not list_snapshots: a local of that name would shadow
    # the module-level helper inside this function.
    list_parser = sub.add_parser(
        "list", help="list all snapshots"
    )
    list_parser.set_defaults(func=cmd_list)

    diff = sub.add_parser(
        "diff", help="compare the two most recent snapshots"
    )
    diff.set_defaults(func=cmd_diff)

    return parser


def main():
    args = build_parser().parse_args()
    logger.setup(verbose=args.verbose)
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
