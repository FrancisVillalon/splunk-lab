---
status: complete
created: 2026-08-14
updated: 2026-08-31
---
# Summary
This documents the verification and preparation steps before the migration starts and guides you to create a snapshot of the current state.
The check results are not recorded here. This document is used as a reference to guide the creation of the pre-migration snapshot.
# Splunk Version & License
Check the Splunk version and ensure that the license is valid

```sql
| rest /services/server/info
| eval errors=validate(
version=="10.4.2","Expected Version 10.4.2, found ".version,
activeLicenseGroup=="Enterprise", "Expected Enterprise, found ".activeLicenseGroup,
upper(licenseState)=="OK", "License has outstanding warnings or quota issues"
)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result activeLicenseGroup activeLicenseSubgroup version build licenseSignature licenseState
```

Check the License

```sql
| rest /services/licenser/licenses
| eval quota_GB=round(quota/1024/1024/1024,2),expiration_readable=strftime(expiration_time,"%Y-%m-%d %H:%M:%S")
| eval errors=validate(
      upper(status)=="VALID",  "License status is ".status,
      expiration_time>now(),   "License expired on ".expiration_readable)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors license_hash label quota_GB expiration_readable max_violations window_period
```

# Roles
Check the base roles and the capabilities they hold. Scenario-specific role scoping is asserted in the scenario manifests.

```sql
| rest /services/authorization/roles
| eval capabilities_count=mvcount(capabilities)
| table title srchIndexesAllowed capabilities_count
```

# Users
Check the users that exist on the splunk instance. Scenario-specific user setup is asserted in the scenario manifests.

```sql
| rest /services/authentication/users
| table title roles defaultApp tz
```


# Scenario Checks
Run every check in the globalcart scenario manifest to ensure that the Splunk instance meets all the needs as detailed in [Scenario Needs](../environment/globalcart-manifest.md#Scenario%20Needs).

| Scenario   | Manifest                                                            |
| ---------- | ------------------------------------------------------------------- |
| GlobalCart | [Verification Checks](../environment/globalcart-manifest.md#Verification%20Checks) |

# Logs check
Check the logs if any of the existing components has had any error logs in the past 8 hours. This is to check for any failures in the current Splunk deployment before freezing the state.

```sql
index=_internal earliest=-8h source=*splunkd.log log_level IN (WARN,ERROR,FATAL)
| stats count as log_count by log_level, component
| eval log_level_num=case(
log_level="FATAL",2,
log_level="ERROR", 1,
log_level="WARN", 0
)
| sort - log_level_num, - log_count
| fields - log_level_num
```

# Freeze the Instance & Backup
Backups will be first created in a staging folder then moved to a mounted folder to hold the backups. Below is the **general shape** of the process that will be carried out. The actual implementation will be done through a bash script which will differ due to automation.

| #   | Stage                                                                             | Note                                                                                                                             |
| --- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Login as the `splunk` service account                                             |                                                                                                                                  |
| 2   | Check `kvstore-status`, both `status` and `backupRestoreStatus` are ready         | Gate. Do not back up a kvstore that is mid-operation                                                                             |
| 3   | Enable kvstore maintenance mode                                                   | Freezes writes so the backup is a clean point in time                                                                            |
| 4   | Create the point-in-time kvstore backup                                           | `splunk backup kvstore` needs a running instance, which is why it precedes the stop                                              |
| 5   | Switch to root for the remaining stages                                           |                                                                                                                                  |
| 6   | Check `/opt/splunk/etc` and `/opt/splunk/var` resolve to owner `splunk`           | Ownership has to be correct before it is captured into the tarballs                                                              |
| 7   | Verify the kvstore archive is intact                                              | List contents and `gzip -t`                                                                                                      |
| 8   | Copy the kvstore backup to `/tmp`                                                 |                                                                                                                                  |
| 9   | Stop `Splunkd`, confirm no `splunk`, `mongod`, `postgresd`  etc. processes remain | On-disk state is only consistent from here on                                                                                    |
| 10  | Archive `etc` and `var` to `/tmp`, preserving ownership and permissions           | Excludes `var/run` and `var/lib/splunk/kvstore`. The kvstore travels as the stage 4 backup, not as the raw mongo directory       |
| 11  | Confirm the exclusions took effect and both tarballs pass `gzip -t`               |                                                                                                                                  |
| 12  | Copy `splunk.secret` to `/tmp`                                                    | Also present inside the `etc` tarball. This standalone copy is the spare and the checksum reference for the post-migration check |
| 13  | Copy the license file to `/tmp`                                                   | Confirm the actual filename first                                                                                                |
| 14  | `sha512sum` every artifact into `splunk-migration.sha512`                         | This is what proves the copy intact on the other side                                                                            |
| 15  | Copy all artifacts into the mounted folder                                        | Only works if the mount has `allow_other` set in `/etc/fstab`                                                                    |
| 16  | Shut down the VM and take a snapshot                                              | This snapshot is the rollback point for the whole migration                                                                      |
| 17  | On the host, run `sha512sum -c splunk-migration.sha512`                           | Verifies the artifacts crossed the mount intact                                                                                  |

Include a section in the pre-migration snapshot `# Script Output` that shows the full output of the script.