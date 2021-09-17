# This File is setting up the CAN Channels on the RPI on the beginning
# Possible updates: Watchdog on Channel Health while system is running

import logging
import can
import subprocess
import threading
import os
from .logger_main import Logger
from .analysis_utils import AnalysisUtils
from .watchdog_can_interface import WATCHCan
import time
config_file = "socketcan_CANSettings.yml"
rootdir = os.path.dirname(os.path.abspath(__file__))
config_dir = "config"
lib_dir = rootdir[:-8]
class CanConfig(WATCHCan):
    """description of class"""
    def __init__(self, file='socketcan_CANSettings.yml', directory=config_dir):

        WATCHCan.__init__(self)
        self._file = file
        self._directory = directory
        #self.logger = logging.getLogger('CAN config')
        self.logger = Logger().setup_main_logger(name = "CAN Config ",console_loglevel=logging.INFO, logger_file = False)
        
        _canSettings = AnalysisUtils().open_yaml_file(file=self._file, directory=self._directory)
        self._can_channels = list(_canSettings)[1:]#['channel0', 'channel1']
        self._can_settings_attr = ['bitrate', 'channel', 'samplePoint', 'SJW', 'tseg1', 'tseg2', 'ipAddress', 'timeout']

        self.can_0_settings = {}
        self.can_1_settings = {}

       
        self._interface = _canSettings['CAN_Interfaces']
        self.sem_read_block = threading.Semaphore(value=0)
        self.sem_recv_block = threading.Semaphore(value=0)
        self.sem_config_block = threading.Semaphore()
        self.ch0 = None
        self.ch1 = None
        self._busOn0 = False
        self._busOn1 = False
        can.util.set_logging_level('warning')

        for channel in self._can_channels:
            for value in _canSettings[channel]:
                if channel == self._can_channels[0]:
                    self.can_0_settings[f'{value}'] = _canSettings[channel][f'{value}']
                else:
                    self.can_1_settings[f'{value}'] = _canSettings[channel][f'{value}']

    def send(self, channel: int, msg: can.message, timeout: int):
        try:
            if channel == self.can_0_settings['channel']:
                if self._busOn0 is True:
                    self.ch0.send(msg, timeout)
                else:
                    self.restart_channel_connection(channel)
                    self.ch0.send(msg, timeout)
            elif channel == self.can_1_settings['channel']:
                if self._busOn1 is True:
                    self.ch1.send(msg, timeout)
                else:
                    self.restart_channel_connection(channel)
                    self.ch1.send(msg, timeout)
        except can.CanError:
            return can.CanError

    def receive(self, channel: int):
        try:
            if channel == self.can_0_settings['channel']:
                if self._busOn0 is True:
                    frame = self.ch0.recv(0.0)
                    return frame
                else:
                    self.restart_channel_connection(channel)
                    frame = self.ch0.recv(0.0)
                    return frame
            elif channel == self.can_1_settings['channel']:
                if self._busOn1 is True:
                    frame = self.ch1.recv(0.0)
                    return frame
                else:
                    self.restart_channel_connection(channel)
                    frame = self.ch0.recv(0.0)
                    return frame
        except can.CanError:
            return can.CanError

    def can_setup(self, channel: int, interface : str):
        self.logger.info("Resetting CAN Interface as soon as communication threads are finished")
        self.sem_config_block.acquire()
        self.logger.info("Resetting CAN Interface")
        self.set_interface(interface)
        if channel == self.can_0_settings['channel']:
            if self._busOn0:
                self.ch0.shutdown()
                subprocess.Popen(["sudo", 'bash', 'can_setup.sh', "can0", f"{self.can_0_settings['bitrate']}",
                                 f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}",
                                 f"{self.can_0_settings['SJW']}", f"{self.can_0_settings['samplePoint']}"],
                                cwd=lib_dir+"/"+config_dir)
                # subprocess.call(['sh', './socketcan_wrapper_enable.sh', f"{self.can_0_settings['bitrate']}",
                #                  f"{self.can_0_settings['samplePoint']}",f"{self.can_0_settings['SJW']}",f"{self.can_0_settings['channel']}","can",
                #                  f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}"],
                #                  cwd=lib_dir+"/canmops")
                # os.system(". " + lib_dir+"/canmops" + "/socketcan_wrapper_enable.sh %s %s %s %s %s %s %s" % ( f"{self.can_0_settings['bitrate']}",
                #                   f"{self.can_0_settings['samplePoint']}",f"{self.can_0_settings['SJW']}","can0","can",
                #                   f"{self.can_0_settings['tseg1']}", f"{self.can_0_settings['tseg2']}"))
            ch_set = self.set_channel_connection(self.can_0_settings['channel'],interface )
        elif channel == self.can_1_settings['channel']:
            if self._busOn1:
                self.ch1.shutdown()
            subprocess.call(['sh', './can_setup.sh', "can1", f"{self.can_1_settings['bitrate']}",
                             f"{self.can_1_settings['tseg1']}", f"{self.can_1_settings['tseg2']}",
                             f"{self.can_1_settings['SJW']}", f"{self.can_1_settings['samplePoint']}"],
                            cwd=lib_dir+"/"+config_dir)
            ch_set = self.set_channel_connection(self.can_1_settings['channel'])

        self.logger.info(f"Channel {channel} is set")
        self.sem_config_block.release()
        self.logger.info("Resetting of CAN Interface finished. Returning to communication.")
        return ch_set
    
    def set_channel_connection(self, channel: int, interface : str):
        """Bind |CAN| socket
           Set the internal attribute for the |CAN| channel
           The function is important to initialise the channel
            """
        try:
            if channel == self.can_0_settings['channel']:
                channel = "can" + str(self.can_0_settings['channel'])
                self.ch0 = can.interface.Bus(bustype=self._interface, channel=channel,
                                             bitrate=self.can_0_settings['bitrate'])
                self.ch0.RECV_LOGGING_LEVEL = 0
                self._busOn0 = True
                self.logger.info(f'Setting of channel {channel} worked.')
                ch_set = self.ch0
            elif channel == self.can_1_settings['channel']:
                channel = "can" + str(self.can_1_settings['channel'])
                self.ch1 = can.interface.Bus(bustype=self._interface, channel=channel,
                                             bitrate=self.can_1_settings['bitrate'])
                self.ch1.RECV_LOGGING_LEVEL = 0
                self._busOn1 = True
                self.logger.info(f'Setting of channel {channel} worked.')
                ch_set = self.ch1
            else:
                self.logger.error(f"Setting of Channel {channel} did not worked because of missing reference in dict")
                ch_set =  None
        except Exception as e:
            self.logger.exception(e)
            self.logger.error(f'Error by setting channel {channel}.')
        return ch_set
        

    def stop_channel(self, channel: int):
        """Close |CAN| channel
            Make sure that this is called so that the connection is closed in a
            correct manner. When this class is used within a :obj:`with` statement
            this method is called automatically when the statement is exited.
            """
        self.logger.info(f'Going to stop channel {channel}')
        if channel == self.can_0_settings['channel']:
            if self._busOn0:
                self.ch0.shutdown()
                self._busOn0 = False
                self.logger.info(f'Channel {channel} was stopped successful.')
        elif channel == self.can_1_settings['channel']:
            if self._busOn1:
                self.ch1.shutdown()
                self._busOn1 = False
                self.logger.info(f'Channel {channel} was stopped successful.')
        else:
            self.logger.error(f"Stopping Channel {channel} did not worked because of missing reference in dict")

    def restart_channel_connection(self, channel: int):
        """Restart |CAN| channel.
        for threaded application, busOff() must be called once for each handle.
        The same applies to busOn() - the physical channel will not go off bus
        until the last handle to the channel goes off bus.
        """
        self.logger.info(f'Restarting Channel {channel}.')
        if channel == self.can_0_settings['channel']:
            if self._busOn0:
                self.ch0.shutdown()
                self.logger.info(f'Channel {channel} was stopped.')
                self._busOn0 = False
                self.set_channel_connection(channel)
                self.logger.info(f'Reset of Channel {channel} finished.')
        elif channel == self.can_1_settings['channel']:
            if self._busOn1:
                self.ch1.shutdown()
                self.logger.info(f'Channel {channel} was stopped.')
                self._busOn1 = False
                self.set_channel_connection(channel)
                self.logger.info(f'Reset of Channel {channel} finished.')
        else:
            self.logger.error(f"Restart of Channel {channel} did not worked because of missing reference in dict")
    def set_interface(self, x):
        self.__interface = x
        
    def get_interface(self):
        """:obj:`str` : Vendor of the CAN interface. Possible values are
        ``'Kvaser'`` and ``'AnaGate'``."""
        return self.__interface

can_config = CanConfig()
can_config.watchdog_notifier.subscribe("restart Interface", can_config.can_setup)
