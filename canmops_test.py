# -*- coding: utf-8 -*-
import sys 
import os
import time
import numpy as np
import asyncio
from canmops.analysis_utils import AnalysisUtils
from canmops.can_wrapper_main   import CanWrapper
from canmops.logger_main   import Logger
import logging
rootdir = os.path.dirname(os.path.abspath(__file__)) 
sys.path.insert(0, rootdir+'/canmops')


log_format = '%(log_color)s[%(levelname)s]  - %(name)s -%(message)s'
log_call = Logger(log_format=log_format, name="CANMOPS Test", console_loglevel=logging.INFO, logger_file=False)
logger = log_call.setup_main_logger()

output_dir = rootdir+"/output_data/"
# All the can configurations of the CAN controller should be set first from $HOME/config/main_cfg.yml
async def test_can_wrapper():
    # Define parameters
    NodeIds = [3]
    SDO_TX = 0x600
    SDO_RX = 0x580
    index = 0x1000
    Byte0= cmd = 0x40 #Defines a read (reads data only from the node) dictionary object in CANOPN standard
    Byte1, Byte2 = index.to_bytes(2, 'little') # divide it into two groups(bytes) of 8 bits each
    Byte3 = subindex = 0
    #Example (1):Write/read CAN messages
    #write CAN message [read dictionary request from master to node]
    # await wrapper.write_can_message(cobid = SDO_TX + NodeIds[0], 
    #                           data = [Byte0,Byte1,Byte2,Byte3,0,0,0,0], 
    #                           flag=0, 
    #                           timeout=30)
    #
    # #Response from the node to master
    # cobid, data, dlc, flag, t , _ = wrapper.read_can_message()
    # print(f'ID: {cobid:03X}; Data: {data.hex()}, DLC: {dlc}')
    # #   #write sdo message
    # print('Writing example CAN Expedited read message ...')
   
    #Example (2): write/read SDO message
    VendorId = await wrapper.read_sdo_can_thread(nodeId=NodeIds[0], 
                                                   index=0x1000,
                                                   subindex=0,
                                                   SDO_TX=SDO_TX,
                                                   SDO_RX=SDO_RX,
                                                   cobid = SDO_TX+NodeIds[0])
    print(VendorId)
    if all(m is not None for m in VendorId):
        print(f'Device type: {VendorId[1]:03X}')
    else:
        print(f'Cannot read the SDO message')

     #Example (3): Read all the ADC channels and Save it to a file in the directory output_data
     # PS. To visualise the data, Users can use the file $HOME/test_files/plot_adc.py
    csv_writer,csv_file = wrapper.create_mopshub_adc_data_file(outputname = f"adc_data_trial_{NodeIds[0]}", # Data file name
                                                               outputdir =output_dir) # # Data directory)
    await wrapper.read_adc_channels(file ="mops_config.yml", #Yaml configurations
                              directory=rootdir+"/config_files", # direstory of the yaml file
                              nodeId = NodeIds[0], # Node Id
                              csv_writer =csv_writer,
                              csv_file = csv_file,
                              outputdir = output_dir) # Number of Iterations  
    
    #
    # await wrapper.read_mopshub_buses(file ="mops_config.yml", #Yaml configurations
    #                           bus_range =range(0,2),  
    #                           directory=rootdir+"/config_files", # direstory of the yaml file
    #                           nodeIds = NodeIds[0], # Node Id
    #                           outputname = "canmops_mopshub_32bus", # Data file name
    #                           outputdir = "/home/dcs/git/mopshub-sw-kcu102/output_data", # # Data directory
    #                           n_readings = 1) # Number of Iterations  
    #

    #Example (2): write/read SDO message [For Developers]
    # VendorId_sync = await wrapper.read_sdo_can_sync(nodeId=NodeIds[0], 
    #                                                index=0x1000,
    #                                                subindex=0,
    #                                                SDO_TX=SDO_TX,
    #                                                SDO_RX=SDO_RX,
    #                                                cobid = SDO_TX+NodeIds[0])
    # if all(m is not None for m in VendorId_sync):
    #     print(f'Device type: {VendorId[1]:03X}')
    # else:
    #     print(f'Cannot read the SDO message')    

    #Example (3): write/read SDO message [For Developers]
    # adc_value = await wrapper.read_sdo_can(nodeId=NodeIds[0], 
    #                                             index=0x1001,
    #                                             subindex=0,
    #                                             bus = 1)
    # if all(m is not None for m in adc_value):
    #     print(f'Device type: {adc_value[1]:03X}')
    # else:
    #     print(f'Cannot read the SDO message')  
    #

    wrapper.stop()  
    
if __name__=='__main__':
    channel = 0
    #wrapper = canWrapper.CanWrapper(interface = "AnaGate",channel = channel, load_config = True, trim_mode = True)
    wrapper = CanWrapper(interface = "socketcan",channel = channel, load_config = True, trim_mode = False)
    #wrapper =  CanWrapper(interface = "Kvaser",channel = channel, load_config = True, trim_mode = True)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    #wrapper.write_can_message(0x555, [0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA], flag=0, timeout=30)
    try:
        asyncio.ensure_future(test_can_wrapper())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.warning("KeyboardInterrupt caught: stopping the Asyncio Loop...")
    finally: 
        loop.run_until_complete(loop.shutdown_asyncgens())
        #loop.stop()
        loop.close()
        logger.warning('Stopping the Loop.')
        
    
    