# Splunk Lab

Personal Splunk practice lab: environment setup notes plus scenario-based
labs for building SPL, lookups, dashboards, and data model skills against
synthetic company datasets.

## Structure

```
environment/   baseline VM + Splunk set, environment manifest
labs/          one folder per scenario (writeup + data + images)
scripts/       helper scripts
```
 
## Labs

| Lab | Scenario |
| --- | --- |
| [GlobalCart](labs/GlobalCart/GlobalCart.md) | Junior data analyst answering ad-hoc revenue/refund questions for an online retailer |
| [IronvaleFinancial](labs/IronvaleFinancial/IronvaleFinancial.md) | SOC analyst triaging security telemetry from a regional bank |
| [LumeoStreaming](labs/LumeoStreaming/LumeoStreaming.md) | BI analyst investigating billing accuracy, service incidents, and churn risk for a streaming platform |

## Environment

- [baseline-ubuntu-vm](environment/baseline-ubuntu-vm.md) — base VM setup
- [baseline-splunk-config](environment/baseline-splunk-config.md) — instance-wide Splunk config
- [globalcart-manifest](environment/globalcart-manifest.md) — object inventory for the GlobalCart scenario
