---
status: complete
created: 2026-08-13
updated: 2026-08-28
---
# Summary
This document details every object the GlobalCart scenario is built from: the app, index and source type underneath it, the lookups and knowledge objects, and the roles and users. Each entry records what an object is for and how it is scoped. It assumes the instance-wide setup in [baseline-splunk-config](baseline-splunk-config.md) is already applied. The document also covers the needs of the scenario as well as the appropriate checks to ensure the environment meets those needs.

# Scenario 
Junior data analyst at GlobalCart, an online retailer across 12 countries. Ad-hoc revenue, refund, and margin questions answered in Splunk rather than Excel.

Full writeup: [GlobalCart](../labs/GlobalCart/GlobalCart.md)
# Dataset

| File           | Index      | Sourcetype       | App        | TZ             | Events | Span                    | Indexed time (epoch time) |
| -------------- | ---------- | ---------------- | ---------- | -------------- | ------ | ----------------------- | ------------------------- |
| sales_data.csv | globalcart | globalcart:sales | globalcart | Asia/Singapore | 6000   | 2026-05-01 → 2026-07-26 | 1786605521                |
Do note that when checking number of events to also scope to `sourcetype=globalcart:sales` as alerts with log event action will be writing to this index as well.
# Required Objects

Everything below lives in the globalcart app, is readable and writable by globalcart_analyst and admin


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

# Scenario Needs
The globalcart scenario has a list of needs as documented below. These needs shape the checks that have to be carried out to ensure that the Splunk environment meets all the needs of the globalcart scenario.

| Need                                                                                                                | Why GlobalCart needs it                                                                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| KV store running and healthy                                                                                        | GlobalCart uses numerous lookups in the scenario. It is paramount that the integrity of this data is maintained.                                                                                                                                                                                       |
| Instance timezone is `Asia/Singapore`                                                                               | The migrated system should be calibrated to follow this timezone. Otherwise, an invalid timezone would cause the displayed time to not align with expectations.<br><br>Do note that in Splunk the timezone is set to `Asia/Hong_Kong` which is effectively the same as setting it to `Asia/Singapore`. |
| Search scheduler is running and scheduled alerts correctly fire                                                     | This scenario has a single scheduled alert related to the loss of revenue. It is important that scheduled alerts are properly firing.                                                                                                                                                                  |
| Role-scoped index access                                                                                            | The persona in this scenario is a junior analyst and should only have access to the globalcart index data. It is important that roles are correctly scoped  to ensure least privilege.                                                                                                                 |
| The lookup_editor app should be installed and usable                                                                | The scenario has a heavy use of lookups. The inclusion of the app is central to the management of said lookups without needing to manually edit configuration files.                                                                                                                                   |
| Existing user must still be able to authenticate with current credentials                                           | Existing users should be able to authenticate on the system with their current credentials.                                                                                                                                                                                                            |
| Access permissions and ownerships should be maintained                                                              | Existing users should be able to correctly access knowledge objects scoped to them.                                                                                                                                                                                                                    |
| The globalcart app must be present                                                                                  | The application specific to the globalcart scenario must exist as all related data or objects live on that app.                                                                                                                                                                                        |
| `globalcart:sales` sourcetype and its field extraction must persist                                                 | The events should correctly have sourcetype `globalcart:sales` and have its fields properly extracted. A failure here will silently break multiple searches that depend on the correct parsing of the event data.                                                                                      |
| The log event alert action should be able to write into  the `globalcart` index with sourcetype `globalcart:alerts` | Alerts with log event action should be searchable in the `globalcart` index by filtering for sourcetype `globalcart:alerts`. Otherwise there is no running log of what alerts fired.                                                                                                                   |
| `globalcart` index must exists and its full datatset retained.                                                      | It is paramount that all events in this scenario are migrated, parsed cleanly and arrive in the `globalcart` index.                                                                                                                                                                                    |

# Verification Checks
This section consists of all the checks to ensure that a Splunk environment meets all the needs of the global cart scenario.

## Knowledge Object Inventory Check
SPL queries to check the required knowledge objects.
### Apps 
Check for `globalcart` and `lookup_editor`

