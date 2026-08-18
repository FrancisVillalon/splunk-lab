---
status: template
captured: 2026-08-18
---
# Summary

| Field          | Value |
| -------------- | ----- |
| Splunk version |       |
| Build          |       |
| License        |       |

# Known Searches

| Scenario   | Check                                                                   | Expected                   | Actual | SPL |
| ---------- | ----------------------------------------------------------------------- | -------------------------- | ------ | --- |
| GlobalCart | Events indexed and with sourcetype `globalcart:sales` in all time range | 6000                       |        |     |
| GlobalCart | Total revenue                                                           | $2,037,941.60              |        |     |
| GlobalCart | Best category + priority tier                                           | Books / Tier3, 1051 orders |        |     |
| GlobalCart | Unique customers in Beauty                                              | 958                        |        |     |
| GlobalCart | category_to_priority rows                                               | 6                          |        |     |
| GlobalCart | country_to_region rows                                                  | 12                         |        |     |
| GlobalCart | product_to_cost rows                                                    | 30                         |        |     |

# Knowledge Objects Inventory

Screenshot of each search result from [[pre-migration-check]] in order

| Object                          | Screenshot |
| ------------------------------- | ---------- |
| Apps                            |            |
| Saved Searches (Reports/Alerts) |            |
| Dashboards                      |            |
| Indexes                         |            |
| Sourcetypes                     |            |
| Roles                           |            |
| Users                           |            |
| Lookups — table files           |            |
| Lookups — collections           |            |
| Lookups — definitions           |            |

# Script Output





# VM Snapshot

| Field    | Value |
| -------- | ----- |
| Name     |       |
| Taken    |       |
| VM state |       |
