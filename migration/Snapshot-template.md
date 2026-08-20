---
status: template
captured: 2026-08-18
type:
---
# Summary

| Field          | Value |
| -------------- | ----- |
| Splunk version |       |
| Build          |       |
| License        |       |
# Knowledge Objects Inventory

Screenshot of each search result from [pre-migration-check](pre-migration-check.md) in order

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
# Known Searches

| Scenario   | Check                                              | Expected                                                  | Actual |
| ---------- | -------------------------------------------------- | --------------------------------------------------------- | ------ |
| GlobalCart | `_indextime`                                       | `min=1786605521` `max=1786605521`<br>`sum=10719633126000` |        |
| GlobalCart | `_time`                                            | `min=1777565523` `max=1785081493`<br>`sum=10688027062398` |        |
| GlobalCart | Events indexed with source type `globalcart:sales` | 6000                                                      |        |
| GlobalCart | Total revenue                                      | $2,037,941.60                                             |        |
| GlobalCart | Best category + priority tier                      | Books / Tier3, 1051 orders                                |        |
| GlobalCart | Unique customers in Beauty                         | 958                                                       |        |
| GlobalCart | category_to_priority rows                          | 6                                                         |        |
| GlobalCart | country_to_region rows                             | 12                                                        |        |
| GlobalCart | product_to_cost rows                               | 30                                                        |        |


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

# Script Output





# VM Snapshot

| Field    | Value |
| -------- | ----- |
| Name     |       |
| Taken    |       |
| VM state |       |