```sql
| rest /services/apps/local 
| search title=globalcart OR title=lookup_editor
| eval off=if(disabled==1 OR disabled=="true",1,0)
| stats count as apps , sum(off) as disabled_count, values(title) as title
| eval errors=validate(
	apps==2,
		"Expected 2 apps only, found ".apps,
	disabled_count==0,
		"An app is disabled"
)
| eval result=(if(isnull(errors),"PASS","FAIL"))
| table result errors apps disabled_count title
```


### Saved Searches (Reports/Alerts)
Check the reports and alerts needed by the global cart scenario

```sql
| rest /servicesNS/-/-/saved/searches
| search  "eai:acl.app"="globalcart"
| stats 
count as savedsearch_count, 
values(eai:acl.owner) as owner, 
values(title) as title, 
values(eai:acl.sharing) as display_for
| eval errors=validate(
savedsearch_count==2, 
	"Expected 2 but found ".savedsearch_count,
mvcount(owner)==1, 
	"Expected 1 owner, found: ".mvjoin(owner,", "),
mvindex(owner,0)=="john", 
	"Unexpected owner: ".mvjoin(owner,", "),
mvcount(display_for)==1, 
	"Expected 1 sharing scope, found: ".mvjoin(display_for,", "),
mvindex(display_for,0)=="user", 
	"Unexpected sharing: ".mvjoin(display_for,", ")
)
| eval result=(if(isnull(errors),"PASS","FAIL"))
| table result errors savedsearch_count title owner display_for
```

### Dashboards
Check the created dashboards need by the globalcart scenario. Check the ownership and permissions.

```sql
| rest /servicesNS/-/-/data/ui/views
| search isDashboard=1 eai:acl.app=globalcart
| stats 
count as dashboard_count, 
values(eai:acl.owner) as owner, 
values(eai:acl.sharing) as display_for 
| eval errors=validate(
dashboard_count==1,
	"Expected 1 dashboard, found ".dashboard_count,
mvcount(owner)==1,
	"Expected 1 owner, found: ".mvjoin(owner,", "),
mvindex(owner,0)=="john", 
	"Unexpected owner: ".mvjoin(owner,", "),
mvcount(display_for)==1, 
	"Expected 1 sharing scope, found: ".mvjoin(display_for,", "),
mvindex(display_for,0)=="user", 
	"Unexpected sharing: ".mvjoin(display_for,", ")
)
| eval result=(if(isnull(errors),"PASS","FAIL"))
| table result errors dashboard_count owner display_for
```
### Indexes
Check information about the `globalcart` index.

```sql
| rest /services/data/indexes
| search title=globalcart
| eval off=if(disabled==1 OR disabled=="true",1,0)
| stats 
count as index_count, sum(off) as disabled_count,
sum(totalEventCount) as events,
sum(currentDBSizeMB) as size_mb,
values("eai:acl.app") as app,
values("eai:acl.sharing") as display_for
| eval errors=validate(
	index_count==1,    
		"Expected 1 globalcart index, found ".index_count,
    disabled_count==0, 
	    "globalcart index is disabled",
    events>=6000,      
	    "Expected >= 6000 events in globalcart index, found ".events,
    size_mb>0,         
	    "currentDBSizeMB is 0, index has no data on disk",
    mvindex(app,0)=="globalcart",  
	    "Expected index scoped to globalcart app, found ".mvjoin(app,", "),
    mvindex(display_for,0)=="app", 
	    "Expected index sharing scope app, found ".mvjoin(display_for,", "))
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors index_count disabled_count events size_mb app display_for
```
### Sourcetypes
Check `globalcart:sales` is shown in the sourcetypes. 

