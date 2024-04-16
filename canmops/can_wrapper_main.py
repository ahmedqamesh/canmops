#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This module provides a class for a CAN wrapper for the ADC channels of the MOPS Chip.
It also provides a function for using this server as a command line tool.
Note
----
:Author: Ahmed Qamesh
:Contact: ahmed.qamesh@cern.ch
:Organization: Bergische Universität Wuppertal
"""
# Standard library modules
#from __future__ import annotations
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from configparser import ConfigParser
from typing import *
import time
import datetime
import keyboard
import atexit
#import numba
import sys
import os
from threading import Thread, Event, Lock
import subprocess
import threading
import numpy as np
#from pip._internal.cli.cmdoptions import pre
#from lxml.html.builder import PRE
from socket import socket
from asyncio.tasks import sleep
try:
    from .analysis import Analysis
    from .logger_main import Logger
    from .analysis_utils import AnalysisUtils
    from .watchdog_can_interface import WATCHCan
except (ImportError, ModuleNotFoundError):
    from analysis import Analysis
    from logger_main   import Logger
    from analysis_utils import AnalysisUtils
    from watchdog_can_interface import WATCHCan
# Third party modules
from collections import deque, Counter
from tqdm import tqdm
import ctypes as ct
import logging
import csv
import asyncio
import queue
from bs4 import BeautifulSoup #virtual env
from typing import List, Any
from random import randint

logger   = Logger(name = " Lib Check ",console_loglevel=logging.INFO, logger_file = False).setup_main_logger()


try:
    import can
    try:
        from .can_bus_config import can_config
        from .can_thread_reader import READSocketcan
    except (ImportError, ModuleNotFoundError):
        from can_bus_config import can_config
        from can_thread_reader import READSocketcan          
except: logger.warning("SocketCAN Package is not installed....."+"[Please ignore the warning if No SocketCAN drivers used.]")

# Import canlib for Kvaser
try:
    from canlib import canlib, Frame
    from canlib.canlib.exceptions import CanGeneralError
    #from canlib.canlib import ChannelData
except: logger.warning("Canlib  Package is not installed....."+"[Please ignore the warning if CANLib packages are not required (in case SocketCAN is used)]")
     
# Import analib for AnaGate
try: import analib
except: logger.warning("AnaGate Package is not installed....."+"[Please ignore the warning if No AnaGate controllers used.]")

rootdir = os.path.dirname(os.path.abspath(__file__))
config_dir = "config_files/"
lib_dir = rootdir[:-8]
log_dir = os.path.join(lib_dir, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logger_file = os.path.join(log_dir, time.strftime('%Y-%m-%d_%H-%M-%S_CAN_Wrapper.log'))
log_call = Logger(name = "CAN Wrapper",console_loglevel=logging.INFO, logger_file = False)

class CanWrapper(object):#READSocketcan):#Instead of object

    def __init__(self,
                 interface=None, channel=None,
                 bitrate=None, samplePoint=None,
                 sjw=None,ipAddress=None,
                 tseg1 = None, tseg2 = None,
                 nodeid =None,
                 trim_mode =None,
                 file_loglevel=logging.INFO, 
                 load_config = False, 
                 console_loglevel=logging.INFO):
       
        super(CanWrapper, self).__init__()  # super keyword to call its methods from a subclass:        
        #Initialize a watchdog (to be done)
        if interface =="socketcan":
            WATCHCan.__init__(self)
        else:
            pass
        #self.start()
        #Begin a thread settings (to be done)
        self.sem_read_block = threading.Semaphore(value=0)
        self.sem_recv_block = threading.Semaphore(value=0)
        self.sem_config_block = threading.Semaphore()
        
        """:obj:`~logging.Logger`: Main logger for this class"""
        log_file = Logger(name = "CAN Wrapper",console_loglevel=logging.INFO, logger_file = False)
        #self.logger = Logger().setup_main_logger(name = "CAN Wrapper",console_loglevel=console_loglevel, logger_file = False)
        self.logger = log_call.setup_main_logger()
        self.logger_file = log_file.setup_file_logger(logger_file = logger_file)
        
        self.logger.info(f'Existing logging Handler: {logger_file}')
        if load_config:
           # Read CAN settings from a file 
            self.__channels, self.__ipAddress,self.__bitrate, self.__samplePoint,\
            self.__sjw, self.__tseg1, self.__tseg2, self.__can_channels, _canSettings =   self.load_settings_file(interface = interface, channel = channel)
            self.can_0_settings = {}     
            self.can_1_settings = {}       
            for ch in self.__can_channels:
                for value in _canSettings[ch]:
                    if ch == self.__can_channels[0]:
                        self.can_0_settings[f'{value}'] = _canSettings[ch][f'{value}']
                    else:
                        if ch == self.__can_channels[1]:
                            self.can_1_settings[f'{value}'] = _canSettings[ch][f'{value}']
        else:
            pass

        self.__filter = [
                    {"can_id": 0x000, "can_mask": 0x700},  # Covers 0x000 to 0x1FF
                    {"can_id": 0x200, "can_mask": 0x700},  # Covers 0x200 to 0x3FF
                    {"can_id": 0x400, "can_mask": 0x7F4},  # Covers 0x400 to 0x554
                    {"can_id": 0x560, "can_mask": 0x7F0},  # Covers 0x560 to 0x56F
                    {"can_id": 0x570, "can_mask": 0x7F0},  # Covers 0x570 to 0x57F
                    {"can_id": 0x580, "can_mask": 0x780},  # Covers 0x580 to 0x5FF
                    {"can_id": 0x600, "can_mask": 0x700},  # Covers 0x600 to 0x7FF
                    {"can_id": 0x701, "can_mask": 0x705},  # Covers 0x700 to 0x7FF
                ]
        self.__ignore_ids = {0x555}    
        # Initialize default arguments
        """:obj:`str` : Internal attribute for the interface"""
        self.__interface = interface
                
        """:obj:`int` : Internal attribute for the bit rate"""
        if bitrate is not None:
            self.__bitrate = bitrate

        if samplePoint is not None:
            self.__samplepoint = samplePoint
            
        if sjw is not None:
            self.__sjw = sjw

        if tseg1 is not None:
            self.__tseg1 = tseg1
        
        if tseg2 is not None:
            self.__tseg2 = tseg2

        """:obj:`int` : Internal attribute for the IP Address"""  
        if ipAddress is not None:
             self.__ipAddress = ipAddress
              
        # Initialize library and set connection parameters
        self.__cnt = Counter()

        """:obj:`bool` : If communication is established"""
        self.__busOn0 = False  
        self.__busOn1 = False
        """:obj:`int` : Internal attribute for the channel index"""
        if channel is not None:
            self.__channel = channel
        self.logger_file.info("Updating settings channel:%s bitrate:%s  sjw:%s tseg1:%s tseg2:%s IP Address:%s"%(self.__channel,
                                                                                                               self.__bitrate, 
                                                                                                               self.__sjw, 
                                                                                                               self.__tseg1, 
                                                                                                               self.__tseg2,
                                                                                                               self.__ipAddress))
        """Internal attribute for the |CAN| channel"""
        self.ch0= None
        self.ch1 = None
        #Setup CAN
        self.can_setup(channel = self.__channel, interface = self.__interface)
        self.set_channel_connection(interface=self.__interface)            
        """Internal attribute for the |CAN| channel"""
        self.__busOn0 = True
        self.__busOn1 = True
        self.__canMsgQueue = deque([], 100)  # queue with a size of 100 to queue all the messages in the bus
        self.__pill2kill = Event()
        self.__lock = Lock()
        self.__kvaserLock = Lock()
        self.logger.success('....Done Initialization!')
        self.logger_file.success('....Done Initialization!')
        if trim_mode == True:
            asyncio.run(self.trim_nodes(channel==channel))    
        
        if nodeid is not None:
            asyncio.run(self.confirm_nodes(nodeIds = [str(nodeid)]))
            self.stop() 
            
    def __str__(self):
        if self.__interface == 'Kvaser':
            num_channels = canlib.getNumberOfChannels()
            for ch in range(0, num_channels):
                chdata = canlib.ChannelData(ch)
                chdataname = chdata.channel_name #device_name
                #chdata_EAN = chdata.card_upc_no
                #chdata_serial = chdata.card_serial_no
                self.logger_file.info(f'{self.__interface}:Using {chdataname}, Bitrate:{self.__bitrate}') 
                return f'Using {chdataname}, Bitrate:{self.__bitrate}'
        if self.__interface == 'AnaGate':
            self.logger_file.info(f'{self.__interface}:Using {self.ch0}, Bitrate:{self.__bitrate}') 
            return f'Using {self.ch0}, Bitrate:{self.__bitrate}'
        else:
            if self.ch0 != None:
                self.logger_file.info(f'{self.__interface}: Using {self.ch0.channel_info}, Bitrate:{self.__bitrate}') 
                return f'Using {self.ch0.channel_info}, Bitrate:{self.__bitrate}'
            if self.ch1 != None:
                self.logger_file.info(f'{self.__interface}: Using {self.ch1.channel_info}, Bitrate:{self.__bitrate}') 
                return f'Using {self.ch1.channel_info}, Bitrate:{self.__bitrate}'
                    
    async def  confirm_nodes(self, channel=0, timeout=None,nodeIds = ["1","2"], trim = False, busId = 0):
        _nodeIds = nodeIds 
        self.set_nodeList(_nodeIds)
        if trim: pass
        else:
            self.logger.notice('Checking MOPS status ...')
            for nodeId in _nodeIds: 
                # Send the status message
                cobid_TX = 0x700 + int(nodeId,16)
                #data_point, reqmsg, requestreg, respmsg,responsereg , status, errorResponse = await self.read_sdo_can(nodeId=int(nodeId,16), index=0x1000, subindex=0x0, bus =0)
                data_point, reqmsg, requestreg, respmsg,responsereg , status, errorResponse = await self.read_sdo_can(nodeId=int(nodeId,16), SDO_TX=0x700, SDO_RX=0x700, index=0x0000, subindex=0x0, bus =0)
                if data_point is None: self.logger.error(f'Connection to MOPS with nodeId {nodeId} in channel {channel} failed')
                else: self.logger.info(f'Connection to MOPS with nodeId {nodeId} in channel {channel} has been '
                                         f'verified.')
                   

    async def trim_nodes(self, channel=0, timeout=None):
        self.logger.notice(f'Start Trimming MOPS in channel {channel} ...')
        # Send the trim  message
        for i in np.arange(0,50): 
            await self.write_can_message(0x555, [0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA], flag=0)
        # receive the message
        time.sleep(1)
        readCanMessage = await self.read_can_message()
        response = all(x is None for x in readCanMessage) 
        if not response:
            cobid_RX, data, dlc, flag, t, _ = readCanMessage
            self.dumpMessage(cobid_RX, data, dlc, flag, t)
            if data[0] == 0x85 or data[0] == 0x05:
                self.logger.info(f'Trimming MOPS in channel {channel} has been '
                                 f'verified.')
            else:
                self.logger.error(f'Trimming MOPS in channel {channel} has been '
                                  f'failed.')
        else:
            self.logger.error(f'Trimming MOPS in channel {channel} has been '
                              f'failed.')                

    def load_settings_file(self, interface = None, channel = None):
        """Load all the information related to the hardware 
        Parameters
        ----------
        interface : str: either socket, kvaser or anagate
        channel: int: define the channel number 
        """
        filename = lib_dir + config_dir + interface + "_CANSettings.yml"
        filename = os.path.join(lib_dir, config_dir + interface + "_CANSettings.yml")
        test_date = time.ctime(os.path.getmtime(filename))
        # Load settings from CAN settings file
        self.logger.notice("Loading CAN settings from the file %s produced on %s" % (filename, test_date))
        try:
            _canSettings = AnalysisUtils().open_yaml_file(file=config_dir + interface + "_CANSettings.yml", directory=lib_dir)
            _can_channels = list(_canSettings)[1:]#['channel0', 'channel1']
            _channel = _canSettings['channel' + str(channel)]["channel"]
            _ipAddress = _canSettings['channel' + str(channel)]["ipAddress"]
            _bitrate = _canSettings['channel' + str(channel)]["bitrate"]
            _sample_point = _canSettings['channel' + str(channel)]["samplePoint"]
            _sjw = _canSettings['channel' + str(channel)]["SJW"]
            _tseg1 = _canSettings['channel' + str(channel)]["tseg1"]
            _tseg2 = _canSettings['channel' + str(channel)]["tseg2"]
            self.logger.info("Found channel:%s with bitrate:%s, sample point:%s, SJW:%s, tesg1:%s, tseg2:%s" %(str(channel),_bitrate,_sample_point, _sjw,_tseg1, _tseg2)) 
            return _channel,_ipAddress, _bitrate,_sample_point, _sjw,_tseg1, _tseg2, _can_channels, _canSettings
        except:
          self.logger.error("Channel %s settings for %s interface Not found" % (str(channel),interface)) 
          return None,None, None,None, None,None, None , None, None
                                      
    def set_channel_connection(self, interface=None):
        """
        Set the internal attribute for the |CAN| channel
        The function is important to initialise the channel
        
        Parameters
            ----------
            interface: String
        """
        self.logger.notice('Going in \'Bus On\' state ...')
        self.logger_file.notice('Going in \'Bus On\' state ...')
        try:
            if interface == 'Kvaser':
                
                self.ch0= canlib.openChannel(int(self.__channel), canlib.canOPEN_ACCEPT_VIRTUAL) 
                self.ch0.setBusOutputControl(canlib.Driver.NORMAL)  # New from tutorial
                self.ch0.setBusParams(freq = int(self.__bitrate), sjw =int(self.__sjw), tseg1=int(self.__tseg1), tseg2=int(self.__tseg2))
                self.ch0.busOn()
                self.__canMsgThread = Thread(target=self.read_can_message_thread)
            elif interface == 'AnaGate':
                self.ch0= analib.Channel(ipAddress=self.__ipAddress, port=self.__channel, baudrate=self.__bitrate)
            elif interface == 'virtual':
                channel = "vcan" + str(self.__channel)
                self.ch0= can.interface.Bus(bustype="socketcan", channel=channel)
                             
            else:
                channel = "can" + str(self.__channel)
                self.ch0= can.interface.Bus(bustype=interface, channel=channel, bitrate=self.__bitrate) 
                self.ch0.set_filters(self.__filter) 
            self.logger.success(str(self))      
        except Exception:
            self.logger.error("TCP/IP or USB socket error in %s interface" % interface)
            self.logger_file.error("Channel definition is %s with interface %s " % (self.ch0,interface)) 
            sys.exit(1)
            #self.logger.success(str(self))        
    
    def start_channel_connection(self, interface =None):
        """
        The function will start the channel connection when sending SDO CAN message
        Parameters
        ----------
        :interface: 'String'
    
        Returns
        -------
        :_ch: obj:`int`

        :_ch:`None`
            In case of errors
        """
        self.logger.notice('Starting CAN Connection ...')
        _interface = self.get_interface()
        if _interface == 'Kvaser':
            if not self.__busOn0:
                self.logger.notice('Going in \'Bus On\' state ...')
                self.__busOn0 = True
            #self.ch0.busOn()
        if _interface == 'AnaGate':
            if not self.ch0.deviceOpen:
                self.logger.notice('Reopening AnaGate CAN interface')
                self.ch0.openChannel() 
            if self.ch0.state != 'CONNECTED':
                self.logger.notice('Restarting AnaGate CAN interface.')
                self.ch0.restart()
            # self.__cbFunc = analib.wrapper.dll.CBFUNC(self._anagateCbFunc())
            # self.ch0.setCallback(self.__cbFunc)
        else:# SocketCAN
            pass
        self.__canMsgThread = Thread(target=self.read_can_message_thread)
        self.__canMsgThread.start()

    async def read_mopshub_buses(self, bus_range, file, directory , nodeIds, outputname, outputdir, n_readings):
        SDO_TX=0x600 
        SDO_RX=0x580
        index = 0x1000
        self.logger.info(f'Reading ADC channels of Mops with ID {nodeId}')
        dev = AnalysisUtils().open_yaml_file(file=file, directory=directory)
        # yaml file is needed to get the object dictionary items
        _adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        _adc_index = list(dev["adc_channels_reg"]["adc_index"])[0]
        _channelItems = [int(channel) for channel in list(_adc_channels_reg)]
        # Write header to the data
        fieldnames = ['time',"test_tx",'bus_id',"nodeId","adc_ch","index","sub_index","adc_data", "adc_data_converted","reqmsg","requestreg","respmsg","responsereg", "status"]
        
        csv_writer = AnalysisUtils().build_data_base(fieldnames=fieldnames,outputname =outputname, directory = outputdir)
        monitoringTime = time.time()
        count = 0
        for point in np.arange(0, n_readings):
            for bus in bus_range:
                for nodeId in nodeIds:  
                # Read ADC channels
                    for c in tqdm(np.arange(len(_channelItems)),colour="green"):
                        channel =  _channelItems[c]
                        subindex = channel - 2
                        data_point, reqmsg, requestreg, respmsg,responsereg , status, errorResponse  =  await self.read_sdo_can(nodeId = nodeId,
                                                                                                                  index=int(_adc_index, 16),
                                                                                                                  subindex=subindex,
                                                                                                                  bus = bus)
                        
                        ts = time.time()
                        elapsedtime = ts - monitoringTime
                        if errorResponse: code = "E"
                        else: code = "R"
                        if data_point is not None:
                             adc_converted = Analysis().adc_conversion(_adc_channels_reg[str(channel)], data_point)
                             adc_converted = round(adc_converted, 3)
                             self.logger.report(f'[{code}] Got data for channel {channel}: = {adc_converted}')
                        else: adc_converted = 0
                        csv_writer.writerow((str(elapsedtime),
                                             str(1),
                                             str(bus),
                                             str(nodeId),
                                             str(channel),
                                             str(_adc_index),
                                             str(subindex),
                                             str(data_point),
                                             str(adc_converted),
                                             reqmsg,
                                             str(requestreg), 
                                             respmsg,
                                             str(responsereg), 
                                             status))
                await asyncio.sleep(0.01)
        self.logger.info(f'No. request timeout = {self.__cnt["SDO_read_request_timeout"]}|| No. read abort {self.__cnt["SDO_read_abort"]}')
        self.logger.notice("MOPSHUB data are saved to %s/%s" % (outputdir,outputname))
            
    def create_mopshub_adc_data_file(self,outputname, outputdir):
        # Write header to the data
        fieldnames = ['Time', 'Channel', "nodeId", "ADCChannel", "ADCData" , "ADCDataConverted"]
        csv_writer = AnalysisUtils().build_data_base(fieldnames=fieldnames,outputname = outputname, directory = outputdir)        
        return csv_writer
    
    async def read_adc_channels(self, file= None, directory= None , nodeId= None, outputdir= None, n_readings= None, csv_writer= None, csv_file = None):
        """Start actual CANopen communication
        This function contains an endless loop in which it is looped over all
        ADC channels. Each value is read using
        :meth:`read_sdo_can_thread` and written to its corresponding
        """     
        self.logger.info(f'Reading ADC channels of Mops with ID {nodeId}')
        def exit_handler():
        # This function will be called on script termination
            self.logger.warning("Script interrupted. Closing the program.")
            self.stop()
            sys.exit(0)
            
        dev = AnalysisUtils().open_yaml_file(file=file, directory=directory)
        # yaml file is needed to get the object dictionary items
        _adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        _adc_index = list(dev["adc_channels_reg"]["adc_index"])[0]
        _channelItems = [int(channel) for channel in list(_adc_channels_reg)]
        atexit.register(exit_handler)
        monitoringTime = time.time()
        i = 0
        try:
            while True:
                i = i+1
                # Read ADC channels
                for c in np.arange(len(_channelItems)): #tqdm(np.arange(len(_channelItems))):
                    channel =  _channelItems[c]
                    subindex = channel - 2                                                                                                 
                    data_point,_,_,_,_,_,errorResponse =  await self.read_sdo_can(nodeId = nodeId, 
                                                                    index = int(_adc_index, 16),
                                                                    subindex = subindex)
                    if errorResponse: code = "E"
                    else: code = "R"
                    #await asyncio.sleep(0.01)
                    ts = time.time()
                    elapsedtime = ts - monitoringTime
                    if data_point is not None:
                        adc_converted = Analysis().adc_conversion(_adc_channels_reg[str(channel)], data_point)
                        adc_converted = round(adc_converted, 3)
                        csv_writer.writerow((str(round(elapsedtime, 1)),
                                             str(self.get_channel()),
                                             str(nodeId),
                                             str(subindex),
                                             str(data_point),
                                             str(adc_converted)))
                        self.logger.report(f'[{code}] Got data for channel {channel}: = {adc_converted} V [ADC = {data_point}]')
                        csv_file.flush() # Flush the buffer to update the file
        except (KeyboardInterrupt):
            #Handle Ctrl+C to gracefully exit the loop
            self.logger.warning("User interrupted. Closing the program.")             
        finally:
            csv_writer.writerow((str(elapsedtime),
                         str(None),
                         str(None),
                         str(None), 
                         str(None), 
                         "End of Test"))  
            csv_file.close()

            self.logger.notice("ADC data are saved to %s" % (outputdir))
            return None
    
    def restart_channel_connection(self, interface = None):
        """Restart |CAN| channel.
        for threaded application, busOff() must be called once for each handle. 
        The same applies to busOn() - the physical channel will not go off bus
        until the last handle to the channel goes off bus.   
        
        """  
        if interface is None: 
            _interface = self.__interface
        else:
            _interface = interface
            
        self.logger.warning('Resetting the CAN channel.')
        #Stop the bus
        with self.lock:
            self.__cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        self.__pill2kill.set()
        if self.__busOn0:
            if _interface == 'Kvaser':
                try:
                    self.__canMsgThread.join()
                except RuntimeError:
                    pass
                self.ch0.busOff()
                self.ch0.close()
            elif _interface == 'AnaGate': 
                self.ch0.close()
            else:
                self.ch0.shutdown()            
        self.__busOn0 = False
        self.set_channel_connection(interface = _interface)
        self.__pill2kill = Event()
        self.logger.notice('The channel is reset') 
        
    def stop(self):
        """Close |CAN| channel
        Make sure that this is called so that the connection is closed in a
        correct manner. When this class is used within a :obj:`with` statement
        this method is called automatically when the statement is exited.
        """
        with self.lock:
            self.__cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        self.logger.warning('Stopping helper threads. This might take a '
                            'minute')
        self.logger.warning('Closing the CAN channel.')
        self.__pill2kill.set()
        if self.__busOn0:
            if self.__interface == 'Kvaser':
                try:
                    self.__canMsgThread.join()
                except RuntimeError:
                    pass
                self.logger.warning('Going in \'Bus Off\' state.')
                self.ch0.busOff()
                self.ch0.close()
            elif self.__interface == 'AnaGate': 
                self.ch0.close()
            else:
                self.ch0.shutdown()
                #channel = "can" + str(self.__channel)
                        
        self.__busOn0 = False
        self.logger.warning('Stopping the server.')
    
    async def read_sdo_can_thread(self, nodeId=None, index=None, subindex=None, max_data_bytes=8, SDO_TX=None, SDO_RX=None, cobid=None,bus = 0):
        """Read an object via |SDO|
    
        Currently expedited and segmented transfer is supported by this method.
        The function will writing the dictionary request from the master to the node then read the response from the node to the master
        The user has to decide how to decode the data.
    
        Parameters
        ----------
        nodeId : :obj:`int`
            The id from the node to read from
        index : :obj:`int`
            The Object Dictionary index to read from
        subindex : :obj:`int`
            |OD| Subindex. Defaults to zero for single value entries.
        timeout : :obj:`int`, optional
            |SDO| timeout in milliseconds
    
        Returns
        -------
        :obj:`list` of :obj:`int`
            The data if was successfully read
        :data:`None`
            In case of errors
        """
        self.logger.notice("Reading an object via |SDO|")
        self.start_channel_connection(interface=self.__interface)
        if nodeId is None or index is None or subindex is None:
            self.logger.warning('SDO read protocol cancelled before it could begin.')         
            return None
        self.logger.info(f'Send SDO read request to node {nodeId}.')
        msg = [0 for i in range(max_data_bytes)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex
        msg[7] =bus
        try:
            await self.write_can_message(cobid, msg)
        except CanGeneralError:
            self.__cnt['SDO_read_request_timeout'] += 1
            return None
        # Wait for response
        t0 = time.perf_counter()
        messageValid = False
        errorResponse = False
        errorSignal = False
        timeout = 1000
        while time.perf_counter() - t0 < timeout / 1000:
            with self.__lock:
                # check the message validity [nodid, msg size,...]
                for i, (cobid_ret, ret, dlc, flag, t) in zip(range(len(self.__canMsgQueue)), self.__canMsgQueue):
                    messageValid = (dlc == 8 
                                    and cobid_ret == SDO_RX + nodeId
                                    and ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42] 
                                    and int.from_bytes([ret[1], ret[2]], 'little') == index
                                    and ret[3] == subindex)
                    # errorResponse is meant to deal with any disturbance in the signal due to the reset of the chip 
                    errorResponse = (dlc == 8 and cobid_ret == 0x88 and ret[0] in [0x00])
            
            if (messageValid or errorResponse):
                del self.__canMsgQueue[i]
                break  
    
            if (messageValid):
                break
            
            if (errorResponse):
                return cobid_ret, None
        else:
            self.logger.warning(f'SDO read response timeout (node {nodeId}, index'f' {index:04X}:{subindex:02X})')
            self.__cnt['SDO_read_response_timeout'] += 1
            return None, None
        
        self.__canMsgThread.join()#Dominic to join the thread with Pill 2 kill 
    
        # Check command byte
        if ret[0] == (0x80):
            abort_code = int.from_bytes(ret[4:], 'little')
            self.logger.error(f'Received SDO abort message while reading '
                              f'object {index:04X}:{subindex:02X} of node '
                              f'{nodeId} with abort code {abort_code:08X}')
            self.__cnt['SDO_read_abort'] += 1
            return None, None
        # Here some Bitwise Operators are needed to perform  bit by bit operation
        # ret[0] =67 [bin(ret[0]) = 0b1000011] //from int to binary
        # (ret[0] >> 2) will divide ret[0] by 2**2 [Returns ret[0] with the bits shifted to the right by 2 places. = 0b10000]
        # (ret[0] >> 2) & 0b11 & Binary AND Operator [copies a bit to the result if it exists in both operands = 0b0]
        # 4 - ((ret[0] >> 2) & 0b11) for expedited transfer the object dictionary does not get larger than 4 bytes.
        n_data_bytes = 4 - ((ret[0] >> 2) & 0b11) if ret[0] != 0x42 else 4
        data = []
        for i in range(n_data_bytes-1): 
            data.append(ret[4 + i])
        self.logger.report(f'Got data: {data}')
        return cobid_ret, int.from_bytes(data, 'little')
    
    async def return_valid_message(self, nodeId, index, subindex, cobid_ret, data_ret, dlc, error_frame, SDO_TX, SDO_RX):
        # The following are the only expected response
        messageValid  = False
        errorSignal   = False  # check any reset signal from the chip
        errorResponse = False  # SocketCAN error message
        #print(hex(SDO_RX + nodeId), hex(cobid_ret), data_ret, hex(data_ret[0]),
        #      hex(int.from_bytes([data_ret[1], data_ret[2]], 'little')),hex(index),
        #      hex(data_ret[3]), hex(subindex))
        errorSignal = (dlc == 8 
                      and cobid_ret == 0x700 + nodeId 
                      and data_ret[0] in [0x05, 0x08,0x85]) 
    
        errorResponse = (dlc == 8 
                         and cobid_ret == 0x88 
                         and data_ret[0] in [0x00]) 
    
        messageValid = (dlc == 8 
                        and cobid_ret == SDO_RX + nodeId
                        and data_ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42] 
                        and int.from_bytes([data_ret[1], data_ret[2]], 'little') == index
                        and data_ret[3] == subindex)       
        # Error counter from microcontroller
        error_counter = (dlc == 1 
                        and cobid_ret == 0x3F3
                        and data_ret[0] in [0x08])   
        
        # Check the validity
        if error_counter : self.logger.error(f'Received error message from Microcontroller with cobid:{hex(cobid_ret)} while calling subindex: {hex(subindex)}')
        if errorSignal   : self.logger.notice(f'Received a reset Signal with cobid:{hex(cobid_ret)} while calling subindex: {hex(subindex)}')
    
        if errorResponse:
            # there is a scenario where the chip reset and send an error message after
            # This loop will:
            # 1. read the can reset signal
            # 2. read the next can message and check its validity
            #self.logger.notice(f'Received an error response with cobid:{hex(cobid_ret)} while calling subindex: {hex(subindex)}')
            self.__cnt['error_frame'] += 1
            cobid_ret, data_ret, dlc, flag, _, _, t, error_frame = await self.read_can_message()
            messageValid = (dlc == 8 
                            and cobid_ret == SDO_RX + nodeId
                            and data_ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42] 
                            and int.from_bytes([data_ret[1], data_ret[2]], 'little') == index
                            and data_ret[3] == subindex)  
        
        
        if messageValid or errorSignal:
            nDatabytes = 4 - ((data_ret[0] >> 2) & 0b11) if data_ret[0] != 0x42 else 4
            data = []
            for i in range(nDatabytes-1): 
                data.append(data_ret[4 + i])
            return int.from_bytes(data, 'little'), messageValid, errorResponse
        else:
            self.logger.warning(f'SDO read response timeout (node {nodeId}, index {index:04X}:{subindex:02X})')
            self.__cnt['SDO_read_response_timeout'] += 1
            return None, messageValid, errorResponse
    
    async def read_sdo_can(self, nodeId=None, index=None, subindex=None, max_data_bytes=8, SDO_TX=0x600, SDO_RX=0x580, bus =0, cobid=None):
        """Read an object via |SDO|
    
        Currently expedited and segmented transfer is supported by this method.
        The function will writing the dictionary request from the master to the node then read the response from the node to the master
        The user has to decide how to decode the data.
    
        Parameters
        ----------
        nodeId : :obj:`int`
            The id from the node to read from
        index : :obj:`int`
            The Object Dictionary index to read from
        subindex : :obj:`int`
            |OD| Subindex. Defaults to zero for single value entries.
        timeout : :obj:`int`, optional
            |SDO| timeout in milliseconds
    
        Returns
        -------
        :obj:`list` of :obj:`int`
            The data if was successfully read
        :data:`None`
            In case of errors
        """
        status =0;
        respmsg, responsereg,errorResponse = None, None, None
        if nodeId is None or index is None or subindex is None:
            self.logger.warning('SDO read protocol cancelled before it could begin.')         
            return None, None, None,respmsg, responsereg , status, errorResponse             
        
        if cobid : cobid = cobid
        else: cobid = SDO_TX + nodeId
        msg = [0 for i in range(max_data_bytes)]
        if SDO_TX==0x600 : msg[0] = 0x40
        else : msg[0] = 0x00
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex 
        msg[7] =bus
        requestreg = Analysis().binToHexa(bin(cobid)[2:].zfill(8)+ 
                                          bin(msg[0])[2:].zfill(8)+ 
                                          bin(msg[1])[2:].zfill(8)+
                                          bin(msg[2])[2:].zfill(8)+
                                          bin(msg[3])[2:].zfill(8)+ 
                                          bin(msg[4])[2:].zfill(8)+
                                          bin(msg[5])[2:].zfill(8)+
                                          bin(msg[6])[2:].zfill(8)+ 
                                          bin(msg[7])[2:].zfill(8))     
        try:
            reqmsg = await self.write_can_message(cobid = cobid,
                                                   data = msg)
        except:
            reqmsg = 0
            self.__cnt['SDO_read_request_timeout'] += 1
            
        
        _frame = await self.read_can_message()
        
        if (not all(m is None for m in _frame[0:2])):
           cobid_ret, msg_ret, dlc, flag, respmsg, responsereg, t, error_frame = _frame
           data_ret, messageValid, errorResponse  = await self.return_valid_message(nodeId, index, subindex, cobid_ret, msg_ret, dlc, error_frame, SDO_TX, SDO_RX)
           if messageValid: status=1;
           else:  status =0;
           # Check command byte
           if msg_ret[0] == (0x80):
                status = 0
                abort_code = int.from_bytes(data_ret[4:], 'little')
                self.logger.error(f'Received SDO abort message while reading '
                                  f'object {index:04X}:{subindex:02X} of node '
                                  f'{nodeId} with abort code {abort_code:08X}')
                self.__cnt['SDO_read_abort'] += 1
                if requestreg is not None: 
                    return None, reqmsg, hex(requestreg),respmsg, responsereg, status, errorResponse
                else: return None, reqmsg, requestreg,respmsg, responsereg, status, errorResponse              
           else:
                return data_ret, reqmsg , hex(requestreg) , respmsg, responsereg  , status, errorResponse     
        else:
            
            status = 0
            if responsereg is not None: return None, reqmsg, hex(responsereg),respmsg, responsereg, status, errorResponse
            else : return None, reqmsg, hex(requestreg),respmsg, responsereg, status, errorResponse               

    async def  write_can_message(self, cobid = None, data = [None], flag=0, dlc = 8):
        """Combining writing functions for different |CAN| interfaces
        Parameters
        ----------
        cobid : :obj:`int`
            |CAN| identifier
        data : :obj:`list` of :obj:`int` or :obj:`bytes`
            Data bytes
        flag : :obj:`int`, optional
            Message flag (|RTR|, etc.). Defaults to zero.
        """
        reqmsg = 0
        if self.__interface == 'Kvaser':
            frame = Frame(id_=cobid, data=data, timestamp=None)#, flags=canlib.MessageFlag.EXT)  #  from tutorial
            self.ch0.writeWait(frame, 100) #
            reqmsg = 1
        elif self.__interface == 'AnaGate':
            if not self.ch0.deviceOpen:
                self.logger.notice('Reopening AnaGate CAN interface')
            self.ch0.write(cobid, data, flag)
            reqmsg = 1
        else:
            msg = can.Message(arbitration_id=cobid, data=data, is_extended_id=False, is_error_frame=False,dlc = dlc)
            try:
                #timeout wait up to this many seconds for message to be ACK'ed or
                # A timeout in the range of 10 milliseconds  with CAN bus speed of 125 kb/s
                self.ch0.send(msg, 10) 
                reqmsg = 1
            except:  # can.CanError:
                self.__cnt['Not_active_bus'] += 1
                self.logger.error("An Error occurred, The bus is not active")
        self.__cnt['tx_msg'] += 1
        return reqmsg
    
    def can_setup(self, channel: int, interface : str):
        self.logger.info("Resetting CAN Interface as soon as communication threads are finished")
        self.sem_config_block.acquire()
        self.set_interface(interface)
        try:
            if channel == self.can_0_settings['channel']:
                #check if the bus is on
                if self.__busOn0:
                    self.ch0.shutdown()
                    self.hardware_config(channel = channel,interface = interface)
            elif channel == self.can_1_settings['channel']:
                if self.__busOn1:
                    self.ch1.shutdown()
                    self.hardware_config(channel = channel,interface = interface)
        except:
            if channel == 0:
                if self.__busOn0:
                    self.ch0.shutdown()
                    self.hardware_config(channel = channel,interface = interface)
            elif channel == 1:
                if self.__busOn1:
                    self.ch1.shutdown()
                    self.hardware_config(channel = channel,interface = interface)            
        self.logger.info(f"Channel {channel} is set")
        self.sem_config_block.release()
        self.logger.info("Resetting of CAN Interface finished. Returning to communication.")
                                                    
    def hardware_config(self, bitrate = None, channel = None, interface = None, sjw = None,samplepoint = None,tseg1 = None,tseg2 = None):
        '''
        Pass channel string (example 'can0') to configure OS level drivers and interface.
        '''
        #sudo chown root:root socketcan_wrapper_enable.sh
        #sudo chmod 4775 socketcan_wrapper_enable.sh
        #sudo bash socketcan_wrapper_enable.sh 111111 0.5 4 can0 can 5 6
        
        
        if interface == "socketcan":
            _bus_type = "can"
            if channel == 0:
                _can_channel = _bus_type + f"{self.can_0_settings['channel']}"
            if channel == 1:
                _can_channel = _bus_type + f"{self.can_1_settings['channel']}"
            self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
            if channel == 0:
                #os.system("." + rootdir + "/socketcan_wrapper_enable.sh %i %s %s %s %s %s %s" % (bitrate, samplepoint, sjw, _can_channel, _bus_type,tseg1,tseg2))
                os.system("bash " + rootdir + "/socketcan_wrapper_enable.sh %s %s %s %s %s %s %s" % (f"{self.can_0_settings['bitrate']}",
                                 f"{self.can_0_settings['samplePoint']}",f"{self.can_0_settings['SJW']}",_can_channel,_bus_type,
                                 f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}"))
                # subprocess.call(['sh', 'bash socketcan_wrapper_enable.sh', f"{self.can_0_settings['bitrate']}",
                #                  f"{self.can_0_settings['samplePoint']}",f"{self.can_0_settings['SJW']}",_can_channel,_bus_type,
                #                  f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}"],
                #                  cwd=rootdir)
            if channel == 1:
                #os.system("." + rootdir + "/socketcan_wrapper_enable.sh %i %s %s %s %s %s %s" % (bitrate, samplepoint, sjw, _can_channel, _bus_type,tseg1,tseg2))
                os.system("bash " + rootdir + "/socketcan_wrapper_enable.sh %s %s %s %s %s %s %s" % (f"{self.can_0_settings['bitrate']}",
                                 f"{self.can_0_settings['samplePoint']}",f"{self.can_0_settings['SJW']}",_can_channel,_bus_type,
                                 f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}"))
                # subprocess.call(['sh', 'bash socketcan_wrapper_enable.sh', f"{self.can_0_settings['bitrate']}",
                #                  f"{self.can_0_settings['samplePoint']}",f"{self.can_0_settings['SJW']}",_can_channel,_bus_type,
                #                  f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}"],
                #                  cwd=rootdir)                  
        elif interface == "virtual":
            _bus_type = "vcan"
            if channel == 0:
                _can_channel = _bus_type + f"{self.can_0_settings['channel']}"
            if channel == 1:
                _can_channel = _bus_type + f"{self.can_1_settings['channel']}"
            self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
            #os.system(". sudo " + rootdir + "/socketcan_wrapper_enable.sh %i %s %s %s %s %s %s" % (bitrate, samplepoint, sjw, _can_channel, _bus_type,tseg1,tseg2))
            if channel == 0:
                subprocess.call(['sh', 'sudo  ./socketcan_wrapper_enable.sh', f"{self.can_0_settings['bitrate']}",
                                 f"{self.can_0_settings['samplePoint']}",f"{self.can_0_settings['SJW']}",_can_channel,_bus_type,
                                 f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}"],
                                 cwd=rootdir)
            if channel == 1:
                subprocess.call(['sh', 'sudo  ./socketcan_wrapper_enable.sh', f"{self.can_1_settings['bitrate']}",
                                 f"{self.can_1_settings['samplePoint']}",f"{self.can_1_settings['SJW']}",_can_channel,_bus_type,
                                 f"{self.can_1_settings['tseg1']}", f"{self.can_1_settings['tseg2']}"],
                                 cwd=rootdir)
                

        else:
            #Do nothing because it is not CAN
            _can_channel = str(channel)
        self.logger.info('%s[%s] Interface is initialized....' % (interface,_can_channel))
           
    def read_can_message_thread(self):
        """Read incoming |CAN| messages and store them in the queue
        :attr:`canMsgQueue`.

        This method runs an endless loop which can only be stopped by setting
        the :class:`~threading.Event` :attr:`pill2kill` and is therefore
        designed to be used as a :class:`~threading.Thread`.
        """
        
        #self.__pill2kill = Event()
        _interface = self.__interface;
        while not self.__pill2kill.is_set(): 
            try:
                if _interface == 'Kvaser':
                    with self.__kvaserLock:#Added for urgent cases
                        frame = self.ch0.read(100)
                    cobid, data, dlc, flag, t = (frame.id, frame.data,
                                                 frame.dlc, frame.flags,
                                                 frame.timestamp)
                    error_frame = None
                    if frame is None or (cobid == 0 and dlc == 0):
                        raise canlib.CanNoMsg
                
                elif _interface == 'AnaGate':
                    cobid, data, dlc, flag, t = self.ch0.getMessage()
                    if (cobid == 0 and dlc == 0):
                        raise analib.CanNoMsg
                else:
                    frame = self.ch0.recv(0.01)
                    if frame is not None:
                        # raise can.CanError
                        cobid, data, dlc, flag, t , error_frame = (frame.arbitration_id, frame.data,
                                                                   frame.dlc, frame.is_extended_id,
                                                                   frame.timestamp, frame.is_error_frame)
                        respmsg = 1
                    else:
                        self.__pill2kill.set()
                        respmsg = 0
                        # raise can.CanError
                    try:
                        responsereg = Analysis().binToHexa(bin(cobid)[2:].zfill(11)+
                                                           bin(data[0])[2:].zfill(8)+
                                                           bin(data[1])[2:].zfill(8)+
                                                           bin(data[2])[2:].zfill(8)+
                                                           bin(data[3])[2:].zfill(8)+
                                                           bin(data[4])[2:].zfill(8)+
                                                           bin(data[5])[2:].zfill(8)+
                                                           bin(data[6])[2:].zfill(8)+
                                                           bin(data[7])[2:].zfill(8))
                            
                    except: 
                        responsereg = 0
                
                with self.__lock:
                    self.__canMsgQueue.appendleft((cobid, data, dlc, flag, t))
                    
                self.dumpMessage(cobid, data, dlc, flag, t)
                self.__cnt['rx_msg'] += 1
                return cobid, data, dlc, flag, t, error_frame
            except:  # (canlib.CanNoMsg, analib.CanNoMsg,can.CanError):
               self.__pill2kill = Event()
               return None, None, None, None, None, None

    async def read_can_message(self, timeout=1.0):
        """Read incoming |CAN| messages without storing any Queue
        This method runs an endless loop which can only be stopped by setting
        """
        respmsg = 0
        try:        
            if self.__interface == 'Kvaser':
                    with self.__kvaserLock:#Added for urgent cases
                        frame = self.ch0.read(100)
                    cobid, data, dlc, flag, t = (frame.id, frame.data,
                                                 frame.dlc, frame.flags,
                                                 frame.timestamp)
                    error_frame = None
                    respmsg = 1
                    if frame is None or (cobid == 0 and dlc == 0):
                        raise canlib.CanNoMsg
                
            elif self.__interface == 'AnaGate':
                cobid, data, dlc, flag, t = self.ch0.getMessage()
                error_frame = None
                respmsg = 1
                #return cobid, data, dlc, flag, t, error_frame
                if (cobid == 0 and dlc == 0):
                    raise analib.CanNoMsg
            else:  
                frame = self.ch0.recv(0.01)
                #print(frame)
                if frame is not None:
                    # raise can.CanError
                    cobid, data, dlc, flag, t , error_frame = (frame.arbitration_id, frame.data,
                                                               frame.dlc, frame.is_extended_id,
                                                               frame.timestamp, frame.is_error_frame)
                    respmsg = 1
                    responsereg = Analysis().binToHexa(bin(cobid)[2:].zfill(11)+
                                                       bin(data[0])[2:].zfill(8)+
                                                       bin(data[1])[2:].zfill(8)+
                                                       bin(data[2])[2:].zfill(8)+
                                                       bin(data[3])[2:].zfill(8)+
                                                       bin(data[4])[2:].zfill(8)+
                                                       bin(data[5])[2:].zfill(8)+
                                                       bin(data[6])[2:].zfill(8)+
                                                       bin(data[7])[2:].zfill(8))
                
                else:
                    respmsg = 0
                    responsereg = 0
            self.__cnt['rx_msg'] += 1        
            return cobid, data, dlc, flag, respmsg, hex(responsereg), t, error_frame
        except:  # (canlib.CanNoMsg, analib.CanNoMsg,can.CanError):
            return None, None, None, None, None, None, None, None
        
        
    # The following functions are to read the can messages
    def _anagateCbFunc(self):
        """Wraps the callback function for AnaGate |CAN| interfaces. This is
        neccessary in order to have access to the instance attributes.

        The callback function is called asychronous but the instance attributes
        are accessed in a thread-safe way.

        Returns
        -------
        cbFunc
            Function pointer to the callback function
        """

        def cbFunc(cobid, data, dlc, flag):
            """Callback function.

            Appends incoming messages to the message queue and logs them.

            Parameters
            ----------
            cobid : :obj:`int`
                |CAN| identifier
            data : :class:`~ctypes.c_char` :func:`~cytpes.POINTER`
                |CAN| data - max length 8. Is converted to :obj:`bytes` for
                internal treatment using :func:`~ctypes.string_at` function. It
                is not possible to just use :class:`~ctypes.c_char_p` instead
                because bytes containing zero would be interpreted as end of
                data.
            dlc : :obj:`int`
                Data Length Code
            flag : :obj:`int`
                Message flags
                class to work.
            """
            data = ct.string_at(data, dlc)
            t = time.time()
            with self.__lock:
                self.__canMsgQueue.appendleft((cobid, data, dlc, flag, t))
            self.dumpMessage(cobid, data, dlc, flag, t)
        
        return cbFunc
    
    def dumpMessage(self, cobid, msg, dlc, flag, t):
        """Dumps a CANopen message to the screen and log file

        Parameters
        ----------
        cobid : :obj:`int`
            |CAN| identifier
        msg : :obj:`bytes`
            |CAN| data - max length 8
        dlc : :obj:`int`
            Data Length Code
        flag : :obj:`int`
            Flags, a combination of the :const:`canMSG_xxx` and
            :const:`canMSGERR_xxx` values
        t : obj'int'
        """
        if self.__interface == 'Kvaser':
            if (flag & canlib.canMSG_ERROR_FRAME != 0):
                self.logger.error("***ERROR FRAME RECEIVED***")
            else:
                msgstr = '{:3X} {:d}   '.format(cobid, dlc)
                for i in range(len(msg)):
                    msgstr += '{:02x}  '.format(msg[i])
                msgstr += '    ' * (8 - len(msg))
                st = datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
                msgstr += str(st)
                self.logger.info(msgstr)

        else:
            msgstr = '{:3X} {:d}   '.format(cobid, dlc)
            for i in range(len(msg)):
                msgstr += '{:02x}  '.format(msg[i])
            msgstr += '    ' * (8 - len(msg))
            st = datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
            msgstr += str(st)
            self.logger.report(msgstr)

    # Setter and getter functions
    def set_interface(self, x):
        self.__interface = x

    def set_nodeList(self, x):
        self.__nodeList = x
    
    def set_channelPorts(self, x):
        self.__can_channels = x
            
    def set_channel(self, x):
        self.__channel = x
    
    def set_ipAddress(self, x):
        self.__ipAddress = x
        
    def set_bitrate(self, bitrate):
        self.__bitrate = bitrate 
 
    def set_sample_point(self, x):
        self.__sample_point = float(x)
                   
    def get_DllVersion(self):
        ret = analib.wrapper.dllInfo()
        return ret
    
    def get_nodeList(self):
        return self.__nodeList

    def get_channelPorts(self):
        return self.__can_channels
        
    def get_bitrate(self):
        return self.__bitrate

    def get_sample_point(self):
        return self.__sample_point
        
    def get_ipAddress(self):
        """:obj:`str` : Network address of the AnaGate partner. Only used for
        AnaGate CAN interfaces."""
        if self.__interface == 'Kvaser':
            raise AttributeError('You are using a Kvaser CAN interface!')
        return self.__ipAddress

    def get_interface(self):
        """:obj:`str` : Vendor of the CAN interface. Possible values are
        ``'Kvaser'`` and ``'AnaGate'``."""
        return self.__interface
    
    def get_channel(self):
        """:obj:`int` : Number of the crurrently used |CAN| channel."""
        return self.__channel
           
    def get_channelState(self, channel):
        return channel.state

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if exception_type is KeyboardInterrupt:
            self.logger.warning('Received Ctrl+C event (KeyboardInterrupt).')
        else:
            self.logger.exception(exception_value)
        self.stop()
        logging.shutdown()
        return True
           
    @property
    def lock(self):
        """:class:`~threading.Lock` : Lock object for accessing the incoming
        message queue :attr:`canMsgQueue`"""
        return self.__lock

    @property
    def canMsgQueue(self):
        """:class:`collections.deque` : Queue object holding incoming |CAN|
        messages. This class supports thread-safe adding and removing of
        elements but not thread-safe iterating. Therefore the designated
        :class:`~threading.Lock` object :attr:`lock` should be acquired before
        accessing it.

        The queue is initialized with a maxmimum length of ``1000`` elements
        to avoid memory problems although it is not expected to grow at all.

        This special class is used instead of the :class:`queue.Queue` class
        because it is iterable and fast."""
        return self.__canMsgQueue
    
    @property
    def kvaserLock(self):
        """:class:`~threading.Lock` : Lock object which should be acquired for
        performing read or write operations on the Kvaser |CAN| channel. It
        turned out that bad things can happen if that is not done."""
        return self.__kvaserLock

    @property
    def cnt(self):
        """:class:`~collections.Counter` : Counter holding information about
        quality of transmitting and receiving. Its contens are logged when the
        program ends."""
        return self.__cnt

    def reset_counters(self):
        self.__cnt.clear()  # Clears all keys and values


    @property
    def pill2kill(self):
        """:class:`threading.Event` : Stop event for the message collecting
        method :meth:`read_can_message_thread`"""
        return self.__pill2kill
    
    # @property
    def channel(self):
        """Currently used |CAN| channel. The actual class depends on the used
        |CAN| interface."""
        return self.ch0

    @property
    def bitRate(self):
        """:obj:`int` : Currently used bit rate. When you try to change it
        :func:`stop` will be called before."""
        if self.__interface == 'Kvaser':
            return self.__bitrate
        else:
            return self.ch0.baudrate
     
    @bitRate.setter
    def bitRate(self, bitrate):
        if self.__interface == 'Kvaser':
            self.stop()
            self.__bitrate = bitrate
            self.start()
        else:
            self.ch0.baudrate = bitrate     

def main():
    """Wrapper function for using the server as a command line tool

    The command line tool accepts arguments for configuring the server which
    are transferred to the :class:`CanWrapper` class.
    """

    # Parse arguments
    parser = ArgumentParser(description='CANMOPS Interpreter for MOPS chip',
                            epilog='For more information contact '
                            'ahmed.qamesh@cern.ch',
                            formatter_class=ArgumentDefaultsHelpFormatter)
    
    parser.set_defaults(interface='socketcan')
    # CAN interface
    CGroup = parser.add_argument_group('CAN interface')
    iGroup = CGroup.add_mutually_exclusive_group()
    iGroup.add_argument('-K', '--kvaser', action='store_const', const='Kvaser',
                        dest='interface',
                        help='Use Kvaser CAN interface (default). When no '
                        'Kvaser interface is found or connected a virtual '
                        'channel is used.')
    iGroup.add_argument('-A', '--anagate', action='store_const',
                        const='AnaGate', dest='interface',
                        help='Use AnaGate Ethernet CAN interface')
    
    iGroup.add_argument('-S', '--socketcan', action='store_const',
                        const='socketcan', dest='interface',
                        help='Use socketcan  interface')
    
    # CAN settings group
    cGroup = parser.add_argument_group('CAN settings')
    cGroup.add_argument('-c', '--channel', metavar='CHANNEL',
                        help='Number of CAN channel to use', 
                        default=0)
    
    cGroup.add_argument('-i', '--ipaddress', metavar='IPADDRESS',
                        default='192.168.1.254', dest='ipAddress',
                        help='IP address of the AnaGate Ethernet CAN '
                        'interface')
    cGroup.add_argument('-b', '--bitrate', metavar='BITRATE',
                        default=125000,
                        help='CAN bitrate as integer in bit/s')

    cGroup.add_argument('-sp', '--samplePoint', metavar='SAMPLEPOINT',
                        default=0.5,
                        help='CAN sample point in decimal')

    cGroup.add_argument('-sjw', '--sjw', metavar='SJW',
                        default=4,
                        help='Synchronization Jump Width')
    
    cGroup.add_argument('-tseg1', '--tseg1', metavar='tseg1',
                        default=0,
                        help='Time Segment1')
    
    cGroup.add_argument('-tseg2', '--tseg2', metavar='tseg2',
                        default=0,
                        help='Time Segment2')
            
    cGroup.add_argument('-nodeid', '--nodeid', metavar='nodeid',
                        default=0,
                        help='Node Id of the MOPS chip under test')
        
    cGroup.add_argument('-trim', '--trim_mode', metavar='trim_mode',
                        default=False,type=bool,
                        help='Trim the chip')
    # Logging configuration
    lGroup = parser.add_argument_group('Logging settings')
    lGroup.add_argument('-cl', '--console_loglevel',
                        choices={'NOTSET', 'SPAM', 'DEBUG', 'VERBOSE', 'INFO',
                                 'NOTICE', 'SUCCESS', 'WARNING', 'ERROR',
                                 'CRITICAL'},
                        default='INFO',
                        help='Level of console logging')

    args = parser.parse_args()
    # Start the server
    wrapper = CanWrapper(**vars(args))  


                    
if __name__ == "__main__":
    main()  