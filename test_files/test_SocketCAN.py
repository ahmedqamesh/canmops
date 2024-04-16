#pip install python-can
from __future__ import print_function
import time
import os
import can
rootdir = os.path.dirname(os.path.abspath(__file__))
print('CAN hardware OS drivers and config for CAN0')
#os.system(". " + rootdir[:-10] + "analysis/socketcan_install.sh")
_filter = [
           {"can_id": 0x000, "can_mask": 0xFFF},  # Covers 0x000 to 0x1FF
           {"can_id": 0x200, "can_mask": 0x700},  # Covers 0x200 to 0x3FF
           {"can_id": 0x400, "can_mask": 0x7F4},  # Covers 0x400 to 0x554
           {"can_id": 0x560, "can_mask": 0x7F0},  # Covers 0x560 to 0x56F
           {"can_id": 0x570, "can_mask": 0x7F0},  # Covers 0x570 to 0x57F
           {"can_id": 0x580, "can_mask": 0x780},  # Covers 0x580 to 0x5FF
           {"can_id": 0x600, "can_mask": 0x700},  # Covers 0x600 to 0x7FF
           {"can_id": 0x701, "can_mask": 0x705},  # Covers 0x700 to 0x7FF
       ]       
bustype = ['socketcan',"pcan","ixxat","vector"]
channel = 'can0'

can.rc['interface'] = 'socketcan'
can.rc['channel'] = 'can0'
can.rc['bitrate'] = 125000
from can.interface import Bus
#bus = Bus()
def producer(id, N = None):
    """:param id: Spam the bus with messages including the data id."""
    bus = can.interface.Bus(bustype=bustype[0], channel=channel, bitrate=125000)
    bus.set_filters(_filter) 
    print(bus)
    msg = can.Message(arbitration_id= 0x703, data=[id, 0, 0, 0, 0, 0, 0, 0], is_extended_id= False) 
    bus.send(msg)
    message = bus.recv(1.0)
    cobid, data, dlc, flag, t = message.arbitration_id, message.data, message.dlc, message.is_extended_id, message.timestamp
    print(f'ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}')
    # for i in range(N):
    #     msg = can.Message(arbitration_id= 0x603, data=[id, i, 16, 1, 0, 0, 0, 0], is_extended_id= False) 
    #     print(msg)
    #     #for msg in bus:
    #     #    print("{X}: {}".format(msg.arbitration_id, msg.data))
    #
    #     #notifier = can.Notifier(bus, [can.Logger("recorded.log"), can.Printer()])
    #     try:
    #         bus.send(msg)
    #         print("Message sent on {}".format(bus.channel_info))
    #     except can.CanError:
    #         print("Message NOT sent")
    #
    #     message = bus.recv(1.0)
    #     #listener(message)
    #     if message is None:
    #         print('Timeout occurred, no message.')
    #     else:
    #         cobid, data, dlc, flag, t = message.arbitration_id, message.data, message.dlc, message.is_extended_id, message.timestamp
    #         print(f'ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}')
    #
    # time.sleep(1)

if __name__ == '__main__':
    pass    
    producer(64, N = 2)


    