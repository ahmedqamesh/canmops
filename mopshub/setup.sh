sudo ip link set down can0

sudo ip link set down can1

sudo ip link set can0 type can bitrate 125000

sudo ip link set can1 type can bitrate 125000

#sudo ip link set can1 type can bitrate 125000 phase-seg1 7 phase-seg2 8 sjw 4 sample-point 0.4

sudo ip link set up can0

sudo ip link set up can1
