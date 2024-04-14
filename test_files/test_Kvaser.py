# 01_sendReceiveSingleCanMsg.py
from canlib import canlib, Frame


# https://github.com/Kvaser/canlib-samples/blob/master/Samples/Python/canlib.py
def set_channelConnection(channel=0,
                 openFlags=canlib.Open.EXCLUSIVE, #canlib.Open.ACCEPT_VIRTUAL,
                 bitrate=111111,#canlib.canBITRATE_125K,
                 outputControl=canlib.Driver.NORMAL,
                 sjw = 4,
                 tseg1 = 5,
                 tseg2 =6):
    ch = canlib.openChannel(channel, openFlags)
    print("Using channel: %s, EAN: %s" % (
        canlib.ChannelData(channel).channel_name,
        canlib.ChannelData(channel).card_upc_no))
    ch.setBusOutputControl(outputControl)
    ch.setBusParams(freq = bitrate,sjw =sjw,tseg1 =tseg1, tseg2 = tseg2)
    ch.busOn()
    return ch


def tearDownChannel(ch):
    ch.busOff()
    ch.close()

print("canlib dll version:", canlib.dllversion())
ch0 = set_channelConnection(channel=0)
NodeIds = [1]
SDO_TX = 0x600
index = 0x1000
Byte0 = cmd = 0x40  # Defines a read (reads data only from the node) dictionary object in CANOPN standard
Byte1, Byte2 = index.to_bytes(2, 'little')
Byte3 = subindex = 0 
frame = Frame(id_=SDO_TX + NodeIds[0], data=[Byte0, Byte1, Byte2, Byte3, 0, 0, 0, 0], flags=canlib.MessageFlag.EXT, dlc=8)
ch0.write(frame)
while True:
    try:
        msgId, msg, dlc, flg, time = ch0.read()
        print("%9d  %9d  0x%02x  %d  %s" % (msgId, time, flg, dlc, msg))
        for i in range(dlc):
            msg[i] = (msg[i] + 1) % 256
        print(msg, ''.join('{:02x}'.format(x) for x in msg))
        cobid, data, dlc, flag, t = (frame.id, frame.data, frame.dlc, frame.flags, frame.timestamp)
        print(f'ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}')
        break
    except (canlib.canNoMsg) as ex:
        pass
    except (canlib.canError) as ex:
        print(ex)
        
tearDownChannel(ch0)
