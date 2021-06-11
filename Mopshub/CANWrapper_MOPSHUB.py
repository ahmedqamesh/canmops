import can
from threading import Thread, Event, Lock
from collections import deque, Counter
import time
from analysisUtils import AnalysisUtils
import csv
import numpy as np
from tqdm import tqdm
from analysis import Analysis

class CANWrapper():
    """description of class"""

    def __init__(self, interface=None, channel=None, bitrate=None, samplePoint=None, sjw=None,ipAddress=None, tseg1 = None, tseg2 = None):
        self.ch = None
        self.channel = 1
        self.interface = "socketcan"
        self.bitrate = 125000
        self.samplePoint = None
        self.sjw = None
        self.tseg1 = None
        self.tseg2 = None
        self.__busOn = True
        self.lock = Lock()
        self.__canMsgQueue = deque([], 100)
        self.__pill2kill = Event()
        self.cnt = Counter()

        super(CANWrapper, self).__init__()

        self.set_channel_connection(interface=self.interface)


    def set_channel_connection(self, interface):
        #Set the internal attribute for the |CAN| channel
        #The function is important to initialise the channel
        try:
            channel = "can" + str(self.channel)
            self.ch = can.interface.Bus(bustype=interface, channel=channel, bitrate=self.bitrate)
            print("Set Channel Worked:\n")
            print(self.ch)
        except Exception:
            print("Error by setting channel config\n")
            #self.logger.error("TCP/IP or USB socket error in %s interface" % interface)
            # sys.exit(1)# it causes that the program is killed completely     

    def confirm_nodes(self, channel=0, timeout=100):
        print("Testing Connection\n")
        cobid_TX = 0x700 + 1        #only for testing
        cobid_RX = 0x700 + 1        #only for testing
        self.write_can_message(cobid_TX, [0, 0, 0, 0, 0, 0, 0, 0], flag=0, timeout=200)
        # receive the message
        readCanMessage = self.read_can_message()
        if readCanMessage is not None:
            cobid_RX, data, _, _, _, _ = readCanMessage
        if cobid_RX == cobid_TX and (data[0] == 0x85 or data[0] == 0x05):
            print("Connection verified!\n")
            print(readCanMessage)
        else:
            print("Connection Error!\n")
            print(readCanMessage)

    def write_can_message(self, cobid, data, flag=0, timeout=None): 
        #Writing function for SocketCAN interface
        msg = can.Message(arbitration_id=cobid, data=data, is_extended_id=False, is_error_frame=False)
        try:
            self.ch.send(msg, timeout)
        except:  
            print("CAN Error in Loop write_can_message")

    def read_can_message(self, timeout=1.0):
        try:        
            frame = self.ch.recv(timeout=timeout)   
            if frame is not None:
                # raise can.CanError
                cobid, data, dlc, flag, t , error_frame = (frame.arbitration_id, frame.data,
                                                            frame.dlc, frame.is_extended_id,
                                                            frame.timestamp, frame.is_error_frame)
            return cobid, data, dlc, flag, t, error_frame
        except:
            return None, None, None, None, None, None

    def read_can_message_thread(self):
        """Read incoming |CAN| messages and store them in the queue
        :attr:`canMsgQueue`.

        This method runs an endless loop which can only be stopped by setting
        the :class:`~threading.Event` :attr:`pill2kill` and is therefore
        designed to be used as a :class:`~threading.Thread`.
        """
        #self.__pill2kill = Event()
        _interface = self.interface;
        while not self.__pill2kill.is_set(): 
            try:
                frame = self.ch.recv(timeout=1.0)
                if frame is None:
                    self.__pill2kill.set()
                    # raise can.CanError
                    cobid, data, dlc, flag, t , error_frame = frame.arbitration_id, frame.data, frame.dlc, frame.is_extended_id, frame.timestamp, frame.is_error_frame
                with self.lock:
                    self.__canMsgQueue.appendleft((cobid, data, dlc, flag, t))
                self.dumpMessage(cobid, data, dlc, flag, t)
                return cobid, data, dlc, flag, t, error_frame
            except:  # (canlib.CanNoMsg, analib.CanNoMsg,can.CanError):
               self.__pill2kill = Event()
               return None, None, None, None, None, None

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
        
        msgstr = '{:3X} {:d}   '.format(cobid, dlc)
        for i in range(len(msg)):
            msgstr += '{:02x}  '.format(msg[i])
        msgstr += '    ' * (8 - len(msg))
        st = datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
        msgstr += str(st)
        #self.logger.info(msgstr)


    def stop(self):
        """Close |CAN| channel
        Make sure that this is called so that the connection is closed in a
        correct manner. When this class is used within a :obj:`with` statement
        this method is called automatically when the statement is exited.
        """
        print("Going to stop the Server\n")
        with self.lock:
            self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        #self.logger.notice(f'Error counters: {self.cnt}')
        #self.logger.warning('Stopping helper threads. This might take a '
                            #'minute')
        #self.logger.warning('Closing the CAN channel.')
        self.__pill2kill.set()
        if self.__busOn:
                self.ch.shutdown()
                channel = "can" + str(self.channel)      
        self.__busOn = False
        #self.logger.warning('Stopping the server.')
        print("Server Stopped\n")

    def restart_channel_connection(self, interface = None):
        """Restart |CAN| channel.
        for threaded application, busOff() must be called once for each handle. 
        The same applies to busOn() - the physical channel will not go off bus
        until the last handle to the channel goes off bus.   
        
        """  
        if interface is None: 
            _interface = self.interface
        else:
            _interface = interface
            
        #self.logger.warning('Resetting the CAN channel.')
        #Stop the bus
        with self.lock:
            self.cnt['Residual CAN messages'] = len(self.__canMsgQueue)
        self.__pill2kill.set()
        if self.__busOn:
                print("Stop Server")
                self.ch.shutdown()
                channel = "can" + str(self.channel)              
        self.__busOn = False
        self.set_channel_connection(interface = _interface)
        self.__pill2kill = Event()
        print("Channel was reseted")
        #self.logger.notice('The channel is reset')

    def start_channel_connection(self, interface =None):
        """
        The function will start the channel connection when sending SDO CAN message
        Parameters
        """
        #self.logger.notice('Starting CAN Connection ...')
        _interface = self.interface
        if not self.__busOn:
            print("Channel wasn't started or crashed")
            wrapper.start_channel_connection()
        else:
            self.__canMsgThread = Thread(target=self.read_can_message_thread)
            self.__canMsgThread.start()

    def read_sdo_can_thread(self, nodeId=None, index=None, subindex=None, timeout=100, MAX_DATABYTES=8, SDO_TX=0x600, SDO_RX=0x580, cobid=None):
        """Read an object via |SDO|
        Currently expedited and segmented transfer is supported by this method.
        The function will writing the dictionary request from the master to the node then read the response from the node to the master
        The user has to decide how to decode the data.
        """
        #self.logger.notice("Reading an object via |SDO|")
        self.start_channel_connection(interface=self.interface)
        if nodeId is None or index is None or subindex is None:
            #self.logger.warning('SDO read protocol cancelled before it could begin.')         
            return None
        self.cnt['SDO read total'] += 1
        #self.logger.info(f'Send SDO read request to node {nodeId}.')
        cobid = SDO_TX + nodeId
        msg = [0 for i in range(MAX_DATABYTES)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subindex
        try:
            self.write_can_message(cobid, msg, timeout=timeout)
        except CanGeneralError:
            self.cnt['SDO read request timeout'] += 1
            return None
        
        # Wait for response
        t0 = time.perf_counter()
        messageValid = False
        errorResponse = False
        errorReset = False
        resetResponse = False
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
            #self.logger.info(f'SDO read response timeout (node {nodeId}, index'
            #                 f' {index:04X}:{subindex:02X})')
            self.cnt['SDO read response timeout'] += 1
            return None, None
        
        # Check command byte
        if ret[0] == (0x80):
            abort_code = int.from_bytes(ret[4:], 'little')
            #self.logger.error(f'Received SDO abort message while reading '
            #                  f'object {index:04X}:{subindex:02X} of node '
            #                  f'{nodeId} with abort code {abort_code:08X}')
            self.cnt['SDO read abort'] += 1
            return None, None
        
        nDatabytes = 4 - ((ret[0] >> 2) & 0b11) if ret[0] != 0x42 else 4
        data = []
        for i in range(nDatabytes): 
            data.append(ret[4 + i])
        #self.logger.info(f'Got data: {data}')
        return cobid_ret, int.from_bytes(data, 'little')


    def read_adc_channels(self, file, directory , nodeId, outputname, outputdir, n_readings):
        """Start actual CANopen communication
        This function contains an endless loop in which it is looped over all
        ADC channels. Each value is read using
        :meth:`read_sdo_can_thread` and written to its corresponding
        """     
        dev = AnalysisUtils().open_yaml_file(file=file, directory=directory)
        # yaml file is needed to get the object dictionary items
        dictionary_items = dev["Application"]["index_items"]
        _adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        _adc_index = list(dev["adc_channels_reg"]["adc_index"])[0]
        _channelItems = [int(channel) for channel in list(_adc_channels_reg)]
        _channelDesc=[dev["adc_channels_reg"]["adc_channels"][str(_channelItems[i])] for i in range(len(_channelItems))]
        #_channelDesc = [str(Desc) for entries in dev["adc_channels_reg"]["adc_channels"][str(_channelItems)]]
        #print(_channelDesc)
        
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
            #for channel in np.arange(_channelItems[0], _channelItems[-1] + 1, 1):
            for i in range (0, len(_channelItems)):
                subindex = _channelItems[i] - 2
                data_point = self.read_sdo_can_thread(nodeId, int(_adc_index, 16), subindex, 1000)
                ts = time.time()
                elapsedtime = ts - monitoringTime
                if data_point is not None:
                    print(type(data_point))
                    #adc_converted = Analysis().adc_conversion(str(_channelDesc[i]), data_point)
                    #adc_converted = round(adc_converted, 3)
                    print(data_point)
                    csv_writer.writerow((str(round(elapsedtime, 1)),
                                         str(self.channel),
                                         str(nodeId),
                                         str(subindex),
                                         str(data_point),
                                         str(data_point)))
                                         #str(adc_converted)))
                    #self.logger.info(f'Got data for channel {channel}: = {adc_converted}')
                    print(data_point)
                pbar.update(1)
            pbar.close()
        #self.logger.notice("ADC data are saved to %s%s" % (outputdir,outputname))



# Start the server
wrapper = CANWrapper()
#wrapper.confirm_nodes()
#wrapper.stop() 
        
