---
status: in-progress
created: 2026-08-26
updated: 2026-08-31
---
# Summary
This document decides whether the source Ubuntu VM system can be retired, the criteria that govern that decision and the actions taken for the retirement itself.

# Leftover Items
This is the list of directories or paths that we check to ensure that nothing of importance is left on the source system before we retire it completely.

| Where checked                                                                             | Result       | Reason                                                                                                                                                |
| ----------------------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| The home directory of the initial user created with the Ubuntu source VM: `/home/francis` | Nothing left | This account was primarily used for the initial setup to setup mount, create splunk service account etc.                                              |
| Home directory of the splunk service account: `/opt/splunk`                               | Nothing left | All folders or files related to moving state as needed in the migration have been backed up and moved.                                                |
| Mounted folders : `/mnt/hgfs/*` `/mnt/*`                                                  | Nothing left | The mounted folder holding the scripts, backups and other data do not live on the source Ubuntu VM and will not be lost when the VM is powered down. |
| Cronjobs on source: `/var/spool/cron/crontabs` `/etc/cron.d` `/etc/cron.*`                | Nothing left | No crontabs were defined by any user on the source machine. `systemctl list-timers --all` comes back clean. Nothing left on source system.             |
| Staging area leftovers: `/tmp/splunk-snapshot-$DATE`                                      | Nothing left | Staging folders should be deleted after every run of the bash script. `/tmp` comes back clean.                                                        |

# Decision
To determine if the migration is successful and complete we can refer to the following table,

| Condition                                       | Check       | Date       |
| ----------------------------------------------- | ----------- | ---------- |
| Post-migration checks all pass                  | PASS        | 31/08/2026 |
| Accepted deviations reviewed and acceptable     | PASS        | 31/08/2026 |
| Backup artifacts intact on the host             | PASS        | 31/08/2026 |
| Leftover items check clean                      | PASS        | 31/08/2026 |
| Target has run the soak period without incident | IN PROGRESS |            |
The source system will be **retired on 4 September 2026**, the target will have a week of real use to surface anything the post-migration checks did not.

# Retirement Actions
Ordered. Steps 5 onward are irreversible, so nothing there starts until the verification below passes.

| #   | Action                                                                                                      | Done | Date |
| --- | ----------------------------------------------------------------------------------------------------------- | ---- | ---- |
| 1   | Run `sha512sum -c splunk-migration.sha512` against the host copy of the backup artifacts                    |      |      |
| 2   | Confirm the container has been up and healthy across the soak window                                        |      |      |
| 3   | Power off the VM, leave it in inventory                                                                     |      |      |
| 4   | Run every check in [Verification](#Verification)                                                            |      |      |
| 5   | Delete the VM and its virtual disks                                                                         |      |      |
| 6   | Remove the VMware shared folder definition backing `/mnt/hgfs`                                              |      |      |
| 7   | Clear any host-side references to `172.16.58.10` in `/etc/hosts`, `known_hosts` and any static routes       |      |      |
| 8   | Mark [baseline-ubuntu-vm](../environment/baseline-ubuntu-vm.md) as retired with the date, and set stage 6 in [migration-overview](migration-overview.md) to complete |      |      |

# Rollback window

| Field                | Value                                                                                                                                                                         |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Span                 | Migration date → 4 September 2026                                                                                                                                             |
| Retained during it   | VM snapshot, `splunk-etc` and `splunk-var` tarballs, kvstore backup, `splunk.secret`, license file                                                                            |
| Triggers a rollback  | A failed check found after sign-off, data loss in the target, or a target failure that cannot be recovered in place                                                           |
| Procedure            | Stop the container, power on the VM from its snapshot, re-run [pre-migration-check](pre-migration-check.md) against it.                                                                             |
| After the window     | The VM is deleted and rollback is no longer possible. Recovery becomes a rebuild from the tarballs onto a fresh instance, which is a slower and separately untested operation |
| Artifacts after that | The backup artifacts are kept even once the VM is gone. They are small and they are the only remaining recovery path                                                          |

# Verification
Run after the VM is powered off and before it is deleted.

| Check                                                                    | Result | Notes |
| ------------------------------------------------------------------------ | ------ | ----- |
| VM is powered off                                                        |        |       |
| Target container still healthy with the source gone                      |        |       |
| Scenario checks still pass against the target                            |        |       |
| Backup artifacts still present on the host and still pass `sha512sum -c` |        |       |
| Clear any host side references to the retired system                     |        |       |
| Documentation updated to reflect migration                               |        |       |
