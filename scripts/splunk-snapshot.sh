#!/usr/bin/env bash
set -euo pipefail

# Vars
DATE=$(date +%F)
SPLUNK_HOME=/opt/splunk
DEST_BASE=/mnt/hgfs/splunk-step-repo/splunk-backup
KV_DIR="$SPLUNK_HOME/var/lib/splunk/kvstorebackup"
SUCCESS=0
# Create temp and delete on script exit
STAGE=$(mktemp -d /tmp/splunk-snapshot-"$DATE"-XXXXXXXX)
DEST=""

# define cleanup
clean() {
  cd /
  rm -rf "$STAGE"
  ((SUCCESS)) || rm -rf "$DEST"
}
trap clean EXIT

# --- (0) Setup
# Check if script is running as sudo
[[ $EUID -eq 0 ]] || {
  echo "[$(date)] run with sudo"
  exit 1
}
# Check is destination folder is writable
[[ -w $DEST_BASE ]] || {
  echo "[$(date)] $DEST_BASE not writable, check vmware shared folder setting or allow_other in /etc/fstab"
  exit 1
}

# Create output folder
DEST=$(mktemp -d "$DEST_BASE/$DATE-XXXXXXXX")

# Create report file
REPORT="$DEST/SNAPSHOT-$DATE.md"
exec > >(tee -a "$REPORT") 2>&1
# Splunk login
echo "[$(date)] Login to Splunk"
sudo -u splunk -H /opt/splunk/bin/splunk login
# Define splunk() function
splunk() { sudo -u splunk -H "$SPLUNK_HOME/bin/splunk" "$@"; }

# --- (1) KVStore backup
echo "[$(date)] Checking kvstore-status"
kvstore_status=$(splunk show kvstore-status)
if ! grep -q "backupRestoreStatus : Ready" <<<"$kvstore_status"; then
  echo "[$(date)] backRestoreStatus is not ready"
  exit 1
else
  echo "[$(date)] backupRestoreStatus is ready!"
fi
if ! grep -q "status : ready" <<<"$kvstore_status"; then
  echo "[$(date)] status is not ready."
  exit 1
else
  echo "[$(date)] status is ready!"
fi

# ----
echo "[$(date)] Backing up kvstore"
splunk backup kvstore -pointInTime true -archiveName "kvstore-backup-$DATE" || {
  echo "[$(date)] kvstore backup command failed"
  exit 1
}

echo "[$(date)] Waiting for kvstore tarball"
KV_TIMEOUT=${KV_TIMEOUT:-600}
deadline=$((SECONDS + KV_TIMEOUT))
KV_TGZ=""
while ((SECONDS < deadline)); do
  KV_TGZ=$(ls -t "$KV_DIR" 2>/dev/null | grep "^kvstore-backup-$DATE.*\.tar\.gz$" | head -1) || true
  [[ -n $KV_TGZ ]] && break
  sleep 2
done
[[ -z $KV_TGZ ]] && {
  echo "[$(date)] No kvstore backup archive found after ${KV_TIMEOUT}s"
  exit 1
}

echo "[$(date)] Waiting for $KV_TGZ to finish writing"
prev=-1
while
  size=$(stat -c%s "$KV_DIR/$KV_TGZ")
  [[ $size -ne $prev ]]
do
  prev=$size
  sleep 2
done

echo "[$(date)] Checking if gzip is valid"
if ! gzip -t "$KV_DIR/$KV_TGZ"; then
  echo "[$(date)] Created gzip is not valid"
  exit 1
else
  echo "[$(date)] Created gzip is valid!"
fi

echo "[$(date)] Staging kvstore backup"
cp -p "$KV_DIR/$KV_TGZ" "$STAGE/"
# ---

# --- (2) Ownership & Permissions of existing folders that need to be reassigned appropriately
echo "[$(date)] Getting current folder permissions and service account details"
SPLUNK_ID=$(getent passwd splunk)
ETC_MODE=$(stat -c '%a' "$SPLUNK_HOME/etc")
VAR_MODE=$(stat -c '%a' "$SPLUNK_HOME/var")

# --- (3) Freeze instance, shutdown splunkd
echo "[$(date)] Stopping Splunkd"
systemctl stop Splunkd
for _ in {1..30}; do
  ps -eo comm | grep -Eiq '^(splunkd|mongod)$' || break
  sleep 2
done
ps -eo comm | grep -Eiq '^(splunkd|mongod)$' && {
  echo "[$(date)] splunk processes still running"
  exit 1
}
echo "[$(date)] Stopped"

# --- (4) Backup and checksum
echo "[$(date)] Backing up and staging \$SPLUNK_HOME/etc"
tar -czf "$STAGE/splunk-etc-$DATE.tar.gz" -C "$SPLUNK_HOME" etc

