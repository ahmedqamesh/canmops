from __future__ import division
import numpy as np
import logging
import numba
import tables as tb
from scipy.optimize import curve_fit
class Analysis(object):
    
    def __init__(self):
        pass
    # Fit functions
    def linear(self, x, m, c):
        return m * x + c

    def quadratic(self, x, a, b, c):
        return a * x**2 + b * x + c

    def red_chisquare(self, observed, expected, observed_error, popt):
        return np.sum(((observed - expected) / observed_error)**2 / (len(observed_error) - len(popt) - 1))

    def ln(self, x, a, b, c):
        return a * np.log(x + b) - c

    def exp(self, x, a, b, c):
        return a * np.exp(-b * x) + c

    def Inverse_square(self, x, a, b, c):
        return a / (x + b)**2 - c
    
    def adc_conversion(self, adc_channels_reg="V", value=None):
        '''
        the function will convert each ADC value into a reasonable physical quantity
        > MOPS has 12 bits ADC value ==> 2^12 = 4096 (this means that we can read from 0 -> 4096 different values)
        > The full 12 bits ADC covers 850 mV (this means that each ADC value corresponds to 4096/850 = 0.207 mV)
        Example: 
        Each ADC value should be multiplied by 0.207 to give the answer in mV
        To measure Voltage: the value should be multiplied by 40 (Resistor ratio)
        '''
        if value is not None:
            if adc_channels_reg == "V":
                value = value * 207 * 10e-6
            elif adc_channels_reg == "T":
                value = value * 207 * 10e-6
            else:
                value = value * 207 * 10e-6
        return value
    def convertion(self,value =None):
        return value
    
    def NTC_convertion(self,value =None):
        '''
        To convert ADC data to temperature you first find the thermistor resistance and then use it to find the temperature.
        https://www.jameco.com/Jameco/workshop/techtip/temperature-measurement-ntc-thermistors.html
        Rt = R0 * (( Vs / Vo ) - 1) 
        
        '''
       
        return value
if __name__ == "__main__":
        pass
