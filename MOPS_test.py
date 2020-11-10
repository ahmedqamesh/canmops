# -*- coding: utf-8 -*-
import sys
import time
import logging
from termcolor import colored
import verboselogs
import coloredlogs as cl
import numpy as np   
from controlServer import canWrapper
def test():
    NodeIds = [1]
    #Example (1): get node Id
    VendorId = wrapper.send_sdo_can(NodeIds[0], 0x1000,0,3000)
    print(f'Device type: {VendorId:03X}')
         
    #Example (2): Read channels 
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
    time.sleep(1)
    wrapper.stop()        


if __name__=='__main__':
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate")
    wrapper = canWrapper.CanWrapper(interface = "socketcan")
    #wrapper = canWrapper.CanWrapper(interface = "Kvaser")
    #wrapper.read_adc_channels()
    test()