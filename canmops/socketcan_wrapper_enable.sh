#!/bin/bash
# variables 
#check the bus type can or virtual.
if [ $5 == "can" ]
then
	
	sudo -S modprobe can
	now=$(date +'%Y-%m-%d'" %T")
	echo -e "\e[1;31m$now -  [NOTICE   ] -Cofiguring CAN drivers\e[0m"
	sudo -S modprobe can-dev
	sudo -S modprobe can-raw
	sudo -S modprobe can-bcm
	sudo -S modprobe kvaser-usb
	#sudo -S lsmod | grep can
 	now=$(date +'%Y-%m-%d'" %T")
	echo -e "\e[1;31m$now -  [NOTICE   ] - Bringing the $4 driver down if Up\e[0m"
	sudo -S ip link set down $4
	now=$(date +'%Y-%m-%d'" %T")
	echo -e "\e[1;31m$now -  [NOTICE   ] - Configuring the SocketCAN interface to bitrate of $1 [Sample Point $2, SJW $3, tseg1 $6 tseg2 $7] \e[0m"
	sudo -S ip link set $4 type $5 bitrate $1 sample-point $2 sjw $3 phase-seg1 $6 phase-seg2 $7
	now=$(date +'%Y-%m-%d'" %T")
	echo -e "\e[1;31m$now -  [NOTICE   ] - Bringing the  $4 driver  up \e[0m"
	sudo -S ip link set up $4
	now=$(date +'%Y-%m-%d'" %T")
	echo -e "\e[1;31m$now -  [NOTICE   ] - Getting $4 Bus informations \e[0m"
	ip -details link show $4

fi

if [ $5 == "vcan" ]
then
	echo "\e[1;31m$now -  [NOTICE   ] - Configuring Virtual Interface $4 \e[0m"
	sudo -S modprobe vcan 
	now=$(date +'%Y-%m-%d'" %T")
	echo "\e[1;31m$now -  [NOTICE   ] - Removing $4 interface if exist \e[0m"
	sudo ip link del $4
	now=$(date +'%Y-%m-%d'" %T")
	echo "\e[1;31m$now -  [NOTICE   ] - Adding $4 to iproute2 ip utility \e[0m"
    	sudo ip link add dev $4 type vcan
	now=$(date +'%Y-%m-%d'" %T")
	echo "\e[1;31m$now -  [NOTICE   ] - Getting $4 Bus informations \e[0m"
	ip -details link show $4

fi 

if [ $5 == "restart" ]
#An automatic bus-off recovery if too many errors occurred on the CAN bus
then	
	now=$(date +'%Y-%m-%d'" %T")
	echo "\e[1;31m$now -  [NOTICE   ] - Restarting $4 Bus \e[0m"
	sudo ip link set $4 type can restart
fi 



