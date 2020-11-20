import pandas as pd
import matplotlib as mpl
import numpy as np
import csv
import tables as tb
from matplotlib import style
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib import pyplot as p
import seaborn as sns 
import matplotlib.pyplot as plt 
#plt.style.use('ggplot')
import scipy
import os
import numpy as np
from matplotlib.pyplot import plotting
rootdir = os.path.dirname(os.path.abspath(__file__))

def get_color(i):
    col_row = ["#f7e5b2", "#fcc48d", "#e64e4b", "#984071", "#58307b", "#432776", "#3b265e", "#4f2e6b", "#943ca6", "#df529e", "#f49cae", "#f7d2bb",
            "#f4ce9f", "#ecaf83", "#dd8a5b", "#904a5d", "#5d375a", "#402b55", "#332d58", "#3b337a", "#365a9b", "#2c4172", "#2f3f60", "#3f5d92",
            "#4e7a80", "#60b37e", "#b3daa3", "#cfe8b7", "#d2d2ba", "#dd8a5b", "#904a5d", "#5d375a", "#4c428d", "#3a3487", "#31222c", "#b3daa3"]
    return col_row[i]
        
data = pd.read_csv(rootdir[:-11] + "/output_data/adc_data.csv", delimiter=",", header=0)
# I am defining two arrays for all the possible tests and operations
operations = ['TimeStamp', 'Channel', "Id", "DLC", "ADCChannel", "ADCData" , "ADCDataConverted"]

pdf_file = rootdir[:-11] + "/output_data/adc_data.pdf"
Pdf = PdfPages(pdf_file)
# Filter the data according to a specific  operation (Which ADC channel)
n_channels = 32
for target in np.arange(1,n_channels):
    print("Plotting data from channel %i"%target)
    fig, ax = plt.subplots()
    condition = (data["ADCChannel"] == target)
    respondant = data[condition]
    ax.plot(respondant["ADCDataConverted"], label="ADC channel No.%i"%target, color =get_color(target)) 
    ax.ticklabel_format(useOffset=False)
    ax.legend(loc="upper left", prop={'size': 8})
    ax.autoscale(enable=True, axis='x', tight=None)
    ax.grid(True)
    ax.set_ylabel(r'ADC value [V]')
    ax.set_xlabel("time [ms]")
    plt.tight_layout()    
    Pdf.savefig()
    plt.close(fig)
Pdf.close()


    