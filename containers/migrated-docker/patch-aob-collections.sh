#!/usr/bin/env bash
set -euo pipefail

# Patch Splunk Add-on Builder (AoB) 4.5.4 for Python 3.10+.
#
# Why:
#   Splunk 10.4.2 runs app code on Python 3.13. Python 3.10 removed the old
#   aliases like `collections.Iterable` (they live in `collections.abc` now).
#   AoB 4.5.4 still uses `collections.Iterable` in a few places, so on this
#   Splunk version:
#
#     CIM Mapping -> Select Data Models -> Select
#       POST /custom/splunk_app_addon-builder/app_edit_cimmapping/save_models -> 500
#       web_service.log: AttributeError: module 'collections' has no attribute 'Iterable'
#                        (bin/tabuilder_utility/common_util.py, flatten())
#       UI banner:       Cannot read properties of undefined (reading '0')
#
#   The UI banner is just the frontend choking on the 500, the real error is
#   the Python one. Net effect: CIM mappings can't be saved at all.
#
# Persistence:
#   AoB lives in the splunk-etc volume, so this survives restarts and container
#   recreation. Re-run after reinstalling/upgrading AoB or wiping the volume.
#   Safe to re-run: already-patched files are left alone.

# Vars
CONTAINER=${CONTAINER:-splunk}
AOB=/opt/splunk/etc/apps/splunk_app_addon-builder
FILES=(
  bin/tabuilder_utility/common_util.py                          # CIM mapping save (the actual bug)
  bin/splunk_app_add_on_builder/jsl/roles.py                    # same alias, used by AoB itself
  bin/ta_generator/resources_lib/4.5.4/aob_py3/jsl/roles.py     # copy bundled into add-ons AoB generates
)

# Run as the splunk user so file ownership doesn't change
dexec() { docker exec -u splunk "$CONTAINER" bash -c "$1"; }

dexec "[[ -d $AOB ]]" || {
  echo "[$(date)] Add-on Builder not found in container $CONTAINER"
  exit 1
}

PATCHED=0
for f in "${FILES[@]}"; do
  path="$AOB/$f"
  if ! dexec "[[ -f $path ]]"; then
    echo "[$(date)] skip (missing): $f"
    continue
  fi
  if ! dexec "grep -q 'collections\.Iterable' $path"; then
    echo "[$(date)] ok (already patched): $f"
    continue
  fi
  # `import collections.abc` still binds `collections`, so other uses keep working
  dexec "sed -i -e 's/^import collections\$/import collections.abc/' \
                -e 's/collections\.Iterable/collections.abc.Iterable/g' $path"
  echo "[$(date)] patched: $f"
  PATCHED=1
done

if ((PATCHED)); then
  echo "[$(date)] Restart Splunk to load the patched code: docker restart $CONTAINER"
fi
