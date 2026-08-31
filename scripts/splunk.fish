#!/usr/bin/env fish

# Path to the Splunk VM. Override per machine:
#   set -x SPLUNK_VMX /path/to/splunk.vmx
set VMX (test -n "$SPLUNK_VMX"; and echo $SPLUNK_VMX; or echo "$HOME/vms/vmware-vms/splunk/splunk.vmx")

if not test -f "$VMX"
  echo "VMX not found: $VMX"
  echo "Set SPLUNK_VMX to the location of your splunk.vmx"
  exit 1
end

switch "$argv[1]"
  case start
    vmrun -T ws start "$VMX" nogui
    echo "VM started"
  case stop
    vmrun -T ws stop "$VMX" soft
    echo "VM stopped"
  case '*'
    echo "usage: (basename(status filename)) start|stop"
    exit 1
end
