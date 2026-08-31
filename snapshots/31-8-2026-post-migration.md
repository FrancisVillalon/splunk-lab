---
status: complete
captured: 2026-08-31
---
# Docker 

| Check                              | Result | Notes |
| ---------------------------------- | ------ | ----- |
| Container Health                   | PASS   |       |
| Playbook Status                    | PASS   |       |
| Docker volumes for `etc` and `var` | PASS   |       |
| Ownership for `etc` and `var`      | PASS   |       |
| Docker Ports                       | PASS   |       |
| Connectivity                       | PASS   |       |
| Splunk state after reboot          | PASS   |       |
# KVStore

| Check                       | Result | Notes                                                          |
| --------------------------- | ------ | -------------------------------------------------------------- |
| KVStore Health on Startup   | PASS   | KVstore runs with no errors on first start of docker container |
| KVStore Health post restore | PASS   | After KVStore restoration, KVStore runs with no errors         |
| KVStore Lookups             | PASS   | KVStore restoration was a success, all lookups are available   |

# Instance

| Check          | Result                                     | Notes                                                                |
| -------------- | ------------------------------------------ | -------------------------------------------------------------------- |
| Splunk version | PASS                                       |                                                                      |
| Splunk license | PASS                                       |                                                                      |
| Roles          | ![](images/image-1225.webp) | This search does not emit its own result so a screenshot is provided |
| Users          |![](images/image-1226.webp) | This search does not emit its own result so a screenshot is provided |

# Artifact Check

| Artifact Name   | Result | Notes                                                                                  |
| --------------- | ------ | -------------------------------------------------------------------------------------- |
| `splunk.secret` | PASS   | Hash of `splunk.secret` in the docker container matches that of pre-migration artifact |

# Scenario Checks
## Globalcart

| Category                   | Check                                                                                     | Result |
| -------------------------- | ----------------------------------------------------------------------------------------- | ------ |
| Knowledge Object Inventory | Apps                                                                                      | PASS   |
| Knowledge Object Inventory | Saved Searches                                                                            | PASS   |
| Knowledge Object Inventory | Dashboards                                                                                | PASS   |
| Knowledge Object Inventory | Indexes                                                                                   | PASS   |
| Knowledge Object Inventory | Sourcetypes                                                                               | PASS   |
| Knowledge Object Inventory | Lookup table files                                                                        | PASS   |
| Knowledge Object Inventory | Collections                                                                               | PASS   |
| Knowledge Object Inventory | Lookup definitions                                                                        | PASS   |
| Access Control             | Role `globalcart_analyst`                                                                 | PASS   |
| Access Control             | User `john`                                                                               | PASS   |
| Known Searches             | `_indextime`                                                                              | PASS   |
| Known Searches             | `_time`                                                                                   | PASS   |
| Known Searches             | Events indexed                                                                            | PASS   |
| Known Searches             | Unique Customers in Beauty                                                                | PASS   |
| Known Searches             | Total revenue                                                                             | PASS   |
| Known Searches             | Best category + priority tier                                                             | PASS   |
| Known Searches             | category_to_priority rows                                                                 | PASS   |
| Known Searches             | country_to_region rows                                                                    | PASS   |
| Known Searches             | product_to_cost rows                                                                      | PASS   |
| Known Searches             | category_to_priority md5 checksum                                                         | PASS   |
| Known Searches             | country_to_region md5 checksum                                                            | PASS   |
| Known Searches             | product_to_cost md5 checksum                                                              | PASS   |
| Functional Checks          | Log in as `john`                                                                          | PASS   |
| Functional Checks          | `john` can search `globalcart` but not sensitive indexes like `_audit`                    | PASS   |
| Functional Checks          | `Too much revenue lost` alert is still scheduled, fires and writes to `globalcart:alerts` | PASS   |
| Functional Checks          | lookup editor app is usable by `john`                                                     | PASS   |

# Logs Check

![](images/image-1235.webp)

__Logs__

No FATAL logs on startup of container 

# Accepted Deviations

| Deviation                                                                                                            | Reason                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| File system adopted by docker container for persistent data storage is `btrfs` instead of the source system's `ext4` | The file system adopted by the persistent data storage of the docker container is the same as the host which in this case is `btrfs`. The source Ubuntu VM adopts `ext4` as the file system. This is a non-issue as Splunk officially supports `btrfs` as detailed [here](https://help.splunk.com/en/splunk-enterprise/get-started/install-and-upgrade/10.4/plan-your-splunk-enterprise-installation/system-requirements-for-use-of-splunk-enterprise-on-premises). |

# Verdict

All post-migration checks pass. Migration was successful.
# Appendix

## Docker

![](images/image-1221.webp)

__Docker health__

![](images/image-1222.webp)

__Playbook Status__

![](images/image-1223.webp)

__Docker Volumes__


![](images/image-1219.webp)

__Folder ownership for `etc` and `var`__

![](images/image-1220.webp)

__Docker published ports__

![](images/image-1224.webp)

__Connectivity Checks__

## KVStore

![](images/image-1227.webp)

__Restored lookups__

![](images/image-1228.webp)

__Maintenance mode disabled and KVStore comes back healthy__

## Artifact

![](images/image-1175.webp)

__`splunk.secret` checksum__

## Functional Checks 

![](images/image-1229.webp)

__Login as John__

![](images/image-1230.webp)

__Searching globalcart index as John__

![](images/image-1231.webp)

__John cannot search `_audit`__

![](images/image-1232.webp)

__Alert fires and writes with sourcetype `globalcart:alerts`__

![](images/image-1233.webp)

__Alert is still scheduled__

![](images/image-1234.webp)

__Lookup App Usable by John__