from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
import numpy as np
import os
import binascii
import yaml
import logging
import sys
try:
    from graphicsUtils          import menuWindow
    from canmops.analysis       import Analysis
    from canmops.logger         import Logger 
    from canmops.analysis_utils  import AnalysisUtils
except:
    pass
rootdir = os.path.dirname(os.path.abspath(__file__)) 
lib_dir = rootdir[:-13]
config_dir = "config/"
class OpcuaWindow(QWidget):  

    def __init__(self, parent=None):
       super(OpcuaWindow, self).__init__(parent)
       self.MenuBar = menuWindow.MenuBar(self)
    def update_opcua_config_box(self):
        self.conf_cic = AnalysisUtils().open_yaml_file(file=config_dir+ "config.yaml", directory=lib_dir)
        dev = AnalysisUtils().open_yaml_file(file=config_dir + "MOPS_cfg.yml", directory=lib_dir)
        self.__deviceName = dev["Application"]["device_name"] 
        self.__version = dev['Application']['device_version']
        self.__appIconDir = dev["Application"]["icon_dir"]
        self.__chipId = dev["Application"]["chipId"]
        self.__nodeIds = dev["Application"]["nodeIds"]
        self.__dictionary_items = dev["Application"]["index_items"]
        self.__index_items = list(self.__dictionary_items.keys())
        self.__adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        self.__adc_index = dev["adc_channels_reg"]["adc_index"]
        self.__mon_index = dev["adc_channels_reg"]["mon_index"] 
        self.__conf_index = dev["adc_channels_reg"]["conf_index"] 
        self.__resistor_ratio = dev["Hardware"]["resistor_ratio"]
        
    def cic_child_window(self,childWindow):
        childWindow.setObjectName("OPCUA servers")
        childWindow.setWindowTitle("OPCUA servers")
        #childWindow.setGeometry(915, 490, 600, 400)
        mainGridLayout = QGridLayout()
        mops_num = 4
        cic_num = 4
        bus_num = 2
        ICON_RED_LED = "graphicsUtils//icons/ICON_RED_LED2.gif"
        ICON_GREEN_LED = "graphicsUtils//icons/ICON_GREEN_LED2.gif"
        plotframe = QFrame()  
        # Add controls into the Splitter. And set the initial size of the game
        #plotframe = [k for k in np.arange(cic_num)]        
        self.mopsBotton = [k for k in np.arange(mops_num)]
        CICGroupBox = [k for k in np.arange(cic_num)]
        BusGroupBox = [k for k in np.arange(bus_num)]
        self.AlarmBox = [k for k in np.arange(mops_num)]
        alarm_led = [[0]*mops_num]*cic_num
        for c in np.arange(cic_num):        
            CICGridLayout = QGridLayout()
            CICGroupBox[c] = QGroupBox("        CIC"+str(c))
            CICGroupBox[c].setStyleSheet("QGroupBox { font-weight: bold;font-size: 16px; background-color: #eeeeec; } ")
            for b in np.arange(bus_num):
                BusGridLayout = QGridLayout()
                BusGroupBox[b] = QGroupBox("Port "+str(b))
                BusGroupBox[b].setStyleSheet("QGroupBox { font-weight: bold;font-size: 10px; background-color: #eeeeec; } ")
                for m in np.arange(mops_num):
                    try:
                        port_num = self.conf_cic["CIC "+str(c)]["MOPS "+str(m)]["Port"]
                        if port_num == b:
                            icon_state =True
                        else:
                            icon_state = False
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
                    self.mopsBotton[s].setObjectName("C"+str(c)+"M"+str(m)+"P"+str(b))
                    self.mopsBotton[s].setIcon(QIcon('graphicsUtils/icons/icon_mops.png'))
                    self.mopsBotton[s].setStatusTip("CIC NO."+str(c)+" MOPS No."+str(m)+" Port No."+str(b))
                    self.mopsBotton[s].clicked.connect(self.cic_group_action)
                    self.AlarmBox[s] = QLabel()
                    self.AlarmBox[s].setMovie(alarm_led[c][m])
                    if s < col_len:
                        BusGridLayout.addWidget(self.mopsBotton[s], s, 1)
                        BusGridLayout.addWidget(self.AlarmBox[s], s, 0)
                    else:
                        BusGridLayout.addWidget(self.mopsBotton [s], s, 1)     #s- col_len, 0)      
                        BusGridLayout.addWidget(self.AlarmBox[s], s, 0)      
                    alarm_led[c][m].start()  
                BusGroupBox[b].setLayout(BusGridLayout)     #s- col_len, 0)  
                
            CICGridLayout.addWidget(BusGroupBox[0], 0, 1)     #s- col_len, 0) 
            CICGridLayout.addWidget(BusGroupBox[1], 1, 1)     #s- col_len, 0)
            CICGroupBox[c].setLayout(CICGridLayout)  
        childWindow.setCentralWidget(plotframe)
        self.textOutputWindow()
        mainGridLayout.addWidget(CICGroupBox[0]   , 0, 0)
        mainGridLayout.addWidget(CICGroupBox[1]   , 0, 1) 
        mainGridLayout.addWidget(CICGroupBox[2]   , 1, 0) 
        mainGridLayout.addWidget(CICGroupBox[3]   , 1, 1) 
        mainGridLayout.addWidget(self.textGroupBox,2,0,2,2)
        plotframe.setLayout(mainGridLayout)
        self.MenuBar.create_statusBar(childWindow)
        QtCore.QMetaObject.connectSlotsByName(childWindow)
        
    def show_cicWindow(self):
        self.cicWindow = QMainWindow()
        self.cic_child_window(childWindow=self.cicWindow)
        self.cicWindow.show()
        
    def cic_group_action(self):
        sender =  self.sender().objectName()
        CIC_num = sender[1:-4]
        MOPS_num = sender[3:-2]
        try:
            msg = self.conf_cic["CIC "+CIC_num]["MOPS "+ MOPS_num]["Port"]
            self.show_deviceWindow()
            
        except:
            msg = "CIC "+CIC_num,"MOPS "+MOPS_num, ": Not Found"
        comunication_object = "INFO"
        self.set_textBox_message(comunication_object = comunication_object , msg = str(msg))
    def show_deviceWindow(self):
        self.deviceWindow = QMainWindow()
        self.device_child_window(childWindow=self.deviceWindow)
        self.deviceWindow.show()
        
    def device_child_window(self, childWindow,device = "MOPS"): 
        '''
        The function will Open a special window for the device [MOPS] .
        The calling function for this is show_deviceWindow
        '''
        try:
            self.MenuBar.create_device_menuBar(childWindow)
        except Exception:
            self.MenuBar = menuWindow.MenuBar(self)
            self.MenuBar.create_device_menuBar(childWindow)
       # _device_name = device
        _channel = 0;#to be done self.get_channel()
        n_channels = 33
        try:
            self.wrapper.confirm_nodes(channel=int(_channel))
        except Exception:
            pass
        #  Open the window
        childWindow.setObjectName("DeviceWindow")
        #childWindow.setWindowTitle("Device Window [ " + _device_name + "]")
        #childWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        childWindow.setGeometry(1175, 10, 200, 770)
        logframe = QFrame()
        logframe.setLineWidth(0.6)
        childWindow.setCentralWidget(logframe)
        
        # Initialize tab screen
        tabLayout = QGridLayout()
        self.devicetTabs = QTabWidget()
        self.tab2 = QWidget() 

        def __set_bus():
            try:
                _nodeid = 1;#self.deviceNodeComboBox.currentText()
               # self.set_nodeId(_nodeid) 
               # self.set_index(self.IndexListBox.currentItem().text())
               # self.set_subIndex(self.subIndexListBox.currentItem().text())
                _sdo_tx = hex(0x600)
                #self.set_canId_tx(str(_sdo_tx))
            except Exception:
                self.error_message("Either Index or SubIndex are not defined")        
                     
        def __set_bus_timer():
            #_nodeid = self.deviceNodeComboBox.currentText()
           # self.set_nodeId(_nodeid) 
            _sdo_tx = hex(0x600)
            #self.set_canId_tx(str(_sdo_tx))
        self.deviceGroupBox(device)           
        firstVLayout = QVBoxLayout()
        firstVLayout.addWidget(self.deviceInfoGroupBox)        
        #firstVLayout.addLayout(BottonHLayout)
        firstVLayout.addSpacing(400)
        VLayout = QVBoxLayout()
        self.indexTextBox = QTextEdit()
        self.indexTextBox.setStyleSheet("background-color: white; border: 2px inset black; min-height: 150px; min-width: 400px;")
        self.indexTextBox.LineWrapMode(1)
        self.indexTextBox.setReadOnly(True)       
        VLayout.addWidget(self.indexTextBox)

        HLayout = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        #close_button.clicked.connect(self.stop_adc_timer)
        close_button.clicked.connect(childWindow.close)
        HLayout.addSpacing(350)
        HLayout.addWidget(close_button)
        # Add Adc channels tab [These values will be updated with the timer self.initiate_adc_timer]
        self.adc_values_window()
        self.monitoring_values_window()
        self.deviceGroupBox()
        self.configuration_values_window()
        
        # initiate a PlotWidget [data holder] for all ADC channels for later trending
       # self.initiate_trending_figure(n_channels=n_channels)
                        
        # tabLayout.addLayout(codidLayout, 2, 0)
        tabLayout.addWidget(self.devicetTabs, 3, 0)
        tabLayout.addLayout(HLayout, 4, 0)
        
        self.devicetTabs.addTab(self.tab2, "Device Channels") 
                
        mainLayout = QGridLayout()     
        HBox = QHBoxLayout()
        send_button = QPushButton("run ")
        send_button.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
        send_button.clicked.connect(__set_bus_timer)
        #send_button.clicked.connect(self.initiate_adc_timer)

        stop_button = QPushButton("stop ")
        stop_button.setIcon(QIcon('graphicsUtils/icons/icon_stop.png'))
       # stop_button.clicked.connect(self.stop_adc_timer)
        
        # update a progress bar for the bus statistics
        progressLabel = QLabel()
        progressLabel.setText("   ")  # Timer load")
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, n_channels)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        progressHLayout = QHBoxLayout()
        progressHLayout.addWidget(progressLabel)
        progressHLayout.addWidget(self.progressBar)
                
        HBox.addWidget(send_button)
        HBox.addWidget(stop_button)
        mainLayout.addWidget(self.ADCGroupBox      , 0, 0, 4, 2)
        mainLayout.addWidget(self.deviceInfoGroupBox , 0, 3, 1, 2)
        mainLayout.addWidget(self.ThirdGroupBox      , 1, 3, 2, 2) 
        mainLayout.addWidget(self.SecondGroupBox     , 3, 3, 1, 2) 
        
        mainLayout.addLayout(HBox , 5, 0)
        mainLayout.addLayout(progressHLayout, 5, 1)
        self.tab2.setLayout(mainLayout)
        self.MenuBar.create_statusBar(childWindow)
        logframe.setLayout(tabLayout)

    def deviceGroupBox(self, device = None):
        '''
        The window holds all the INFO needed for the connected device
        '''
        # Define subGroup
        self.deviceInfoGroupBox = QGroupBox()
        deviceInfoGridLayout = QGridLayout()
        # Icon
        iconLayout = QHBoxLayout()
        icon = QLabel(self)
        pixmap = QPixmap('graphicsUtils/icons/icon_mops.png')
        icon.setPixmap(pixmap.scaled(100, 100))
        iconLayout.addSpacing(50)
        iconLayout.addWidget(icon)    
        
        # Device Name
        deviceLayout = QHBoxLayout()
        deviceTypeLabel = QLabel()
        deviceTypeLabel.setText("Device:")
        deviceTitleLabel = QLabel()
        newfont = QFont("OldEnglish", 12, QtGui.QFont.Bold)
        deviceTitleLabel.setFont(newfont)
        deviceTitleLabel.setText(device)
        deviceLayout.addWidget(deviceTypeLabel)
        deviceLayout.addWidget(deviceTitleLabel)    
        # Chip ID
        chipLayout = QHBoxLayout()
        chipIdLabel = QLabel()
        chipIdLabel.setText("Chip Id:")
        chipIdTextBox = QLabel()
        newfont = QFont("OldEnglish", 12, QtGui.QFont.Bold)
        chipIdTextBox.setFont(newfont)
        chipIdTextBox.setText("chip 1 ")        
        chipLayout.addWidget(chipIdLabel)
        chipLayout.addWidget(chipIdTextBox)
        deviceInfoGridLayout.addLayout(iconLayout, 0, 0)
        deviceInfoGridLayout.addLayout(deviceLayout, 1, 0)
        deviceInfoGridLayout.addLayout(chipLayout, 2, 0) 
        self.deviceInfoGroupBox.setLayout(deviceInfoGridLayout)
        
    def adc_values_window(self):
        '''
        The function will create a QGroupBox for ADC Values [it is called by the function device_child_window]
        '''
        # info to read the ADC from the yaml file
        self.ADCGroupBox = QGroupBox("ADC Channels")
        FirstGridLayout = QGridLayout()
        _adc_channels_reg = self.__adc_channels_reg
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
               # self.trendingBotton[s].clicked.connect(self.show_trendWindow)
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
        self.ADCGroupBox.setLayout(FirstGridLayout)

    def monitoring_values_window(self):
        '''
        The function will create a QGroupBox for Monitoring Values [it is called by the function device_child_window]
        '''
        self.SecondGroupBox = QGroupBox("Monitoring Values")
        labelvalue = [0 for i in np.arange(20)]  # 20 is just a hypothetical number
        self.monValueBox = [0 for i in np.arange(20)]
        SecondGridLayout = QGridLayout()
        _dictionary = self.__dictionary_items
        _mon_indices = list(self.__mon_index)
        for i in np.arange(len(_mon_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex="subindex_items"))
            for s in np.arange(len(_subIndexItems)):
                subindex_description_item = AnalysisUtils().get_subindex_description_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex=_subIndexItems[s])
                labelvalue[s] = QLabel()
                labelvalue[s].setText(subindex_description_item + ":")
                labelvalue[s].setStatusTip('%s [index = %s & subIndex = %s]' % (subindex_description_item[9:-11], _mon_indices[i], _subIndexItems[s])) 
                self.monValueBox[s] = QLineEdit("")
                self.monValueBox[s].setStyleSheet("background-color: white; border: 1px inset black;")
                self.monValueBox[s].setReadOnly(True)
                self.monValueBox[s].setFixedWidth(80)
                SecondGridLayout.addWidget(labelvalue[s], s, 0)
                SecondGridLayout.addWidget(self.monValueBox[s], s, 1)
        self.SecondGroupBox.setLayout(SecondGridLayout)

                    
    def textOutputWindow(self):
        '''
        The function defines the GroupBox output window for the CAN messages
        '''  
        self.textGroupBox = QGroupBox("Log Window")
        self.textBox = QTextEdit()
        self.textBox.setReadOnly(True)
        self.textBox.resize(30, 30)
        textOutputWindowLayout = QGridLayout()
        textOutputWindowLayout.addWidget(self.textBox, 1, 0)
        self.textGroupBox.setLayout(textOutputWindowLayout)

        
    def set_textBox_message(self, comunication_object=None, msg=None):
        if comunication_object == "SDO_RX": 
            color = QColor("black")
            mode = "RX [hex] :"
        if comunication_object == "SDO_TX": 
            color = QColor("blue") 
            mode = "TX [hex] :"
        if comunication_object == "INFO": 
            color = QColor("green")
            mode = " "
        if comunication_object == "ADC": 
            color = QColor("green")
            mode = " :"
        if comunication_object == "ErrorFrame": 
            color = QColor("red")
            mode = "E:  "
        if comunication_object == "newline":
            color = QColor("green")
            mode = ""        
        self.textBox.setTextColor(color)
        self.textBox.append(mode+msg)
   
    def clear_textBox_message(self):
         self.textBox.clear()
         
                 
    def configuration_values_window(self):
        '''
        The function will create a QGroupBox for Configuration Values [it is called by the function device_child_window]
        '''
        self.ThirdGroupBox = QGroupBox("Configuration Values")
        labelvalue = [0 for i in np.arange(20)]  # 20 is just a hypothetical number
        self.confValueBox = [0 for i in np.arange(20)]
        ThirdGridLayout = QGridLayout()
        _dictionary = self.__dictionary_items
        _conf_indices = list(self.__conf_index)
        a = 0 
        for i in np.arange(len(_conf_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_conf_indices[i], subindex="subindex_items"))
            for s in np.arange(len(_subIndexItems)):
                subindex_description_item = AnalysisUtils().get_subindex_description_yaml(dictionary=_dictionary, index=_conf_indices[i], subindex=_subIndexItems[s])
                labelvalue[a] = QLabel()
                labelvalue[a].setText(subindex_description_item + ":")
                self.confValueBox[a] = QLineEdit("")
                self.confValueBox[a].setStyleSheet("background-color: white; border: 1px inset black;")
                self.confValueBox[a].setReadOnly(True)
                self.confValueBox[a].setFixedWidth(80)
                labelvalue[a].setStatusTip('%s [index = %s & subIndex = %s]' % (subindex_description_item[9:-11], _conf_indices[i], _subIndexItems[s])) 
                ThirdGridLayout.addWidget(labelvalue[a], a, 0)
                ThirdGridLayout.addWidget(self.confValueBox[a], a, 1)
                a = a + 1
        self.ThirdGroupBox.setLayout(ThirdGridLayout)  
                           
if __name__ == "__main__":
    pass

