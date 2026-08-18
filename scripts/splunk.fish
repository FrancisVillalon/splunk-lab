#!/usr/bin/env fish

set VMX "/mnt/990pro/Work/vms/vmware-vms/splunk/splunk.vmx"

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
