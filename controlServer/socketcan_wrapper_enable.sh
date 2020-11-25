#!/bin/bash
# variables
CHANNEL="can"
echo "Initializing SocketCAN...."
echo "Setting the bus to a bitrate of $1 [Sample Point $2]"
echo "CAN hardware OS drivers and config"
sudo -S modprobe can
#sudo -S modprobe systec_can
sudo -S modprobe can-dev
sudo -S modprobe can-raw
sudo -S modprobe can-bcm
sudo -S modprobe kvaser-usb
sudo -S lsmod | grep can

echo "Bringing the can$3 driver down if Up"
sudo -S ip link set down $CHANNEL$3

echo "Configuring the SocketCAN interface to bitrate of" $1
sudo -S ip link set $CHANNEL$3 type can bitrate $1 sample-point $2

echo "Bringing the  can$3 driver  up"
sudo -S ip link set up $CHANNEL$3
ifconfig $CHANNEL$3
ip -details link show $CHANNEL$3


