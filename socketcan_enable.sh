#!/bin/bash
# variables
echo "Initializing SocketCAN...."
# SocketCAN script
echo "CAN hardware OS drivers and config"
sudo -S modprobe can
#sudo -S modprobe systec_can
sudo -S modprobe can-dev
sudo -S modprobe can-raw
sudo -S modprobe can-bcm
sudo -S modprobe kvaser-usb
sudo -S lsmod | grep can
for bus in 0 1
do
	BITRATE=125000
	CHANNEL="can"
	SAMPLEPOINT=0.5
	SJW=4
	PHASESEG1=4
	PHASESEG2=3
	#while true; do cansend can1 600#DeadBeefDeadBeef; sleep 0.9; done
	#candump -ta any -c
	sudo ip link set can$bus type can restart
	echo "-------------------------------"
	echo "(1)Bringing the can$bus driver down if Up"
	sudo -S ip link set down $CHANNEL$bus
	echo "-------------------------------"
	echo "(2)Configuring can$bus with a bitrate of $BITRATE [Sample Point $SAMPLEPOINT]"	
	sudo -S ip link set $CHANNEL$bus type can bitrate $BITRATE sample-point $SAMPLEPOINT sjw $SJW phase-seg1 $PHASESEG1 phase-seg2 $PHASESEG2
	echo "-------------------------------"
	echo "(3)Bringing the  can$bus driver  up"
	sudo -S ip link set up $CHANNEL$bus
	ip -details link show $CHANNEL$bus
	echo "========================================================================"
done
echo "=========================Dumping CAN bus traffic ======================="
candump any -t A -x -c -e

