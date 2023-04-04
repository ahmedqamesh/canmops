# -*- coding: utf-8 -*-
import sys
import os
import time
import numpy as np
import asyncio
from canmops.analysis_utils import AnalysisUtils
from canmops.can_wrapper_main   import CanWrapper
rootdir = os.path.dirname(os.path.abspath(__file__)) 
# All the can configurations of the CAN controller should be set first from $HOME/config/main_cfg.yml
async def test_can_wrapper():
    # Define parameters
    NodeIds = [0,1]
    SDO_TX = 0x600
    SDO_RX = 0x580
    index = 0x1000
    Byte0= cmd = 0x40 #Defines a read (reads data only from the node) dictionary object in CANOPN standard
    Byte1, Byte2 = index.to_bytes(2, 'little') # divide it into two groups(bytes) of 8 bits each
    Byte3 = subindex = 0
    
    #Example (1):Write/read CAN messages
    #write CAN message [read dictionary request from master to node]
    await wrapper.read_mopshub_buses(bus_range = [1], 
                                     file ="mops_config.yml", #Yaml configurations
                                     directory=rootdir+"/config_files", # direstory of the yaml file
                                     nodeId = NodeIds, # Node Id
                                     outputname = "mopshub_data_32", # Data file name
                                     outputdir = rootdir +"/output_data", # # Data directory
                                     n_readings = 50) # Number of Iterations
    wrapper.stop()  


        
if __name__=='__main__':
    channel = 0
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate",channel = channel, load_config = True)
    wrapper = CanWrapper(interface = "socketcan",channel = channel, load_config = True)
    #wrapper =  CanWrapper(interface = "Kvaser",channel = channel, load_config = True)
    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(test_can_wrapper())
        loop.run_forever()
    finally: 
        #can_config.stop_channel(channel)
        #can_config.stop()
        loop.close()

    
    