```sql
| rest /servicesNS/-/-/configs/conf-props 
| search title=globalcart*
| stats count as st_count,
        values(TZ) as tz,
        values("eai:acl.app") as app,
        values("eai:acl.perms.read") as read_perms,
        values("eai:acl.perms.write") as write_perms
| eval errors=validate(
    st_count==1,
        "Expected 1 globalcart:sales stanza, found ".st_count,
    mvindex(app,0)=="globalcart",
        "Expected sourcetype in globalcart app, found: ".mvjoin(app,", "),
    mvindex(tz,0)=="Asia/Hong_Kong",
        "Unexpected TZ: ".mvjoin(tz,", "),
    mvcount(read_perms)==2,
        "Expected 2 read roles, found: ".mvjoin(read_perms,", "),
    isnotnull(mvfind(read_perms,"^admin$")),
        "admin missing from read perms",
    isnotnull(mvfind(read_perms,"^globalcart_analyst$")),
        "globalcart_analyst missing from read perms",
    mvcount(write_perms)==2,
        "Expected 2 write roles, found: ".mvjoin(write_perms,", "),
    isnotnull(mvfind(write_perms,"^admin$")),
        "admin missing from write perms",
    isnotnull(mvfind(write_perms,"^globalcart_analyst$")),
        "globalcart_analyst missing from write perms")
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors st_count app tz read_perms write_perms
```

Do note that the alert action log event does not create a stanza when a sourcetype is defined in the action. Therefore `globalcart:alerts` is not visible in this query. 
### Lookups
First check lookup table files

```sql
| rest /servicesNS/-/-/data/lookup-table-files
| search "eai:acl.app"=globalcart
| eval read_bad=if(mvcount('eai:acl.perms.read')==2
        AND isnotnull(mvfind('eai:acl.perms.read',"^admin$"))
        AND isnotnull(mvfind('eai:acl.perms.read',"^globalcart_analyst$")),0,1),
       write_bad=if(mvcount('eai:acl.perms.write')==2
        AND isnotnull(mvfind('eai:acl.perms.write',"^admin$"))
        AND isnotnull(mvfind('eai:acl.perms.write',"^globalcart_analyst$")),0,1)
| stats count as file_count, sum(read_bad) as bad_read, sum(write_bad) as bad_write,
        values(title) as titles
| eval errors=validate(
    file_count==1,
        "Expected 1 lookup table file(s), found ".file_count.": ".mvjoin(titles,", "),
    bad_read==0,
        bad_read." lookup table file(s) with unexpected read perms: expected admin + globalcart_analyst",
    bad_write==0,
        bad_write." lookup table file(s) with unexpected write perms: expected admin + globalcart_analyst")
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors file_count titles bad_read bad_write
```

Then check the collections 

```sql
| rest /servicesNS/-/-/storage/collections/config
| search title=region OR title=cost_supplier
| eval read_bad=if(mvcount('eai:acl.perms.read')==2
        AND isnotnull(mvfind('eai:acl.perms.read',"^admin$"))
        AND isnotnull(mvfind('eai:acl.perms.read',"^globalcart_analyst$")),0,1),
       write_bad=if(mvcount('eai:acl.perms.write')==2
        AND isnotnull(mvfind('eai:acl.perms.write',"^admin$"))
        AND isnotnull(mvfind('eai:acl.perms.write',"^globalcart_analyst$")),0,1)
| stats count as collection_count, sum(read_bad) as bad_read, sum(write_bad) as bad_write,
        values(title) as titles
| eval errors=validate(
    collection_count==2,
        "Expected 2 collection(s), found ".collection_count.": ".mvjoin(titles,", "),
    bad_read==0,
        bad_read." collection(s) with unexpected read perms: expected admin + globalcart_analyst",
    bad_write==0,
        bad_write." collection(s) with unexpected write perms: expected admin + globalcart_analyst")
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors collection_count titles bad_read bad_write

```

 Finally check lookup definitions which will show both kv store lookups and file based lookups

