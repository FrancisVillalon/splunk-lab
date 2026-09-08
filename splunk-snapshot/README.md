# splunkshot

`btool` answers what the effective configuration is right now. It cannot tell you
what changed. splunkshot freezes that answer to disk so two points in time can be
compared.

> [!WARNING]
> The tool right now  is an early prototype.


## Where it runs

It shells out to `$SPLUNK_HOME/bin/splunk btool`, so it has to run **on the Splunk
instance**, as a user that can read `$SPLUNK_HOME/etc`. `SPLUNK_HOME` is hard-coded
to `/opt/splunk`.

In this lab, Splunk is the `splunk` container and the tool directory is bind-mounted
into it at `/mnt/splunk-snapshot` (see
[`containers/migrated-docker/docker-compose.yml`](../containers/migrated-docker/docker-compose.yml)):

```
docker exec -u 0 -w /mnt/splunk-snapshot splunk python3 splunkshot.py snapshot
```

`-u 0` is required. The container's default user is `ansible` (uid 999), the
bind-mounted `snapshots/` directory is owned by the host user, and without it the
run fails at `mkdir` with
`PermissionError: [Errno 13] Permission denied: 'snapshots/snapshot_N'`.
The consequence is that snapshots come back **root-owned on the host**, so removing
them using `clear` needs `sudo`.

The mount is read-write, so snapshots written inside the container land in
`splunk-snapshot/snapshots/` on the host, where `diff` and `list` read them with the
host's own Python and no Splunk present at all.

## Quickstart

See what has been captured already, then take a snapshot of the instance as it
stands. Numbering continues from the highest existing snapshot:

```
$ python3 splunkshot.py list
[17:36:46] [INFO] [splunkshot:cmd_list]  Listing all snapshots...
[17:36:46] [INFO] [splunkshot:cmd_list]   - snapshot_1
[17:36:46] [INFO] [splunkshot:cmd_list]   - snapshot_2
[17:36:46] [INFO] [splunkshot:cmd_list]   - snapshot_3

$ docker exec -u 0 -w /mnt/splunk-snapshot splunk python3 splunkshot.py snapshot
[17:38:36] [INFO] [splunkshot:cmd_snapshot]  Creating snapshot directory: snapshots/snapshot_4
[17:38:36] [INFO] [splunkshot:cmd_snapshot]  Snapshotting configurations...
[17:38:36] [INFO] [splunkshot:cmd_snapshot]  Snapshot completed. Snapshot saved in snapshots/snapshot_4.
```

Change something, snapshot again, then compare the pair:

```
$ python3 splunkshot.py diff
[17:36:48] [INFO] [splunkshot:cmd_diff]  Comparing snapshots/snapshot_2 -> snapshots/snapshot_3
[17:36:48] [INFO] [splunkshot:cmd_diff]  7 difference(s): 5 added, 1 modified, 1 moved

indexes.conf
  > [_audit] allowBulkDataMove: /opt/splunk/etc/system/default/indexes.conf -> /opt/splunk/etc/system/local/indexes.conf

inputs.conf
  ~ [http] disabled: 1 -> 0
  + [splunktcp://9997] _rcvbuf = 1572864
  + [splunktcp://9997] disabled = 0
  + [splunktcp://9997] host = $decideOnStartup
  + [splunktcp://9997] index = default

server.conf
  + [general] allowed_unarchive_commands = _auto,bzip2,gzip,zstd
```

A receiving port opened, HEC enabled, and `_audit` picking up a local override.

The report goes to **stdout**; progress and summary lines go to the logger on
**stderr**. `diff > drift.txt` captures the changes without status lines mixed in.

## Commands

| Command    | Does                                                      | Exit                            |
| ---------- | --------------------------------------------------------- | ------------------------------- |
| `snapshot` | Captures the six confs into a new `snapshots/snapshot_N/` | 0                               |
| `diff`     | Compares the two most recent snapshots                    | 0 clean · 1 drift · 2 can't run |
| `list`     | Lists snapshot directories                                | 0                               |
| `clear`    | Deletes every `snapshot_*` directory. No confirmation     | 0                               |

