import pandas as pd
import csv
from matplotlib import style
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt 
plt.style.use('ggplot')
import os
import numpy as np
rootdir = os.path.dirname(os.path.abspath(__file__))
file_name = rootdir[:-11] +"/output_data/adc_data_1.csv"
pdf_file = file_name[:-3]+"pdf"
def get_color(i):
    col_row = ["#000000", "#3a3487", "#f7e5b2", "b", "g", "r", "y", "c", "m", "lime", "#943ca6", "#df529e", "#f49cae", "tab:blue",
            "tab:orange", "tab:purple", "tab:pink", "#332d58", "#3b337a", "#365a9b", "#2c4172", "#2f3f60", "#3f5d92",
            "#4e7a80", "#60b37e", "darkgoldenrod", "darksalmon", "darkgreen", "#904a5d", "#5d375a", "#4c428d", "#31222c", "#b3daa3","#f4ce9f", "#ecaf83"]
    return col_row[i]
 
 
data = pd.read_csv( file_name, delimiter=",", header=0)
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
    ax.plot(respondant["Time"],respondant["ADCDataConverted"], label="ADC channel No.%i"%target, color =get_color(target))
    ax.ticklabel_format(useOffset=False)
    ax.legend(loc="upper left", prop={'size': 8})
    ax.autoscale(enable=True, axis='x', tight=None)
    ax.grid(True)
    ax.set_ylabel(r'ADC value [V]')
    ax.set_xlabel("Time [S]")
    plt.tight_layout()    
    Pdf.savefig()
    plt.close(fig)
print("Plots are saved to %s" % (pdf_file))
Pdf.close()


    