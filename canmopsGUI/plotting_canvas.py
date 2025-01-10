########################################################
"""
    This file is part of the MOPS-Hub project.
    Author: Ahmed Qamesh (University of Wuppertal)
    email: ahmed.qamesh@cern.ch  
    Date: 01.05.2020
"""
########################################################

from __future__ import division
import numpy as np
from kafe import *
from kafe.function_library import quadratic_3par
from numpy import loadtxt, arange
import csv
from scipy.optimize import curve_fit
import tables as tb
from mpl_toolkits.mplot3d import Axes3D
import itertools
from math import pi, cos, sin
from scipy.linalg import norm
import os
import seaborn as sns
sns.set(style="white", color_codes=True)
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from matplotlib.pyplot import *
import pylab as P
import matplotlib as mpl
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import gridspec
from matplotlib.colors import LogNorm
from matplotlib.patches import Circle
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredDrawingArea
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import colors
from matplotlib.ticker import PercentFormatter
from matplotlib.ticker import NullFormatter
from matplotlib.ticker import StrMethodFormatter
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
try:
    from canmops.analysis_utils  import AnalysisUtils
    from canmops.analysis       import Analysis
    from canmops.logger_main         import Logger 
    from canmopsGUI.plot_style import *
    an = Analysis()
    log_call = Logger(name = " Plotting  ",console_loglevel=logging.INFO, logger_file = False)
except(ImportError, ModuleNotFoundError):
    from plot_style import *
    pass
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.animation as animation
from typing import *
from PyQt5 import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from matplotlib.figure import Figure

import pandas as pd




class PlottingCanvas(FigureCanvas):     

    def __init__(self,tests = None , console_loglevel = logging.INFO, test_file=None,name_prefix = None, plot_prefix =None):
        try:
            self.logger = log_call.setup_main_logger()
        except :
            self.logger = logging
        self.fig = Figure(dpi = 100)
        self.ax = self.fig.add_subplot(111)
        super(FigureCanvas,self).__init__(self.fig)
        plt.clf()
        plt.style.use('bmh')        
        self.ax.cla()
        if plot_prefix == "adc_data" :
            self.plot_adc_data(test_file = test_file, adc_value =tests[0] )                                 
        if plot_prefix == "trial_plot" :
            self.update_plot_data(test_file = test_file)
        else:
            pass
        self.draw()

    def check_last_row (self, data_frame = None, file_name = None,column = "status"):
        data_frame_last_row = data_frame.tail(1)
        pattern_exists = any(data_frame_last_row[column].astype(str).str.contains("End of Test"))
        if pattern_exists: data_frame = data_frame.iloc[:-1]
        else: pass
        return data_frame

    def update_plot_data(self,test_file):
        try:
            data = pd.read_csv(test_file, header=1, encoding = 'utf-8').fillna(0)
            data.plot(ax = self.ax)
            
            legend = self.ax.legend(loc="upper left", prop={'size': 8})
            legend.set_draggable(True)
            
            self.ax.set_xlabel('X axis', fontsize=12)
            self.ax.set_ylabel('Y axis', fontsize=12)
        except:
            self.logger.error(f"Corrupted data File: {test_file}")
            
    def plot_adc_data(self, test_file=None, adc_value=[0]):    
        '''
        The function plots the ADC data collected over time as it is saved
        into the file (test_file)
        '''
        data = pd.read_csv( test_file, header = 1, delimiter=",")
        data = self.check_last_row(data_frame = data,file_name = test_file,column = f'ADCDataConverted')
        condition = (data["ADCChannel"] == adc_value)
        respondant = data[condition]
        self.logger.info("Plotting data from channel %i"%adc_value)
        self.ax.plot(respondant["Time"],respondant["ADCDataConverted"], label="ADC channel No.%i"%adc_value, color =col_row[adc_value])
        #self.ax.yaxis.set_major_formatter(ScalarFormatter)
        self.ax.ticklabel_format(useOffset=False)
        
        self.ax.legend(loc="upper left")
        self.ax.autoscale(enable=True, axis='x', tight=None)
        self.ax.grid(True)
        self.ax.set_title("ADC data from channel %i"%adc_value)
        self.ax.set_ylabel(r'ADC value [V]')
        self.ax.set_xlabel("Time line [S]")

    
    def close(self, PdfPages=False):
            PdfPages.close()

if __name__ == "__main__":
    PlottingCanvas().plot_adc_data(test_file="/home/dcs/git/canmops/output_data/adc_data_3_0_gui.csv", adc_value=3)
    pass
