#!/bin/bash
# variables
n_buses=1
echo "Initializing SocketCAN...."
BITRATE=114285
CHANNEL="can"
SAMPLEPOINT=0.5
echo "Setting the bus to a bitrate of $BITRATE [Sample Point $SAMPLEPOINT]"

#echo "Unloading all the kernel modules if on"
#sudo modprobe -r can_bcm
#sudo modprobe -r systec_can
#sudo modprobe -r can_raw
#sudo modprobe -r can
#sudo modprobe -r can_dev
# SocketCAN script
echo "CAN hardware OS drivers and config"
sudo -S modprobe can
#sudo -S modprobe systec_can
sudo -S modprobe can-dev
sudo -S modprobe can-raw
sudo -S modprobe can-bcm
sudo -S modprobe kvaser-usb
sudo -S lsmod | grep can

for i in 0  
do
   echo "Bringing the can$i driver down if Up"
   sudo -S ip link set down $CHANNEL$i
	
	echo "Configuring the SocketCAN interface to bitrate of" $BITRATE
	sudo -S ip link set $CHANNEL$i type can bitrate $BITRATE sample-point $SAMPLEPOINT
	
	echo "Bringing the  can$i driver  up"
	sudo -S ip link set up $CHANNEL$i
	ifconfig $CHANNEL$i
done
for i in range 0 $n_buses 
do 
	ip -details link show $CHANNEL$i
done

