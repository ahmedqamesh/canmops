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
def test():
    # Define parameters
    NodeIds = [1,8]
    SDO_TX = 0x600
    SDO_RX = 0x580
    index = 0x1000
    Byte0= cmd = 0x40 #Defines a read (reads data only from the node) dictionary object in CANOPN standard
    Byte1, Byte2 = index.to_bytes(2, 'little') # divide it into two groups(bytes) of 8 bits each
    Byte3 = subindex = 0
    
    #Example (1):Write/read CAN messages
    #write CAN message [read dictionary request from master to node]
    wrapper.write_can_message(cobid = SDO_TX + NodeIds[0], 
                              data = [Byte0,Byte1,Byte2,Byte3,0,0,0,0], 
                              flag=0, 
                              timeout=30)
    
    #Response from the node to master
    cobid, data, dlc, flag, t , _ = wrapper.read_can_message()
    print(f'ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}')
    #   #write sdo message
    print('Writing example CAN Expedited read message ...')
   
    #Example (2): write/read SDO message
    VendorId = wrapper.read_sdo_can_thread(nodeId=NodeIds[0], 
                                                   index=0x1000,
                                                   subindex=0,
                                                   timeout=3000,
                                                   SDO_TX=SDO_TX,
                                                   SDO_RX=SDO_RX,
                                                   cobid = SDO_TX+NodeIds[0])
    
    if all(m is not None for m in VendorId):
        print(f'Device type: {VendorId[1]:03X}')
    else:
        print(f'Cannot read the SDO message')

     #Example (3): Read all the ADC channels and Save it to a file in the directory output_data
     # PS. To visualise the data, Users can use the file $HOME/test_files/plot_adc.py
    wrapper.read_adc_channels(file ="MOPS_cfg.yml", #Yaml configurations
                              directory=rootdir+"/config", # direstory of the yaml file
                              nodeId = NodeIds[0], # Node Id
                              outputname = "adc_data_trial", # Data file name
                              outputdir = rootdir + "/output_data", # # Data directory
                              n_readings = 1) # Number of Iterations
    wrapper.stop()        


if __name__=='__main__':
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate",channel = 0)
    wrapper = CanWrapper(interface = "socketcan",channel = 0)
    #wrapper =  CanWrapper(interface = "Kvaser",channel = 0)
    test()