`-v` enables debug logging and is a global flag — it goes **before** the subcommand
(`splunkshot.py -v diff`, not `splunkshot.py diff -v`).

Drift exits `1` and failure exits `2` deliberately, so a caller can tell "the configs
differ" from "the tool could not run". A post-migration check can branch on that:

```
python3 splunkshot.py diff; case $? in
  0) echo "no drift" ;;
  1) echo "drift — review the report" ;;
  2) echo "check failed to run" ;;
esac
```

## Reading a diff

Changes are grouped by conf file, one change per line:

| | Kind | Means |
| --- | --- | --- |
| `+` | added | The setting is present in the new snapshot only |
| `-` | removed | Present in the old snapshot only |
| `~` | modified | Same setting, different value: `old -> new` |
| `>` | moved | Same *value*, different file winning |

`moved` is the one worth understanding. Splunk resolves a setting from whichever
file wins on precedence, and `default -> local` for an identical value means the
config is now pinned locally rather than inherited. 

Multi-line values (an `EVAL` or `EXTRACT` spanning several lines) are flattened to
`\n` in the report so one change stays on one line. The snapshot keeps the real
newlines.

## Snapshots

`snapshot` captures a fixed list of six confs: `inputs`, `props`, `transforms`,
`outputs`, `indexes`, `server`. This list can be expanded but is left barebones for the prototype.

If any of the listed `confs` do not exist on the host, the rest of them will be snapshotted.

Snapshot directories are 1-indexed and the higher the value of the suffix, the later the snapshot.

Each `<conf>.snapshot` file is JSON Lines, one resolved setting per line, sorted:

```json
{"app": "system", "config": "props.conf", "key": "ANNOTATE_PUNCT", "path": "/opt/splunk/etc/system/default/props.conf", "scope": "default", "stanza": "(?i)source::....zip(.\\d+)?", "value": "True"}
```

Sorted because the settings are held in a set, which has no order of its own —
without it, two snapshots of an unchanged instance would differ on every line.
JSON rather than a delimited format because stanzas and values both contain spaces
and `=`.

A setting's **identity** is `(config, stanza, key)`.  The `path`, `app` and `scope` are excluded because they are where it came from. Keeping
those separate is what lets the diff tell `modified` apart from `moved`.

## How it works

1. `find $SPLUNK_HOME/etc -name '*.conf'` lists what confs exist at all.
2. `splunk btool <conf> list --debug` prints every effective setting prefixed with
   the file it resolved from.
3. That output is parsed into `Setting` records. A line without a `/path/to/file.conf` prefix
   is a continuation of the previous value, not a new setting -> btool prints
   multi-line conf values verbatim.
4. Diffing is keyed on identity rather than whole-object set difference, which would
   report a value change as one removal plus one addition and make it
   indistinguishable from a real delete plus a real add.

`diff` walks the union of `.snapshot` files across both directories rather than the
fixed conf list, so a conf that appears only after a migration is reported as added
settings instead of being skipped.

## Limitations

- **Runs locally only.** `SPLUNK_HOME` is fixed at `/opt/splunk` and there is no
  remote transport.
- **The snapshots directory is relative to the working directory** (`./snapshots`).
  Run it from somewhere else and you silently start a fresh, empty snapshot set.
  Run it from the tool directory.
- **`diff` always compares the two most recent snapshots.** There is no way to name
  an arbitrary pair.
- **Six confs, single instance.** No `authorize`, `authentication`, `web`, or app
  confs; no cluster and no distributed search.
- **btool reports effective config**, which is a feature here but means a setting in
  a disabled app won't appear, and a syntax error btool skips is invisible.
- **`clear` is unguarded** and deletes every snapshot without asking — and cannot
  delete root-owned snapshots taken via `docker exec -u 0` without `sudo`.