# This File is setting up the CAN Channels on the RPI on the beginning
# Possible updates: Watchdog on Channel Health while system is running
import logger_setup
import logging
import can
from analysisUtils import AnalysisUtils
import subprocess


class CanConfig:
    """description of class"""

    def __init__(self, file, directory):

        self._file = file
        self._directory = directory

        self._can_channels = ['channel0', 'channel1']
        self._can_settings_attr = ['Bitrate', 'Channel', 'SamplePoint', 'SJW', 'tseg1', 'tseg2', 'ipAddress', 'Timeout']

        self.can_0_settings = {}
        self.can_1_settings = {}

        _canSettings = AnalysisUtils().open_yaml_file(file=self._file, directory=self._directory)

        self._interface = _canSettings['CAN_Interfaces']
        self.ch0 = None
        self.ch1 = None
        self._busOn0 = False
        self._busOn1 = False

        for channel in self._can_channels:
            for value in _canSettings[channel]:
                if channel == self._can_channels[0]:
                    self.can_0_settings[f'{value}'] = _canSettings[channel][f'{value}']
                else:
                    self.can_1_settings[f'{value}'] = _canSettings[channel][f'{value}']

        self.logger = logging.getLogger('mopshub_log.can_config')

    def can_setup(self):
        subprocess.call(['sh', './can_setup.sh', f"{self.can_0_settings['Bitrate']}", f"{self.can_0_settings['tseg1']}",
                         f"{self.can_0_settings['tseg2']}", f"{self.can_0_settings['SJW']}",
                         f"{self.can_0_settings['SamplePoint']}", f"{self.can_1_settings['Bitrate']}",
                         f"{self.can_1_settings['tseg1']}", f"{self.can_1_settings['tseg2']}",
                         f"{self.can_1_settings['SJW']}", f"{self.can_1_settings['SamplePoint']}"],
                        cwd='/home/pi/mopsopc-for-beginners-master/config')

        self.set_channel_connection(self.can_0_settings['Channel'])
        self.set_channel_connection(self.can_1_settings['Channel'])

    def set_channel_connection(self, channel):
        # Set the internal attribute for the |CAN| channel
        # The function is important to initialise the channel
        if channel is None:
            self.logger.error('Missing definition which channel should be set!')
            return 0

        try:
            if channel == self.can_0_settings['Channel']:
                channel = "can" + str(self.can_0_settings['Channel'])
                self.ch0 = can.interface.Bus(bustype=self._interface, channel=channel,
                                             bitrate=self.can_0_settings['Bitrate'])
                self._busOn0 = True
            elif channel == self.can_1_settings['Channel']:
                channel = "can" + str(self.can_1_settings['Channel'])
                self.ch1 = can.interface.Bus(bustype=self._interface, channel=channel,
                                             bitrate=self.can_1_settings['Bitrate'])
                self._busOn1 = True
            self.logger.info('Setting of channel %s worked.', channel)
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Error by setting channel %s.', channel)
            self.logger.info('System shutdown')
            # sys.exit(1)

    def stop(self, channel=None):
        """Close |CAN| channel
            Make sure that this is called so that the connection is closed in a
            correct manner. When this class is used within a :obj:`with` statement
            this method is called automatically when the statement is exited.
            """
        self.logger.info('Going to stop channel %s', channel)
        # with self.lock:
        # self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        # self.__pill2kill.set()
        if channel == self.can_0_settings['Channel']:
            if self._busOn0:
                self.ch0.shutdown()
                self._busOn0 = False
        elif channel == self.can_1_settings['Channel']:
            if self._busOn1:
                self.ch1.shutdown()
                self._busOn1 = False
        self.logger.info('Channel %s was stopped successful.', channel)

    def restart_channel_connection(self, channel=None):
        """Restart |CAN| channel.
        for threaded application, busOff() must be called once for each handle.
        The same applies to busOn() - the physical channel will not go off bus
        until the last handle to the channel goes off bus.
        """
        if channel is None:
            self.logger.error('Missing parameter. Can not restart channel')
            return None

        self.logger.info('Restarting Channel %s.', channel)
        # with self.lock:
        #    self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        # self.__pill2kill.set()
        if channel == self.can_0_settings['Channel']:
            if self._busOn0:
                self.ch0.shutdown()
                self.logger.info('Channel %s was stopped.', channel)
                self._busOn0 = False
                self.set_channel_connection(channel)
        elif channel == self.can_1_settings['Channel']:
            if self._busOn1:
                self.ch1.shutdown()
                self.logger.info('Channel %s was stopped.', channel)
                self._busOn1 = False
                self.set_channel_connection(channel)
        # self.__pill2kill = Event()
        self.logger.info('Reset of Channel %s finished.', channel)


can_config = CanConfig("can_config.yml", "config")