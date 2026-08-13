---
status: complete
created: 2026-08-12
updated: 2026-08-12
---
# Summary
Instance-wide Splunk configuration applied once, on top of a fresh install, before any scenario is built. 

# Web TLS

```
# $SPLUNK_HOME/etc/system/local/web.conf
[settings]
enableSplunkWebSSL = true
```

# Base Roles

| Role    | Field                | Default | Set to                                | Inherits | Reason                                                                                                                                                                                                                                           |
| ------- | -------------------- | ------- | ------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `user`  | `srchIndexesAllowed` | `*`     | `main`                                | –        | Base user should not be allowed to search scenario related indexes                                                                                                                                                                               |
| `power` | `srchIndexesAllowed` | `*`     | `_internal, history,   main, summary` | `user`   | Power role should not be allowed to freely search scenario related indexes. Access is granted through scenario roles, not inherited from base. `_internal` is allowed because it backs job inspector, allowing for debugging scheduled searches. |

# Apps & Add-ons

| App                                | Source     | Version | Reason                           |
| ---------------------------------- | ---------- | ------- | -------------------------------- |
| Splunk App for Lookup File Editing | SplunkBase | 4.0.7   | For easier management of lookups |

# Verification

The role checks need an account holding only the role under test — an admin session sees
everything and proves nothing. Two throwaway accounts, one per base role, are enough, and
they stay useful for every scenario built on this baseline.

| Check                             | Expected                                                                                         |
| --------------------------------- | ------------------------------------------------------------------------------------------------ |
| Splunk Web serves HTTPS           | `curl -k -I https://172.16.58.10:8000` returns 200; plain HTTP on 8000 no longer answers         |
| Indexes visible to `user`         | `\| eventcount summarize=false index=*` as a user-only account lists `main` and nothing else     |
| Indexes visible to `power`        | Same search as a power-only account lists `_internal`, `history`, `main`, `summary` only         |
| Scenario indexes unreachable      | `index=globalcart` as either account returns no results                                          |
| Lookup File Editing app installed | `\| rest /services/apps/local \| table title, version, disabled` shows it at 4.0.7, not disabled |
