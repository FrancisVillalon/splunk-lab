---
status: in-progress
created: 2026-08-14
updated: 2026-08-17
---
#splunk #migration

# Summary
This documents the verification and preparation steps before the migration starts and guides you to create a snapshot of the current state.

# Splunk Version
Check the Splunk version 

```
| rest /services/server/info
| table activeLicenseGroup activeLicenseSubgroup version build licenseSignature
```

# Splunk License
Check the Splunk license

```
| rest /services/licenser/licenses
| eval quota_GB=round(quota/1024/1024/1024,2)
| eval expiration_readable=strftime(expiration_time, "%Y-%m-%d %H:%M:%S")
| table license_hash label quota_GB expiration_readable status max_violations window_period
```

# Known Searches
These proves the data survived the move. The following list should be verified using SPL.

| Scenario   | Check                                                 | Expected                   |
| ---------- | ----------------------------------------------------- | -------------------------- |
| GlobalCart | Events indexed and with sourcetype `globalcart:sales` | 6000                       |
| GlobalCart | Total revenue                                         | $2,037,941.60              |
| GlobalCart | Best category + priority tier                         | Books / Tier3, 1051 orders |
| GlobalCart | Unique customers in Beauty                            | 958                        |
| GlobalCart | category_to_priority rows                             | 6                          |
| GlobalCart | country_to_region rows                                | 12                         |
| GlobalCart | product_to_cost rows                                  | 30                         |

# Knowledge Objects Inventory 
Inventory the knowledge objects created. These mainly look at the knowledge objects created for the globalcart scenario.

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

# Freeze the Instance & Backup
Backups will be first created in `/tmp` and then moved to  `/mnt/hgfs/splunk-step-repo/splunk-backup` to hold the backups

```bash
# Login
sudo -u splunk -H /opt/splunk/bin/splunk login

# Check if both backupRestoreStatus and status is ready
sudo -u splunk -H /opt/splunk/bin/splunk show kvstore-status

# Create backup of kvstore 
sudo -u splunk -H /opt/splunk/bin/splunk backup kvstore -pointInTime true -archiveName kvstore-backup-<date>

# Change to root user, run rest of the commands as root
sudo su -

# Check ownership of /etc and /var, the owner must resolve to splunk
stat -c '%U %G %u %g %a %n' /opt/splunk/etc
stat -c '%U %G %u %g %a %n' /opt/splunk/var

# Check kvstore backup
ls -lh /opt/splunk/var/lib/splunk/kvstorebackup/
tar -tzf /opt/splunk/var/lib/splunk/kvstorebackup/kvstore-backup-<date>.tar.gz | head -50
gzip -t  /opt/splunk/var/lib/splunk/kvstorebackup/kvstore-backup-<date>.tar.gz

# Move kvstore backup to /tmp
cp /opt/splunk/var/lib/splunk/kvstorebackup/kvstore-backup-<date>.tar.gz /tmp/
 
# Stop Splunk so on-disk state is consistent
systemctl stop Splunkd
systemctl is-active Splunkd
ps -eo user,comm | grep -Ei 'splunk|mongod'

# Archive the state that has to travel, preserving ownership and permissions
tar -czpf /tmp/splunk-etc-<date>.tar.gz -C /opt/splunk etc
tar -czpf /tmp/splunk-var-<date>.tar.gz \
--exclude='var/run/*' \
--exclude='var/lib/splunk/kvstore/*' \
-C /opt/splunk var 

# Check exclusions took effect
tar -tzf /tmp/splunk-var-<date>.tar.gz | grep -E '^var/(run|lib/splunk/kvstore)/.' | head
tar -tzf /tmp/splunk-var-<date>.tar.gz | grep kvstorebackup | head
gzip -t /tmp/splunk-etc-<date>.tar.gz /tmp/splunk-var-<date>.tar.gz && echo "tarballs exists"

# Copy splunk.secret to /tmp
cp /opt/splunk/etc/auth/splunk.secret /tmp/
# Check license file name
ls /opt/splunk/etc/licenses/enterprise
# Copy license file to /tmp
cp /opt/splunk/etc/licenses/enterprise/Splunk.License.lic /tmp/

# Checksum all so the copy can be proven intact on the other side
cd /tmp
sha512sum \
splunk-etc-<date>.tar.gz \
splunk-var-<date>.tar.gz \
kvstore-backup-<date>.tar.gz \
splunk.secret \
Splunk.License.lic \
| tee splunk-migration.sha512


# Move everything into the mounted folder, this only works if the mounted folder has allow_other in etc/fstab
cp /tmp/splunk-etc-<date>.tar.gz \
/tmp/splunk-var-<date>.tar.gz \
/tmp/kvstore-backup-<date>.tar.gz \
/tmp/splunk.secret \
/tmp/Splunk.License.lic \
/tmp/splunk-migration.sha512 \
/mnt/hgfs/splunk-step-repo/splunk-backup/
```

Then shutdown the VM and perform a **snapshot** .

Also check on the hostside the backups were correctly moved into the mounted folder
```bash
cd path/to/folder
sha512sum -c splunk-migration.sha512
```

# Artifacts

| Artifact                       | Size | Path |
| ------------------------------ | ---- | ---- |
| `splunk-etc-<date>.tar.gz`     |      |      |
| `splunk-var-<date>.tar.gz`     |      |      |
| `kvstore-backup-<date>.tar.gz` |      |      |
| `splunk.secret`                |      |      |
| License file (actual name:  )  |      |      |

