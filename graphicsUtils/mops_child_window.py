from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
from canmops.analysis_utils import AnalysisUtils
from canmops.logger_main    import Logger 
from graphicsUtils import main_gui_window, menu_window, data_monitoring
import numpy as np
import time
import os
import binascii
import yaml
import logging
rootdir = os.path.dirname(os.path.abspath(__file__)) 
lib_dir = rootdir[:-13]
config_dir = "config/"
class MopsChildWindow(QWidget):  

    def __init__(self, parent=None,console_loglevel=logging.INFO,opcua_config = "opcua_config.yaml"):
       super(MopsChildWindow, self).__init__(parent)
       self.logger = Logger().setup_main_logger(name=" MOPS GUI ", console_loglevel=console_loglevel)
       dev = AnalysisUtils().open_yaml_file(file=config_dir + "MOPS_cfg.yml", directory=lib_dir)
       self.configure_devices(dev)
       max_mops_num = 4
       max_bus_num = 4

    def bus_child_window(self,childWindow):      
        mopsBotton = [k for k in np.arange(max_mops_num)]
        BusGroupBox = [k for k in np.arange(max_bus_num)]
        for c in np.arange(cic_num):        
            CICGridLayout = QGridLayout()
            CICGroupBox[c] = QGroupBox("        CIC"+str(c))
            CICGroupBox[c].setStyleSheet("QGroupBox { font-weight: bold;font-size: 16px; background-color: #eeeeec; } ")
            for b in np.arange(max_bus_num):
                BusGridLayout = QGridLayout()
                BusGroupBox[b] = QGroupBox("Port "+str(b))
                BusGroupBox[b].setStyleSheet("QGroupBox { font-weight: bold;font-size: 10px; background-color: #eeeeec; } ")
                for m in np.arange(max_mops_num):               
                    col_len = int(mops_num / 2)
                    s = m
                    mopsBotton[m] = QPushButton("  ["+str(m)+"]")
                    mopsBotton[m].setObjectName("C"+str(c)+"M"+str(m)+"P"+str(b))
                    mopsBotton[m].setIcon(QIcon('graphicsUtils/icons/icon_mops.png'))
                    mopsBotton[m].setStatusTip("CIC NO."+str(c)+" MOPS No."+str(m)+" Port No."+str(b))
                    mopsBotton[m].clicked.connect(self.cic_group_action)
                    if s < col_len:
                        BusGridLayout.addWidget(mopsBotton[s], s, 1)
                    else:
                        BusGridLayout.addWidget(mopsBotton [s], s, 1)     #s- col_len, 0)      
                BusGroupBox[b].setLayout(BusGridLayout)     #s- col_len, 0)  
                
            CICGridLayout.addWidget(BusGroupBox[0], 0, 1)     #s- col_len, 0) 
            CICGridLayout.addWidget(BusGroupBox[1], 1, 1)     #s- col_len, 0)
            CICGroupBox[c].setLayout(CICGridLayout)  
        childWindow.setCentralWidget(plotframe)
        mainGridLayout.addWidget(CICGroupBox[0]   , 0, 0)
        plotframe.setLayout(mainGridLayout)
        self.MenuBar.create_statusBar(childWindow)
        QtCore.QMetaObject.connectSlotsByName(childWindow)
        
                
    def update_opcua_config_box(self):
        self.conf_cic = AnalysisUtils().open_yaml_file(file=config_dir+ "opcua_config.yaml", directory=lib_dir)

    def configure_devices(self, dev):
        '''
        The function provides all the configuration parameters stored in the configuration file of the device [e.g. MOPS] stored in the config_dir
        '''
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
        self.__refresh_rate = dev["Application"]["refresh_rate"] #millisecondsrefresh_rate
        self.__ref_voltage = dev["Hardware"]["ref_voltage"] 
        return  self.__deviceName, self.__version, self.__appIconDir,self.__nodeIds, self.__dictionary_items, self.__adc_channels_reg,\
            self.__adc_index, self.__chipId, self.__index_items, self.__conf_index, self.__mon_index, self.__resistor_ratio, self.__refresh_rate, self.__ref_voltage
               
            
    def define_object_dict_window(self,connected_node = None, mainWindow = None):
        def __set_bus():
            try:
                _nodeid = self.deviceNodeComboBox.currentText()
                mainWindow.set_nodeId(_nodeid) 
                mainWindow.set_index(self.IndexListBox.currentItem().text())
                mainWindow.set_subIndex(self.subIndexListBox.currentItem().text())
                _sdo_tx = hex(0x600)
                mainWindow.set_canId_tx(str(_sdo_tx))
            except Exception:
                mainWindow.error_message("Either Index or SubIndex are not defined")        
                   
        def __restart_device():
            _sdo_tx = hex(0x00)
            _cobid = _sdo_tx  # There is no need to add any Node Id
            mainWindow.set_cobid(_cobid)
            mainWindow.set_bytes([0, 0, 0, 0, 0, 0, 0, 0]) 
            self.logger.info("Restarting the %s device with a cobid of  %s" % (mainWindow.get_deviceName(), str(_cobid)))
            mainWindow.write_can_message()

        def __reset_device():
             # Apply bus settings
            _nodeid = self.deviceNodeComboBox.currentText()
            _nodeid = int(_nodeid, 16)
            _sdo_tx = hex(0x700)
            _cobid = hex(0x700 + _nodeid)
            mainWindow.set_cobid(_cobid)
            mainWindow.set_bytes([0, 0, 0, 0, 0, 0, 0, 0]) 
            self.logger.info("Resetting the %s device with a cobid of %s" % (mainWindow.get_deviceName(), str(_cobid)))
            mainWindow.write_can_message()
                    
        def __get_subIndex_description(): 
            dictionary = self.__dictionary_items
            index = self.IndexListBox.currentItem().text()
            if self.subIndexListBox.currentItem() is not None:
                subindex = self.subIndexListBox.currentItem().text()
                self.subindex_description_items = AnalysisUtils().get_subindex_description_yaml(dictionary=dictionary, index=index, subindex=subindex)
                description_text = self.index_description_items + "<br>" + self.subindex_description_items
                self.indexTextBox.setText(description_text) 
            
        def __get_subIndex_items():
            index = mainWindow.get_index()
            dictionary = self.__dictionary_items
            subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=dictionary, index=index, subindex="subindex_items"))
            self.subIndexListBox.clear()
            for item in subIndexItems: self.subIndexListBox.addItem(item)
        
        def __get_index_description():
            dictionary = self.__dictionary_items
            if self.IndexListBox.currentItem() is not None:
                index = self.IndexListBox.currentItem().text()
                self.index_description_items = AnalysisUtils().get_info_yaml(dictionary=dictionary , index=index, subindex="description_items")
                self.indexTextBox.setText(self.index_description_items)

        def __set_subIndex_value():
            if self.subIndexListBox.currentItem() is not None:
                subindex = self.subIndexListBox.currentItem().text()
                mainWindow.set_subIndex(subindex)
        
        def __set_index_value():
            index = self.IndexListBox.currentItem().text()
            mainWindow.set_index(index)
        
        GridLayout = QGridLayout()
        self.deviceInfoGroupBox = self.device_info_box(device = mainWindow.get_deviceName())
        BottonHLayout = QVBoxLayout()
        startButton = QPushButton("")
        startButton.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
        startButton.setStatusTip('Send CAN message')  # show when move mouse to the icon
        startButton.clicked.connect(__set_bus)
        startButton.clicked.connect(mainWindow.read_sdo_can_thread)

        resetButton = QPushButton()
        resetButton.setIcon(QIcon('graphicsUtils/icons/icon_reset.png'))
        _cobid_index = hex(0x700)
        resetButton.setStatusTip('Reset the chip [The %s chip should reply back with a cobid index %s]' % (mainWindow.get_deviceName(), str(_cobid_index)))
        resetButton.clicked.connect(__reset_device)
                       
        restartButton = QPushButton()
        restartButton.setIcon(QIcon('graphicsUtils/icons/icon_restart.png'))
        restartButton.setStatusTip('Restart the chip [The %s chip should reply back with a cobid 0x00]' % mainWindow.get_deviceName())
        restartButton.clicked.connect(__restart_device)
        
        BottonHLayout.addWidget(startButton)
        BottonHLayout.addWidget(resetButton)
        BottonHLayout.addWidget(restartButton)
        
        firstVLayout = QVBoxLayout()
        firstVLayout.addWidget(self.deviceInfoGroupBox)        
        firstVLayout.addLayout(BottonHLayout)
        firstVLayout.addSpacing(400)
        VLayout = QVBoxLayout()
        self.indexTextBox = QTextEdit()
        self.indexTextBox.setStyleSheet("background-color: white; border: 2px inset black; min-height: 150px; min-width: 400px;")
        self.indexTextBox.LineWrapMode(1)
        self.indexTextBox.setReadOnly(True)      
        VLayout.addWidget(self.indexTextBox)
        
        indexLabel = QLabel()
        indexLabel.setText("   Index   ")
        self.IndexListBox = QListWidget()
        indexItems = self.__index_items
        self.IndexListBox.setFixedWidth(70)
        
        for item in indexItems: self.IndexListBox.addItem(item)
        self.IndexListBox.currentItemChanged.connect(__set_index_value) 
        self.IndexListBox.currentItemChanged.connect(__get_subIndex_items)
        self.IndexListBox.currentItemChanged.connect(__get_index_description)  
        
        subIndexLabel = QLabel()
        subIndexLabel.setText("SubIndex")
        self.subIndexListBox = QListWidget()
        self.subIndexListBox.setFixedWidth(60)
        self.subIndexListBox.currentItemChanged.connect(__set_subIndex_value)  
        self.subIndexListBox.currentItemChanged.connect(__get_subIndex_description)  
        
        GridLayout.addWidget(indexLabel, 0, 1)
        GridLayout.addWidget(subIndexLabel, 0, 2)
        GridLayout.addLayout(firstVLayout, 1, 0)
        GridLayout.addWidget(self.IndexListBox, 1, 1)
        GridLayout.addWidget(self.subIndexListBox, 1, 2)
        GridLayout.addLayout(VLayout, 0, 3, 0, 4)
        return GridLayout
                                
    def device_child_window(self, childWindow, device = "MOPS", cic = None, port = None , mops = None, mainWindow = None, readout_thread = None): 
        '''
        The function will Open a special window for the device [MOPS] .
        The calling function for this is show_deviceWindow
        '''
        try:
            self.MenuBar.create_device_menuBar(childWindow)
        except Exception:
            self.MenuBar = menu_window.MenuWindow(self)
            self.MenuBar.create_device_menuBar(childWindow)
            
        self.DataMonitoring = data_monitoring.DataMonitoring(self)    
        if device:
            _device_name = device
        else:
            _device_name = self.__deviceName 
            

        n_channels = 33
        nodeItems = self.__nodeIds

        #  Open the window
        childWindow.setObjectName("DeviceWindow")
        childWindow.setWindowTitle("Device Window [ " + _device_name + "]")
        childWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        childWindow.setGeometry(1175, 10, 200, 770)
        logframe = QFrame()
        logframe.setLineWidth(0.6)
        mainLayout = QGridLayout()    
        childWindow.setCentralWidget(logframe)
        
        # Initialize tab screen
        tabLayout = QGridLayout()
        self.devicetTabs = QTabWidget()  
        self.tab2 = QWidget()        
        self.devicetTabs.addTab(self.tab2, "Device Channels")         
        if cic is None:
            _channel = mainWindow.get_channel()        
            try:
                self.wrapper.confirm_nodes(channel=int(_channel))
            except Exception:
                pass
        
            self.tab1 = QWidget()
            nodeLabel = QLabel()
            nodeLabel.setText("Connected nodes :")
            self.deviceNodeComboBox = QComboBox()
            mainWindow.set_nodeList(nodeItems)
            for item in list(map(str, nodeItems)): self.deviceNodeComboBox.addItem(item)
            
            _connectedNode = self.deviceNodeComboBox.currentText()
                             
            def __set_bus_timer():
                _nodeid = self.deviceNodeComboBox.currentText()
                mainWindow.set_nodeId(_nodeid) 
                _sdo_tx = hex(0x600)
                mainWindow.set_canId_tx(str(_sdo_tx))
            
            def __check_file_box(): 
                self.saveDirCheckBox.setChecked(True)
                self.SaveDirTextBox.setReadOnly(True)
                self.SaveDirTextBox.setStyleSheet(" background-color: lightgray;")
                mainWindow.set_default_file(self.SaveDirTextBox.text())
                self.set_default_file(self.SaveDirTextBox.text())
                                    
            def _set_default_file():
                _nodeid = self.deviceNodeComboBox.currentText()
                _default_file = "adc_data_"+_nodeid+".csv"
                mainWindow.set_default_file(_default_file)
                self.set_default_file(_default_file)
                self.set_dir_text_box(_default_file)
            
            _nodeid = self.deviceNodeComboBox.currentText()
            _default_file = "adc_data_"+_nodeid+".csv"
            
            mainWindow.set_default_file(_default_file)

            self.deviceNodeComboBox.currentIndexChanged.connect(_set_default_file)
                        
            objectDictLayout = self.define_object_dict_window(connected_node = _connectedNode, mainWindow = mainWindow)
            self.tab1.setLayout(objectDictLayout) 
            nodeHLayout = QHBoxLayout()
            nodeHLayout.addWidget(nodeLabel)
            nodeHLayout.addWidget(self.deviceNodeComboBox)
            nodeHLayout.addSpacing(400)
            tabLayout.addLayout(nodeHLayout, 1, 0)
            HBox = QHBoxLayout()
            send_button = QPushButton("run ")
            send_button.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
            send_button.clicked.connect(__set_bus_timer)
            send_button.clicked.connect(__check_file_box)
            send_button.clicked.connect(mainWindow.initiate_adc_timer)
    
            stop_button = QPushButton("stop ")
            stop_button.setIcon(QIcon('graphicsUtils/icons/icon_stop.png')) 
            stop_button.clicked.connect(mainWindow.stop_adc_timer)
    
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
            mainLayout.addLayout(HBox , 5, 0)
            mainLayout.addLayout(progressHLayout, 5, 1)
            self.devicetTabs.addTab(self.tab1, "Object Dictionary")
            self.device_info_box(device=device, cic = cic, port = port , mops = mops,data_file = _default_file)  
        else:
            self.progressBar = None               
            self.device_info_box(device=device, cic = cic, port = port , mops = mops)
            self.graphWidget = self.DataMonitoring.initiate_trending_figure(n_channels=n_channels)


        HLayout = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        close_button.clicked.connect(mainWindow.stop_adc_timer)
        close_button.clicked.connect(childWindow.close)
        HLayout.addSpacing(350)
        HLayout.addWidget(close_button)
        # Add Adc channels tab [These values will be updated with the timer self.initiate_adc_timer]
        _adc_channels_reg = self.__adc_channels_reg
        self.channelValueBox, self.trendingBox = self.adc_values_window(adc_channels_reg = _adc_channels_reg, mainWindow = mainWindow,cic = cic, port = port , mops = mops)
        self.monValueBox = self.monitoring_values_window()
        self.confValueBox  =  self.configuration_values_window()
        
        tabLayout.addWidget(self.devicetTabs, 3, 0)
        tabLayout.addLayout(HLayout, 4, 0)
        mainLayout.addWidget(self.ADCGroupBox      , 0, 0, 4, 2)
        mainLayout.addWidget(self.deviceInfoGroupBox , 0, 3, 1, 2)
        mainLayout.addWidget(self.ThirdGroupBox      , 1, 3, 2, 2) 
        mainLayout.addWidget(self.SecondGroupBox     , 3, 3, 1, 2) 
        
        
        self.tab2.setLayout(mainLayout)
        self.MenuBar.create_statusBar(childWindow)
        logframe.setLayout(tabLayout)
        return self.channelValueBox, self.trendingBox , self.monValueBox , self.confValueBox, self.progressBar

    def device_info_box(self, device = None, cic = None, port = None , mops = None, data_file = None):
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
        
  
        # CIC Name
        if cic is not None:
            cicLayout = QHBoxLayout()
            cicLabel = QLabel()
            cicLabel.setText("CIC Id:")
            cicTitleLabel = QLabel()
            cicTitleLabel.setText(cic)
            cicLayout.addWidget(cicLabel)
            cicLayout.addWidget(cicTitleLabel)  
            deviceInfoGridLayout.addLayout(cicLayout, 3, 0)
        # Port Name
        if port is not None:
            portLayout = QHBoxLayout()
            portLabel = QLabel()
            portLabel.setText("Port No.:")
            portTitleLabel = QLabel()
            portTitleLabel.setText(port)
            portLayout.addWidget(portLabel)
            portLayout.addWidget(portTitleLabel)  
            deviceInfoGridLayout.addLayout(portLayout, 4, 0)
            
        # Port Name
        if mops is not None:
            mopsLayout = QHBoxLayout()
            mopsLabel = QLabel()
            mopsLabel.setText("Node id")
            mopsTitleLabel = QLabel()
            mopsTitleLabel.setText(mops)
            mopsLayout.addWidget(mopsLabel)
            mopsLayout.addWidget(mopsTitleLabel)  
            deviceInfoGridLayout.addLayout(mopsLayout, 5, 0)

        # Port Name
        if data_file is not None:
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
        
            def _dir_stat_change(b):
                if b.isChecked() == True:
                    self.SaveDirTextBox.setReadOnly(True)
                    self.SaveDirTextBox.setStyleSheet(" background-color: lightgray;")
                    self.set_default_file(self.SaveDirTextBox.text())
                else:
                    self.SaveDirTextBox.setReadOnly(False)  
                    self.SaveDirTextBox.setStyleSheet(" background-color: white;")
            
            self.set_default_file(data_file)
            dataLayout = QHBoxLayout()
            SaveDirLabel = QLabel()
            SaveDirLabel.setText("Data Output File")
            
            self.SaveDirTextBox = QLineEdit()           
            self.SaveDirTextBox.setStyleSheet("background-color: lightgray; border: 1px inset black;")
            self.SaveDirTextBox.setReadOnly(True)
            self.SaveDirTextBox.setFixedWidth(80)   
            self.SaveDirTextBox.setText(str(data_file))   
            self.saveDirCheckBox = QCheckBox("")
            self.saveDirCheckBox.setChecked(True)
            self.saveDirCheckBox.toggled.connect(lambda:_dir_stat_change(self.saveDirCheckBox))
            self.SaveDirTextBox.setStatusTip("The file where the ADC value are saved after scanning[%s]"%(lib_dir + "output_data/"+self.__default_file+".csv"))
            dataLayout.addWidget(SaveDirLabel)
            dataLayout.addWidget(self.SaveDirTextBox)
            dataLayout.addWidget(self.saveDirCheckBox)  
            deviceInfoGridLayout.addLayout(deviceLayout, 1, 0)
            deviceInfoGridLayout.addLayout(dataLayout, 6, 0)
                    
        # Chip ID
        chipLayout = QHBoxLayout()
        chipIdLabel = QLabel()
        chipIdLabel.setText("Chip Id:")
        chipIdTextBox = QLabel()
        newfont = QFont("OldEnglish", 12, QtGui.QFont.Bold)
        chipIdTextBox.setFont(newfont)
        chipIdTextBox.setText(self.__chipId)        
        chipLayout.addWidget(chipIdLabel)
        chipLayout.addWidget(chipIdTextBox)
        deviceInfoGridLayout.addLayout(iconLayout, 0, 0)
        deviceInfoGridLayout.addLayout(chipLayout, 2, 0) 
        self.deviceInfoGroupBox.setLayout(deviceInfoGridLayout)
        return self.deviceInfoGroupBox
        
    def adc_values_window(self,adc_channels_reg = None, mainWindow =None,cic = None, port = None , mops = None):
        '''
        The function will create a QGroupBox for ADC Values [it is called by the function device_child_window]
        '''
        # info to read the ADC from the yaml file
        self.ADCGroupBox = QGroupBox("ADC Channels")
        FirstGridLayout = QGridLayout()
        _adc_channels_reg = adc_channels_reg
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
                labelChannel[s].setText(subindex_description_item[25:29] + " [V]:")
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
                if cic is not None:
                    self.trendingBotton[s].clicked.connect(lambda: mainWindow.show_trendWindow(int(cic),int(port),int(mops)))
                else:
                    self.trendingBotton[s].clicked.connect(lambda: mainWindow.show_trendWindow())
                    
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
        return self.channelValueBox, self.trendingBox

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
        return self.monValueBox
    
    def configuration_values_window(self):
        '''
        The function will create a QGroupBox for Configuration Values [it is called by the function device_child_window]
        '''
        self.ThirdGroupBox = QGroupBox("Configuration Values")
        labelvalue = [0 for i in np.arange(8)]  # 20 is just a hypothetical number
        self.confValueBox = [0 for i in np.arange(8)]
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
        return self.confValueBox       
        
        
    def read_adc_channels(self):
        _dictionary = self.__dictionary_items
        _adc_indices = list(self.__adc_index)
        for i in np.arange(len(_adc_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex="subindex_items"))
            _start_a = 3  # to ignore the first subindex it is not ADC
            
            for subindex in np.arange(_start_a, len(_subIndexItems) + _start_a - 1):
                s = subindex - _start_a
                adc_value = np.random.randint(0,100)
                self.channelValueBox[s].setText(str(adc_value))   
                if self.trendingBox[s] == True:
                    if len(self.x[s]) >= 10:# Monitor a window of 100 points is enough to avoid Memory issues 
                        self.DataMonitoring.reset_data_holder(adc_value,s) 
                    self.DataMonitoring.update_figure(data=adc_value, subindex=subindex, graphWidget = self.graphWidget[s])     
            #This will be used later for limits 
            if adc_value <=95:
                self.channelValueBox[s].setStyleSheet("color: black;")
            else:
                self.channelValueBox[s].setStyleSheet(" background-color: red;")  
        
        try:                        
            for c in np.arange(len(self.confValueBox)):
                adc_value = np.random.randint(0,100)
                self.confValueBox[c].setText(str(adc_value))      
                
                #This will be used later for limits 
                if adc_value <=95:
                    self.confValueBox[c].setStyleSheet("color: black;")
                else:

                    self.confValueBox[c].setStyleSheet(" background-color: red;")
                    
        except:
            pass          
        
        try:    
            for m in np.arange(len(self.monValueBox)):
                adc_value = np.random.randint(0,100)
                self.monValueBox[m].setText(str(adc_value))
                #This will be used later for limits 
                if adc_value <=95:
                    self.monValueBox[m].setStyleSheet("color: black;")
                else:

                    self.monValueBox[m].setStyleSheet(" background-color: red;")
        except:
            pass      

    def show_trendWindow(self):
        trend = QMainWindow(self)
        subindex = self.sender().objectName()
        s = int(subindex) - 3     
        self.trendingBox[s] = True  
        n_channels = 33
        for i in np.arange(0, n_channels): self.graphWidget[i].clear()  # clear any old plots
        self.x, self.y = self.DataMonitoring.trend_child_window(childWindow=trend, subindex=int(subindex), n_channels=n_channels)
        trend.show()

    def set_default_file(self,x):
        self.__default_file = x
    
    def get_default_file(self):
        return self.__default_file
    
    def set_dir_text_box(self,x):
        self.__default_file = x
        self.SaveDirTextBox.setText(str(x))

   
