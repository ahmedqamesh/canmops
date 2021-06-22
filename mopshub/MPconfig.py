import RPi.GPIO as GPIO
import numpy as np
import logging


class MPconfig():
    """
    This class is going to handle everything related to the Multiplexer on the Mopshub-for beginners.
    The class should switch the data select inputs to the values corresponding to the current CAN channel.
    Without this functionality it is not possible to choose the right MOPS to talk to.
    """

    def __init__(self):
        self.__selA0 = 7
        self.__selA1 = 29
        self.__selA2 = 31
        self.__selB0 = 15
        self.__selB1 = 16
        self.__selB2 = 37

        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)

        GPIO.setup(self.__selA0, GPIO.OUT)
        GPIO.setup(self.__selA1, GPIO.OUT)
        GPIO.setup(self.__selA2, GPIO.OUT)

        GPIO.setup(self.__selB0, GPIO.OUT)
        GPIO.setup(self.__selB1, GPIO.OUT)
        GPIO.setup(self.__selB2, GPIO.OUT)

        """
        A and B are related to different the two CAN channel CAN1 and CAN2
        It is important to not choose on both CAN channel the same Multiplexer channel as the signals than could
        be read on both.
        """
        # Format of switch Table: [MPchannel, A0/B0, A1/B1, A2/B2]
        self.switch_table = np.array([[25, GPIO.LOW, GPIO.LOW, GPIO.LOW],
                                     [26, GPIO.HIGH, GPIO.LOW, GPIO.LOW],
                                     [27, GPIO.LOW, GPIO.HIGH, GPIO.LOW],
                                     [28, GPIO.HIGH, GPIO.HIGH, GPIO.LOW],
                                     [29, GPIO.LOW, GPIO.LOW, GPIO.HIGH],
                                     [30, GPIO.HIGH, GPIO.LOW, GPIO.HIGH],
                                     [31, GPIO.LOW, GPIO.HIGH, GPIO.HIGH],
                                     [32, GPIO.HIGH, GPIO.HIGH, GPIO.HIGH]])

        logging.basicConfig(level=logging.DEBUG)

    def mp_switch(self, mp_channel, can_channel):

        if mp_channel is None or can_channel is None:
            logging.error('Missing Parameter. Can not switch MP channels')
            return 0

        table_offset = 25
        __mp_channel = int(mp_channel) - table_offset
        #indexing of switch table: [y][x]
        try:
            if can_channel == 1:
                GPIO.output(self.__selA0, int(self.switch_table[__mp_channel][1]))
                GPIO.output(self.__selA1, int(self.switch_table[__mp_channel][2]))
                GPIO.output(self.__selA2, int(self.switch_table[__mp_channel][3]))
                logging.info('MP Channel was set to Channel %s with A0 = %s, A1 = %s, A2 = %s', mp_channel,
                            self.switch_table[__mp_channel][1], self.switch_table[__mp_channel][2],
                            self.switch_table[__mp_channel][3])

            if can_channel == 0:
                GPIO.output(self.__selB0, int(self.switch_table[__mp_channel][1]))
                GPIO.output(self.__selB1, int(self.switch_table[__mp_channel][2]))
                GPIO.output(self.__selB2, int(self.switch_table[__mp_channel][3]))
                logging.info('MP Channel was set to Channel %s with B0 = %s, B1 = %s, B2 = %s', mp_channel,
                            self.switch_table[__mp_channel][1], self.switch_table[__mp_channel][2],
                            self.switch_table[__mp_channel][3])
        except:
            logging.error('Some ERROR occurred while setting MP Channel %s', mp_channel)

mp = MPconfig()