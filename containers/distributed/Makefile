COMPOSE := docker compose
DS			:= ds1
SPLUNK	:= /opt/splunk/bin/splunk
DS_APPS	:= /opt/splunk/etc/deployment-apps
DS_SC		:= /opt/splunk/etc/system/local/serverclass.conf

.PHONY: up deploy-apps reload provision-ds deprovision-ds status down bootstrap

## Full setup of environment
bootstrap:
	$(MAKE) provision-ds
	$(MAKE) deploy-apps

## Bring the stack up, blocks until all health checks pass
up:
	$(COMPOSE) up -d --wait

deploy-apps: up
	$(COMPOSE) exec -T -u 0 $(DS) rm -rf $(DS_APPS)
	$(COMPOSE) cp ./deployment-apps $(DS):$(DS_APPS)
	$(COMPOSE) cp ./serverclass.conf $(DS):$(DS_SC)
	$(COMPOSE) exec -T -u 0 $(DS) chown -R splunk:splunk $(DS_APPS) $(DS_SC)
	$(MAKE) reload

## Reload the deployment server, rescans deployment apps and rereads serverclass
reload:
	$(COMPOSE) exec -T -u splunk $(DS) \
		bash -c '$(SPLUNK) reload deploy-server -auth admin:$$SPLUNK_PASSWORD'

## Provision ds1's own base config. ds1 is not a deployment client, so
## nothing pushes to it -- this target is its config-management plane.
provision-ds: up
	$(COMPOSE) exec -T -u 0 $(DS) rm -rf /opt/splunk/etc/apps/all_outputs_to_idx /opt/splunk/etc/apps/all_deployment_key
	$(COMPOSE) cp ./deployment-apps/all_outputs_to_idx/ $(DS):/opt/splunk/etc/apps/
	$(COMPOSE) cp ./deployment-apps/all_deployment_key/ $(DS):/opt/splunk/etc/apps/
	$(COMPOSE) exec -T -u 0 $(DS) chown -R splunk:splunk /opt/splunk/etc/apps/all_outputs_to_idx /opt/splunk/etc/apps/all_deployment_key
	$(COMPOSE) exec -T -u splunk $(DS) $(SPLUNK) restart

## Remove ds1's locally provisioned apps, reverting it to a non-forwarding DS
deprovision-ds: up
	$(COMPOSE) exec -T -u 0 $(DS) rm -rf /opt/splunk/etc/apps/all_outputs_to_idx /opt/splunk/etc/apps/all_deployment_key
	$(COMPOSE) exec -T -u splunk $(DS) $(SPLUNK) restart

## Check the currently loaded deployment apps and clients
status:
	$(COMPOSE) exec -T $(DS) ls $(DS_APPS)
	$(COMPOSE) exec -T -u splunk $(DS) \
		bash -c '$(SPLUNK) list deploy-clients -auth admin:$$SPLUNK_PASSWORD'

## Bring stack down
down:
	$(COMPOSE) down
