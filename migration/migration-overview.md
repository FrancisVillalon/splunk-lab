---
status: complete
created: 2026-08-25
updated: 2026-08-31
---
# Summary
This document is an overview of all related documents to the migration process that moves an all-in-one deployment of Splunk from an Ubuntu VM to a docker container.
# Document Flow

| Stage | Document                                                                      | Question it answers                                   | Document Status |
| ----- | ----------------------------------------------------------------------------- | ----------------------------------------------------- | --------------- |
| 1     | [baseline-ubuntu-vm](../environment/baseline-ubuntu-vm.md), [baseline-splunk-config](../environment/baseline-splunk-config.md) and any scenario manifests | What exists on the source system today?               | COMPLETE        |
| 2     | [migration-readiness-check](migration-readiness-check.md)                                                 | Should the move be attempted, and what is the target? | COMPLETE        |
| 3     | [pre-migration-check](pre-migration-check.md) & [pre-migration snapshot](../snapshots/31-8-2026-pre-migration.md) | Is the source state captured, verified and frozen?    | COMPLETE        |
| 4     | [baseline-docker-container](../environment/baseline-docker-container.md)                                                 | What is the target, as actually built?                | COMPLETE        |
| 5     | [post-migration-check](post-migration-check.md) & [post-migration snapshot](../snapshots/31-8-2026-post-migration.md) | Did the state survive the move?                       | COMPLETE        |
| 6     | [source-retirement-check](source-retirement-check.md)                                                   | Can the source system be retired?                     | IN PROGRESS     |
