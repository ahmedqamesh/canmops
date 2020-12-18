#!/bin/bash
# variables 
#check the bus type can or virtual.
if [ $5 == "can" ]
then
	echo "Cofiguring drivers"
	sudo -S modprobe can
	sudo -S modprobe can-dev
	sudo -S modprobe can-raw
	sudo -S modprobe can-bcm
	sudo -S modprobe kvaser-usb
	sudo -S lsmod | grep can
 
	echo "Bringing the $4 driver down if Up"
	sudo -S ip link set down $4

	echo "Configuring the SocketCAN interface to bitrate of $1 [Sample Point $2, SJW $3]"
	sudo -S ip link set $4 type can bitrate $1 sample-point $2 sjw $3

	echo "Bringing the  $4 driver  up"
	sudo -S ip link set up $4

	echo "Getting $4 Bus informations"
	ip -details link show $4

fi

if [ $5 == "vcan" ]
then
	echo "Configuring Virtual Interface $4"
	sudo -S modprobe vcan 
	echo "Removing $4 interface if exist"
	sudo ip link del $4

	echo "Adding $4 to iproute2 ip utility"
    	sudo ip link add dev $4 type vcan
	
	echo "Getting $4 Bus informations"
	ip -details link show $4

fi 

if [ $5 == "restart" ]
#An automatic bus-off recovery if too many errors occurred on the CAN bus
then
	echo "Restarting the Bus"
	sudo ip link set canX type can restart-ms 100
fi 



