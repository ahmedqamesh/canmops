import logging
from typing import List, Any
from threading import Thread, Event, Lock
from collections import deque, Counter
import time
from analysisUtils import AnalysisUtils
from analysis import Analysis
from CANconfig import CANconfig
from MPconfig import mp
from PEconfig import pe
from random import randint


class CANWrapper(CANconfig):
    """description of class"""

    def __init__(self):
        self.lock = Lock()
        self.__canMsgQueue = deque([], 100)
        self.__pill2kill = Event()
        self.cnt = Counter()

        super(CANWrapper, self).__init__("socketcan_CANSettings.yml", "config")

    def read_can_message_thread(self):
        """Read incoming |CAN| messages and store them in the queue
        :attr:`canMsgQueue`.

        This method runs an endless loop which can only be stopped by setting
        the :class:`~threading.Event` :attr:`pill2kill` and is therefore
        designed to be used as a :class:`~threading.Thread`.
        """
        # self.__pill2kill = Event()
        _interface = self._interface
        channel = '1'
        while not self.__pill2kill.is_set():
            try:
                if channel == self._channel0:
                    frame = self.ch0.recv(timeout=1.0)
                elif channel == self._channel1:
                    frame = self.ch1.recv(timeout=1.0)
                if frame is None:
                    self.__pill2kill.set()
                    # raise can.CanError
                cobid, data, dlc, flag, t, error_frame = frame.arbitration_id, frame.data, frame.dlc, frame.is_extended_id, frame.timestamp, frame.is_error_frame
                with self.lock:
                    self.__canMsgQueue.appendleft((cobid, data, dlc, flag, t))
                return cobid, data, dlc, flag, t, error_frame
            except:
                self.__pill2kill = Event()
                logging.warning('There was no msg received on channel %s', channel)
                return None, None, None, None, None, None

    def start_channel_connection(self, channel):
        """
        The function will start the channel connection when sending SDO CAN message
        Parameters
        """
        logging.info('Starting CAN connection')
        status = False
        if str(channel) == self._channel0:
            if not self._busOn0:
                logging.warning('Channel %s was not started or crashed', channel)
                self.restart_channel_connection(channel)
            status = True
        elif str(channel) == self._channel1:
            if not self._busOn1:
                logging.warning('Channel %s was not started or crashed', channel)
                self.restart_channel_connection(channel)
            status = True
        if status:
            self.__canMsgThread = Thread(target=self.read_can_message_thread)
            self.__canMsgThread.start()

    def read_sdo_can_thread(self, nodeId=None, index=None, subindex=None, timeout=100, channel=None, MAX_DATABYTES=8,
                            SDO_TX=0x600, SDO_RX=0x580):
        """Read an object via |SDO|
        Currently expedited and segmented transfer is supported by this method.
        The function will writing the dictionary request from the master to the node then read the response from the node to the master
        The user has to decide how to decode the data.
        """
        logging.info('Reading an object via |SDO|')
        self.start_channel_connection(channel)
        if nodeId is None or index is None or subindex is None:
            logging.warning('SDO read protocol cancelled before it could begin.')
            return None
        self.cnt['SDO read total'] += 1
        logging.info('Send SDO read request to node %s', nodeId)
        cobid = SDO_TX + nodeId
        msg = [0 for i in range(MAX_DATABYTES)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex
        try:
            self.write_can_message(channel, cobid, msg, timeout=timeout)
        except:
            self.cnt['SDO read request timeout'] += 1
            return None

        # Wait for response
        t0 = time.perf_counter()
        messageValid = False
        errorResponse = False
        while time.perf_counter() - t0 < timeout / 1000:
            with self.lock:
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
            logging.info('SDO read response timeout.')
            logging.info('NodeID: %s', nodeId)
            logging.info('Index: %s', index)
            logging.info('Subindex: %s', subindex)
            self.cnt['SDO read response timeout'] += 1
            return None

        # Check command byte
        if ret[0] == (0x80):
            abort_code = int.from_bytes(ret[4:], 'little')
            logging.error('Received SDO abort message while reading')
            logging.error('Object: %s', index)
            logging.error('Subindex: %s', subindex)
            logging.error('NodeID: %s', nodeId)
            logging.error('Abort code: %s', abort_code)
            self.cnt['SDO read abort'] += 1
            return None, None

        nDatabytes = 4 - ((ret[0] >> 2) & 0b11) if ret[0] != 0x42 else 4
        data = []
        for i in range(nDatabytes):
            data.append(ret[4 + i])
        logging.info('Got data %s', data)
        return cobid_ret, int.from_bytes(data, 'little')

    def read_adc_channels(self, file, directory, nodeId, mp_channel, can_channel):
        """Start actual CANopen communication
        This function contains an endless loop in which it is looped over all
        ADC channels. Each value is read using
        :meth:`read_sdo_can_thread` and written to its corresponding
        """

        #Setting Multiplexer
        try:
            mp.mp_switch(mp_channel, can_channel)
            logging.info('MP Channel was set to %s and can channel to %s', mp_channel, can_channel)
        except:
            logging.error('MP channel %s could not be set', mp_channel)
            return None
        #Check power status
        try:
            status = pe.check_status(mp_channel)
            if status != 0:
                logging.error('Power is not enabled on Channel %s', mp_channel)
                pe.addressable_latch_mode(mp_channel, 0)
                logging.info('Power for channel %s was enabled', mp_channel)
        except:
            logging.error('Error while enabling Power of channel %s', mp_channel)
            return None

        dev = AnalysisUtils().open_yaml_file(file=file, directory=directory)
        logging.info('Reading from yaml to get dictionary items')
        # yaml file is needed to get the object dictionary items
        dictionary_items = dev["Application"]["index_items"]
        _adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        _adc_index = list(dev["adc_channels_reg"]["adc_index"])[0]
        _channelItems = [int(channel) for channel in list(_adc_channels_reg)]
        _channelDesc: List[Any] = [dev["adc_channels_reg"]["adc_channels"][str(_channelItems[i])] for i in
                                   range(len(_channelItems))]

        logging.info('Reading ADC channels of Mops with ID %s', nodeId)
        mops_readout = [[0 for x in range(3)] for y in range(len(_channelItems))]  # indexing: [y][x]

        monitoringTime = time.time()
        # Read ADC channels
        for i in range(0, len(_channelItems)):
            subindex = _channelItems[i] - 2
            #data_point = randint(0, 100)
            data_point = self.read_sdo_can_thread(nodeId, int(_adc_index, 16), subindex, self._timeout_ch0, can_channel)
            if data_point is not None:
                adc_converted = Analysis().adc_conversion(str(_channelDesc[i]), data_point[0])
                adc_converted = round(adc_converted, 3)
                adc_converted = adc_converted * 100 * randint(10, 100)
                mops_readout[i][0] = (_channelItems[i])  # adc channel_index
                mops_readout[i][1] = data_point
                mops_readout[i][1] = int(adc_converted)  # datapoint of channel read
                mops_readout[i][2] = str(_channelDesc[i])  # description of channel
                logging.info('Got data for ADC channel %s = %s', subindex, data_point)
        return mops_readout


wrapper = CANWrapper()
