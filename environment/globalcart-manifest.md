---
status: Complete
created: 2026-08-13
updated: 2026-08-13
---
# Summary
This document details every object the GlobalCart scenario is built from: the app, index and source type underneath it, the lookups and knowledge objects layered on top, and the roles and users that gate access to them. Each entry records what an object is for and how it is scoped, not how it is defined. It assumes the instance-wide setup in [baseline-splunk-config](baseline-splunk-config.md) is already applied, and closes with the figures a correct rebuild should reproduce.

# Scenario 
Junior data analyst at GlobalCart, an online retailer across 12 countries. Ad-hoc revenue, refund, and margin questions answered in Splunk rather than Excel.

Full writeup: [GlobalCart](../labs/GlobalCart/GlobalCart.md)
# Dataset

| File           | Index      | Sourcetype       | App        | TZ             | Events | Span                    | Indexed time (epoch time) |
| -------------- | ---------- | ---------------- | ---------- | -------------- | ------ | ----------------------- | ------------------------- |
| sales_data.csv | globalcart | globalcart:sales | globalcart | Asia/Singapore | 6000   | 2026-05-01 → 2026-07-26 | 1786605521                |
Do note that when checking number of events to also scope to `sourcetype=globalcart:sales` as alerts with log event action will be writing to this index as well.
# Required Objects

Everything below lives in the globalcart app, is readable by globalcart_analyst, and is
writable by admin. Deviations are noted per object; ownership and sharing mechanics are
left to the conf files.

## Foundation

| Object            | Type        | Detail                                                                                                  |
| ----------------- | ----------- | ------------------------------------------------------------------------------------------------------- |
| globalcart        | app         | Home folder globalcart; all conf below lives in its local/                                              |
| globalcart        | index       | Size/retention left at defaults, fine at this volume                                                    |
| globalcart:sales  | source type | Globalcart sales data ingested from sales_data.csv                                                      |
| globalcart:alerts | source type | Global cart alerts events that are generated from the log event alert action. Not ingested from a file. |

## Lookups

> [!note]
> These definition names supersede the ones in [GlobalCart](../labs/GlobalCart/GlobalCart.md), which was written against an
> earlier build and still uses KVPriority, priority_lookup, region_lookup and
> cost_supplier_lookup. Queries copied from the writeup need the names swapped.

### File-based

| Definition           | Table file           | Key → Output        | Purpose                                    |
| -------------------- | -------------------- | ------------------- | ------------------------------------------ |
| category_to_priority | lookups/priority.csv | category → priority | Maps each product category to a Tier 1 → 6 |

### KV store

| Definition        | Collection    | Key → Output                   | Purpose                                                                          |
| ----------------- | ------------- | ------------------------------ | -------------------------------------------------------------------------------- |
| country_to_region | region        | country → region               | Maps country to their respective regions as the data does not include regions.   |
| product_to_cost   | cost_supplier | product → cost_price, supplier | Maps product to both cost and supplier so as to enable profit margin calculation |

## Reports, Dashboards & Alerts

| Name                  | Type      | Purpose                                                                                                                                                                                        | Owned  by | Display For |
| --------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- | ----------- |
| Revenue by Device     | report    | Revenue split by device                                                                                                                                                                        | john      | Owner       |
| Revenue by Device     | dashboard | Single panel over the report above                                                                                                                                                             | john      | Owner       |
| Too much revenue lost | alert     | Fires when all time refund revenue > $500; triggered alert (high sev) + log event. Time range is set to all time to guarantee it fires. This was created for to test alerting in the scenario. | john      | Owner       |

# Role & Users

| Role               | Inherits | Allowed Indexes | Default App |
| ------------------ | -------- | --------------- | ----------- |
| globalcart_analyst | power    | globalcart      | globalcart  |

| Username | Full Name | Email                 | Role               | Default App | TZ                        |
| -------- | --------- | --------------------- | ------------------ | ----------- | ------------------------- |
| john     | John Doe  | john.d@globalcart.com | globalcart_analyst | globalcart  | Asia/Singapore GMT +08:00 |
# Verification

| Check                         | Expected                                                  | Notes                                                                                                                                                                   |
| ----------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_indextime`                  | `min=1786605521` `max=1786605521`<br>`sum=10719633126000` | The entire csv was added in bulk so the real check is that <br>`min == max` and the `sum` remains the same otherwise there are events that have a different index time. |
| `_time`                       | `min=1777565523` `max=1785081493`<br>`sum=10688027062398` | The values here should all match otherwise the parsed event time is erroneous.                                                                                          |
| Events indexed                | 6000                                                      | Scoped to globalcart:sales                                                                                                                                              |
| Unique Customers in Beauty    | 958                                                       |                                                                                                                                                                         |
| Total revenue                 | $2,037,941.60                                             | Equals dataset’s full revenue                                                                                                                                           |
| Best category + priority tier | Books / Tier3, 1051 orders                                | Checks if category_to_priority lookup and event data match                                                                                                              |
| category_to_priority checksum | 6                                                         | Covers all 6 categories in the dataset, check with `\| inputlookup definition`                                                                                          |
| country_to_region rows        | 12                                                        | Covers all 12 countries in the dataset, check with  `\| inputlookup definition`                                                                                         |
| product_to_cost rows          | 30                                                        | Covers all 30 products in the dataset, check with `\| inputlookup definition`                                                                                           |

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

10 -- checksum rows in lookup
| inputlookup <lookup_name> 
| eval k=_key
| tojson output_field=j
| eval j=md5(j)
| stats list(j) as hashes
| eval hash=md5(mvjoin(hashes,"~"))
```
