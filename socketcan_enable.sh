#!/bin/bash
# variables

echo "Initializing SocketCAN...."
for bus in 0 1
do
	#bus=1
	BITRATE=125000
	CHANNEL="can"
	SAMPLEPOINT=0.5
	SJW=4
	PHASESEG1=3
	PHASESEG2=4
	#while true; do cansend can1 600#DeadBeefDeadBeef; sleep 0.9; done
	echo "Setting the bus to a bitrate of $BITRATE [Sample Point $SAMPLEPOINT]"
	# SocketCAN script
	echo "CAN hardware OS drivers and config"
	sudo -S modprobe can
	sudo -S modprobe can-dev
	sudo -S modprobe can-raw
	sudo -S modprobe can-bcm
	sudo -S modprobe kvaser-usb
	sudo -S lsmod | grep can

	echo "Bringing the can$bus driver down if Up"
	sudo -S ip link set down $CHANNEL$bus
	
	echo "Configuring the SocketCAN interface to bitrate of" $BITRATE
	sudo -S ip link set $CHANNEL$bus type can bitrate $BITRATE sample-point $SAMPLEPOINT sjw $SJW phase-seg1 $PHASESEG1 phase-seg2 $PHASESEG2

	echo "Bringing the  can$i driver  up"
	sudo -S ip link set up $CHANNEL$bus
	ip -details link show $CHANNEL$bus
	echo "=========================================================="
done

