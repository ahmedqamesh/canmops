import logging
from MPconfig import MPconfig
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    logging.error(ImportError)
    logging.warning('RPI GPIO could not be imported')


class PEconfig(MPconfig):
    """
    Some Text
    """

    def __init__(self):
        self.__CE = 36
        self.__Data = 32
        self.__Res = 33

        MPconfig.__init__(self)

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        GPIO.setup(self.__CE, GPIO.OUT)
        GPIO.setup(self.__Data, GPIO.OUT)
        GPIO.setup(self.__Res, GPIO.OUT)

        self.power_off_table = [1, 1, 1, 1, 1, 1, 0, 1]
        self.locked_by_user = [False for _ in range(8)]
        self.locked_by_sys = [False for _ in range(8)]
        self.current_status_table = [0, 0, 0, 0, 0, 0, 0, 0]

        self.logger = logging.getLogger('mopshub_log.power_enable_config')

    def set_power_off(self):
        for i in range(0, len(self.power_off_table)):
            value = self.power_off_table[i]
            status = self.addressable_latch_mode(i, value)
            self.memory_mode()
            self.current_status_table[i] = status

    def reset_mode(self):
        try:
            GPIO.output(self.__Res, GPIO.LOW)
            GPIO.output(self.__CE, GPIO.HIGH)
            self.logger.info('Latch was reseted')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Some Error occurred while resetting Latch')

    def addressable_latch_mode(self, channel, data, set_flag=None):
        try:
            GPIO.output(self.__Res, GPIO.HIGH)
            GPIO.output(self.__CE, GPIO.LOW)
            self.logger.info('Latch is now in the addressable latch mode')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Some Error occurred while activating addressable latch mode')

        if channel in range(0, 8):
            __channel = channel
        elif channel in range(25, 33):
            table_offset = 25
            __channel = channel - table_offset
        else:
            self.logger.error(f'Could not identify channel {channel}')
            return 0

        mp = self.mp_switch(__channel, 1)

        try:
            if bool(self.locked_by_sys[__channel]) is False:
                if bool(self.locked_by_user[__channel]) is False or set_flag is not None:
                    # important Latch is connected to all Address related with A means we have to choose here channel 1
                    # this hole channel 1 and 0 think relating to address A and B has to be improved
                    if mp is True:
                        GPIO.output(self.__Data, int(data))
                        self.current_status_table[__channel] = data
                    if set_flag is not None:
                        self.locked_by_user[__channel] = set_flag
                    self.logger.info('Write to Latch address: %s , value = %s was successful', channel, data)
                    return data
                else:
                    logging.error('Power of Channel %s was locked by user', __channel)
            else:
                logging.error('Power of Channel %s was locked by sys while start up', __channel)
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Error while writing to Latch address = %s, value = %s', channel, data)
            return None

    def memory_mode(self):
        try:
            GPIO.output(self.__Res, GPIO.HIGH)
            GPIO.output(self.__CE, GPIO.HIGH)
            self.logger.info('Latch is now in the memory mode')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Some Error occurred while activating memory mode')

    def demultiplexer_mode(self, channel, data):
        try:
            GPIO.output(self.__Res, GPIO.LOW)
            GPIO.output(self.__CE, GPIO.LOW)
            self.logger.info('Latch is now in the demultiplexer mode')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error('Some Error occurred while activating demultiplexer mode')

    def check_status(self, channel):
        if channel in range(0, 8):
            __channel = channel
        elif channel in range(25, 33):
            table_offset = 25
            __channel = channel - table_offset
        else:
            self.logger.error(f'Could not identify channel {channel}')
            return 0

        return self.current_status_table[__channel], self.locked_by_sys[__channel], self.locked_by_user[__channel]


power_signal = PEconfig()