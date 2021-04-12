# -*- coding: utf-8 -*-
import sys
import os
import time
import numpy as np
from controlServer.analysisUtils import AnalysisUtils
from controlServer.canWrapper   import CanWrapper
rootdir = os.path.dirname(os.path.abspath(__file__)) 
def test():
    # Define parameters
    NodeIds = [1,8]
    SDO_TX = 0x600
    SDO_RX = 580
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
        print(f'Device type: {VendorId:03X}')
    else:
        print(f'Cannot read the CAN message')

     #Example (3): Read all the ADC channels and Save it to a file
    wrapper.read_adc_channels(file ="MOPS_cfg.yml", #Yaml configurations
                              directory=rootdir+"/config", # direstory of the yaml file
                              nodeId = NodeIds[0], # Node Id
                              outputname = "adc_data_test", # Data file name
                              outputdir = rootdir + "/output_data", # # Data directory
                              n_readings = 20) # Number of Iterations
    wrapper.stop()        


if __name__=='__main__':
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate")
    wrapper = CanWrapper(interface = "socketcan")
    #wrapper = canWrapper.CanWrapper(interface = "Kvaser")
    test()