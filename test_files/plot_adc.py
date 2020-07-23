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
rootdir = os.path.dirname(os.path.abspath(__file__))
data = pd.read_csv(rootdir[:-11] + "/output_data/adc_data.csv", delimiter=",", header=0)
# I am defining two arrays for all the possible tests and operations
operations = ['TimeStamp', 'Channel', "Id", "DLC", "ADCChannel", "ADCData" , "ADCDataConverted"]
target_operation = 0
# I will define a pdf file to include all the final plots
#pdf_file = rootdir[:-11] + "/output_data/adc_data.pdf"
#Pdf = PdfPages(pdf_file)
# Filter the data according to a specific  operation
condition = (data["ADCChannel"] == target_operation)
respondant = data[condition]
print(respondant["ADCDataConverted"]) 
fig, ax = plt.subplots()
ax.plot(respondant["ADCDataConverted"]) 
#ax.errorbar(x_axis, v_in, yerr=0.0, color="yellow", fmt='-',  markerfacecolor='white', ms=3, label="Power supply voltage  $U_S$ [V]")
ax.ticklabel_format(useOffset=False)
#ax.legend(loc="upper left", prop={'size': 8})
ax.autoscale(enable=True, axis='x', tight=None)
#ax.set_xlim([-0.04,0])
ax.grid(True)
ax.set_ylabel(r'Value [V]')
ax.set_xlabel("time $t$ [ms]")

plt.tight_layout()    
#     im = ax.imshow(corr_matrix)
#     im.set_clim(-1, 1)
#     ax.grid(False)
#     cb = ax.figure.colorbar(im, ax=ax, format='% .2f')
#     cb.set_label("r value")
#     ax.set_xlabel('Voltage [kV]')
#     ax.set_ylabel('Current [mA]')
#     ax.set_title('correlation matrix for the whole survey', fontsize=12)   
#     plt.xticks(rotation=45)
#     ax.legend(["Data correlation", line], facecolor='white')
while True:
    plt.pause(0.05)
    plt.show()
#     #plt.savefig(rootdir +"/"+operation+"_correlation_"+test+".png")
#     #Pdf.savefig()

# plt.close(fig)
#Pdf.close()