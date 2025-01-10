########################################################
"""
    This file is part of the MOPS-Hub project.
    Author: Ahmed Qamesh (University of Wuppertal)
    email: ahmed.qamesh@cern.ch  
    Date: 01.05.2020
"""
########################################################

# 01_sendReceiveSingleCanMsg.py
from canlib import canlib, Frame

__filter_canlib = [
            #{"can_id": 0x000, "can_mask": 0x7FF},  # Covers 0x000 to 0x1FF
            {"can_id": 0x500, "can_mask": 0x540},  # Covers 0x580 to 0x5FF
            # {"can_id": 0x600, "can_mask": 0x770},  # Covers 0x600 to 0x7FF
        ]
__ignore_ids = [{"can_id": 0x555, "can_mask": 0x7FF}]  
# https://github.com/Kvaser/canlib-samples/blob/master/Samples/Python/canlib.py
def set_channelConnection(channel=0,
                 openFlags=canlib.Open.EXCLUSIVE, #canlib.Open.ACCEPT_VIRTUAL,
                 bitrate=125000,#canlib.canBITRATE_125K,
                 outputControl=canlib.Driver.NORMAL,
                 sjw = 4,
                 tseg1 = 7,
                 tseg2 =8):
    canlib.initializeLibrary()
    ch = canlib.openChannel(channel)
    print("Using channel: %s, EAN: %s" % (canlib.ChannelData(channel).channel_name,canlib.ChannelData(channel).card_upc_no))
    ch.setBusOutputControl(outputControl)
    ch.setBusParams(freq = bitrate,sjw =sjw,tseg1 =tseg1, tseg2 = tseg2)
    ch.busOn() 
    for filt in __filter_canlib:
        canid = filt["can_id"]
        mask = filt["can_mask"]   
        ch.canSetAcceptanceFilter(canid,mask)
    print("canlib dll version:", canlib.dllversion())    
    return ch


def tearDownChannel(ch):
    ch.busOff()
    ch.close()

def read_sdo_can(SDO_TX =0x600,index = 0x1000 ,subindex =0 ,NodeIds = [3]):
    Byte0 = cmd = 0x40  # Defines a read (reads data only from the node) dictionary object in CANOPN standard
    Byte1, Byte2 = index.to_bytes(2, 'little')
    Byte3 = subindex = 0 
    frame = Frame(id_=SDO_TX + NodeIds[0], data=[Byte0, Byte1, Byte2, Byte3, 0, 0, 0, 0], dlc=8 , flags=canlib.MessageFlag.STD)
    ch0.write(frame)
    cobid, data, dlc, flag, t = (frame.id, frame.data, frame.dlc, frame.flags, frame.timestamp)
    print(f'(TX) ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}, Flag: {flag}, Time: {t}')
    print('Reading The Frame:')
    try:
        frame_ret = ch0.read(100)
        cobid_ret, data_ret, dlc_ret, flag_ret, t_ret = (frame_ret.id, frame_ret.data,
                                frame_ret.dlc, frame_ret.flags, frame_ret.timestamp)
        print(f'(RX) ID: {cobid_ret:03X}; Data: {data_ret.hex()}, DLC: {dlc_ret}, Flag: {flag_ret}, Time: {t_ret}')
        frame_ret = ch0.read(500)
        print('Searching any Frames')
        print(frame_ret)
    except (canlib.canNoMsg) as ex:
        pass
    except (canlib.canError) as ex:
        print(ex)
    print('---------------------------------------')
    return Frame

ch0 = set_channelConnection(channel=0)  

read_sdo_can(SDO_TX =0x600,index = 0x1000 ,subindex =0 ,NodeIds = [3])
read_sdo_can(SDO_TX =0x700,index = 0x1000 ,subindex =0 ,NodeIds = [3])

tearDownChannel(ch0)