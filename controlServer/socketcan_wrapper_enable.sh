#!/bin/bash
# variables 
CHANNEL="can"
echo "Initializing SocketCAN...."
echo "Setting the bus to a bitrate of $1 [Sample Point $2, SJW $3]"
echo "CAN hardware OS drivers and config"
sudo -S modprobe can
#sudo -S modprobe systec_can
sudo -S modprobe can-dev
sudo -S modprobe can-raw
sudo -S modprobe can-bcm
sudo -S modprobe kvaser-usb
sudo -S lsmod | grep can

echo "Bringing the can$4 driver down if Up"
sudo -S ip link set down $CHANNEL$4

echo "Configuring the SocketCAN interface to bitrate of" $1
sudo -S ip link set $CHANNEL$4 type can bitrate $1 sample-point $2 sjw $3

echo "Bringing the  can$4 driver  up"
sudo -S ip link set up $CHANNEL$4

ip -details link show $CHANNEL$4