echo "[$(date)] Backing up and staging \$SPLUNK_HOME/var, excluding /var/run/* & /var/lib/splunk/kvstore/*"
tar -cf "$STAGE/splunk-var-$DATE.tar" \
  --exclude='var/run/*' --exclude='var/lib/splunk/kvstore/*' -C "$SPLUNK_HOME" var

# KV VERSION FILE
KV_VERSIONFILE=$(cd "$SPLUNK_HOME/var/run/splunk/kvstore_upgrade" && ls -1 versionFile* 2>/dev/null | head -1)
[[ -n $KV_VERSIONFILE ]] || {
  echo "[$(date)] no versionFile found"
  exit 1
}
echo "[$(date)] Appending kvstore version marker $KV_VERSIONFILE"
tar -rf "$STAGE/splunk-var-$DATE.tar" \
  -C "$SPLUNK_HOME" "var/run/splunk/kvstore_upgrade/$KV_VERSIONFILE"
gzip "$STAGE/splunk-var-$DATE.tar"

# --- (5) Check backups
echo "[$(date)] Checking if exclusions were applied"
[[ $(tar -tzf "$STAGE/splunk-var-$DATE.tar.gz" |
  grep -Ev "^var/run/splunk/kvstore_upgrade/$KV_VERSIONFILE\$" | # Invert match
  grep -Ec '^var/(run|lib/splunk/kvstore)/.') -eq 0 ]] || {      #supress normal output --> print count of matches
  echo "[$(date)] excluded paths leaked into the var tarball"
  exit 1
}
echo "[$(date)] Exclusions were applied successfully!"

# Check version marker exists in tarball
echo "[$(date)] Checking if version marker is missing from var tarball"
tar -tzf "$STAGE/splunk-var-$DATE.tar.gz" |
  grep -qx "var/run/splunk/kvstore_upgrade/$KV_VERSIONFILE" || {
  echo "[$(date)] version marker missing from var tarball"
  exit 1
}
echo "[$(date)] Version marker exists!"

if ! gzip -t "$STAGE/splunk-etc-$DATE.tar.gz" "$STAGE/splunk-var-$DATE.tar.gz"; then
  echo "[$(date)] Created gzips are not valid."
  exit 1
else
  echo "[$(date)] Created gzips are valid for both etc and var!"
fi

# --- (6) Grab License and Splunk.secret
echo "[$(date)] Grabbing license file and splunk.secret"

# Grab path of license file
shopt -s nullglob
files=("$SPLUNK_HOME"/etc/licenses/enterprise/*.lic)
shopt -u nullglob
if [[ ${#files[@]} -eq 0 ]]; then
  echo "[$(date)] No .lic found in $SPLUNK_HOME/etc/licenses/enterprise/"
  exit 1
fi
LICENSE="${files[0]}"

LICENSE_BASE=$(basename "$LICENSE")
SPLUNK_SECRET="$SPLUNK_HOME/etc/auth/splunk.secret"
echo "[$(date)] Stage license file and splunk.secret"
cp -p "$LICENSE" "$SPLUNK_SECRET" "$STAGE/"

# --- (7) Checksum, deliver, prove the copy landed intact
cd "$STAGE"
echo "[$(date)] Calculating SHA512 sum for etc tarball, var tarball, "
sha512sum "splunk-etc-$DATE.tar.gz" "splunk-var-$DATE.tar.gz" "$KV_TGZ" splunk.secret "$LICENSE_BASE" |
  tee splunk-migration.sha512
echo "[$(date)] Copying data to destination folder..."
cp "splunk-etc-$DATE.tar.gz" "splunk-var-$DATE.tar.gz" "$KV_TGZ" splunk.secret "$LICENSE_BASE" \
  splunk-migration.sha512 "$DEST/"
sync
echo "[$(date)] Checking SHA512 hashes"
if (cd "$DEST" && sha512sum -c splunk-migration.sha512); then
  echo "[$(date)] Hashes verified! Snapshot done!"
else
  echo "[$(date)] Hash mismatch."
  exit 1
fi

# --- (8) Report
echo "[$(date)] Artifact table"
echo
echo "| Artifact | Size | Path |"
echo "| -------- | ---- | ---- |"
while read -r _ name; do
  printf '| `%s` | %s | `%s` |\n' "$name" "$(du -h "$DEST/$name" | cut -f1)" "$DEST/$name"
done <splunk-migration.sha512
echo
echo "[$(date)] SHA512 checksums"
echo
cat splunk-migration.sha512
echo
echo "[$(date)] Ownership and Permissions"
echo
echo "| Value | Result |"
echo "| ----- | ------ |"
echo "| splunk UID:GID on the VM | \`$SPLUNK_ID\` |"
echo "| Mode on \`$SPLUNK_HOME/etc\` | $ETC_MODE |"
echo "| Mode on \`$SPLUNK_HOME/var\` | $VAR_MODE |"
echo "[$(date)] Report: $REPORT"
SUCCESS=1