```sql
| rest /servicesNS/-/-/data/transforms/lookups
| search "eai:acl.app"=globalcart
| eval read_bad=if(mvcount('eai:acl.perms.read')==2
        AND isnotnull(mvfind('eai:acl.perms.read',"^admin$"))
        AND isnotnull(mvfind('eai:acl.perms.read',"^globalcart_analyst$")),0,1),
       write_bad=if(mvcount('eai:acl.perms.write')==2
        AND isnotnull(mvfind('eai:acl.perms.write',"^admin$"))
        AND isnotnull(mvfind('eai:acl.perms.write',"^globalcart_analyst$")),0,1)
| stats count as def_count, sum(read_bad) as bad_read, sum(write_bad) as bad_write,
        values(title) as titles
| eval errors=validate(
    def_count==3,
        "Expected 3 lookup definition(s), found ".def_count.": ".mvjoin(titles,", "),
    bad_read==0,
        bad_read." lookup definition(s) with unexpected read perms: expected admin + globalcart_analyst",
    bad_write==0,
        bad_write." lookup definition(s) with unexpected write perms: expected admin + globalcart_analyst")
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors def_count titles bad_read bad_write
```

## Access Control Check
SPL queries to check the roles and users the scenario depends on.

### Roles
Check the `globalcart_analyst` role exists and is scoped to the globalcart index only.

```sql
| rest /services/authorization/roles
| search title=globalcart_analyst
| stats count as role_count,
        values(srchIndexesAllowed) as indexes,
        values(imported_roles) as inherits,
        values(defaultApp) as default_app
| eval errors=validate(
    role_count==1,
        "Expected 1 globalcart_analyst role, found ".role_count,
    mvcount(indexes)==1,
        "Expected 1 allowed index, found: ".mvjoin(indexes,", "),
    mvindex(indexes,0)=="globalcart",
        "Unexpected allowed index: ".mvjoin(indexes,", "),
    isnotnull(mvfind(inherits,"^power$")),
        "globalcart_analyst does not inherit power, inherits: ".mvjoin(inherits,", "),
    mvindex(default_app,0)=="globalcart",
        "Unexpected default app: ".mvjoin(default_app,", "))
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors role_count indexes inherits default_app
```

### Users
Check the `john` persona exists with the right role, default app and timezone.

```sql
| rest /services/authentication/users
| search title=john
| stats count as user_count,
        values(roles) as roles,
        values(defaultApp) as default_app,
        values(tz) as tz
| eval errors=validate(
    user_count==1,
        "Expected 1 user john, found ".user_count,
    mvcount(roles)==1,
        "Expected 1 role, found: ".mvjoin(roles,", "),
    mvindex(roles,0)=="globalcart_analyst",
        "Unexpected role: ".mvjoin(roles,", "),
    mvindex(default_app,0)=="globalcart",
        "Unexpected default app: ".mvjoin(default_app,", "),
    mvindex(tz,0)=="Asia/Singapore" OR mvindex(tz,0)=="Asia/Hong_Kong",
        "Unexpected tz: ".mvjoin(tz,", "))
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors user_count roles default_app tz
```


## Known Searches Check

| Check                             | Expected                                                  | Notes                                                                                                                                                                   |
| --------------------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `_indextime`                      | `min=1786605521` `max=1786605521`<br>`sum=10719633126000` | The entire csv was added in bulk so the real check is that <br>`min == max` and the `sum` remains the same otherwise there are events that have a different index time. |
| `_time`                           | `min=1777565523` `max=1785081493`<br>`sum=10688027062398` | The values here should all match otherwise the parsed event time is erroneous.                                                                                          |
| Events indexed                    | 6000                                                      | Scoped to globalcart:sales                                                                                                                                              |
| Unique Customers in Beauty        | 958                                                       |                                                                                                                                                                         |
| Total revenue                     | $2,037,941.60                                             | Equals dataset’s full revenue                                                                                                                                           |
| Best category + priority tier     | Books / Tier3, 1051 orders                                | Checks if category_to_priority lookup and event data match                                                                                                              |
| category_to_priority rows         | 6                                                         | Covers all 6 categories in the dataset, check with `\| inputlookup definition`                                                                                          |
| country_to_region rows            | 12                                                        | Covers all 12 countries in the dataset, check with  `\| inputlookup definition`                                                                                         |
| product_to_cost rows              | 30                                                        | Covers all 30 products in the dataset, check with `\| inputlookup definition`                                                                                           |
| category_to_priority md5 checksum | 2cba9a0163c0218b30963d2fc4250cd4                          | Checksums all the data inside the lookup to ensure the integrity of the data                                                                                            |
| country_to_region md5 checksum    | 96e7b1bb0e5fb655268f839e8c84e1dd                          | Checksums all the data inside the lookup to ensure the integrity of the data                                                                                            |
| product_to_cost md5 checksum      | db6bd8a4c73711a7addcb338304703d2                          | Checksums all the data inside the lookup to ensure the integrity of the data                                                                                            |

