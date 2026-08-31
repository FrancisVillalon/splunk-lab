---
status: complete
created: 2026-08-19
updated: 2026-08-31
---
# Summary
Documents all the steps taken to get a working docker container with Splunk version 10.4.2.
# Create named docker volumes

```bash
# Check splunk user id
docker run --rm --entrypoint id splunk/splunk:10.4.2 splunk
# -> uid=41812(splunk) gid=41812(splunk) groups=41812(splunk),999(ansible)  

# Create empty named volumes
docker volume create splunk-etc
docker volume create splunk-var

# Populate named volumes using a throwaway alpine container
docker run --rm -i -v splunk-etc:/data alpine sh -c 'tar -xzf - --strip-components=1 -C /data && chown -R 41812:41812 /data' < /<backup_folder>/<backup_etc>
docker run --rm -i -v splunk-var:/data alpine sh -c 'tar -xzf - --strip-components=1 -C /data && chown -R 41812:41812 /data' < /<backup_folder>/<backup_var>
  
# Check ownership and mode
docker run --rm -v splunk-etc:/etc-data -v splunk-var:/var-data alpine ls -ld /etc-data /var-data
```

```bash
# If needed delete the volumes and reextract
docker volume rm splunk-etc
docker volume rm splunk-var
docker volume list
```

# Create the provisioning defaults
The container is provisioned by the Splunk ansible playbook, which reads `/tmp/defaults/default.yml` and the `SPLUNK_PASSWORD` environment variable. Both files live next to `docker-compose.yml`.

`default.yml` only names the admin account. The account itself already exists in the migrated `etc/passwd`, so nothing here creates a user, it just tells the playbook which account to authenticate as.

```yaml
# default.yml
splunk:
  admin_user: admin
```

The password is supplied separately so it stays out of the compose file. This is the password of the existing admin account on the source VM, not a new one.

```bash
# .env
SPLUNK_PASSWORD=<existing admin password from the source VM>
```

> [!note]
> `user-seed.conf` is deliberately not used here. See the provisioning method decision in [migration-readiness-check](../migration/migration-readiness-check.md).

# Create the docker compose

```yaml
services:
  splunk:
    image: splunk/splunk:10.4.2
    container_name: splunk
    hostname: splunk
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
      - "127.0.0.1:8089:8089"
    environment:
      TZ: Asia/Singapore
      SPLUNK_START_ARGS: --accept-license
      SPLUNK_GENERAL_TERMS: --accept-sgt-current-at-splunk-com
      SPLUNK_PASSWORD: ${SPLUNK_PASSWORD}
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
      nproc: 20480
    volumes:
      - splunk-etc:/opt/splunk/etc
      - splunk-var:/opt/splunk/var
      - ./default.yml:/tmp/defaults/default.yml
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 8G
volumes:
  splunk-etc:
    external: true
  splunk-var:
    external: true
```

# Run Docker

```bash
docker compose up -d  # -> Start docker container
docker compose logs -f # -> Ensure ansible playbook ran successfully
docker ps -a # -> Ensure docker container is healthy
```

After docker container is running and known to be healthy, run post-migration checks.