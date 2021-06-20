# This File is setting up the CAN Channels on the RPI on the begining
# Possible updates: Watchdog on Channel Health while system is running

import can
from analysisUtils import AnalysisUtils


class CANconfig():
    """description of class"""

    def __init__(self, file, directory):

        self._file = file
        self._directory = directory

        _canSettings = AnalysisUtils().open_yaml_file(file=self._file, directory=self._directory)
        self._interface = _canSettings['CAN_Interfaces']
        self.ch0 = None
        self.ch1 = None
        self._channel0 = str(_canSettings['channel0']["channel"])
        self._channel1 = str(_canSettings['channel1']["channel"])
        self._bitrate_ch0 = _canSettings['channel0']["bitrate"]
        self._bitrate_ch1 = _canSettings['channel1']["bitrate"]
        self._samplePoint_ch0 = _canSettings['channel0']["samplePoint"]
        self._samplePoint_ch1 = _canSettings['channel1']["samplePoint"]
        self._sjw_ch0 = _canSettings['channel0']["SJW"]
        self._sjw_ch1 = _canSettings['channel1']["SJW"]
        self._tseg1_ch0 = _canSettings['channel0']["tseg1"]
        self._tseg1_ch1 = _canSettings['channel1']["tseg1"]
        self._tseg2_ch0 = _canSettings['channel0']["tseg2"]
        self._tseg2_ch1 = _canSettings['channel1']["tseg2"]
        self._ipAddress_ch0 = _canSettings['channel0']["ipAddress"]
        self._ipAddress_ch1 = _canSettings['channel1']["ipAddress"]
        self._timeout_ch0 = _canSettings['channel0']["timeout"]
        self._timeout_ch1 = _canSettings['channel1']["timeout"]
        self._busOn0 = False
        self._busOn1 = False

        self.set_channel_connection(self._channel0)
        self.set_channel_connection(self._channel1)

    def set_channel_connection(self, channel=None):
        # Set the internal attribute for the |CAN| channel
        # The function is important to initialise the channel

        if channel is None:
            print("Missing Parameter has to be specified!")
            return 0

        try:
            if channel == self._channel0:
                channel = "can" + str(self._channel0)
                self.ch0 = can.interface.Bus(bustype=self._interface, channel=channel, bitrate=self._bitrate_ch0)
                print("Set Channel Worked: ", self.ch0, "\n")
                self._busOn0 = True
            elif channel == self._channel1:
                channel = "can" + str(self._channel1)
                self.ch1 = can.interface.Bus(bustype=self._interface, channel=channel, bitrate=self._bitrate_ch1)
                print("Set Channel Worked: ", self.ch1, "\n")
                self._busOn1 = True
        except Exception:
            print("Error by setting channel config\n")
            # self.logger.error("TCP/IP or USB socket error in %s interface" % interface)
            # sys.exit(1)# it causes that the program is killed completely

    def confirm_nodes(self, channel=None, nodeID=None):
        # print("Testing Connection")

        if nodeID is None or channel is None:
            print("Missing Parameter has to be specified!")
            return 0

        cobid_TX = 0x700 + int(nodeID, 16)
        cobid_RX = 0x700 + int(nodeID, 16)

        if channel == self._channel0:
            _timeout = self._timeout_ch0
        else:
            _timeout = self._timeout_ch1
        self.write_can_message(channel, cobid_TX, [0, 0, 0, 0, 0, 0, 0, 0], flag=0, timeout=_timeout)
        # receive the message
        readCanMessage = self.read_can_message(_timeout, channel)
        if readCanMessage is not None:
            _cobid_RX, data, _, _, _, _ = readCanMessage
            if cobid_RX == cobid_TX and (data[0] == 0x85 or data[0] == 0x05):
                print("Connection verified! Mops NodeID:", nodeID)
            else:
                print("Connection Error! Mops NodeID:", nodeID)
        else:
            print("Error while confirming node with ID", nodeID)

    def read_can_message(self, timeout=None, channel=None):
        try:
            if channel == self._channel0:
                frame = self.ch0.recv(timeout=timeout)
            elif channel == self._channel1:
                frame = self.ch1.recv(timeout=timeout)
            if frame is not None:
                # raise can.CanError
                cobid, data, dlc, flag, t, error_frame = (frame.arbitration_id, frame.data,
                                                          frame.dlc, frame.is_extended_id,
                                                          frame.timestamp, frame.is_error_frame)
            return cobid, data, dlc, flag, t, error_frame
        except:
            return None

    def write_can_message(self, channel, cobid, data, timeout):
        # Writing function for SocketCAN interface
        msg = can.Message(arbitration_id=cobid, data=data, is_extended_id=False, is_error_frame=False)
        try:
            if channel == self._channel0 and self._busOn0 is True:
                self.ch0.send(msg, timeout)
            elif channel == self._channel1 and self._busOn1 is True:
                self.ch1.send(msg, timeout)
        except:
            print("CAN Error in Loop write_can_message\n")

    def stop(self, channel=None):
        """Close |CAN| channel
            Make sure that this is called so that the connection is closed in a
            correct manner. When this class is used within a :obj:`with` statement
            this method is called automatically when the statement is exited.
            """
        print("Going to stop the Server")
        # with self.lock:
        # self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        # self.logger.notice(f'Error counters: {self.cnt}')
        # self.logger.warning('Stopping helper threads. This might take a '
        # 'minute')
        # self.logger.warning('Closing the CAN channel.')
        # self.__pill2kill.set()
        if channel == self._channel0:
            if self._busOn0:
                self.ch0.shutdown()
                self._busOn0 = False
                print("Server Stopped: ", self.ch0, "\n")
        elif channel == self._channel1:
            if self._busOn1:
                self.ch1.shutdown()
                self._busOn1 = False
                print("Server Stopped: ", self.ch1, "\n")
        # self.logger.warning('Stopping the server.')

    def restart_channel_connection(self, channel=None):
        """Restart |CAN| channel.
        for threaded application, busOff() must be called once for each handle.
        The same applies to busOn() - the physical channel will not go off bus
        until the last handle to the channel goes off bus.
        """
        if channel is None:
            print("Missing Parameter")
            return None

        # self.logger.warning('Resetting the CAN channel.')
        # Stop the bus
        # with self.lock:
        #    self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        # self.__pill2kill.set()
        if channel == self._channel0:
            if self._busOn0:
                print("Stop Server")
                self.ch0.shutdown()
                self._busOn0 = False
                self.set_channel_connection(channel)
        elif channel == self._channel1:
            if self._busOn1:
                print("Stop Server")
                self.ch1.shutdown()
                self._busOn1 = False
                self.set_channel_connection(channel)
        # self.__pill2kill = Event()
        print("Channel was reseted\n")
        # self.logger.notice('The channel is reset')
