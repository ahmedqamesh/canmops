#!/bin/bash
# variables
echo "Initializing SocketCAN...."
BITRATE=125000
CHANNEL="can"
#echo "Unloading all the kernel modules if on"
#sudo modprobe -r can_bcm
#sudo modprobe -r systec_can
#sudo modprobe -r can_raw
#sudo modprobe -r can
#sudo modprobe -r can_dev
# SocketCAN script
echo "CAN hardware OS drivers and config"
sudo -S modprobe can
sudo -S modprobe systec_can
sudo -S modprobe can-dev
sudo -S modprobe can-raw
sudo -S modprobe can-bcm
sudo -S modprobe kvaser-usb
sudo -S lsmod | grep can

for i in 0 1 
do
   echo "Bringing the can$i driver down if Up"
   sudo -S ip link set down $CHANNEL$i
	
	echo "Configuring the SocketCAN interface to bitrate of" $BITRATE
	sudo -S ip link set $CHANNEL$i type can bitrate $BITRATE
	
	echo "Bringing the  can$i driver  up"
	sudo -S ip link set up $CHANNEL$i
	ifconfig $CHANNEL$i
done
for i in 0 1
do 
	ifconfig $CHANNEL$i
done

