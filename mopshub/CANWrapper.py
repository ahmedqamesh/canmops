import logging
from typing import List, Any
from threading import Thread, Event, Lock
from collections import deque, Counter
import time
from analysisUtils import AnalysisUtils
from MPconfig import MPconfig
from CANconfig import can_config
from PEconfig import power_signal
from random import randint
from analysis import Analysis
# import logger_setup
import can


class CANWrapper(MPconfig):
    """description of class"""

    def __init__(self):

        MPconfig.__init__(self)
        self.lock = Lock()
        self.__canMsgQueue = deque([], 100)
        self.__pill2kill = Event()
        self.cnt = Counter()
        self.buffer = can.BufferedReader()
        self.counter = 0

        self.logger = logging.getLogger('mopshub_log.can_wrapper')

        can_config.can_setup()

    def read_can_message_thread(self, cobid, subindex, channel, counter):
        """Read incoming |CAN| messages and store them in the queue
        :attr:`canMsgQueue`.

        This method runs an endless loop which can only be stopped by setting
        the :class:`~threading.Event` :attr:`pill2kill` and is therefore
        designed to be used as a :class:`~threading.Thread`.
        """
        # self.__pill2kill = Event()
        _interface = can_config._interface
        while not self.__pill2kill.is_set():
            try:
                if channel == can_config.can_0_settings['Channel']:
                    for msg in can_config.ch0:
                        if msg.arbitration_id == cobid and msg.data[3] == subindex:
                            frame = msg
                            break
                elif channel == can_config.can_1_settings['Channel']:
                    for msg in can_config.ch1:
                        if msg.arbitration_id == cobid and msg.data[3] == subindex:
                            frame = msg
                            break
                else:
                    return None, None, None, None, None, None
                if frame is None:
                    self.__pill2kill.set()
                    # raise can.CanError
                cobid, data, dlc, flag, t, error_frame = (frame.arbitration_id, frame.data,
                                                          frame.dlc, frame.is_extended_id,
                                                          frame.timestamp, frame.is_error_frame)
                self.logger.info('We received a msg: %s', frame)
                with self.lock:
                    self.__canMsgQueue.appendleft((cobid, data, dlc, flag, t, counter))
                return cobid, data, dlc, flag, t, error_frame
            except Exception as e:
                self.logger.exception(e)
                self.__pill2kill = Event()
                self.logger.warning('There was no msg received on channel %s', channel)
                return None, None, None, None, None, None

    def start_channel_connection(self, channel, cobid, subindex, counter):
        """
        The function will start the channel connection when sending SDO CAN message
        Parameters
        """
        self.logger.info('Starting CAN connection')
        status = False
        if channel == can_config.can_0_settings['Channel']:
            if not can_config._busOn0:
                self.logger.warning('Channel %s was not started or crashed', channel)
                can_config.restart_channel_connection(channel)
            status = True
        elif channel == can_config.can_1_settings['Channel']:
            if not can_config._busOn1:
                self.logger.warning('Channel %s was not started or crashed', channel)
                can_config.restart_channel_connection(channel)
            status = True
        if status:
            # self.read_can_message(self._timeout_ch1, channel)
            self.__canMsgThread = Thread(target=self.read_can_message_thread, args=(cobid, subindex, channel, counter))
            self.__canMsgThread.start()

    def read_sdo_can_thread(self, node_id=None, index=None, subindex=None, timeout=100, channel=None, max_data_bytes=8,
                            sdo_tx=0x600, sdo_rx=0x580):
        """Read an object via |SDO|
        Currently expedited and segmented transfer is supported by this method.
        The function will writing the dictionary request from the master to the node then read the response from
        the node to the master
        The user has to decide how to decode the data.
        """
        self.counter += 1
        counter = self.counter
        self.logger.info('Reading an object via |SDO|')
        # self.start_channel_connection(channel)
        if node_id is None or index is None or subindex is None:
            self.logger.warning('SDO read protocol cancelled before it could begin.')
            return None
        self.cnt['SDO read total'] += 1
        self.logger.info('Send SDO read request to node %s', node_id)
        cobid = sdo_tx + node_id
        msg = [0 for i in range(max_data_bytes)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex
        try:
            self.start_channel_connection(channel, sdo_rx + node_id, subindex, counter)
            self.write_can_message(channel, cobid, msg, timeout=timeout)
        except Exception as e:
            self.logger.exception(e)
            self.cnt['SDO read request timeout'] += 1
            return None

        # Wait for response
        t0 = time.perf_counter()
        message_valid = False
        error_response = False
        while time.perf_counter() - t0 < timeout / 1000:
            with self.lock:
                # check the message validity [node id, msg size,...]
                for i, (cobid_ret, ret, dlc, flag, t, counter_rec) in zip(range(len(self.__canMsgQueue)),
                                                                          self.__canMsgQueue):
                    if counter != counter_rec:
                        self.logger.error('Loop counter %s is not the same as Thread counter %s',
                                          counter, counter_rec)
                    message_valid = (dlc == 8
                                     and cobid_ret == sdo_rx + node_id
                                     and ret[0] in [0x80, 0x43, 0x47, 0x4b, 0x4f, 0x42]
                                     and int.from_bytes([ret[1], ret[2]], 'little') == index
                                     and ret[3] == subindex)
                    # errorResponse is meant to deal with any disturbance in the signal due to the reset of the chip
                    error_response = (dlc == 8 and cobid_ret == 0x88 and ret[0] in [0x00])
            if message_valid or error_response:
                del self.__canMsgQueue[i]
                break
            if message_valid:
                break
            if error_response:
                return cobid_ret, None
        else:
            self.logger.info('SDO read response timeout.')
            self.logger.info('NodeID: %s', node_id)
            self.logger.info('Index: %s', index)
            self.logger.info('Subindex: %s', subindex)
            self.cnt['SDO read response timeout'] += 1
            return None

        # Check command byte
        if ret[0] == 0x80:
            abort_code = int.from_bytes(ret[4:], 'little')
            self.logger.error('Received SDO abort message while reading')
            self.logger.error('Object: %s', index)
            self.logger.error('Subindex: %s', subindex)
            self.logger.error('NodeID: %s', node_id)
            self.logger.error('Abort code: %s', abort_code)
            self.cnt['SDO read abort'] += 1
            return None, None

        n_data_bytes = 4 - ((ret[0] >> 2) & 0b11) if ret[0] != 0x42 else 4
        data = []
        for i in range(n_data_bytes):
            data.append(ret[4 + i])
        self.logger.info('Got data %s', data)
        return cobid_ret, int.from_bytes(data, 'little')

    def read_adc_channels(self, file, directory, node_id, mp_channel, can_channel):
        """Start actual CANopen communication
        This function contains an endless loop in which it is looped over all
        ADC channels. Each value is read using
        :meth:`read_sdo_can_thread` and written to its corresponding
        """
        # Setting Multiplexer
        try:
            self.mp_switch(mp_channel, can_channel)
            self.logger.info('MP Channel was set to %s and can channel to %s', mp_channel, can_channel)
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('MP channel %s could not be set', mp_channel)
            return None

        # Check power status
        try:
            # status = [status, locked_by_sys, locked_by_user]
            status = power_signal.check_status(mp_channel)
            if mp_channel != 31:
                if status[0] == 1 and bool(status[2]) is False and bool(status[1] is False):
                    self.logger.error('Power is not enabled on Channel %s', mp_channel)
                    power_signal.addressable_latch_mode(mp_channel, 0)
                    self.logger.info('Power for channel %s was enabled', mp_channel)
                elif bool(status[1]) is True:
                    self.logger.info('Power Channel %s is locked by sys', mp_channel)
                    self.logger.info('Power is disabled and can not be enabled for the channel %s', mp_channel)
                    return None
                elif bool(status[2]) is True:
                    self.logger.info('Power Channel %s is locked by user', mp_channel)
                    self.logger.info('Power is disabled and can not be enabled on channel %s through this routine',
                                     mp_channel)
                    return None
            else:
                if status[0] == 0 and bool(status[2]) is False and bool(status[1] is False):
                    self.logger.error('Power is not enabled on Channel %s', mp_channel)
                    power_signal.addressable_latch_mode(mp_channel, 1)
                    self.logger.info('Power for channel %s was enabled', mp_channel)
                elif bool(status[1]) is True:
                    self.logger.info('Power Channel %s is locked by sys', mp_channel)
                    self.logger.info('Power is disabled and can not be enabled for the channel %s', mp_channel)
                    return None
                elif bool(status[2]) is True:
                    self.logger.info('Power Channel %s is locked by user', mp_channel)
                    self.logger.info('Power is disabled and can not be enabled on channel %s through this routine',
                                     mp_channel)
                    return None
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Error while enabling Power of channel %s', mp_channel)

        dev = AnalysisUtils().open_yaml_file(file=file, directory=directory)
        self.logger.info('Reading from yaml to get dictionary items')
        # yaml file is needed to get the object dictionary items
        _adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        _adc_index = list(dev["adc_channels_reg"]["adc_index"])[0]
        _channelItems = [int(channel) for channel in list(_adc_channels_reg)]
        _channelDesc: List[Any] = [dev["adc_channels_reg"]["adc_channels"][str(_channelItems[i])] for i in
                                   range(len(_channelItems))]

        self.logger.info('Reading ADC channels of Mops with ID %s', node_id)
        mops_readout = [[0 for _ in range(3)] for _ in range(len(_channelItems))]  # indexing: [y][x]

        if can_channel == can_config.can_0_settings['Channel']:
            timeout = can_config.can_0_settings['Timeout']
        else:
            timeout = can_config.can_1_settings['Timeout']

        # Read ADC channels
        for i in range(0, len(_channelItems)):
            subindex = _channelItems[i] - 2

            data_point = self.read_sdo_can_thread(node_id, int(_adc_index, 16), subindex,
                                                  timeout, can_channel)
            # data_point = randint(0, 100)
            if data_point is not None:
                adc_converted = Analysis().adc_conversion(str(_channelDesc[i]), data_point[0])
                adc_converted = round(adc_converted, 3)
                adc_converted = adc_converted * 100 * randint(10, 100)
                mops_readout[i][0] = (_channelItems[i])  # adc channel_index
                # mops_readout[i][1] = data_point
                mops_readout[i][1] = int(adc_converted)  # datapoint of channel read
                mops_readout[i][2] = str(_channelDesc[i])  # description of channel
                self.logger.info('Got data for ADC channel %s = %s', subindex, data_point)
        return mops_readout

    def confirm_nodes(self, channel: int, node_id: int):
        self.logger.info('Testing Connection')

        if node_id is None or channel is None:
            self.logger.error('Missing parameter. Can not confirm nodes')
            return 0

        cobid_tx = 0x700 + node_id

        if channel == can_config.can_0_settings['Channel']:
            _timeout = can_config.can_0_settings['Timeout']
        else:
            _timeout = can_config.can_1_settings['Timeout']
        self.write_can_message(channel, cobid_tx, [0, 0, 0, 0, 0, 0, 0, 0], timeout=_timeout)
        # receive the message
        can_msg_rx = self.read_can_message(_timeout, channel)
        if can_msg_rx is not None:
            cobid_rx, data, _, _, _, _ = can_msg_rx
            if cobid_rx == cobid_tx and (data[0] == 0x85 or data[0] == 0x05):
                self.logger.info('Connection to Mops verified. NodeID: %s', node_id)
                return True
            else:
                self.logger.error('Connection Error! Mops NodeID: %s', node_id)
                return False
        else:
            self.logger.error('No msg received. ERROR while confirming Mops with NodeID: %s', node_id)
            return False

    def read_can_message(self, timeout=1.0, channel=None):
        try:
            if channel == can_config.can_0_settings['Channel']:
                frame = can_config.ch0.recv(timeout=timeout)
            elif channel == can_config.can_1_settings['Channel']:
                frame = can_config.ch1.recv(timeout=timeout)
            else:
                return None
            self.logger.info('Reading from channel %s', channel)
            if frame is not None:
                cobid, data, dlc, flag, t, error_frame = (frame.arbitration_id, frame.data,
                                                          frame.dlc, frame.is_extended_id,
                                                          frame.timestamp, frame.is_error_frame)
            else:
                return None
            self.logger.info('Reading was successful.')
            self.logger.info(frame)
            return cobid, data, dlc, flag, t, error_frame
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('No msg could read from channel %s.', channel)
            return None

    def write_can_message(self, channel, cobid, data, timeout):
        # Writing function for SocketCAN interface
        msg = can.Message(arbitration_id=cobid, data=data, is_extended_id=False, is_error_frame=False)
        try:
            if channel == can_config.can_0_settings['Channel'] and can_config._busOn0 is True:
                can_config.ch0.send(msg, timeout)
            elif channel == can_config.can_1_settings['Channel'] and can_config._busOn1 is True:
                can_config.ch1.send(msg, timeout)
            self.logger.info('Sending msg on channel %s. Cobid: %s', channel, cobid)
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('ERROR while sending msg on channel', channel)
