---
status: complete
created: 2026-08-14
updated: 2026-08-31
---
# Summary
This document details all the checks that will be conducted in the post-migration. 
The check results are not recorded here. This document is used as a reference to guide the creation of the post-migration snapshot.
# Docker Container Checks
Check container health, ansible playbook completed with no errors

```bash
docker ps -a
docker compose logs -f
```

Check `splunk.secret` in the container has the same sha512 checksum as the original 
```bash
docker exec -u 0 -it splunk sha512sum /opt/splunk/etc/auth/splunk.secret
```

Check ownership and mode of `/opt/splunk/etc` and `/opt/splunk/var`, ensure it is owned by `41812`

```bash
docker exec -u 0 -it splunk ls -ldn /opt/splunk/etc
docker exec -u 0 -it splunk ls -ldn /opt/splunk/var
```

Check ports published 

```bash
docker port splunk
```

Check the resource limit was applied

```bash
docker exec splunk cat /sys/fs/cgroup/memory.max
docker exec splunk cat /sys/fs/cgroup/cpu.max      # "quota period", e.g. "200000 100000" = 2 CPUs
docker exec splunk cat /sys/fs/cgroup/memory.current
```

Check that the web instance is reachable over `https` and not on `http`

```bash
curl -k -I https://127.0.0.1:8000 
curl -k -I http://127.0.0.1:8000 # Should be empty reply
```

Check that Splunk state survives and the instance cleanly reboots after a manual shutdown

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk stop
docker compose down

# After complete exit
docker compose up -d 
# Check compose logs as well as Splunk warnings if any
```

> [!note]
> Replace splunk with whatever the container name is
# Splunk Version & License
Check the Splunk version 

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

# KVStore Restore
First login into splunk

```bash
docker exec -u splunk -it splunk /opt/splunk/bin/splunk login
```

Then check that the kvstore is healthy in this splunk instance

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk show kvstore-status 
```

Check what kvstore backups landed in the docker container. The kvstore backup that was made in pre-migration should exist there.

```bash
docker exec -u splunk splunk ls -lh /opt/splunk/var/lib/splunk/kvstorebackup/
```

If there is no kvstorebackup present in the above folder, we need to copy the kvstore backup that was made in pre-migration into this folder.

```bash
docker cp path/to/kvstorebackup/file.tar.gz splunk:/opt/splunk/var/lib/splunk/kvstorebackup/
docker exec -u root splunk chown -R 41812:41812 /opt/splunk/var/lib/splunk/kvstorebackup
```

Freeze writes by going into maintenance mode

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk enable kvstore-maintenance-mode 
docker exec -u splunk splunk /opt/splunk/bin/splunk show kvstore-status 
```

Restore the kvstore 

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk restore kvstore -pointInTime true -archiveName <archivename> 
```

Unfreeze by exiting maintenance mode

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk disable kvstore-maintenance-mode 
```

Verify the kvstore is healthy 

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk show kvstore-status 
```

# Artifact Integrity Template
After the migration check the hash of artifacts.

| Artifact        | Result |
| --------------- | ------ |
| `splunk.secret` |        |
# Scenario Checks
Run every check in the globalcart scenario manifest to ensure that the Splunk instance meets all the needs as detailed in [Scenario Needs](../environment/globalcart-manifest.md#Scenario%20Needs).

| Scenario   | Manifest                                                            |
| ---------- | ------------------------------------------------------------------- |
| GlobalCart | [Verification Checks](../environment/globalcart-manifest.md#Verification%20Checks) |
# Logs check
After the instance is up we perform the following checks

```sql
-- Check if any of the components in the last 1h window has an unusual number of logs with level not info. May indicate a current failure in the splunk deployment invisible to the existing checks. 
index=_internal earliest=-1h source=*splunkd.log log_level IN (WARN,ERROR,FATAL)
| stats count as log_count by log_level, component
| eval log_level_num=case(
log_level="FATAL",2,
log_level="ERROR", 1,
log_level="WARN", 0
)
| sort - log_level_num, - log_count
| fields - log_level_num
```

# Accepted Deviations Template
Check for accepted deviations from the pre-migration state

| Deviation | Reason |
| --------- | ------ |
|           |        |
