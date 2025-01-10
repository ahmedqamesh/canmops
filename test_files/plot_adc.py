########################################################
"""
    This file is part of the MOPS-Hub project.
    Author: Ahmed Qamesh (University of Wuppertal)
    email: ahmed.qamesh@cern.ch  
    Date: 01.05.2020
"""
########################################################
import pandas as pd
import csv
from matplotlib import style
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt 
#plt.style.use('ggplot')
import os
import numpy as np
from plot_style import *
rootdir = os.path.dirname(os.path.abspath(__file__))
test_file = rootdir[:-11] +"/output_data/adc_data_3_0_gui.csv"
pdf_file = test_file[:-3]+"pdf"
 
data = pd.read_csv(test_file, header=1, encoding = 'utf-8').fillna(0)
# I am defining two arrays for all the possible tests and operations
operations = ['TimeStamp', 'Channel', "Id", "DLC", "ADCChannel", "ADCData" , "ADCDataConverted"]


Pdf = PdfPages(pdf_file)
# Filter the data according to a specific  operation (Which ADC channel)
n_channels = 32
_start_a = 3  # to ignore the first subindex it is not ADC
for target in np.arange(_start_a,n_channels+_start_a):
    print("Plotting data from channel %i"%target)
    fig, ax = plt.subplots()
    condition = (data["ADCChannel"] == target)
    respondant = data[condition]
    ax.plot(respondant["Time"],respondant["ADCDataConverted"], label="ADC channel No.%i"%target)
    ax.ticklabel_format(useOffset=False)
    ax.legend(loc="upper left")
    ax.autoscale(enable=True, axis='x', tight=None)
    ax.grid(True)
    ax.set_ylim([0,0.6])
    ax.set_ylabel(r'ADC value [V]')
    ax.set_xlabel("Time [S]")
    plt.tight_layout()    
    Pdf.savefig()
    plt.close(fig)
print("Plots are saved to %s" % (pdf_file))
Pdf.close()


    