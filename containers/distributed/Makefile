COMPOSE := docker compose
DS			:= ds1
SPLUNK	:= /opt/splunk/bin/splunk
DS_APPS	:= /opt/splunk/etc/deployment-apps
DS_SC		:= /opt/splunk/etc/system/local/serverclass.conf

.PHONY: up deploy-apps reload status down

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

## Check the currently loaded deployment apps and clients
status:
	$(COMPOSE) exec -T $(DS) ls $(DS_APPS)
	$(COMPOSE) exec -T -u splunk $(DS) \
		bash -c '$(SPLUNK) list deploy-clients -auth admin:$$SPLUNK_PASSWORD'

## Bring stack down
down:
	$(COMPOSE) down