The known searches above can be validated using the checks below. Each check emits its own result.

### `_indextime`

```sql
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| stats count as events, min(_indextime) as i_min, max(_indextime) as i_max, sum(_indextime) as i_sum
| eval errors=validate(
    events==6000,
        "Expected 6000 events, found ".events,
    i_min==i_max,
        "Events have differing index times, min ".i_min." max ".i_max,
    i_min==1786605521,
        "Expected _indextime 1786605521, found ".i_min,
    i_sum==10719633126000,
        "Expected _indextime sum 10719633126000, found ".i_sum)
| eval result=if(isnull(errors),"PASS","FAIL")
| foreach i_min i_max [ eval <<FIELD>>_formatted=strftime(<<FIELD>>,"%F %T %Z") ]
| table result errors events i_min i_max i_sum i_min_formatted i_max_formatted
```

### `_time`

```sql
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| stats count as events, min(_time) as t_min, max(_time) as t_max, sum(_time) as t_sum
| eval errors=validate(
    events==6000,
        "Expected 6000 events, found ".events,
    t_min==1777565523,
        "Expected _time min 1777565523, found ".t_min,
    t_max==1785081493,
        "Expected _time max 1785081493, found ".t_max,
    t_sum==10688027062398,
        "Expected _time sum 10688027062398, found ".t_sum)
| eval result=if(isnull(errors),"PASS","FAIL")
| foreach t_min t_max [ eval <<FIELD>>_formatted=strftime(<<FIELD>>,"%F %T %Z") ]
| table result errors events t_min t_max t_sum t_min_formatted t_max_formatted
```

### Events indexed

```sql
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| stats count as events
| eval errors=validate(
    events==6000,
        "Expected 6000 events, found ".events)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors events
```

### Unique customers in Beauty

```sql
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now category="Beauty"
| stats dc(customer_id) as unique_customers
| eval errors=validate(
    unique_customers==958,
        "Expected 958 unique customers in Beauty, found ".unique_customers)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors unique_customers
```

### Total revenue

```sql
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| stats sum(revenue) as total_revenue
| eval total_revenue=round(total_revenue,2)
| eval errors=validate(
    total_revenue==2037941.60,
        "Expected total revenue 2037941.60, found ".total_revenue)
| eval result=if(isnull(errors),"PASS","FAIL")
| eval total_revenue_formatted="$".tostring(total_revenue,"commas")
| table result errors total_revenue total_revenue_formatted
```

### Best category + priority tier

```sql
index=globalcart sourcetype=globalcart:sales earliest=0 latest=now
| lookup category_to_priority category OUTPUT priority
| stats count as orders by category, priority
| sort - orders
| head 1
| eval errors=validate(
    category=="Books",
        "Expected top category Books, found ".category,
    priority=="Tier3",
        "Expected priority Tier3, found ".priority,
    orders==1051,
        "Expected 1051 orders, found ".orders)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors category priority orders
```

### `category_to_priority` rows

```sql
| inputlookup category_to_priority
| stats count as rows
| eval errors=validate(
    rows==6,
        "Expected 6 rows in category_to_priority, found ".rows)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors rows
```

### `country_to_region` rows

```sql
| inputlookup country_to_region
| stats count as rows
| eval errors=validate(
    rows==12,
        "Expected 12 rows in country_to_region, found ".rows)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors rows
```

### `product_to_cost` rows

```sql
| inputlookup product_to_cost
| stats count as rows
| eval errors=validate(
    rows==30,
        "Expected 30 rows in product_to_cost, found ".rows)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors rows
```

