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
from __future__ import annotations
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from configparser import ConfigParser
from typing import *
import time
import datetime
#import numba
import sys
import os
from threading import Thread, Event, Lock
import numpy as np
from pip._internal.cli.cmdoptions import pre
from lxml.html.builder import PRE
from _socket import socket
try:
    from .analysis import Analysis
    from .logger_main import Logger
    from .analysis_utils import AnalysisUtils
    from .can_bus_config import can_config
    from .can_thread_reader import READSocketcan
except (ImportError, ModuleNotFoundError):
    from analysis import Analysis
    from logger_main   import Logger
    from analysis_utils import AnalysisUtils
    from can_bus_config import can_config
    from can_thread_reader import READSocketcan    
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

#from csv import writer
logger = Logger().setup_main_logger(name = " Lib Check ",console_loglevel=logging.INFO, logger_file = False)
# Import Socketcan for Socketcan
try:
    import can
except:
     logger.warning("SocketCAN Package is not installed....."+"[Please ignore the warning if No SocketCAN drivers used.]")

# Import canlib for Kvaser
try:
    from canlib import canlib, Frame
    from canlib.canlib.exceptions import CanGeneralError
    #from canlib.canlib import ChannelData
except:
    
    logger.warning("Canlib  Package is not installed....."+"[Please ignore the warning if CANLib packages are not required (in case SocketCAN is used)]")
     
# Import analib for AnaGate
try:
    import analib
except:
    logger.warning("AnaGate Package is not installed....."+"[Please ignore the warning if No AnaGate controllers used.]")

rootdir = os.path.dirname(os.path.abspath(__file__))
config_dir = "config/"
lib_dir = rootdir[:-8]

