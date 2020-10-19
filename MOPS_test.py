# -*- coding: utf-8 -*-
import sys
import time
import logging
from termcolor import colored
import verboselogs
import coloredlogs as cl
import numpy as np   
from controlServer import canWrapper
""":obj:`~logging.Logger`: Main logger for this class"""
verboselogs.install()
logger = logging.getLogger("MOPS testing")
logformat='%(asctime)s - %(levelname)s - %(message)s'
cl.install(fmt=logformat, level=logging.INFO, isatty=True, milliseconds=True)
        
def test():
    NodeIds = [1]
    #Example (1): get node Id
    VendorId = wrapper.send_sdo_can(NodeIds[0], 0x1000,0,3000)
    print(f'Device type: {VendorId:03X}')
         
    #Example (2): Read channels 
    c_index = 0x2400
    n_channels = np.arange(3,35)
    c_subindices  = ["0","1","2","3","4","5","6","7","8","9","A","B","C","D","E","F",
                    "10","11","12","13","14","15","16","17","18","19","1A","1B","1C","1D","1E",
                    "20","21","22","23","24","25","26","27","28","29","2A","2B","2C","2D","2E","2F","30","31"]
    values = []
    for c_subindex in c_subindices: # Each i represents one channel
         value = wrapper.send_sdo_can(NodeIds[0], c_index,int(c_subindex,16),3000)
         values = np.append(values, value)
    n_channels = n_channels.tolist()
    
    for channel in n_channels:
        if values[n_channels.index(channel)] is not None:
             print("Channel %i = %0.3f "%(channel,values[n_channels.index(channel)]))
        else:
            print("Channel %i = %s "%(channel,"None"))
    time.sleep(1)
    wrapper.stop()        


if __name__=='__main__':
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate", set_channel =True)
    wrapper = canWrapper.CanWrapper(interface = "socketcan", set_channel =True)
    #wrapper = canWrapper.CanWrapper(interface = "Kvaser", set_channel =True)
    #wrapper.read_adc_channels()
    test()