# -*- coding: utf-8 -*-
import sys
import os
import time
import numpy as np
from controlServer import canWrapper
def test():
    # Define parameters
    NodeIds = wrapper.get_nodeList()
    SDO_RX = 0x600
    index = 0x1000
    Byte0= cmd = 0x40 #Defines a read (reads data only from the node) dictionary object in CANOPN standard
    Byte1, Byte2 = index.to_bytes(2, 'little') # divide it into two groups(bytes) of 8 bits each
    Byte3 = subindex = 0
    #write CAN message [read dictionary request from master to node]
    wrapper.writeCanMessage(SDO_RX + NodeIds[0], [Byte0,Byte1,Byte2,Byte3,0,0,0,0], flag=0, timeout=30)
    #Response from the node to master
    cobid, data, dlc, flag, t = wrapper.read_can_message()
    print(f'ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}')
    #   #write sdo message
    print('Writing example CAN Expedited read message ...')
   
    #Example (1): get node Id
    
    VendorId = wrapper.send_sdo_can(NodeIds[0], 0x1000,0,3000)
    #print(f'Device type: {VendorId:03X}')
         
    c_index = 0x2400
    c_subindices  = ["1","2","3","4","5","6","7","8","9","A","B","C","D","E","F",
                    "10","11","12","13","14","15","16","17","18","19","1A","1B","1C","1D","1E","1F","20"]
    values = []
    for c_subindex in c_subindices: # Each i represents one channel
         value = wrapper.send_sdo_can(NodeIds[0], c_index,int(c_subindex,16),3000)
         values = np.append(values, value)

    for c_index in c_subindices:
        id = c_subindices.index(c_index)
        channel = int(c_index, 16)+2
        if values[id] is not None:
             print("Channel %i = %0.3f "%(channel,values[id]))
        else:
            print("Channel %i = %s "%(channel,"None"))
    wrapper.stop()        


if __name__=='__main__':
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate")
    wrapper = canWrapper.CanWrapper(interface = "socketcan")
    #wrapper = canWrapper.CanWrapper(interface = "Kvaser")
    #wrapper.read_adc_channels()
    test()