class CanWrapper(READSocketcan):#Instead of object

    def __init__(self,
                 interface=None, channel=None,
                 bitrate=None, samplePoint=None,
                 sjw=None,ipAddress=None,
                 tseg1 = None, tseg2 = None,
                 nodeid =None,
                 conf_file="main_cfg.yml",
                 file_loglevel=logging.INFO, 
                 logdir=None,
                 console_loglevel=logging.INFO):
       
        super(CanWrapper, self).__init__()  # super keyword to call its methods from a subclass:        
        # Read configurations from a file
        self.__conf = AnalysisUtils().open_yaml_file(file=config_dir + conf_file, directory=rootdir[:-8])
        self.__channelPorts = self.__conf["channel_ports"]
        self.__channel = list(self.__conf['channel_ports'])[0]
       # Read CAN settings from a file 
        filename = os.path.join(lib_dir, config_dir + interface +"_CANSettings.yml")
        test_date = time.ctime(os.path.getmtime(filename))
        # Load settings from CAN settings file
        _canSettings = AnalysisUtils().open_yaml_file(file=config_dir + interface + "_CANSettings.yml", directory=lib_dir)

        """:obj:`~logging.Logger`: Main logger for this class"""
        if logdir is None:
            #'Directory where log files should be stored'
            logdir = os.path.join(lib_dir, 'log')
                            
        ts = os.path.join(logdir, time.strftime('%Y-%m-%d_%H-%M-%S_CAN_Wrapper.'))
        self.logger = Logger().setup_main_logger(name = "CAN Wrapper",console_loglevel=console_loglevel, logger_file = False)
        
        self.logger_file = Logger().setup_file_logger(name = "CANWrapper",console_loglevel=console_loglevel, logger_file = ts)#for later usage
        self.logger.info(f'Existing logging Handler: {ts}'+'log')
        
        if bitrate is None:
            self.logger.notice("Loading CAN settings from the file %s produced on %s" % (filename, test_date))
            _default_channel = self.__channel
            self.__channels = _canSettings['channel'+str(_default_channel)]["channel"] 
            self.__ipAddress =  _canSettings['channel'+str(_default_channel)]["ipAddress"]
            self.__bitrate =  _canSettings['channel'+str(_default_channel)]["bitrate"]
            self.__samplePoint = _canSettings['channel'+str(_default_channel)]["samplePoint"]
            self.__sjw = _canSettings['channel'+str(_default_channel)]["SJW"]
            self.__tseg1 = _canSettings['channel'+str(_default_channel)]["tseg2"]   
            self.__tseg2 =_canSettings['channel'+str(_default_channel)]["tseg2"]     
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
        self.error_counter = 0
        
        """:obj:`bool` : If communication is established"""
        self.__busOn = False  
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
        self.__ch = None
        
        if interface == "developer_trial":
            self.__ch = can_config.can_setup(channel = self.__channel, interface = self.__interface)
            can_config.start()
            self.start()
            can.util.set_logging_level('warning')
        else:
            self.set_channel_connection(interface=self.__interface)            
        """Internal attribute for the |CAN| channel"""
        self.__busOn = True
        self.__canMsgQueue = deque([], 100)  # queue with a size of 100 to queue all the messages in the bus
        self.__pill2kill = Event()
        self.__lock = Lock()
        self.__kvaserLock = Lock()
        self.logger.success('....Done Initialization!')
        self.logger_file.success('....Done Initialization!')
        
        if nodeid is not None:
            self.confirm_nodes(nodeIds = [str(nodeid)])
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
            self.logger_file.info(f'{self.__interface}:Using {self.__ch}, Bitrate:{self.__bitrate}') 
            return f'Using {self.__ch}, Bitrate:{self.__bitrate}'
        else:
            self.logger_file.info(f'{self.__interface}: Using {self.__ch.channel_info}, Bitrate:{self.__bitrate}') 
            return f'Using {self.__ch.channel_info}, Bitrate:{self.__bitrate}'
                    
    async def  confirm_nodes(self, channel=0, timeout=100,nodeIds = ["1","2"]):
        self.logger.notice('Checking MOPS status ...')
        _nodeIds = nodeIds 
        self.set_nodeList(_nodeIds)
        self.logger.info(f'Connection to channel {channel} has been verified.')
        for nodeId in _nodeIds: 
            # Send the status message
            cobid_TX = 0x700 + int(nodeId,16)
            cobid_RX = 0x700 + int(nodeId,16)
            await self.write_can_message(cobid_TX, [0, 0, 0, 0, 0, 0, 0, 0], flag=0, timeout=200)
            # receive the message
            readCanMessage = self.read_can_message()
            if readCanMessage is not None:
                cobid_RX, data, _, _, _, _ = readCanMessage
            if cobid_RX == cobid_TX and (data[0] == 0x85 or data[0] == 0x05):
                self.logger.info(f'Connection to MOPS with nodeId {nodeId} in channel {channel} has been '
                                 f'verified.')
            else:
               self.logger.error(f'Connection to MOPS with nodeId {nodeId} in channel {channel} failed')
                                
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
                
                self.__ch = canlib.openChannel(int(self.__channel), canlib.canOPEN_ACCEPT_VIRTUAL) 
                self.__ch.setBusOutputControl(canlib.Driver.NORMAL)  # New from tutorial
                self.__ch.setBusParams(freq = int(self.__bitrate), sjw =int(self.__sjw), tseg1=int(self.__tseg1), tseg2=int(self.__tseg2))
                self.__ch.busOn()
                self.__canMsgThread = Thread(target=self.read_can_message_thread)
            elif interface == 'AnaGate':
                self.__ch = analib.Channel(ipAddress=self.__ipAddress, port=self.__channel, baudrate=self.__bitrate)
            elif interface == 'virtual':
                channel = "vcan" + str(self.__channel)
                self.__ch = can.interface.Bus(bustype="socketcan", channel=channel)
                             
            else:
                channel = "can" + str(self.__channel)
                self.__ch = can.interface.Bus(bustype=interface, channel=channel, bitrate=self.__bitrate) 
                  
        except Exception:
            self.logger.error("TCP/IP or USB socket error in %s interface" % interface)
            self.logger_file.error("Channel definition is %s with interface %s " % (self.__ch,interface)) 
        self.logger.success(str(self))        
    
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
            if not self.__busOn:
                self.logger.notice('Going in \'Bus On\' state ...')
                self.__busOn = True
            #self.__ch.busOn()
        if _interface == 'AnaGate':
            if not self.__ch.deviceOpen:
                self.logger.notice('Reopening AnaGate CAN interface')
                self.__ch.openChannel() 
            if self.__ch.state != 'CONNECTED':
                self.logger.notice('Restarting AnaGate CAN interface.')
                self.__ch.restart()
            # self.__cbFunc = analib.wrapper.dll.CBFUNC(self._anagateCbFunc())
            # self.__ch.setCallback(self.__cbFunc)
        else:# SocketCAN
            pass
        self.__canMsgThread = Thread(target=self.read_can_message_thread)
        self.__canMsgThread.start()
        
    async def read_adc_channels(self, file, directory , nodeId, outputname, outputdir, n_readings):
        """Start actual CANopen communication
        This function contains an endless loop in which it is looped over all
        ADC channels. Each value is read using
        :meth:`read_sdo_can_thread` and written to its corresponding
        """     
        self.logger.info(f'Reading ADC channels of Mops with ID {nodeId}')
        dev = AnalysisUtils().open_yaml_file(file=file, directory=directory)
        # yaml file is needed to get the object dictionary items
        _adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        _adc_index = list(dev["adc_channels_reg"]["adc_index"])[0]
        _channelItems = [int(channel) for channel in list(_adc_channels_reg)]
        # Write header to the data
        out_file_csv = AnalysisUtils().open_csv_file(outname=outputname, directory=outputdir)
        fieldnames = ['Time', 'Channel', "nodeId", "ADCChannel", "ADCData" , "ADCDataConverted"]
        writer = csv.DictWriter(out_file_csv, fieldnames=fieldnames)
        writer.writeheader()    
        csv_writer = csv.writer(out_file_csv)  # , delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)          
        monitoringTime = time.time()
        for point in np.arange(0, n_readings): 
            # Read ADC channels
            pbar = tqdm(total=len(_channelItems) + 1 , desc="ADC channels", iterable=True)
            for c in np.arange(len(_channelItems)):
                channel =  _channelItems[c]
                subindex = channel - 2
                data_point =  await self.read_sdo_can(nodeId, int(_adc_index, 16), subindex, 1000)
                # sdo_data =  await self.read_sdo_can_sync(nodeId, int(_adc_index, 16), subindex, 1000)
                # if all(m is not None for m in sdo_data):
                #     data_point = sdo_data[1]  
                # else:
                #     data_point =None
                await asyncio.sleep(0.01)
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
                    self.logger.info(f'Got data for channel {channel}: = {adc_converted}')
                pbar.update(1)
            pbar.close()
        self.logger.notice("ADC data are saved to %s%s" % (outputdir,outputname))

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
            self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        self.__pill2kill.set()
        if self.__busOn:
            if _interface == 'Kvaser':
                try:
                    self.__canMsgThread.join()
                except RuntimeError:
                    pass
                self.__ch.busOff()
                self.__ch.close()
            elif _interface == 'AnaGate': 
                self.__ch.close()
            else:
                self.__ch.shutdown()            
        self.__busOn = False
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
            self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        self.logger.notice(f'Error counters: {self.cnt}')
        self.logger.warning('Stopping helper threads. This might take a '
                            'minute')
        self.logger.warning('Closing the CAN channel.')
        self.__pill2kill.set()
        if self.__busOn:
            if self.__interface == 'Kvaser':
                try:
                    self.__canMsgThread.join()
                except RuntimeError:
                    pass
                self.logger.warning('Going in \'Bus Off\' state.')
                self.__ch.busOff()
                self.__ch.close()
            elif self.__interface == 'AnaGate': 
                self.__ch.close()
            else:
                self.__ch.shutdown()
                #channel = "can" + str(self.__channel)
                        
        self.__busOn = False
        self.logger.warning('Stopping the server.')

    async def read_sdo_can_sync(self, nodeId=None, index=None, subindex=None, timeout=2000, max_data_bytes=8,
                                SDO_TX=0x600, SDO_RX=0x580, cobid=None):
        """Read an object via |SDO|
        Currently expedited and segmented transfer is supported by this method.
        The function will writing the dictionary request from the master to the node then read the response from
        the node to the master
        The user has to decide how to decode the data.
        """
        self.logger.info('Reading an object via |SDO|')
        channel = self.__channel
        if nodeId is None or index is None or subindex is None or channel is None:
            self.logger.warning('SDO read protocol cancelled before it could begin.')
            return None

        self.cnt['SDO read total'] += 1
        self.logger.info(f'Send SDO read request to node {nodeId}')

        cobid = SDO_TX + nodeId
        msg = [0 for _ in range(max_data_bytes)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex

        can_config.sem_config_block.acquire()
        #self.logger.info("Start Communication")
        try:
            #await self.write_can_message(channel, cobid, msg, timeout=timeout)
            msg_fram = can.Message(arbitration_id=cobid, data=msg, is_extended_id=False, is_error_frame=False)
            can_config.send(channel, msg_fram, timeout) 
            self.current_subindex = subindex
            self.current_channel = channel
            self.cobid_ret = SDO_RX + nodeId
        except can.CanError as e:
            self.logger.exception(e)
            self.cnt['SDO read request timeout'] += 1
            return None
        can_config.sem_recv_block.release()
        #self.logger.info("Send Thread is waiting for receive thread to finish socket read")
        # Wait for can-message
        can_config.sem_read_block.acquire()
        #self.logger.info("Receiving is finished. Processing received data")
        can_config.sem_config_block.release()
        #self.logger.info("Communication finished")
        # Process can-messages
        message_valid = False
        error_response = False
        if self.__interface == 'socketcan':
            while not self.receive_queue.empty():
                frame = self.receive_queue.get()
                if frame is not None:
                    cobid_ret, ret, dlc, flag, t, error_frame = (frame.arbitration_id, frame.data,
                                                                 frame.dlc, frame.is_extended_id,
                                                                 frame.timestamp, frame.is_error_frame)
                    message_valid = (dlc == max_data_bytes
                                     and cobid_ret == SDO_RX + nodeId
                                     and ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42]
                                     and int.from_bytes([ret[1], ret[2]], 'little') == index
                                     and ret[3] == subindex)
                    error_response = (dlc == 8 and cobid_ret == 0x88 and ret[0] in [0x00])
                if error_response:
                    self.error_counter += 1
                    return None
                if message_valid:
                    #self.logger.info(f'msg received: {frame}')
                    break
                else:
                    self.logger.info(f'SDO read response timeout (node {nodeId}, index'
                                     f' {index:04X}:{subindex:02X})')
                    self.cnt['SDO read response timeout'] += 1
                    return None
        else:
            # Wait for response
            t0 = time.perf_counter()
            messageValid = False
            errorResponse = False
            errorReset = False
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
                    break
                
                else:
                    self.logger.info(f'SDO read response timeout (node {nodeId}, index'
                                     f' {index:04X}:{subindex:02X})')
                    self.cnt['SDO read response timeout'] += 1
                    return None, None
                self.__canMsgThread.join()#Dominic to join the thread with Pill 2 kill 
                    


        # Check command byte
        if ret[0] == 0x80:
            abort_code = int.from_bytes(ret[4:], 'little')
            self.logger.error('Received SDO abort message while reading')
            self.logger.error(f'Object: {index}')
            self.logger.error(f'Subindex: {subindex}')
            self.logger.error(f'NodeID: {nodeId}')
            self.logger.error(f'Abort code: {abort_code}')
            self.cnt['SDO read abort'] += 1
            return None
        # Here some Bitwise Operators are needed to perform  bit by bit operation
        # ret[0] =67 [bin(ret[0]) = 0b1000011] //from int to binary
        # (ret[0] >> 2) will divide ret[0] by 2**2 [Returns ret[0] with the bits shifted to the right by 2 places. = 0b10000]
        # (ret[0] >> 2) & 0b11 & Binary AND Operator [copies a bit to the result if it exists in both operands = 0b0]
        # 4 - ((ret[0] >> 2) & 0b11) for expedited transfer the object dictionary does not get larger than 4 bytes.
        n_data_bytes = 4 - ((ret[0] >> 2) & 0b11) if ret[0] != 0x42 else 4
        data = []
        for i in range(n_data_bytes): 
            data.append(ret[4 + i])
        self.logger.info(f'Got data: {data}')
        return cobid_ret, int.from_bytes(data, 'little')
    
    
    async def read_sdo_can_thread(self, nodeId=None, index=None, subindex=None, timeout=100, max_data_bytes=8, SDO_TX=None, SDO_RX=None, cobid=None):
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
        self.cnt['SDO read total'] += 1
        self.logger.info(f'Send SDO read request to node {nodeId}.')
        msg = [0 for i in range(max_data_bytes)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex
        try:
            await self.write_can_message(cobid, msg, timeout=timeout)
        except CanGeneralError:
            self.cnt['SDO read request timeout'] += 1
            return None
        # Wait for response
        t0 = time.perf_counter()
        messageValid = False
        errorResponse = False
        errorReset = False
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
            self.logger.info(f'SDO read response timeout (node {nodeId}, index'
                             f' {index:04X}:{subindex:02X})')
            self.cnt['SDO read response timeout'] += 1
            return None, None
        self.__canMsgThread.join()#Dominic to join the thread with Pill 2 kill 
    
        # Check command byte
        if ret[0] == (0x80):
            abort_code = int.from_bytes(ret[4:], 'little')
            self.logger.error(f'Received SDO abort message while reading '
                              f'object {index:04X}:{subindex:02X} of node '
                              f'{nodeId} with abort code {abort_code:08X}')
            self.cnt['SDO read abort'] += 1
            return None, None
        # Here some Bitwise Operators are needed to perform  bit by bit operation
        # ret[0] =67 [bin(ret[0]) = 0b1000011] //from int to binary
        # (ret[0] >> 2) will divide ret[0] by 2**2 [Returns ret[0] with the bits shifted to the right by 2 places. = 0b10000]
        # (ret[0] >> 2) & 0b11 & Binary AND Operator [copies a bit to the result if it exists in both operands = 0b0]
        # 4 - ((ret[0] >> 2) & 0b11) for expedited transfer the object dictionary does not get larger than 4 bytes.
        n_data_bytes = 4 - ((ret[0] >> 2) & 0b11) if ret[0] != 0x42 else 4
        data = []
        for i in range(n_data_bytes): 
            data.append(ret[4 + i])
        self.logger.info(f'Got data: {data}')
        return cobid_ret, int.from_bytes(data, 'little')
    
    def return_valid_message(self, nodeId, index, subindex, cobid_ret, data_ret, dlc, error_frame, SDO_TX, SDO_RX):
        # The following are the only expected response
        messageValid = False
        errorReset = False  # check any reset signal from the chip
        errorResponse = False  # SocketCAN error message
    
        errorReset = (dlc == 8 
                      and cobid_ret == 0x700 + nodeId 
                      and data_ret[0] in [0x05, 0x08]) 
    
        errorResponse = (dlc == 8 
                         and cobid_ret == 0x88 
                         and data_ret[0] in [0x00]) 
    
        messageValid = (dlc == 8 
                and cobid_ret == SDO_RX + nodeId
                and data_ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42] 
                and int.from_bytes([data_ret[1], data_ret[2]], 'little') == index
                and data_ret[3] == subindex)       
        # Check the validity
        if errorReset:
            cobid_ret, data_ret, dlc, flag, t, error_frame = self.read_can_message()
            messageValid = (dlc == 8 
                    and cobid_ret == SDO_RX + nodeId
                    and data_ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42] 
                    and int.from_bytes([data_ret[1], data_ret[2]], 'little') == index
                    and data_ret[3] == subindex)
    
        if errorResponse:
            # there is a scenario where the chip reset and send an error message after
            # This loop will:
            # 1. read the can reset signal
            # 2. read the next can message and check its validity
            try:
                cobid_ret, data_ret, dlc, flag, t, error_frame = self.read_can_message(timeout=1.0)
            except Exception:
                self.logger.error("Cannot read messages from the bus")
            errorReset = (dlc == 8 and cobid_ret == 0x700 + nodeId and data_ret[0] in [0x05, 0x08]) 
            if (errorReset):
                cobid_ret, data_ret, dlc, flag, t, error_frame = self.read_can_message(timeout=1.0)
                messageValid = (dlc == 8 
                        and cobid_ret == SDO_TX + nodeId
                        and data_ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42] 
                        and int.from_bytes([data_ret[1], data_ret[2]], 'little') == index
                        and data_ret[3] == subindex)
            else:
               return None
    
        if messageValid:
            nDatabytes = 4 - ((data_ret[0] >> 2) & 0b11) if data_ret[0] != 0x42 else 4
            data = []
            for i in range(nDatabytes): 
                data.append(data_ret[4 + i])
            return int.from_bytes(data, 'little')
    
        else:
            self.logger.info(f'SDO read response timeout (node {nodeId}, index'
                 f' {index:04X}:{subindex:02X})')
            self.cnt['SDO read response timeout'] += 1
            return None
    
    async def read_sdo_can(self, nodeId=None, index=None, subindex=None, timeout=100, max_data_bytes=8, SDO_TX=0x600, SDO_RX=0x580):
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
        if nodeId is None or index is None or subindex is None:
            self.logger.warning('SDO read protocol cancelled before it could begin.')         
            return None
        self.cnt['SDO read total'] += 1
        cobid = SDO_TX + nodeId
        msg = [0 for i in range(max_data_bytes)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex
        try:
            await self.write_can_message(cobid, msg, timeout=timeout)
        except CanGeneralError:
            self.cnt['SDO read request timeout'] += 1
            return None
        _frame = self.read_can_message()
        if (_frame):
           cobid_ret, ret, dlc, flag, t, error_frame = _frame
           data_ret = self.return_valid_message(nodeId, index, subindex, cobid_ret, ret, dlc, error_frame, SDO_TX, SDO_RX)
           # Check command byte
           if ret[0] == (0x80):
                abort_code = int.from_bytes(data_ret[4:], 'little')
                self.logger.error(f'Received SDO abort message while reading '
                                  f'object {index:04X}:{subindex:02X} of node '
                                  f'{nodeId} with abort code {abort_code:08X}')
                self.cnt['SDO read abort'] += 1
                return None            
           else:
                return data_ret      
    

    async def  write_can_message(self, cobid, data, flag=0, timeout=None):
        """Combining writing functions for different |CAN| interfaces
        Parameters
        ----------
        cobid : :obj:`int`
            |CAN| identifier
        data : :obj:`list` of :obj:`int` or :obj:`bytes`
            Data bytes
        flag : :obj:`int`, optional
            Message flag (|RTR|, etc.). Defaults to zero.
        timeout : :obj:`int`, optional
            |SDO| write timeout in milliseconds. When :data:`None` or not
            given an infinit timeout is used.
        """
        if self.__interface == 'Kvaser':
            if timeout is None:
                timeout = 0xFFFFFFFF
            frame = Frame(id_=cobid, data=data, timestamp=None)#, flags=canlib.MessageFlag.EXT)  #  from tutorial
            self.__ch.writeWait(frame, timeout) #
        
        elif self.__interface == 'AnaGate':
            if not self.__ch.deviceOpen:
                self.logger.notice('Reopening AnaGate CAN interface')
            self.__ch.write(cobid, data, flag)
        else:
            msg = can.Message(arbitration_id=cobid, data=data, is_extended_id=False, is_error_frame=False)
            try:
                self.__ch.send(msg, timeout)
            except:  # can.CanError:
                self.logger.error("An Error occurred, The bus is not active")
                # self.hardware_config(str(self.__channel), self.__interface)
            
    def hardware_config(self, bitrate, channel, interface, sjw,samplepoint,tseg1,tseg2):
        '''
        Pass channel string (example 'can0') to configure OS level drivers and interface.
        '''
        if interface == "socketcan":
            _bus_type = "can"
            _can_channel = _bus_type + channel
            self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
            os.system(". " + rootdir + "/socketcan_wrapper_enable.sh %i %s %s %s %s %s %s" % (bitrate, samplepoint, sjw, _can_channel, _bus_type,tseg1,tseg2))
        elif interface == "virtual":
            _bus_type = "vcan"
            _can_channel = _bus_type + channel
            self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
            os.system(". " + rootdir + "/socketcan_wrapper_enable.sh %i %s %s %s %s %s %s" % (bitrate, samplepoint, sjw, _can_channel, _bus_type,tseg1,tseg2))
        else:
            _can_channel = channel
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
                        frame = self.__ch.read(100)
                    cobid, data, dlc, flag, t = (frame.id, frame.data,
                                                 frame.dlc, frame.flags,
                                                 frame.timestamp)
                    error_frame = None
                    if frame is None or (cobid == 0 and dlc == 0):
                        raise canlib.CanNoMsg
                
                elif _interface == 'AnaGate':
                    cobid, data, dlc, flag, t = self.__ch.getMessage()
                    if (cobid == 0 and dlc == 0):
                        raise analib.CanNoMsg
                else:
                    frame = self.__ch.recv(timeout=1.0)
                    if frame is None:
                        self.__pill2kill.set()
                        # raise can.CanError
                    cobid, data, dlc, flag, t , error_frame = frame.arbitration_id, frame.data, frame.dlc, frame.is_extended_id, frame.timestamp, frame.is_error_frame
                with self.__lock:
                    self.__canMsgQueue.appendleft((cobid, data, dlc, flag, t))
                self.dumpMessage(cobid, data, dlc, flag, t)
                return cobid, data, dlc, flag, t, error_frame
            except:  # (canlib.CanNoMsg, analib.CanNoMsg,can.CanError):
               self.__pill2kill = Event()
               return None, None, None, None, None, None

    def read_can_message(self, timeout=1.0):
        """Read incoming |CAN| messages without storing any Queue
        This method runs an endless loop which can only be stopped by setting
        """
        try:        
            if self.__interface == 'Kvaser':
                    with self.__kvaserLock:#Added for urgent cases
                        frame = self.__ch.read(100)
                    cobid, data, dlc, flag, t = (frame.id, frame.data,
                                                 frame.dlc, frame.flags,
                                                 frame.timestamp)
                    error_frame = None
                    if frame is None or (cobid == 0 and dlc == 0):
                        raise canlib.CanNoMsg
                
            elif self.__interface == 'AnaGate':
                cobid, data, dlc, flag, t = self.__ch.getMessage()
                error_frame = None
                #return cobid, data, dlc, flag, t, error_frame
                if (cobid == 0 and dlc == 0):
                    raise analib.CanNoMsg
            else:
                frame = self.__ch.recv(timeout=timeout)   
                if frame is not None:
                    # raise can.CanError
                    cobid, data, dlc, flag, t , error_frame = (frame.arbitration_id, frame.data,
                                                               frame.dlc, frame.is_extended_id,
                                                               frame.timestamp, frame.is_error_frame)
            return cobid, data, dlc, flag, t, error_frame
        except:  # (canlib.CanNoMsg, analib.CanNoMsg,can.CanError):
            return None, None, None, None, None, None
        
        
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

    # Setter and getter functions
    def set_interface(self, x):
        self.__interface = x

    def set_nodeList(self, x):
        self.__nodeList = x
    
    def set_channelPorts(self, x):
        self.__channelPorts = x
            
    def set_channel(self, x):
        self.__channel = x
    
    def set_ipAddress(self, x):
        self.__ipAddress = x
        
    def set_bitrate(self, bitrate):
        if self.__interface == 'Kvaser':
            self.__bitrate = bitrate
        else:
            self.__bitrate = bitrate 
 
    def set_sample_point(self, x):
        self.__sample_point = float(x)
                   
    def get_DllVersion(self):
        ret = analib.wrapper.dllInfo()
        return ret
    
    def get_nodeList(self):
        return self.__nodeList

    def get_channelPorts(self):
        return self.__channelPorts
        
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

    @property
    def pill2kill(self):
        """:class:`threading.Event` : Stop event for the message collecting
        method :meth:`read_can_message_thread`"""
        return self.__pill2kill
    
    # @property
    def channel(self):
        """Currently used |CAN| channel. The actual class depends on the used
        |CAN| interface."""
        return self.__ch

    @property
    def bitRate(self):
        """:obj:`int` : Currently used bit rate. When you try to change it
        :func:`stop` will be called before."""
        if self.__interface == 'Kvaser':
            return self.__bitrate
        else:
            return self.__ch.baudrate
     
    @bitRate.setter
    def bitRate(self, bitrate):
        if self.__interface == 'Kvaser':
            self.stop()
            self.__bitrate = bitrate
            self.start()
        else:
            self.__ch.baudrate = bitrate     

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