class EventTimer(QWidget):
    def __init__(self,parent=None,console_loglevel=logging.INFO):
        super(EventTimer, self).__init__(parent)
        """:obj:`~logging.Logger`: Main logger for this class"""
        self.logger = Logger().setup_main_logger(name=" Timer Init ", console_loglevel=console_loglevel)

    def initiate_timer(self, period=None):
        '''
        The function will  update the GUI with the ADC data ach period in ms.
        '''  
        self.timer = QtCore.QTimer()     
        self.timer.start()
        return  self.timer    
    
    def stop_timer(self,dut= None):
        '''
        The function will  stop the timer.
        '''        
        try:
            self.timer.stop()
            self.logger.notice("Stopping %s timer..."%dut)
        except Exception:
            pass
        
    def showTime(self):
        time=QDateTime.currentDateTime()
        timeDisplay=time.toString('yyyy-MM-dd hh:mm:ss dddd')
        self.label.setText(timeDisplay)

    def startTimer(self):
        self.timer.start(1000)
        self.startBtn.setEnabled(False)
        self.endBtn.setEnabled(True)

    def endTimer(self):
        self.timer.stop()
        self.startBtn.setEnabled(True)
        self.endBtn.setEnabled(False)
                
if __name__ == "__main__":
    pass
    
     
