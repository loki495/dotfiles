#!/bin/sh
NEXTLINE=0
FIND=""
for I in `file /boot/vmlinuz*`; do
  if [ ${NEXTLINE} -eq 1 ]; then
    FIND="${I}"
    NEXTLINE=0
   else
    if [ "${I}" = "version" ]; then NEXTLINE=1; fi
  fi
done
if [ ! "${FIND}" = "" ]; then
  CURRENT_KERNEL=`uname -r`
  echo "Installed: ${CURRENT_KERNEL}"
  echo "Found: ${FIND}"
  if [ ! "${CURRENT_KERNEL}" = "${FIND}" ]; then
    echo "Boot required"
  else
    echo "Reboot not needed"
  fi
fi
