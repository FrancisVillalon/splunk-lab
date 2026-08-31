# Splunk Lab

Single-instance Splunk Enterprise 10.4.2 — built on an Ubuntu VM, migrated to
Docker, and verified against datasets with known-good answers.

## Migration

Six gates, each passing before the next starts. Migrated 31 Aug 2026; source VM
retires 4 Sep after a soak window.

| # | Stage | Question | Status |
| --- | --- | --- | --- |
| 1 | [baseline-ubuntu-vm](environment/baseline-ubuntu-vm.md) · [baseline-splunk-config](environment/baseline-splunk-config.md) · [manifest](environment/globalcart-manifest.md) | What's on the source? | done |
| 2 | [readiness-check](migration/migration-readiness-check.md) | Should it move, and to what? | done |
| 3 | [pre-check](migration/pre-migration-check.md) → [snapshot](snapshots/31-8-2026-pre-migration.md) | State captured and frozen? | done |
| 4 | [container-build](environment/baseline-docker-container.md) | What got built? | done |
| 5 | [post-check](migration/post-migration-check.md) → [snapshot](snapshots/31-8-2026-post-migration.md) | Did state survive? | done |
| 6 | [retirement-check](migration/source-retirement-check.md) | Can the source go? | in progress |

Worth a look:

- [Where this method breaks](migration/migration-readiness-check.md#method-of-migration-implications) — the assumptions it rests on, and why it fails on a cluster
- [Risk register](migration/migration-readiness-check.md#risk-register) — signals and responses, written before the work
- [Rollback window](migration/source-retirement-check.md#rollback-window) — what's retained, and when recovery stops being possible

## Labs

Synthetic scenarios that double as the migration's verification fixtures. Event
counts, revenue totals and lookup checksums are known in advance and asserted as
`PASS`/`FAIL` in [globalcart-manifest](environment/globalcart-manifest.md).

| Lab | Scenario |
| --- | --- |
| [GlobalCart](labs/GlobalCart/GlobalCart.md) | Ad-hoc revenue and refund analysis for an online retailer |
| [IronvaleFinancial](labs/IronvaleFinancial/IronvaleFinancial.md) | SOC triage of security telemetry for a regional bank |
| [LumeoStreaming](labs/LumeoStreaming/LumeoStreaming.md) | Billing accuracy, incidents and churn for a streaming platform |

All lab data is generated. Nothing in `known_bad_ips.csv` is real threat intelligence.

## Layout

```
environment/   source VM, container target, Splunk config, scenario manifests
migration/     the six-stage runbook and its checks
snapshots/     captured state either side of the move
labs/          one folder per scenario (writeup + data + images)
containers/    docker compose definitions
scripts/       VM control, pre-migration freeze and backup
```
