echo "Setting up Can Interface"

echo "---------------------------------"

echo "Set down Interfaces"

sudo ip link set down can0

sudo ip link set down can1

echo "---------------------------------"

echo "Configure Interfaces"

sudo ip link set can0 type can bitrate $1 phase-seg1 $2 phase-seg2 $3 sjw $4 sample-point $5

sudo ip link set can1 type can bitrate $6 phase-seg1 $7 phase-seg2 $8 sjw $9 sample-point $10

echo "---------------------------------"

echo "Bring up Interfaces"

sudo ip link set up can0

sudo ip link set up can1

echo "---------------------------------"
