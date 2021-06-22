import RPi.GPIO as GPIO
import numpy as np
import logging
from MPconfig import MPconfig, mp
import time


class PEconfig(MPconfig):
    """
    Some Text
    """

    def __init__(self):
        self.__CE = 36
        self.__Data = 32
        self.__Res = 33

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        GPIO.setup(self.__CE, GPIO.OUT)
        GPIO.setup(self.__Data, GPIO.OUT)
        GPIO.setup(self.__Res, GPIO.OUT)

        self.default_status_table = np.array([[25, GPIO.LOW],
                                              [26, GPIO.LOW],
                                              [27, GPIO.LOW],
                                              [28, GPIO.LOW],
                                              [29, GPIO.LOW],
                                              [30, GPIO.LOW],
                                              [31, GPIO.LOW],
                                              [32, GPIO.LOW]])

        self.current_status_table = np.array([[25, GPIO.LOW],
                                              [26, GPIO.LOW],
                                              [27, GPIO.LOW],
                                              [28, GPIO.LOW],
                                              [29, GPIO.LOW],
                                              [30, GPIO.LOW],
                                              [31, GPIO.LOW],
                                              [32, GPIO.LOW]])

        self.set_default()
        self.memory_mode()

    def set_default(self):
        for i in range(0, len(self.default_status_table)):
            channel = self.default_status_table[i][0]
            value = self.default_status_table[i][1]
            status = self.addressable_latch_mode(channel, value)
            self.current_status_table[i][1] = status

    def reset_mode(self):
        try:
            GPIO.output(self.__Res, GPIO.LOW)
            GPIO.output(self.__CE, GPIO.HIGH)
            logging.info('Latch was reseted')
        except:
            logging.error('Some Error occurred while resetting Latch')

    def addressable_latch_mode(self, channel, data):
        try:
            GPIO.output(self.__Res, GPIO.HIGH)
            GPIO.output(self.__CE, GPIO.LOW)
            logging.info('Latch is now in the addressable latch mode')
        except:
            logging.error('Some Error occurred while activating addressable latch mode')

        try:
            mp.mp_switch(channel, 0)
            GPIO.output(self.__Data, int(data))
            logging.info('Write to Latch address: %s , value = %s was successful', channel, data)
            return data
        except:
            logging.error('Error while writing to Latch address = %s, value = %s', channel, data)

    def memory_mode(self):
        try:
            GPIO.output(self.__Res, GPIO.HIGH)
            GPIO.output(self.__CE, GPIO.HIGH)
            logging.info('Latch is now in the memory mode')
        except:
            logging.error('Some Error occurred while activating memory mode')

    def demultiplexer_mode(self, channel, value):
        try:
            GPIO.output(self.__Res, GPIO.LOW)
            GPIO.output(self.__CE, GPIO.LOW)
            logging.info('Latch is now in the demultiplexer mode')
        except:
            logging.error('Some Error occurred while activating demultiplexer mode')

    def check_status(self, mp_channel):
        table_offset = 25
        __mp_channel = mp_channel - table_offset
        return self.current_status_table[__mp_channel][1]


pe = PEconfig()
