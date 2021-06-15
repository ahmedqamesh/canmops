import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from typing import *
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from random import randint
from PyQt5 import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from canmops.analysisUtils  import AnalysisUtils
import random
import sys
import numpy as np
import pyqtgraph as pg
import time
import sys 
import os
rootdir = os.path.dirname(os.path.abspath(__file__)) 
config_dir = "config/"
lib_dir = lib_dir = rootdir[:]
class OpcuaWindow(QMainWindow):
    def __init__(self):
        super(OpcuaWindow, self).__init__(None)
        self.conf_cic = AnalysisUtils().open_yaml_file(file=config_dir + "config.yaml", directory=lib_dir)
        dev = AnalysisUtils().open_yaml_file(file=config_dir + "MOPS_cfg.yml", directory=lib_dir)
        self.__adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        self.__dictionary_items = dev["Application"]["index_items"]
        self.__adc_index = dev["adc_channels_reg"]["adc_index"]
        pass
    
    def device_child_window(self,childWindow):
        MessageWindow = QMainWindow()
        childWindow.setObjectName("DeviceWindow")
        #childWindow.setGeometry(1175, 10, 200, 770)
        logframe = QFrame()
        logframe.setLineWidth(0.9)
        childWindow.setCentralWidget(logframe)
        self.cic_group_window()

        mainLayout = QGridLayout()   
        #mainLayout.addWidget(self.FirstGroupBox    , 0, 0, 4, 2)
        mainLayout.addWidget(self.CICGroupBox[0]   , 0, 0)
        mainLayout.addWidget(self.CICGroupBox[1]   , 0, 1) 
        mainLayout.addWidget(self.CICGroupBox[2]   , 1, 0) 
        mainLayout.addWidget(self.CICGroupBox[3]   , 1, 1) 
        logframe.setLayout(mainLayout)

    def show_adc_window(self):
        sender =  self.sender().objectName()
        cic_num  = sender[1:-2]
        mops_num = sender[3:]
       # try:
        self.adcWindow = QMainWindow()
        self.adc_values_window(childWindow = self.adcWindow, cic_num = cic_num, mops_num = mops_num)
        self.adcWindow.show()
        #except:
        #    print("CIC "+cic_num,"MOPS "+mops_num, ": Not Found")

    
    
    def show_deviceWindow(self):
        self.deviceWindow = QMainWindow()
        self.device_child_window(childWindow=self.deviceWindow)
        self.deviceWindow.show()
            
    
    def alarm_timers(self,period = 500):
        self.alarm = QtCore.QTimer(self)
        self.alarm.setInterval(period)
        self.alarm.timeout.connect(self.read_adc_channels)
        self.alarm.start()
                
    def cic_group_window(self):
        mops_num = 4
        cic_num = 4
        ICON_RED_LED = "graphicsUtils//icons/ICON_RED_LED2.gif"
        ICON_GREEN_LED = "graphicsUtils//icons/ICON_GREEN_LED2.gif"
        # Add controls into the Splitter. And set the initial size of the game
        self.mopsBotton = [k for k in np.arange(mops_num)]
        self.CICGroupBox = [k for k in np.arange(cic_num)]
        self.AlarmBox = [k for k in np.arange(mops_num)]
        alarm_led = [[0]*mops_num]*cic_num
        for c in np.arange(cic_num):
            CICGridLayout = QGridLayout()
            self.CICGroupBox[c] = QGroupBox("        CIC"+str(c))
            self.CICGroupBox[c].setStyleSheet("QGroupBox { font-weight: bold;font-size: 16px; } ")
            for m in np.arange(mops_num):
                try:
                    self.conf_cic["CIC "+str(c)]["MOPS "+str(m)]
                    icon_state =True
                except:
                    icon_state = False
                if icon_state:
                    alarm_led[c][m] = QMovie(ICON_GREEN_LED)
                else: 
                    alarm_led[c][m] = QMovie(ICON_RED_LED)
                    
                alarm_led[c][m].setScaledSize(QSize().scaled(20, 20, Qt.KeepAspectRatio))                 
                col_len = int(mops_num / 2)
                s = m
                self.mopsBotton[s] = QPushButton("  ["+str(m)+"]")
                self.mopsBotton[s].setObjectName("C"+str(c)+"M"+str(m))
                self.mopsBotton[s].setIcon(QIcon('graphicsUtils/icons/icon_mops.png'))
                self.mopsBotton[s].clicked.connect(self.cic_group_action)
                self.AlarmBox[s] = QLabel()
                self.AlarmBox[s].setMovie(alarm_led[c][m])
                if s < col_len:
                    CICGridLayout.addWidget(self.mopsBotton[s], s, 1)
                    CICGridLayout.addWidget(self.AlarmBox[s], s, 0)
                else:
                    CICGridLayout.addWidget(self.mopsBotton[s], s, 1)     #s- col_len, 0)      
                    CICGridLayout.addWidget(self.AlarmBox[s], s, 0)      
                alarm_led[c][m].start()
            self.CICGroupBox[c].setLayout(CICGridLayout)

    def cic_group_action(self):
        sender =  self.sender().objectName()
        CIC_num = sender[1:-2]
        MOPS_num = sender[3:]
        try:
            print(self.conf_cic["CIC "+CIC_num]["MOPS "+MOPS_num])
            state =True
            self.show_adc_window
        except:
            print("CIC "+CIC_num,"MOPS "+MOPS_num, ": Not Found")
            state = False

    def adc_values_window(self,childWindow,cic_num = None, mops_num = None):
        '''
        The function will create a QGroupBox for ADC Values [it is called by the function device_child_window]
        '''
        childWindow.setWindowTitle("CIC"+cic_num +" MOPS"+mops_num+"Window")
        childWindow.setObjectName("DeviceWindow")
        childWindow.setGeometry(1175, 10, 200, 770)        
        logframe = QFrame()
        childWindow.setCentralWidget(logframe)
        logframe.setLineWidth(0.9)
        # info to read the ADC from the yaml file
        self.FirstGroupBox = QGroupBox("ADC Channels")
        FirstGridLayout = QGridLayout()
        _adc_channels_reg = self.__adc_channels_reg#self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _adc_indices = list(self.__adc_index)
        for i in np.arange(len(_adc_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex="subindex_items"))
            labelChannel = [_subIndexItems[k] for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            self.channelValueBox = [_subIndexItems[k] for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            self.trendingBox = [False for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            self.trendingBotton = [_subIndexItems[k] for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            _start_a = 3  # to start from channel 3
            for subindex in np.arange(_start_a, len(_subIndexItems) + _start_a - 1):
                s = subindex - _start_a
                s_correction = subindex - 2
                labelChannel[s] = QLabel()
                self.channelValueBox[s] = QLineEdit()
                self.channelValueBox[s].setStyleSheet("background-color: white; border: 1px inset black;")
                self.channelValueBox[s].setReadOnly(True)
                self.channelValueBox[s].setFixedWidth(80)
                subindex_description_item = AnalysisUtils().get_subindex_description_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex=_subIndexItems[s_correction])
                labelChannel[s].setStatusTip('ADC channel %s [index = %s & subIndex = %s]' % (subindex_description_item[25:29],
                                                                                            _adc_indices[i],
                                                                                             _subIndexItems[s_correction]))  # show when move mouse to the icon
                labelChannel[s].setText(subindex_description_item[25:29] + ":")
                icon = QLabel(self)
                if _adc_channels_reg[str(subindex)] == "V": 
                    icon_dir = 'graphicsUtils/icons/icon_voltage.png'
                else: 
                    icon_dir = 'graphicsUtils/icons/icon_thermometer.png'
                pixmap = QPixmap(icon_dir)
                icon.setPixmap(pixmap.scaled(20, 20))
                self.trendingBotton[s] = QPushButton()
                self.trendingBotton[s].setObjectName(str(subindex))
                self.trendingBotton[s].setIcon(QIcon('graphicsUtils/icons/icon_trend.jpg'))
                self.trendingBotton[s].setStatusTip('Data Trending for %s' % subindex_description_item[25:29])
                #self.trendingBotton[s].clicked.connect(self.show_trendWindow)
#                 self.trendingBox[s] = QCheckBox("")
#                 self.trendingBox[s].setChecked(False)
                col_len = int(len(_subIndexItems) / 2)
                if s < col_len:
                    FirstGridLayout.addWidget(icon, s, 0)
                    # FirstGridLayout.addWidget(self.trendingBox[s], s, 1)
                    FirstGridLayout.addWidget(self.trendingBotton[s], s, 2)
                    FirstGridLayout.addWidget(labelChannel[s], s, 3)
                    FirstGridLayout.addWidget(self.channelValueBox[s], s, 4)
                else:
                    FirstGridLayout.addWidget(icon, s - col_len, 5)
                    # FirstGridLayout.addWidget(self.trendingBox[s], s-col_len, 6)
                    FirstGridLayout.addWidget(self.trendingBotton[s], s - col_len, 7)
                    FirstGridLayout.addWidget(labelChannel[s], s - col_len, 8)
                    FirstGridLayout.addWidget(self.channelValueBox[s], s - col_len , 9)         
        self.FirstGroupBox.setLayout(FirstGridLayout)
        mainLayout = QGridLayout()   
        mainLayout.addWidget(self.FirstGroupBox , 0, 0, 4, 2)
        logframe.setLayout(mainLayout)             
if __name__=='__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = OpcuaWindow()
    app.show_deviceWindow()
    qApp.exec_()
    
    
        


