---
status: in-progress
created: 2026-08-14
updated: 2026-08-17
---
# Summary
This document details all the checks conduct post-migration to determine if the migration was a success and if it is good enough to retire the source system.

# Docker Container Checks
Check container health, ansible playbook completed with no errors

```
docker ps -a
docker compose logs -f
```

Check `splunk.secret` in the container has the same sha512 check sum as the original 
```
docker exec -u 0 -it splunk sha512sum /opt/splunk/etc/auth/splunk.secret
```

Check ownership and mode of `/opt/splunk/etc` and `/opt/splunk/var`, ensure it is owned by `41812`

```
docker exec -u 0 -it splunk ls -ldn /opt/splunk/etc
docker exec -u 0 -it splunk ls -ldn /opt/splunk/var
```

Check ports published 

```
docker port splunk
```

Check the resource limit was applied

```
docker exec splunk cat /sys/fs/cgroup/memory.max
docker exec splunk cat /sys/fs/cgroup/cpu.max      # "quota period", e.g. "200000 100000" = 2 CPUs
docker exec splunk cat /sys/fs/cgroup/memory.current
```

Check that the web instance is reachable over `https` and not on `http`

```
curl -k -I https://127.0.0.1:8000 
curl -k -I http://127.0.0.1:8000 # Should be empty reply
```

> [!note]
> Replace splunk with what ever the container name is
# Splunk Version
Check the Splunk version matches with the pre-migration

```
| rest /services/server/info
| table activeLicenseGroup activeLicenseSubgroup version build licenseSignature
```

# Splunk License
Check the Splunk license matches with the pre-migration

```
| rest /services/licenser/licenses
| eval quota_GB=round(quota/1024/1024/1024,2)
| eval expiration_readable=strftime(expiration_time, "%Y-%m-%d %H:%M:%S")
| table license_hash label quota_GB expiration_readable status max_violations window_period
```
# KVStore Restore
First login into splunk

```bash
docker exec -u splunk -it splunk /opt/splunk/bin/splunk login
```

First check that the kvstore is healthy in this splunk instance

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk show kvstore-status 
```

Check what kvstore backups landed in the docker container. The kvstore backup that was made in pre-migration should exist there.

```bash
docker exec -u splunk splunk ls -lh /opt/splunk/var/lib/splunk/kvstorebackup/
```

If there is no kvstorebackup present in the above folder, we need to copy the kvstorebackup that was made in pre-migration into this folder.

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

# Knowledge Objects Inventory 
Inventory the knowledge objects created and check them against the pre-migration

## Apps 
Check for `globalcart` and `lookup_editor` as these are the ones we added in the `globalcart-manifest` and `baseline-splunk-config`

```
| rest /services/apps/local 
| table title, version, disabled
| search title=globalcart OR title=lookup_editor
```

## Saved Searches (Reports/Alerts)
Check the reports and alerts created in the globalcart-manifest are found 

```
| rest /servicesNS/-/-/saved/searches
| search "eai:acl.sharing"="user"
| table title "eai:acl.owner" "eai:acl.app" "eai:acl.sharing"
```

## Dashboards
Check the created dashboards in the globalcart-manifest are found 

```
| rest /servicesNS/-/-/data/ui/views
| search isDashboard=1 eai:acl.app=globalcart
| table title label "eai:acl.app" "eai:acl.owner" "eai:acl.sharing" isVisible
```
## Indexes
Check information about the `globalcart` index which is the only index we added 

```
| rest /services/data/indexes 
| search title=globalcart
| table title disabled currentDBSizeMB totalEventCount maxDataSize frozenTimePeriodInSecs homePath coldPath thawedPath eai:acl.app eai:acl.owner eai:acl.sharing
```
## Sourcetypes
Check `globalcart:sales` is shown in the sourcetypes. 

```
| rest /servicesNS/-/-/configs/conf-props 
| search title=globalcart:sales
| table title TZ author category description eai:acl.app eai:acl.owner eai:acl.perms.read eai:acl.perms.write
```

Do note that the alert action log event does not create a stanza when a sourcetype is defined in the action. Therefore `globalcart:alerts` is not visible in this query. 
## Roles
Check the base roles and created roles like `globalcart_analyst` exists and have the appropriate access to indexes and number of capabilities

```
| rest /services/authorization/roles 
| table title, srchIndexesAllowed, capabilities
| eval capabilities_count=mvcount(capabilities)
| fields - capabilities
```

## Users
Check the users that exist on the splunk instance

 ```