### Lookup checksums

One block per lookup. The hash covers every row.

```sql
| inputlookup category_to_priority
| eval k=_key
| sort k
| tojson output_field=j
| eval j=md5(j)
| stats list(j) as hashes
| eval hash=md5(mvjoin(hashes,"~"))
| eval errors=validate(
    hash=="2cba9a0163c0218b30963d2fc4250cd4",
        "Expected category_to_priority hash 2cba9a0163c0218b30963d2fc4250cd4, found ".hash)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors hash
```

```sql
| inputlookup country_to_region
| eval k=_key
| sort k
| tojson output_field=j
| eval j=md5(j)
| stats list(j) as hashes
| eval hash=md5(mvjoin(hashes,"~"))
| eval errors=validate(
    hash=="96e7b1bb0e5fb655268f839e8c84e1dd",
        "Expected country_to_region hash 96e7b1bb0e5fb655268f839e8c84e1dd, found ".hash)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors hash
```

```sql
| inputlookup product_to_cost
| eval k=_key
| sort k
| tojson output_field=j
| eval j=md5(j)
| stats list(j) as hashes
| eval hash=md5(mvjoin(hashes,"~"))
| eval errors=validate(
    hash=="db6bd8a4c73711a7addcb338304703d2",
        "Expected product_to_cost hash db6bd8a4c73711a7addcb338304703d2, found ".hash)
| eval result=if(isnull(errors),"PASS","FAIL")
| table result errors hash
```

## Functional Checks

| Check                                                                                     | Reason                                                                                          |
| ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Log in as `john`                                                                          | Checks that the created persona account can login to the Splunk instance                        |
| `john` can search `globalcart` but not sensitive indexes like  `_audit`                   | Created persona account is only allowed to search data needed for its role                      |
| `Too much revenue lost` alert is still scheduled, fires and writes to `globalcart:alerts` | Scheduled alert fires and can write into `globalcart` index with sourcetype `globalcart:alerts` |
| lookup editor app is usable by `john`                                                     | Ensures the lookup app is usable as the scenario demands heavy usage of lookups                 |

# Results Template

| Category                   | Check                                                                                     | Result |
| -------------------------- | ----------------------------------------------------------------------------------------- | ------ |
| Knowledge Object Inventory | Apps                                                                                      |        |
| Knowledge Object Inventory | Saved Searches                                                                            |        |
| Knowledge Object Inventory | Dashboards                                                                                |        |
| Knowledge Object Inventory | Indexes                                                                                   |        |
| Knowledge Object Inventory | Sourcetypes                                                                               |        |
| Knowledge Object Inventory | Lookup table files                                                                        |        |
| Knowledge Object Inventory | Collections                                                                               |        |
| Knowledge Object Inventory | Lookup definitions                                                                        |        |
| Access Control             | Role `globalcart_analyst`                                                                 |        |
| Access Control             | User `john`                                                                               |        |
| Known Searches             | `_indextime`                                                                              |        |
| Known Searches             | `_time`                                                                                   |        |
| Known Searches             | Events indexed                                                                            |        |
| Known Searches             | Unique Customers in Beauty                                                                |        |
| Known Searches             | Total revenue                                                                             |        |
| Known Searches             | Best category + priority tier                                                             |        |
| Known Searches             | category_to_priority rows                                                                 |        |
| Known Searches             | country_to_region rows                                                                    |        |
| Known Searches             | product_to_cost rows                                                                      |        |
| Known Searches             | category_to_priority md5 checksum                                                         |        |
| Known Searches             | country_to_region md5 checksum                                                            |        |
| Known Searches             | product_to_cost md5 checksum                                                              |        |
| Functional Checks          | Log in as `john`                                                                          |        |
| Functional Checks          | `john` can search `globalcart` but not sensitive indexes like `_audit`                    |        |
| Functional Checks          | `Too much revenue lost` alert is still scheduled, fires and writes to `globalcart:alerts` |        |
| Functional Checks          | lookup editor app is usable by `john`                                                     |        |
