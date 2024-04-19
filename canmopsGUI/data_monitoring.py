from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.animation as animation
from typing import *
from PyQt5 import *
from PyQt5 import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import random
from random import randint
import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph import *
import time
import matplotlib as mpl
from canmopsGUI.plot_style import *
icon_location = "canmopsGUI/icons/"
class DataMonitoring(QMainWindow):

    def __init__(self, parent=None):
        super(DataMonitoring, self).__init__(parent)

    def trend_child_window(self, childWindow=None, subindex=None, n_channels=None):
        '''
        The window starts the child window for the trending data of each ADC channel [it is called by the trending button beside each channel]
        '''
        trendGroupBox = QGroupBox("")   
        childWindow.setObjectName("")
        childWindow.setWindowTitle("Online data monitoring for ADC channel %s" % str(subindex))
        childWindow.resize(600, 300)  # w*h
        logframe = QFrame()
        logframe.setLineWidth(1)
        childWindow.setCentralWidget(logframe)
        self.trendLayout = QGridLayout()
        
        # initiate trending data
        self.x = [0] * n_channels
        self.y = [0] * n_channels
        for i in np.arange(0, n_channels):
            self.x[i] = list([0])
            self.y[i] = list([0])
        # initiate trending Figure  
        s = int(subindex) - 3
        
        def __disable_figure():
            #self.trendingBox[s] = False  
            self.x[s] = list([0])
            self.y[s] = list([0])
            self.graphWidget[s].clear()
            
        Fig = self.graphWidget[s]
        #for i in np.arange(0, n_channels): self.graphWidget[i].clear()  # clear any old plots
        close_button = QPushButton("close")
        close_button.setIcon(QIcon(icon_location+'icon_close.jpg'))
        close_button.clicked.connect(__disable_figure)
        close_button.clicked.connect(childWindow.close)
        
        self.trendLayout.addWidget(Fig, 0, 0)
        self.trendLayout.addWidget(close_button, 1, 0)
        trendGroupBox.setLayout(self.trendLayout)
        logframe.setLayout(self.trendLayout) 
        return self.x, self.y
            
    def initiate_trending_figure(self, subindex=None, n_channels=None):
        '''
        The function defines a PlotWidget [data holder] for all ADC channels, 
        This widget provides a contained canvas on which plots of any type can be added and configured. 
        '''
        # prepare a PlotWidget
        self.correct_range = 0
        self.graphWidget = [pg.PlotWidget(background="w") for i in np.arange(n_channels)]
        for s in np.arange(n_channels): 
            # Add Title
            self.graphWidget[s].setTitle("Online data monitoring for ADC channel %s" % str(s + 3))
            # Add Axis Labels
            self.graphWidget[s].setLabel('left', "<span style=\"color:black; font-size:15px\">Voltage[V]</span>")
            self.graphWidget[s].setLabel('bottom', "<span style=\"color:black; font-size:15px\">Time line [Steps]</span>")
    
            # Add grid
            self.graphWidget[s].showGrid(x=True, y=True)
            self.graphWidget[s].getAxis("bottom").setStyle(tickTextOffset=10)
            
            # set style
            self.graphWidget[s].setStyleSheet("background-color: black;"
                                    "color: black;"
                                    "border-width: 1.5px;"
                                    "border-color: black;"
                                    "margin:0.0px;"
                                    "solid black;")      
        return self.graphWidget
    

    def update_figure(self, data=None, subindex=None, graphWidget = None):
        '''
        The function will update the graphWidget with ADC data.
        '''  
        s = int(subindex) - 3  # the first ADC channel is channel 3 
        data_line = graphWidget.plot(self.x[s], self.y[s],name="Ch%i" % subindex)#, pen=pg.mkPen(self.get_color(s)) 
        self.x[s] = np.append(self.x[s], self.x[s][-1] + 1)  # Add a new value 1 higher than the last
        self.y[s].append(data)  # Add a new value.
        data_line.setData(self.x[s][1:], self.y[s][1:])  # Update the data line.
        
    
    def reset_data_holder(self,adc_value,s):
        self.correct_range = self.correct_range + 100
        self.x[s] = list([self.correct_range])
        self.y[s] = list([round(adc_value, 3)])
        self.graphWidget[s].clear()


class LiveMonitoringDistribution(FigureCanvas):
    
    """A canvas that updates itself every second with a new plot."""

    def __init__(self, parent=None, period=200, data = None):
        super(LiveMonitoringDistribution, self).__init__(parent)
        self.setParent(parent)
        #self.initiate_trending_figure()
        #self.initiate_timer(period=period, data =data)
        
    def initiate_trending_figure(self, n_channels = None):
        fig = Figure(edgecolor="black", linewidth="2.5")  # , facecolor="#e1ddbf")
        self.axes = fig.add_subplot(111)
        FigureCanvas.__init__(self, fig)
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding), FigureCanvas.updateGeometry(self)
        self.data =  list(range(2))  # 100 time points
        self.axes.set_xlabel(r'CAN Data', size=10)
        self.axes.set_ylabel(r'Counts', size=10) 
        self.axes.grid(True)
        plt.tight_layout()

    def stop_timer(self):
        self.timer.stop() 
                
    def update_figure(self, y = None):
        #self.main.send_sdo_data()  # to be replaced with send_sdo_can
        #y = self.main.get_data_point()
        self.data.append(y)
        # print(len(self.data))
        hist_data, edges = np.histogram(self.data, bins=np.arange(0, 100, 1))  #
        x, y = edges[:-1], hist_data
        self.axes.fill_between(x, y, color='#F5A9BC', label="Data")
        self.draw()
        
if __name__ == '__main__':
    pass
