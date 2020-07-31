# -*- coding: utf-8 -*-
import sys
import os
import analib
import time
import logging
import numpy as np
from controlServer import canWrapper
def test():
    # Define parameters
    NodeIds = wrapper.get_nodeList()
    interface =wrapper.get_interface()
    SDO_RX = 0x600
    index = 0x1000
    Byte0= cmd = 0x40 #Defines a read (reads data only from the node) dictionary object in CANOPN standard
    Byte1, Byte2 = index.to_bytes(2, 'little') # divide it into two groups(bytes) of 8 bits each
    Byte3 = subindex = 0
    #write CAN message [read dictionary request from master to node]
    while True:
        wrapper.writeCanMessage(SDO_RX + NodeIds[0], [Byte0,Byte1,Byte2,Byte3,0,0,0,0], flag=0, timeout=30)
        #Response from the node to master
        cobid, data, dlc, flag, t = wrapper.read_can_message()
        print(f'ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}')
        time.sleep(3)
    #   #write sdo message
    print('Writing example CAN Expedited read message ...')
   
    #Example (1): get node Id
    VendorId = wrapper.sdoRead(NodeIds[0], 0x1000,0,3000)
    
    print(f'Device type: {VendorId:03X}')
         
    #Example (2): Read channels 
    n_channels = np.arange(3,35)
    c_subindices  = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F",
                    "10","11","12","13","14","15","16","17","18","19","1A","1B","1C","1D","1E",
                    "20","21","22","23","24","25","26","27","28","29","2A","2B","2C","2D","2E","2F","30","31"]
    values = []
    for c_subindex in c_subindices: # Each i represents one channel
         c_index = 0x2400
         value = wrapper.sdoRead(NodeIds[0], c_index,int(c_subindex,16),3000)
         values = np.append(values, value)
    n_channels = n_channels.tolist()
    for channel in n_channels:
        if values[n_channels.index(channel)] is not None:
             print("Channel %i = %0.3f "%(channel,values[n_channels.index(channel)]))
        else:
            print("Channel %i = %s "%(channel,"None"))
    wrapper.stop()        


if __name__=='__main__':
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate", set_channel =True)
    #wrapper = canWrapper.CanWrapper(interface = "socketcan", set_channel =True)
    wrapper = canWrapper.CanWrapper(interface = "Kvaser", set_channel =True)
    #wrapper.read_adc_channels()
    test()