| rest /services/authentication/users 
| table title, roles, defaultApp, tz
 ```

## Lookups
First check lookup table files

```
| rest /servicesNS/-/-/data/lookup-table-files
| search eai:acl.app=globalcart
| table author eai:acl.app eai:acl.perms.read eai:acl.perms.write title id updated
```

Then check the collections 

```
| rest /servicesNS/-/-/storage/collections/config
| search title=region OR title=cost_supplier
| table title author disabled eai:acl.app eai:acl.perms.read eai:acl.perms.write
```

 Finally check lookup definitions which will show both kv store lookups and file based lookups

```
| rest /servicesNS/-/-/data/transforms/lookups
| search eai:acl.app=globalcart
| table author eai:acl.app eai:acl.perms.read eai:acl.perms.write title id updated
```

# Known Searches
These proves the data survived the move. The following list should be verified using SPL with the time range set to `all time`.

| Scenario   | Check                                              | Expected                                                  |
| ---------- | -------------------------------------------------- | --------------------------------------------------------- |
| GlobalCart | `_indextime`                                       | `min=1786605521` `max=1786605521`<br>`sum=10719633126000` |
| GlobalCart | `_time`                                            | `min=1777565523` `max=1785081493`<br>`sum=10688027062398` |
| GlobalCart | Events indexed with source type `globalcart:sales` | 6000                                                      |
| GlobalCart | Total revenue                                      | $2,037,941.60                                             |
| GlobalCart | Best category + priority tier                      | Books / Tier3, 1051 orders                                |
| GlobalCart | Unique customers in Beauty                         | 958                                                       |
| GlobalCart | category_to_priority rows                          | 6                                                         |
| GlobalCart | country_to_region rows                             | 12                                                        |
| GlobalCart | product_to_cost rows                               | 30                                                        |

```sql
1 -- Check _indextime
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| stats count, min(_indextime) as i_min, max(_indextime) as i_max, sum(_indextime) as i_sum
| foreach *_min *_max [ eval <<FIELD>>_formatted=strftime(<<FIELD>>,"%F %T %Z")]

2 -- Check _time
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| stats count, min(_time) as t_min, max(_time) as t_max, sum(_time) as t_sum
| foreach *_min *_max [ eval <<FIELD>>_formatted=strftime(<<FIELD>>,"%F %T %Z")]

3 -- Events indexed
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| stats count

4 -- Unique customers in beauty
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now category="Beauty"
| stats dc(customer_id) as UniqueCustomers

5 -- Total Revenue 
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now 
| stats sum(revenue) as TotalRevenue
| fieldformat TotalRevenue="$".tostring(TotalRevenue,"commas")

6 -- Best category + priority tier
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now 
| lookup category_to_priority category OUTPUT priority 
| stats count as orders by category, priority
| sort -orders limit=1

7 -- category_to_priority lookup rows
| inputlookup category_to_priority | stats count

8 -- country_to_region lookup rows
| inputlookup country_to_region | stats count

9 -- product_to_cost lookup rows
| inputlookup product_to_cost | stats count

10 -- checksum rows in a lookup
| inputlookup <lookup_name> 
| eval k=_key
| tojson output_field=j
| eval j=md5(j)
| stats list(j) as hashes
| eval hash=md5(mvjoin(hashes,"~"))
```

# Functional Checks

| Check                                                                                                      | Status |
| ---------------------------------------------------------------------------------------------------------- | ------ |
| Log in as `john`                                                                                           |        |
| `john` can search `globalcart` but not sensitive indexes like  `_audit`                                    |        |
| `Too much revenue lost` alert is still scheduled, fires and writes to `globalcart:alerts`                  |        |
| `splunk stop` the container, `docker compose down` then `docker compose up` and see if the state survives. |        |

# Accepted Deviations
