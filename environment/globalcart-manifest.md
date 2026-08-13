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

| File           | Index      | Sourcetype       | App        | TZ             | Events | Span                    |
| -------------- | ---------- | ---------------- | ---------- | -------------- | ------ | ----------------------- |
| sales_data.csv | globalcart | globalcart:sales | globalcart | Asia/Singapore | 6000   | 2026-05-01 → 2026-07-26 |

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

| Name                  | Type      | Purpose                                                                                                                                                                                        |
| --------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Revenue by Device     | report    | Revenue split by device                                                                                                                                                                        |
| Revenue by Device     | dashboard | Single panel over the report above                                                                                                                                                             |
| Too much revenue lost | alert     | Fires when all time refund revenue > $500; triggered alert (high sev) + log event. Time range is set to all time to guarantee it fires. This was created for to test alerting in the scenario. |

# Role & Users

| Role               | Inherits | Allowed Indexes | Default App |
| ------------------ | -------- | --------------- | ----------- |
| globalcart_analyst | power    | globalcart      | globalcart  |

| Username | Full Name  | Email                   | Role                 | Default App  | TZ                          |
| -------- | ---------- | ----------------------- | -------------------- | ------------ | --------------------------- |
| john   | John Doe | john.d@globalcart.com | globalcart_analyst | globalcart | Asia/Singapore GMT +08:00 |
# Verification

| Check                         | Expected                   | Notes                                                                           |
| ----------------------------- | -------------------------- | ------------------------------------------------------------------------------- |
| Events indexed                | 6000                       | Scoped to globalcart:sales                                                      |
| Unique Customers in Beauty    | 958                        |                                                                                 |
| Total revenue                 | $2,037,941.60              | Equals dataset’s full revenue                                                   |
| Best category + priority tier | Books / Tier3, 1051 orders | Checks if category_to_priority lookup and event data match                      |
| category_to_priority rows     | 6                          | Covers all 6 categories in the dataset, check with `\| inputlookup definition`  |
| country_to_region rows        | 12                         | Covers all 12 countries in the dataset, check with  `\| inputlookup definition` |
| product_to_cost rows          | 30                         | Covers all 30 products in the dataset, check with `\| inputlookup definition`   |