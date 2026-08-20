---
status: complete
created: 2026-08-19
updated: 2026-08-20
---
# Summary
Documents all the steps taken to migrate the environment
# Create named docker volumes

```bash
# Check splunk user id
docker run --rm --entrypoint id splunk/splunk:10.4.2 splunk
# -> uid=41812(splunk) gid=41812(splunk) groups=41812(splunk),999(ansible)  

# Create empty named volumes
docker volume create splunk-etc
docker volume create splunk-var

# Populate named volumes using a throwaway alpine container
docker run --rm -i -v splunk-etc:/data alpine sh -c 'tar -xzf - --strip-components=1 -C /data && chown -R 41812:41812 /data' < /mnt/990pro/Work/repo/splunk-step/splunk-backup/<backup_folder>/<backup_etc>

docker run --rm -i -v splunk-var:/data alpine sh -c 'tar -xzf - --strip-components=1 -C /data && chown -R 41812:41812 /data' < /mnt/990pro/Work/repo/splunk-step/splunk-backup/<backup_folder>/<backup_var>
  
# Check owernship and mode
docker run --rm -v splunk-etc:/etc-data -v splunk-var:/var-data alpine ls -ld /etc-data /var-data
```

```bash
# If needed delete the volumes and reextract
docker volume rm splunk-etc
docker volume rm splunk-var
docker volume list
```

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
          cpus: "4"
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

After docker container is running and known to be healthy, run post migration checks.