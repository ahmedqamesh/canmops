
from __future__ import annotations
import signal

import  time
import sys
import pandas as pd
import os
import logging
import numpy as np
from typing import *
from sys import stdout
from matplotlib.backends.qt_compat import QtCore, QtWidgets
import pyqtgraph as pg
from PyQt5 import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from random import randint
from graphicsUtils import menuWindow
from controlServer.analysis import Analysis
from controlServer.analysisUtils import AnalysisUtils
from controlServer.canWrapper   import CanWrapper
import csv
from csv import writer
import yaml
# Third party modules
import coloredlogs as cl
import verboselogs
rootdir = os.path.dirname(os.path.abspath(__file__)) 
lib_dir = rootdir[:-13]
config_dir = "config/"

class MainWindow(QMainWindow):

    def __init__(self, parent=None,
                 console_loglevel=logging.INFO,
                 logformat='%(asctime)s - %(levelname)s - %(message)s'):
        super(MainWindow, self).__init__(parent)
        """:obj:`~logging.Logger`: Main logger for this class"""
        verboselogs.install()
        self.logger = logging.getLogger(__name__)
        cl.install(fmt=logformat, level=console_loglevel, isatty=True, milliseconds=True)
         
        # Start with default settings
        self.logger = logging.getLogger(__name__)
        # Read configurations from a file    
        self.__conf = AnalysisUtils().open_yaml_file(file=config_dir + "main_cfg.yml", directory=lib_dir)
        self.__appName = self.__conf["Application"]["app_name"] 
        self.__appVersion = self.__conf['Application']['app_version']
        self.__appIconDir = self.__conf["Application"]["app_icon_dir"]
        self.__canSettings = self.__conf["Application"]["can_settings"]
        self.__bitrate_items = self.__conf['default_values']['bitrate_items']
        self.__sample_points = self.__conf['default_values']['sample_points']
        self.__bytes = self.__conf["default_values"]["bytes"]
        self.__subIndex = self.__conf["default_values"]["subIndex"]
        self.__cobid = self.__conf["default_values"]["cobid"]
        self.__dlc = self.__conf["default_values"]["dlc"]
        self.__interfaceItems = list(self.__conf['CAN_Interfaces'].keys()) 
        self.__channelPorts = self.__conf["channel_ports"]
        self.__devices = self.__conf["Devices"]
         
        self.__timeout = 2000
        self.__period = 0.05
        self.__interface = None
        self.__channel = None
        self.__ipAddress = None
        self.__bitrate = None
        self.__sample_point =None
        self.index_description_items = None
        self.wrapper = None
        
    def Ui_ApplicationWindow(self):
        '''
        The function Will start the main graphical interface with its main components
        1. The menu bar
        2. The tools bar
        3. Bus settings box
        4. Message settings box
        5. output window
        6. Bytes monitoring box 
        7. Configured devices
        8. extra box for can statistics is to be added [Qamesh]
        '''
        self.logger.info("Initializing The Graphical Interface")
        # create MenuBar
        self.MenuBar = menuWindow.MenuBar(self)
        self.MenuBar.create_menuBar(self)

        # create statusBar
        self.MenuBar.create_statusBar(self)
        
        # create toolBar
        toolBar = self.addToolBar("tools")
        self.show_toolBar(toolBar, self)

        # 1. Window settings
        self.setWindowTitle(self.__appName + "_" + self.__appVersion)
        self.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        self.adjustSize()
        self.setGeometry(10, 10, 900, 770)
        
        self.defaultSettingsWindow()
        self.default_message_window()
        self.textOutputWindow()
        self.tableOutputWindow()
        self.configure_device_box()
        
        # Create a frame in the main menu for the gridlayout
        mainFrame = QFrame()
        mainFrame.setLineWidth(0.6)
        self.setCentralWidget(mainFrame)
            
        # SetLayout
        mainLayout = QGridLayout()
        mainLayout.addWidget(self.defaultSettingsGroupBox, 0, 0)
        mainLayout.addWidget(self.defaultMessageGroupBox, 1, 0)  
        mainLayout.addWidget(self.textGroupBox, 0, 1, 2, 1)
        mainLayout.addWidget(self.monitorGroupBox, 3, 0, 2, 2)
        mainLayout.addWidget(self.configureDeviceBoxGroupBox, 5, 0)
        mainFrame.setLayout(mainLayout)
        # 3. Show
        self.show()
    
    def defaultSettingsWindow(self):
        '''
        The function defines the GroupBox for the default bus settings
        e.g. for Communication purposes the user needs to define   
        1. The CAN Bus [e.g. channel 0, 2, 3,....] 
        2. The Interface [e.g. socketcan, kvaser, Anagate]
        All the options in every widget are defined in the file main_cfg.yml
        '''    
        self.defaultSettingsGroupBox = QGroupBox("Bus Settings")
        plotframe = QFrame()
        plotframe.setStyleSheet("QWidget { background-color: #eeeeec; }")
        plotframe.setLineWidth(0.6)
        self.setCentralWidget(plotframe)
        
        defaultSettingsWindowLayout = QGridLayout()
        __interfaceItems = self.__interfaceItems
        __channelList = self.__channelPorts
        
        channelLabel = QLabel()
        channelLabel.setText(" CAN Channels")
        self.channelComboBox = QComboBox()
        self.channelComboBox.setStatusTip('Possible ports as defined in the main_cfg.yml file')
        for item in list(__channelList): self.channelComboBox.addItem(item)  

        interfaceLabel = QLabel()
        interfaceLabel.setText("  Interfaces")
        self.interfaceComboBox = QComboBox()
        for item in __interfaceItems[:]: self.interfaceComboBox.addItem(item)
        self.interfaceComboBox.activated[str].connect(self.set_interface)
        self.interfaceComboBox.setStatusTip('Select the connected interface')
        self.interfaceComboBox.setCurrentIndex(2)
        
        self.connectButton = QPushButton("")
        icon = QIcon()
        icon.addPixmap(QPixmap('graphicsUtils/icons/icon_connect.jpg'), QIcon.Normal, QIcon.On)
        icon.addPixmap(QPixmap('graphicsUtils/icons/icon_disconnect.jpg'), QIcon.Normal, QIcon.Off)
        self.connectButton.setIcon(icon)
        self.connectButton.setStatusTip('Connect the interface and set the channel')
        self.connectButton.setCheckable(True)
        
        def on_channelComboBox_currentIndexChanged():
            _interface = self.interfaceComboBox.currentText()
            _channel = self.channelComboBox.currentText()
            _channels = AnalysisUtils().get_info_yaml(dictionary=self.__conf['CAN_Interfaces'], index=_interface, subindex="channels")
            
            self.set_interface(_interface)
            self.set_channel(int(_channel))
            try:
                _nodeItems = _channels[int(_channel)]
                self.nodeComboBox.clear()
                self.nodeComboBox.addItems(list(map(str, _nodeItems)))
            except Exception:
                self.logger.warning("No interface connected to the selected port")
                self.nodeComboBox.clear()
                pass

        self.channelComboBox.setCurrentIndex(0)
        self.connectButton.clicked.connect(on_channelComboBox_currentIndexChanged)
        self.connectButton.clicked.connect(self.connect_server)
                
        defaultSettingsWindowLayout.addWidget(channelLabel, 0, 0)
        defaultSettingsWindowLayout.addWidget(self.channelComboBox, 1, 0)
        defaultSettingsWindowLayout.addWidget(interfaceLabel, 0, 1)
        defaultSettingsWindowLayout.addWidget(self.interfaceComboBox, 1, 1)
        defaultSettingsWindowLayout.addWidget(self.connectButton, 1, 2)
         
        plotframe.setLayout(defaultSettingsWindowLayout)
        self.defaultSettingsGroupBox.setLayout(defaultSettingsWindowLayout)
                       
    def default_message_window(self):
        '''
        The function defines the GroupBox for a default SDO CANOpen message parameters
        e.g. A standard  CANOpen message needs
        1. NodeId [e.g. channel 0, 2, 3,...128] 
        2. CobId [600+NodeId]
        3. Index
        4. SubIndex
        All the options in every widget are defined in the file main_cfg.yml
        '''  
        self.defaultMessageGroupBox = QGroupBox("Message Settings")
        plotframe = QFrame()
        plotframe.setStyleSheet("QWidget { background-color: #eeeeec; }")
        plotframe.setLineWidth(0.6)
        self.setCentralWidget(plotframe)
        
        defaultMessageWindowLayout = QGridLayout()                        
        nodeLabel = QLabel()
        nodeLabel.setText("NodeId ")
        self.nodeComboBox = QComboBox()
        self.nodeComboBox.setStatusTip('Connected CAN Nodes as defined in the main_cfg.yml file')
        self.nodeComboBox.setFixedSize(70, 25)
        
        cobidLabel = QLabel()
        cobidLabel.setText("   CobId   ")
        self.mainCobIdTextBox = QLineEdit(self.__cobid)
        self.mainCobIdTextBox.setFixedSize(70, 25)
        
        indexLabel = QLabel()
        indexLabel.setText("   Index   ")
        self.mainIndexTextBox = QLineEdit("0x1000")
        self.mainIndexTextBox.setFixedSize(70, 25)
        
        subIndexLabel = QLabel()
        subIndexLabel.setText("SubIndex")
        self.mainSubIndextextbox = QLineEdit(self.__subIndex)
        self.mainSubIndextextbox.setFixedSize(70, 25)
        
        def __apply_CANMessageSettings():
            try:
                self.set_index(self.mainIndexTextBox.text())
                self.set_subIndex(self.mainSubIndextextbox.text())
                self.set_nodeId(self.nodeComboBox.currentText())
                self.set_cobid(self.mainCobIdTextBox.text())
            except Exception:
                self.error_message(text="Make sure that the CAN interface is connected")
                
        self.startButton = QPushButton("")
        self.startButton.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
        self.startButton.setStatusTip('Send CAN message')
        self.startButton.clicked.connect(__apply_CANMessageSettings)
        self.startButton.clicked.connect(self.read_sdo_can_thread)                 
        defaultMessageWindowLayout.addWidget(nodeLabel, 3, 0)
        defaultMessageWindowLayout.addWidget(self.nodeComboBox, 4, 0)   
        
        defaultMessageWindowLayout.addWidget(cobidLabel, 3, 1)
        defaultMessageWindowLayout.addWidget(self.mainCobIdTextBox, 4, 1)
        
        defaultMessageWindowLayout.addWidget(indexLabel, 3, 2)
        defaultMessageWindowLayout.addWidget(self.mainIndexTextBox, 4, 2)        
        
        defaultMessageWindowLayout.addWidget(subIndexLabel, 3, 3)
        defaultMessageWindowLayout.addWidget(self.mainSubIndextextbox, 4, 3)       
        defaultMessageWindowLayout.addWidget(self.startButton, 4, 4)

        
        plotframe.setLayout(defaultMessageWindowLayout)
        self.defaultMessageGroupBox.setLayout(defaultMessageWindowLayout)
                    
    def textOutputWindow(self):
        '''
        The function defines the GroupBox output window for the CAN messages
        '''  
        self.textGroupBox = QGroupBox("   Output Window")
        plotframe = QFrame()
        plotframe.setStyleSheet("QWidget { background-color: #eeeeec; }")
        plotframe.setLineWidth(0.8)
        self.textBox = QTextEdit()
        self.textBox.setReadOnly(True)
        self.textBox.resize(20, 20)
        textOutputWindowLayout = QGridLayout()
        textOutputWindowLayout.addWidget(self.textBox, 1, 0)
        self.setCentralWidget(plotframe)
        plotframe.setLayout(textOutputWindowLayout)
        self.textGroupBox.setLayout(textOutputWindowLayout)
        
    def tableOutputWindow(self):
        '''
        The function defines the GroupBox output table for Bytes monitoring for RX and TX messages
        '''  
        self.monitorGroupBox = QGroupBox("Bytes Monitoring")
        plotframe = QFrame()
        plotframe.setStyleSheet("QWidget { background-color: #eeeeec; }")
        plotframe.setLineWidth(0.6)
        self.setCentralWidget(plotframe)
        
        def __graphic_view():
            byteLabel = QLabel()
            byteLabel.setText("Bytes")
            byteLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            graphicsview = QtWidgets.QGraphicsView()
            graphicsview.setStyleSheet("QWidget { background-color: rgba(255, 255, 255, 10);  margin:0.0px; }")
            graphicsview.setFixedSize(20, 100)
            proxy = QtWidgets.QGraphicsProxyWidget()
            proxy.setWidget(byteLabel)
            proxy.setTransformOriginPoint(proxy.boundingRect().center())
            proxy.setRotation(-90)
            scene = QtWidgets.QGraphicsScene(graphicsview)
            scene.addItem(proxy)
            graphicsview.setScene(scene)
            return graphicsview
        
        def __bitLabel():
            bitLabel = QLabel()
            bitLabel.setText("Bits")
            bitLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            bitLabel.setAlignment(Qt.AlignCenter)   
            return bitLabel         
        
        RXgraphicsview = __graphic_view()
        TXgraphicsview = __graphic_view()
        RXbitLabel = __bitLabel()
        TXbitLabel = __bitLabel()
        
        # Set the table headers
        n_bytes = 8
        col = [str(i) for i in np.arange(n_bytes)]
        row = [str(i) for i in np.arange(n_bytes - 1, -1, -1)]
        # RXTables       
        self.hexRXTable = QTableWidget()  # Create a table
        self.hexRXTable.setColumnCount(1)  # Set n columns
        self.hexRXTable.setRowCount(n_bytes)  # and n rows
        self.hexRXTable.resizeColumnsToContents()  # Do the resize of the columns by content
        self.hexRXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.hexRXTable.setHorizontalHeaderLabels(["Hex"])
        self.hexRXTable.verticalHeader().hide()
        self.hexRXTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.hexRXTable.resizeColumnsToContents()
        self.hexRXTable.clearContents()  # clear cells
        self.hexRXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexRXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexRXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.decRXTable = QTableWidget()  # Create a table
        self.decRXTable.setColumnCount(1)  # Set n columns
        self.decRXTable.setRowCount(n_bytes)  # and n rows
        self.decRXTable.resizeColumnsToContents()  # Do the resize of the columns by content
        self.decRXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.decRXTable.setHorizontalHeaderLabels(["Decimal"])
        self.decRXTable.verticalHeader().hide()
        self.decRXTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.decRXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.decRXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.decRXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.decRXTable.resizeColumnsToContents()
        self.decRXTable.clearContents()  # clear cells
          
        self.RXTable = QTableWidget()  # Create a table
        self.RXTable.setColumnCount(n_bytes)  # Set n columns
        self.RXTable.setRowCount(n_bytes)  # and n rows
        # Do the resize of the columns by content
        self.RXTable.resizeColumnsToContents()
        self.RXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.RXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.RXTable.setHorizontalHeaderLabels(row)
        self.RXTable.setVerticalHeaderLabels(col)
        self.RXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.RXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.RXTable.setVisible(False)
        self.RXTable.verticalScrollBar().setValue(0)
        self.RXTable.resizeColumnsToContents()
        self.RXTable.setVisible(True)
        
        line = QFrame()
        line.setGeometry(QRect(320, 150, 118, 3))
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        
        # TXTables
        self.hexTXTable = QTableWidget()  # Create a table
        self.hexTXTable.setColumnCount(1)  # Set n columns
        self.hexTXTable.setRowCount(n_bytes)  # and n rows
        self.hexTXTable.resizeColumnsToContents()  # Do the resize of the columns by content
        self.hexTXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.hexTXTable.setHorizontalHeaderLabels(["Hex"])
        self.hexTXTable.verticalHeader().hide()
        self.hexTXTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.hexTXTable.resizeColumnsToContents()
        self.hexTXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexTXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexTXTable.clearContents()  # clear cells
        self.hexTXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.decTXTable = QTableWidget(self)  # Create a table
        self.decTXTable.setColumnCount(1)  # Set n columns
        self.decTXTable.setRowCount(n_bytes)  # and n rows
        self.decTXTable.resizeColumnsToContents()  # Do the resize of the columns by content
        self.decTXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.decTXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.decTXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.decTXTable.setHorizontalHeaderLabels(["Decimal"])
        self.decTXTable.verticalHeader().hide()
        self.decTXTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.decTXTable.resizeColumnsToContents()
        self.decTXTable.clearContents()  # clear cells
        self.decTXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)  
        self.TXTable = QTableWidget(self)  # Create a table
        self.TXTable.setColumnCount(n_bytes)  # Set n columns
        self.TXTable.setRowCount(n_bytes)  # and n rows
        # Do the resize of the columns by content
        self.TXTable.resizeColumnsToContents()
        self.TXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.TXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.TXTable.setHorizontalHeaderLabels(row)
        self.TXTable.setVerticalHeaderLabels(col)
        self.TXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.TXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.TXTable.setVisible(False)
        self.TXTable.verticalScrollBar().setValue(0)
        self.TXTable.resizeColumnsToContents()
        self.TXTable.setVisible(True)
        
        self.TXProgressBar = QProgressBar()
        self.TXProgressBar.setRange(0, 1)
        self.TXProgressBar.setValue(0)
        self.TXProgressBar.setTextVisible(False)
        
        TXLayout = QHBoxLayout()
        TXLabel = QLabel()
        TXLabel.setText("TX:")
        TXLayout.addWidget(TXLabel)
        TXLayout.addWidget(self.TXProgressBar)
              
        self.RXProgressBar = QProgressBar()
        self.RXProgressBar.setRange(0, 1)
        self.RXProgressBar.setValue(0)
        self.RXProgressBar.setTextVisible(False)
        
        RXLayout = QHBoxLayout()
        RXLabel = QLabel()
        RXLabel.setText("RX:")
        RXLayout.addWidget(RXLabel)
        RXLayout.addWidget(self.RXProgressBar)
        
        def setTableWidth():
            width = self.RXTable.verticalHeader().width()
            width += self.RXTable.horizontalHeader().length()
            self.RXTable.setMinimumWidth(width)
        
        def setTableLength():
            length = self.RXTable.verticalHeader().length()
            length += self.RXTable.horizontalHeader().width()
            self.RXTable.setMaximumHeight(length);
            
        setTableWidth()
        setTableLength()
                

        gridLayout = QGridLayout()

        gridLayout.addLayout(TXLayout, 0 , 1)
        gridLayout.addWidget(TXbitLabel, 1, 2)
        gridLayout.addWidget(TXgraphicsview, 2, 0)
        gridLayout.addWidget(self.TXTable, 2, 1)
        gridLayout.addWidget(self.hexTXTable, 2, 2)
        gridLayout.addWidget(self.decTXTable, 2, 3)
        
        gridLayout.addWidget(line, 2, 4, 2, 4)
                
        gridLayout.addLayout(RXLayout, 0 ,6)        
        gridLayout.addWidget(RXbitLabel, 1, 6)
        gridLayout.addWidget(RXgraphicsview, 2,5)
        gridLayout.addWidget(self.RXTable, 2, 6)
        gridLayout.addWidget(self.hexRXTable, 2, 7)
        gridLayout.addWidget(self.decRXTable, 2, 8)
        
        plotframe.setLayout(gridLayout)
        self.monitorGroupBox.setLayout(gridLayout)
                

        
    def configure_device_box(self):
        '''
        The function provides a frame for the configured devices  according to the file main_cfg.yml
        '''
        self.configureDeviceBoxGroupBox = QGroupBox("Configured Devices")
        plotframe = QFrame()
        plotframe.setStyleSheet("QWidget { background-color: #eeeeec; }")
        plotframe.setLineWidth(0.6)
        
        self.configureDeviceBoxLayout = QHBoxLayout()
        deviceLabel = QLabel()
        self.deviceButton = QPushButton("")
        self.deviceButton.setStatusTip('Choose the configuration yaml file')
        if self.__devices[0] == "None":
            deviceLabel.setText("Configure Device")
            self.deviceButton.setIcon(QIcon('graphicsUtils/icons/icon_question.png'))
            self.deviceButton.clicked.connect(self.update_device_box)
        else:
            deviceLabel.setText("[" + self.__devices[0] + "]")
            self.update_device_box()
        self.configureDeviceBoxLayout.addWidget(deviceLabel)
        self.configureDeviceBoxLayout.addWidget(self.deviceButton)
        self.setCentralWidget(plotframe)
        plotframe.setLayout(self.configureDeviceBoxLayout)
        self.configureDeviceBoxGroupBox.setLayout(self.configureDeviceBoxLayout)

    def update_device_box(self):
        '''
        The function Will update the configured device section with the registered devices according to the file main_cfg.yml
        '''
        if self.__devices[0] == "None":
            conf = self.child.open()
        else:
            conf = AnalysisUtils().open_yaml_file(file=config_dir + self.__devices[0] + "_cfg.yml", directory=lib_dir)
        
        self.__devices.append(conf["Application"]["device_name"])
        
        self.deviceButton.deleteLater()
        self.configureDeviceBoxLayout.removeWidget(self.deviceButton)
        self.deviceButton = QPushButton("")
        deviceName, version, icon_dir, nodeIds, dictionary_items, adc_channels_reg, _ , _, chipId = self.configure_devices(conf)
        # Load ADC calibration constants
        #adc_calibration = pd.read_csv(config_dir + "adc_calibration.csv", delimiter=",", header=0)
        #condition = (adc_calibration["chip"] == chipId)
        #chip_parameters = adc_calibration[condition]
        #print(chip_parameters["calib_a"],chip_parameters["calib_b"] )
        self.set_deviceName(deviceName)
        self.set_version(version)
        self.set_icon_dir(icon_dir)
        self.set_nodeList(nodeIds)
        self.set_dictionary_items(dictionary_items) 
        self.set_adc_channels_reg(adc_channels_reg)               
        self.deviceButton.setIcon(QIcon(self.get_icon_dir()))
        self.deviceButton.clicked.connect(self.show_deviceWindow)
        self.configureDeviceBoxLayout.addWidget(self.deviceButton)
         
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
        
        return  self.__deviceName, self.__version, self.__appIconDir, self.__nodeIds, self.__dictionary_items, self.__adc_channels_reg, self.__adc_index, self.__resistor_ratio, self.__chipId
    
        
    def connect_server(self):
        '''
        The function is starts calling the CANWrapper [called by the connectButton].
        First: if the option settings in the file main_cfg.yaml is True. The function will search for any stored settings
               from the previous run for the chosen interface [the file socketcan__CANSettings.yml], Otherwise The settings in the file main_cfg.yaml will be taken
            e.g [bitrate, Sjw, Sample point,....]
        Second: Communication with CAN wrapper will begin
        ''' 
        if self.connectButton.isChecked():
            _interface = self.get_interface()    
            try: 
                filename = lib_dir + config_dir + _interface + "_CANSettings.yml"
                if (os.path.isfile(filename)and self.__canSettings):
                    filename = os.path.join(lib_dir, config_dir + _interface + "_CANSettings.yml")
                    test_date = time.ctime(os.path.getmtime(filename))
                    # Load settings from CAN settings file
                    _canSettings = AnalysisUtils().open_yaml_file(file=config_dir + _interface + "_CANSettings.yml", directory=lib_dir)
                    self.logger.notice("Loading CAN settings from the file %s produced on %s" % (filename, test_date))
                    _channels = _canSettings['CAN_Interfaces'][_interface]["channels"]
                    _ipAddress = _canSettings['CAN_Interfaces'][_interface]["ipAddress"]
                    _bitrate = _canSettings['CAN_Interfaces'][_interface]["bitrate"]
                    _nodIds = _canSettings['CAN_Interfaces'][_interface]["nodIds"]
                    _samplePoint = _canSettings['CAN_Interfaces'][_interface]["samplePoint"]
                    _sjw = _canSettings['CAN_Interfaces'][_interface]["SJW"]
                       
                    # Update settings
                    self.set_nodeList(_nodIds)
                    self.set_channelPorts(list(str(_channels)))                
                    self.set_channel(_channels)
                    _channel = self.get_channel()
                    # Update buttons
                    self.channelComboBox.clear()
                    self.channelComboBox.addItems(list(str(_channels)))
                    self.nodeComboBox.clear()
                    self.nodeComboBox.addItems(list(map(str, _nodIds)))
                    
                    
                    self.wrapper = CanWrapper(interface=_interface, bitrate=_bitrate, samplePoint = _samplePoint, sjw = _sjw, ipAddress=_ipAddress,
                                                                channel=_channel)
                    if self.__deviceName == "MOPS":
                        self.wrapper.confirm_Mops(channel=_channel)
                    else:
                        pass
                    
                else:
                    _channel = self.get_channel()
                    _bitrate = self.get_bitrate()
                    _samplePoint =self.get_sample_point()
                    self.wrapper = CanWrapper(interface=_interface, bitrate=_bitrate, samplePoint = _samplePoint, channel=_channel)
                    
                
                    if self.__deviceName == "MOPS":
                        self.wrapper.confirm_Mops(channel=_channel)
                    else:
                        pass 
            except:
                self.connectButton.setChecked(False)
        else:
           self.stop_server()
           self.stop_random_timer()
        self.control_logger = self.wrapper.logger
        
    
    def stop_server(self):
        '''
        Stop the communication with CAN wrapper
        ''' 
        try:
            self.stop_adc_timer()
            self.wrapper.stop()
        except:
            pass

    def set_can_settings(self): 
        '''
        The function will set all the required parameters for the CAN communication
        1. get the required parameters for the CAN communication e.g. bitrate, interface, channel,.......
        2. Save the settings to a file _CANSettings.yaml
        3. Initialize the main server CANWrapper 
        ''' 
        try: 
            _bitrate = self.get_bitrate()
            _interface = self.get_interface()
            _channel = self.get_channel()
            _channels = AnalysisUtils().get_info_yaml(dictionary=self.__conf['CAN_Interfaces'], index=_interface, subindex="channels")
            _sample_point = self.get_sample_point()
            _sjw = self.get_sjw()
            _nodeItems = _channels[int(_channel)]
            _timeout = 500
            if _interface == "AnaGate":
                 self.set_ipAddress(self.firsttextbox.text()) 
                 _ipAddress = self.get_ipAddress()
            else:
                _ipAddress = None
                pass
            # Change the buttons view in the main GUI
            self.logger.info("Applying changes to the main server") 
            self.interfaceComboBox.clear()
            self.interfaceComboBox.addItems([_interface])
            self.channelComboBox.clear()
            self.channelComboBox.addItems([str(_channel)])
            self.nodeComboBox.clear()
            self.nodeComboBox.addItems(list(map(str, _nodeItems)))
            self.connectButton.setChecked(True)
            # Save the settings into a file
            dict_file = {"CAN_Interfaces": {_interface:{"bitrate":_bitrate ,"samplePoint":_sample_point,"SJW":_sjw, "ipAddress":str(_ipAddress), "timeout":_timeout, "channels":int(_channel), "nodIds":_nodeItems}}}
            self.logger.info("Saving CAN settings to the file %s" % lib_dir + config_dir + _interface + "_CANSettings.yml") 
            with open(lib_dir + config_dir + _interface + "_CANSettings.yml", 'w') as yaml_file:
                yaml.dump(dict_file, yaml_file, default_flow_style=False)
            
            # Apply the settings to the main server
            self.wrapper = CanWrapper(interface=_interface, bitrate=_bitrate, ipAddress=str(_ipAddress),
                                                channel=int(_channel),sjw = int(_sjw))
            # restart the channel
            self.wrapper.hardware_config(channel = int(_channel))
        except Exception:
          self.error_message(text="Please choose an interface or close the window")
 
    def restart_socketchannel(self):
        '''
        The function will restart the SocketCAN 
        '''   
        _interface = "socketcan"
        try: 
            filename = lib_dir + config_dir + _interface + "_CANSettings.yml"
            filename = os.path.join(lib_dir, config_dir + _interface + "_CANSettings.yml")
            test_date = time.ctime(os.path.getmtime(filename))
            # Load settings from CAN settings file
            _canSettings = AnalysisUtils().open_yaml_file(file=config_dir + _interface + "_CANSettings.yml", directory=lib_dir)
            _channel = _canSettings['CAN_Interfaces'][_interface]["channels"]
            _bitrate = _canSettings['CAN_Interfaces'][_interface]["bitrate"]
            _samplePoint = _canSettings['CAN_Interfaces'][_interface]["samplePoint"]
            _sjw = _canSettings['CAN_Interfaces'][_interface]["SJW"]
                    
            os.system(". " + rootdir[:-14] + "/controlServer/socketcan_wrapper_enable.sh %i %s %s %i" %(_bitrate,_samplePoint,_sjw,_channel))
        except Exception:
           self.error_message(text="Settings file doesnt exist at %s"%(lib_dir + config_dir + _interface))          

    def dump_socketchannel(self,channel):
        self.logger.info("Dumping %s channel"%channel)
        print_command = "echo ==================== Dumping %s bus traffic ====================\n"%channel
        candump_command="candump %s -x -c -t A"%channel
        os.system("gnome-terminal -e 'bash -c \""+print_command+candump_command+";bash\"'")

    '''
    Define all child windows
    '''        
              
    def dump_child_window(self, ChildWindow):
        ChildWindow.setObjectName("Bus Messages")
        ChildWindow.setWindowTitle("Bus Messages")
        ChildWindow.setGeometry(915, 490, 600, 400)
        mainLayout = QGridLayout()
        # Define a frame for that group
        
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(plotframe)
        # Define dumpGroupBox
        dumpGroupBox = QGroupBox()
        self.dumptextBox = QTextEdit()
        self.dumptextBox.setReadOnly(True)
        textOutputWindowLayout = QGridLayout()
        textOutputWindowLayout.addWidget(self.dumptextBox, 0, 0)
        dumpGroupBox.setLayout(textOutputWindowLayout)
        
        #dump can messages
        self.initiate_dump_can_timer(5000)
        
        buttonBox = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        close_button.clicked.connect(ChildWindow.close)
        buttonBox.addWidget(close_button)
                 
        mainLayout.addWidget(dumpGroupBox , 0, 0)
        mainLayout.addLayout(buttonBox , 2, 0)
        plotframe.setLayout(mainLayout) 
        QtCore.QMetaObject.connectSlotsByName(ChildWindow)
        
    def can_message_child_window(self, ChildWindow):
        ChildWindow.setObjectName("CAN Message")
        ChildWindow.setWindowTitle("CAN Message")
        ChildWindow.setGeometry(915, 490, 250, 315)
        mainLayout = QGridLayout()
        __channelList = self.__channelPorts
        _cobeid = self.get_cobid()
        _bytes = self.get_bytes()
        if type(_cobeid) == int:
            _cobeid = hex(_cobeid)
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(plotframe)
        # Define First Group
        FirstGroupBox = QGroupBox("")
        # comboBox and label for channel
        FirstGridLayout = QGridLayout() 
        cobidLabel = QLabel("CAN Identifier")
        cobidLabel.setText("CAN Identifier:")
        cobidtextbox = QLineEdit(str(_cobeid))
        FirstGridLayout.addWidget(cobidLabel, 0, 0)
        FirstGridLayout.addWidget(cobidtextbox, 0, 1) 
        FirstGroupBox.setLayout(FirstGridLayout) 
        
        SecondGroupBox = QGroupBox("Message Data [hex]")
        # comboBox and label for channel
        SecondGridLayout = QGridLayout()
        ByteList = ["Byte0 :", "Byte1 :", "Byte2 :", "Byte3 :", "Byte4 :", "Byte5 :", "Byte6 :", "Byte7 :"] 
        LabelByte = [ByteList[i] for i in np.arange(len(ByteList))]
        self.ByteTextbox = [ByteList[i] for i in np.arange(len(ByteList))]        
        for i in np.arange(len(ByteList)):
            LabelByte[i] = QLabel(ByteList[i])
            LabelByte[i].setText(ByteList[i])
            self.ByteTextbox[i] = QLineEdit(str(_bytes[i]))
            if i <= 3:
                SecondGridLayout.addWidget(LabelByte[i], i, 0)
                SecondGridLayout.addWidget(self.ByteTextbox[i], i, 1)
            else:
                SecondGridLayout.addWidget(LabelByte[i], i - 4, 4)
                SecondGridLayout.addWidget(self.ByteTextbox[i], i - 4, 5)
        SecondGroupBox.setLayout(SecondGridLayout) 
        
        def __apply_CANMessageSettings():
            _cobid = cobidtextbox.text() 
            textboxValue = [self.ByteTextbox[i] for i in np.arange(len(self.ByteTextbox))]
            
            for i in np.arange(len(self.ByteTextbox)):
                textboxValue[i] = self.ByteTextbox[i].text()
            bytes_int = [int(b, 16) for b in textboxValue]
            _index = hex(int.from_bytes([bytes_int[1], bytes_int[2]], byteorder=sys.byteorder))
            _subIndex = hex(int.from_bytes([bytes_int[3]], byteorder=sys.byteorder))
            
            self.set_cobid(_cobid)
            self.set_bytes(bytes_int)
            self.set_subIndex(_subIndex)
            self.set_index(_index)
            #self.read_sdo_can_thread()
        
            
        buttonBox = QHBoxLayout()
        send_button = QPushButton("Send")
        send_button.setIcon(QIcon('graphicsUtils/icons/icon_true.png'))
        send_button.clicked.connect(__apply_CANMessageSettings)
        send_button.clicked.connect(self.write_can_message)
        
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        close_button.clicked.connect(ChildWindow.close)

        buttonBox.addWidget(send_button)
        buttonBox.addWidget(close_button)
                 
        mainLayout.addWidget(FirstGroupBox , 0, 0)
        mainLayout.addWidget(SecondGroupBox , 1, 0)
        mainLayout.addLayout(buttonBox , 2, 0)

        plotframe.setLayout(mainLayout) 
        self.MenuBar.create_statusBar(ChildWindow)
        QtCore.QMetaObject.connectSlotsByName(ChildWindow)
                      
    def can_settings_child_window(self, ChildWindow):
        ChildWindow.setObjectName("CAN Settings")
        ChildWindow.setWindowTitle("CAN Settings")
        ChildWindow.setGeometry(915, 10, 250, 100)
        #ChildWindow.resize(250, 400)  # w*h
        mainLayout = QGridLayout()
        _channelList = self.__channelPorts
        # Define a frame for that group
        plotframe = QFrame(ChildWindow)
        plotframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(plotframe)
        
        # Define First Group
       # FirstGroupBox = QGroupBox("")
        FirstGridLayout = QGridLayout()
        
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(ChildWindow.close)
        
        FirstGridLayout.addWidget(clear_button, 0, 0)
       # FirstGroupBox.setLayout(FirstGridLayout)
        
        # Define the second group
        SecondGroupBox = QGroupBox("Bus Configuration")
        SecondGridLayout = QGridLayout()        
        # comboBox and label for channel
        chLabel = QLabel()
        chLabel.setText("CAN Interface    :")
        
        interfaceLayout = QHBoxLayout()
        __interfaceItems = [""] + self.__interfaceItems
        interfaceComboBox = QComboBox()
        for item in __interfaceItems: interfaceComboBox.addItem(item)
        interfaceComboBox.activated[str].connect(self.set_interface)
        
        interfaceLayout.addWidget(interfaceComboBox)
        # Another group will be here for Bus parameters
        self.BusParametersGroupBox()
        
        channelLabel = QLabel()
        channelLabel.setText("CAN Bus: ")
        channelComboBox = QComboBox()
        for item in _channelList: channelComboBox.addItem(item)
        channelComboBox.activated[str].connect(self.set_channel)

        # FirstButton
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(ChildWindow.close)
        
        SecondGroupBox.setLayout(SecondGridLayout)
        SecondGridLayout.addWidget(chLabel, 0, 0)
        SecondGridLayout.addLayout(interfaceLayout, 1, 0)
        SecondGridLayout.addWidget(channelLabel, 2, 0)
        SecondGridLayout.addWidget(channelComboBox, 3, 0)
        
        def _interfaceParameters():
            SecondGridLayout.removeWidget(self.SubSecondGroupBox)
            self.SubSecondGroupBox.deleteLater()
            self.SubSecondGroupBox = None
            _interface = interfaceComboBox.currentText()
            _channel = channelComboBox.currentText()
            self.set_channel(_channel)
            self.set_interface(_interface)
            self.BusParametersGroupBox(ChildWindow=ChildWindow , interface=_interface)
            SecondGridLayout.addWidget(self.SubSecondGroupBox, 4, 0)        

        interfaceComboBox.activated[str].connect(_interfaceParameters)
        # Define Third Group
        ThirdGroupBox = QGroupBox("")
        ThirdGridLayout = QGridLayout()
        
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.png'))
        close_button.clicked.connect(ChildWindow.close)
        ThirdGridLayout.addWidget(close_button, 0, 1)
        ThirdGroupBox.setLayout(ThirdGridLayout)
        # mainLayout.addWidget(FirstGroupBox, 0, 0)
        mainLayout.addWidget(SecondGroupBox, 1, 0)
        mainLayout.addWidget(ThirdGroupBox, 2, 0)
        plotframe.setLayout(mainLayout) 
        self.MenuBar.create_statusBar(ChildWindow)
        QtCore.QMetaObject.connectSlotsByName(ChildWindow)                
        
    def BusParametersGroupBox(self, ChildWindow=None, interface="Others"):
        # Define subGroup
        self.SubSecondGroupBox = QGroupBox("Bus Parameters")
        SubSecondGridLayout = QGridLayout()
        firstLabel = QLabel("firstLabel")
        secondLabel = QLabel("secondLabel")
        thirdLabel = QLabel("thirdLabel")
        sampleLabel = QLabel("sampleLabel")
        firstComboBox = QComboBox()
        thirdTextBox = QLineEdit("125000")
        thirdTextBox.setFixedSize(70, 25)              
        secondLabel.setText("SJW:")
        secondItems = ["1", "2", "3", "4"]
        secondComboBox = QComboBox()
        for item in secondItems: secondComboBox.addItem(item)
        thirdLabel.setText("Bit Speed [bit/s]:")
        thirdItems = self.get_bitrate_items()
        thirdComboBox = QComboBox()
        for item in thirdItems: thirdComboBox.addItem(item)
        sampleLabel.setText("Sample point")
        sampleItems = self.get_sample_points()
        sampleComboBox = QComboBox()
        sampleComboBox.setStatusTip('The location of Sample point in percentage inside each bit period')
        for item in sampleItems: sampleComboBox.addItem(item)                   
        if (interface == "AnaGate"):
            firstLabel.setText("IP address:")
            self.firsttextbox = QLineEdit('192.168.1.254')
            SubSecondGridLayout.addWidget(firstLabel, 0, 0)
            SubSecondGridLayout.addWidget(self.firsttextbox, 0, 1)
        else:
            pass                  
        
        def _set_bus():
            self.set_sjw(secondComboBox.currentText())
            self.set_bitrate(thirdTextBox.text())  
            self.set_sample_point(sampleComboBox.currentText())
            
        set_button = QPushButton("Set in all")
        set_button.setStatusTip('The button will apply the same settings for all CAN controllers')  # show when move mouse to the icon
        set_button.setIcon(QIcon('graphicsUtils/icons/icon_true.png'))
        set_button.clicked.connect(_set_bus)
        set_button.clicked.connect(self.set_can_settings)
        
        SubSecondGridLayout.addWidget(secondLabel, 1, 0)
        SubSecondGridLayout.addWidget(secondComboBox, 1, 1)
        SubSecondGridLayout.addWidget(thirdLabel, 2, 0)
        #SubSecondGridLayout.addWidget(thirdComboBox, 2, 1)
        SubSecondGridLayout.addWidget(thirdTextBox, 2, 1)
        SubSecondGridLayout.addWidget(sampleLabel, 3, 0)
        SubSecondGridLayout.addWidget(sampleComboBox, 3, 1) 
        SubSecondGridLayout.addWidget(set_button, 4, 1) 
        self.SubSecondGroupBox.setLayout(SubSecondGridLayout)
                
                
    '''
    Define can communication messages
    '''
    def read_sdo_can(self):
        """Read an object via |SDO| with message validity check
        1. Request the SDO message parameters [e.g.  Index, subindex and _nodeId]
        2. Communicate with the read_sdo_can function in the CANWrapper to send SDO message
        3. Print the result if print_sdo is True
        The function is called by the following functions: 
           a) read_adc_channels
           b)  read_monitoring_values    
           c) read_configuration_values
        """
        try:
            _index = int(self.get_index(), 16)
            _subIndex = int(self.get_subIndex(), 16)
            _nodeId = self.get_nodeId()
            _nodeId = int(_nodeId[0])
            _interface = self.get_interface()
            data_RX = self.wrapper.read_sdo_can(_nodeId, _index, _subIndex, self.__timeout)
            return data_RX
        except Exception:
            self.error_message(text="Make sure that the CAN interface is connected")
            return None
                           
    def read_sdo_can_thread(self, trending=False, print_sdo=True):
        """Read an object via |SDO| in a thread
        1. Request the SDO message parameters [e.g.  Index, subindex and _nodeId]
        2. Communicate with the read_sdo_can_thread function in the CANWrapper to send SDO message
        3. Print the result if print_sdo is True
        The function is called by the following functions: 
           a) send_random_can
           b) device_child_window
           c) default_message_window 
           d) can_message_child_window
        """
        try:
            _index = int(self.get_index(), 16)
            _subIndex = int(self.get_subIndex(), 16)
            _nodeId = self.get_nodeId()
            _nodeId = int(_nodeId[0])
            _cobid_TX = self.get_cobid()
            _cobid_RX, data_RX = self.wrapper.read_sdo_can_thread(nodeId= _nodeId, index=_index, subindex=_subIndex, timeout=self.__timeout,cobid=int(_cobid_TX,16))
            if print_sdo == True:
                #self.control_logger.disabled = False
                self.print_sdo_can(index=_index, subIndex=_subIndex, response_from_node=data_RX, cobid_TX = int(_cobid_TX,16), cobid_RX = _cobid_RX )
        except Exception:
            self.error_message(text="Make sure that the CAN interface is connected")

    def print_sdo_can(self , index=None, subIndex=None, response_from_node=None, cobid_TX = None, cobid_RX = None):
        # printing the read message with cobid = SDO_RX + nodeId
        MAX_DATABYTES = 8
        msg = [0 for i in range(MAX_DATABYTES)]
        msg[0] = 0x40  # Defines a read (reads data only from the node) dictionary object in CANOPN standard
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subIndex
        #  fill the Bytes/bits table
        self.set_table_content(bytes=msg, comunication_object="SDO_TX")
        # printing RX     
        self.set_textBox_message(comunication_object="SDO_TX", msg=str([hex(m)[2:] for m in msg]),cobid = str(hex(cobid_TX)+" "))
        # print decoded response
        if response_from_node is not None:
            # printing response 
            b1, b2, b3, b4 = response_from_node.to_bytes(4, 'little')
            RX_response = [0x43] + msg[1:4] + [b1, b2, b3, b4]
            # fill the Bytes/bits table       
            self.set_table_content(bytes=RX_response, comunication_object="SDO_RX")
            # printing TX   
            self.set_textBox_message(comunication_object="SDO_RX", msg=str([hex(m)[2:] for m in RX_response]), cobid = str(hex(cobid_RX)+" "))
            # print decoded response
            decoded_response = f'{response_from_node:03X}\n-----------------------------------------------------------------------'
            self.set_textBox_message(comunication_object="Decoded", msg=decoded_response,cobid =str(hex(cobid_RX)+": ADC value = "))
        else:
            TX_response = "No Response Message"
            self.set_textBox_message(comunication_object="ErrorFrame", msg=TX_response,cobid = str("NONE"+"  "))
            decoded_response = f'------------------------------------------------------------------------'
            self.set_textBox_message(comunication_object="newline", msg=decoded_response,cobid =None)

    def send_random_can(self): 
        """
        The function will send random messages to the bus with random index and random subindex 
        The function is called by the following functions: 
           a)  RandomDumpMessage_action button
           b)  initiate_random_timer
        """
        _index = np.random.randint(1000, 2500)
        _subIndex = np.random.randint(0, 5)
        _nodeId = int(self.nodeComboBox.currentText())
        _cobid_TX = self.mainCobIdTextBox.text()
        
        self.set_nodeId(self.nodeComboBox.currentText())
        self.set_index(str(_index))
        self.set_subIndex(str(_subIndex))
        self.set_cobid(_cobid_TX)
        
        # clear cells
        self.TXProgressBar.setValue(0)
        self.TXTable.clearContents()  
        self.hexTXTable.clearContents()
        self.decTXTable.clearContents()
        
        #send SDO can
        self.read_sdo_can_thread(print_sdo=True)  
 
    def dump_can_message(self): 
        """
        The function is to be used later for CANdump [Qamesh]
        """
        readCanMessage = self.wrapper.read_can_message_thread()
        self.dumptextBox.append(readCanMessage)
                               
    def write_can_message(self):
        """
        The function will send a standard CAN message and receive it using the function read_can_message_thread 
        1. Request the SDO message parameters [e.g.  _cobid, Index, subindex and bytes]
        2. Print the TX message in the textBox and the Bytes table
        3. Communicate with the write_can_message function in the CANWrapper to send the CAN message
        4. Communicate with the read_can_message_thread function to read the CAN message
        The function is called by the following functions: 
           a)  __restart_device
           b)  __reset_device
           c)  can_message_child_window
        """
        
        _cobid_TX = self.get_cobid()
        _bytes = self.get_bytes()
        _index = hex(int.from_bytes([_bytes[1], _bytes[2]], byteorder=sys.byteorder))
        _subIndex = hex(int.from_bytes([_bytes[3]], byteorder=sys.byteorder))
        #fill the Bytes table     
        self.set_table_content(bytes=_bytes, comunication_object="SDO_TX")
        #fill the textBox     
        self.set_textBox_message(comunication_object="SDO_TX", msg=str([hex(b)[2:] for b in _bytes]), cobid = str(_cobid_TX)+" ")    
        try: 
            # Send the can Message
            self.wrapper.write_can_message(int(_cobid_TX,16), _bytes, flag=0, timeout=self.__timeout)
            # receive the message
            self.read_can_message_thread()
        except Exception:
            self.error_message(text="Make sure that the CAN interface is connected")
            
    def read_can_message_thread(self, print_sdo=True):

        readCanMessage = self.wrapper.read_can_message_thread()
        if readCanMessage is not None:
           cobid_ret, data_ret , dlc, flag, t = readCanMessage
           data_ret_int = int.from_bytes(data_ret, byteorder=sys.byteorder)
           # get the data in Bytes
           b1, b2, b3, b4, b5, b6, b7, b8 = data_ret_int.to_bytes(8, 'little') 
           self.logger.info(f'Got data: [{b5:02x},  {b6:02x},  {b7:02x}, {b8:02x}]') 
           # make an array of the bytes data
           data_ret_bytes = [b1, b2, b3, b4, b5, b6, b7, b8]
           # get the hex form of each byte
           data_ret_hex = [hex(b)[2:] for b in data_ret_bytes]
           if print_sdo == True:
               #fill the Bytes table     
               self.set_table_content(bytes=data_ret, comunication_object="SDO_RX")
               #fill the textBox
               self.set_textBox_message(comunication_object="SDO_RX", msg=str(data_ret_hex),cobid = str(hex(cobid_ret)+" "))
        else:
            cobid_ret, data_ret, dlc, flag, t = None, None, None, None, None
            RX_response = "No Response Message"
            self.set_textBox_message(comunication_object="ErrorFrame", msg=RX_response,cobid = str("NONE"+"  "))
        #fill the textBox
        decoded_response = f'------------------------------------------------------------------------'
        self.set_textBox_message(comunication_object="newline", msg=decoded_response, cobid = None) 
        return cobid_ret, data_ret, dlc, flag, t
    

    def device_child_window(self, ChildWindow):    
        '''
        The function will Open a special window for the device [MOPS] .
        The calling function for this is show_deviceWindow
        '''
        _channel = self.get_channel()
        n_channels = 33
        try:
            self.wrapper.confirm_Mops(channel=int(_channel))
        except Exception:
            pass
        #  Open the window
        ChildWindow.setObjectName("DeviceWindow")
        ChildWindow.setWindowTitle("Device Window [ " + self.__deviceName + "]")
        ChildWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        ChildWindow.setGeometry(1175, 10, 200, 770)
        logframe = QFrame()
        logframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(logframe)
        
        # Initialize tab screen
        self.tabLayout = QGridLayout()
        self.devicetTabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget() 
        
        nodeLabel = QLabel()
        nodeLabel.setText("Connected nodes :")
                
        deviceNodeComboBox = QComboBox()
        nodeItems = self.__nodeIds
        self.set_nodeList(nodeItems)
        for item in list(map(str, nodeItems)): deviceNodeComboBox.addItem(item)

        cobidLabel = QLabel()
        cobidLabel.setText("CAN Identifier")
        CobIdTextBox = QLineEdit(self.__cobid)
        CobIdTextBox.setFixedSize(70, 25)
            
        def __set_bus():
            self.set_nodeId(deviceNodeComboBox.currentText())
            self.set_cobid(CobIdTextBox.text())
                   
        def __restart_device():
            _cobeid = hex(0x0)
            self.set_cobid(_cobeid)
            self.set_bytes([0, 0, 0, 0, 0, 0, 0, 0]) 
            self.logger.info("Restarting the %s device with a cobid message %s"%(self.get_deviceName(), str(_cobeid)))
            self.write_can_message()

        def __reset_device():
            _cobeid = hex(0x701)
            self.set_cobid(_cobeid)
            self.set_bytes([0, 0, 0, 0, 0, 0, 0, 0]) 
            self.logger.info("Resetting the %s device with a cobid message %s"%(self.get_deviceName(), str(_cobeid)))
            self.write_can_message()
                    
        def __get_subIndex_description():        
            dictionary = self.__dictionary_items
            index = self.IndexListBox.currentItem().text()
            if self.subIndexListBox.currentItem() is not None:
                subindex = self.subIndexListBox.currentItem().text()
                self.subindex_description_items = AnalysisUtils().get_subindex_description_yaml(dictionary=dictionary, index=index, subindex=subindex)
                description_text = self.index_description_items + "<br>" + self.subindex_description_items
                self.indexTextBox.setText(description_text) 
            
        def __get_subIndex_items():
            index = self.get_index()
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
                
        self.GridLayout = QGridLayout()    
        icon = QLabel(self)
        pixmap = QPixmap(self.get_icon_dir())
        icon.setPixmap(pixmap.scaled(100, 100))
        
        device_title = QLabel()
        newfont = QFont("Times", 12, QtGui.QFont.Bold)
        device_title.setFont(newfont)
        device_title.setText("        " + self.get_deviceName())
        BottonHLayout = QVBoxLayout()
        startButton = QPushButton("")
        startButton.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
        startButton.setStatusTip('Send CAN message')  # show when move mouse to the icon
        startButton.clicked.connect(__set_bus)
        startButton.clicked.connect(self.read_sdo_can_thread)

        resetButton = QPushButton()
        resetButton.setIcon(QIcon('graphicsUtils/icons/icon_reset.png'))
        resetButton.setStatusTip('Reset the chip [The %s chip should reply back with a cobid 0x701]'%self.get_deviceName())
        resetButton.clicked.connect(__reset_device)
                       
        restartButton = QPushButton()
        restartButton.setIcon(QIcon('graphicsUtils/icons/icon_restart.png'))
        restartButton.setStatusTip('Restart the chip [The %s chip should reply back with a cobid 0x00]'%self.get_deviceName())
        restartButton.clicked.connect(__restart_device)
        
        BottonHLayout.addWidget(startButton)
        BottonHLayout.addWidget(resetButton)
        BottonHLayout.addWidget(restartButton)
        
        firstVLayout = QVBoxLayout()
        firstVLayout.addWidget(icon)
        firstVLayout.addWidget(device_title)
        firstVLayout.addLayout(BottonHLayout)
        firstVLayout.addSpacing(300)
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
        self.IndexListBox.currentItemChanged.connect(self.set_index_value) 
        self.IndexListBox.currentItemChanged.connect(__get_subIndex_items)
        self.IndexListBox.currentItemChanged.connect(__get_index_description)  
        
        subIndexLabel = QLabel()
        subIndexLabel.setText("SubIndex")
        self.subIndexListBox = QListWidget()
        self.subIndexListBox.setFixedWidth(60)
        self.subIndexListBox.currentItemChanged.connect(self.set_subIndex_value)  
        self.subIndexListBox.currentItemChanged.connect(__get_subIndex_description)  
        
        self.GridLayout.addWidget(indexLabel, 0, 1)
        self.GridLayout.addWidget(subIndexLabel, 0, 2)
        self.GridLayout.addLayout(firstVLayout, 1, 0)
        self.GridLayout.addWidget(self.IndexListBox, 1, 1)
        self.GridLayout.addWidget(self.subIndexListBox, 1, 2)
        self.GridLayout.addLayout(VLayout, 0, 3, 0, 4)
        self.tab1.setLayout(self.GridLayout)        

        HLayout = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        close_button.clicked.connect(self.stop_adc_timer)
        close_button.clicked.connect(ChildWindow.close)
        HLayout.addSpacing(350)
        HLayout.addWidget(close_button)
        
        # Add Adc channels tab [These values will be updated with the timer self.initiate_adc_timer]
        self.adc_values_window()
        self.monitoring_values_window()
        self.configuration_values_window()
        
        # initiate a PlotWidget [data holder] for all ADC channels for later trending
        self.initiate_trending_figure(n_channels = n_channels)
                        
        nodeHLayout = QHBoxLayout()
        nodeHLayout.addWidget(nodeLabel)
        nodeHLayout.addWidget(deviceNodeComboBox)
        nodeHLayout.addSpacing(400)
        
        codidLayout = QHBoxLayout()
        codidLayout.addWidget(cobidLabel)
        codidLayout.addWidget(CobIdTextBox)
        codidLayout.addSpacing(400)
        
        self.tabLayout.addLayout(nodeHLayout, 1, 0)
        self.tabLayout.addLayout(codidLayout, 2, 0)
        self.tabLayout.addWidget(self.devicetTabs, 3, 0)
        self.tabLayout.addLayout(HLayout, 4, 0)
        
        self.devicetTabs.addTab(self.tab2, "Device Channels") 
        self.devicetTabs.addTab(self.tab1, "Object Dictionary")
        
                
        mainLayout = QGridLayout()     
        HBox = QHBoxLayout()
        send_button = QPushButton("run ")
        send_button.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
        send_button.clicked.connect(__set_bus)
        send_button.clicked.connect(self.initiate_adc_timer)

        stop_button = QPushButton("stop ")
        stop_button.setIcon(QIcon('graphicsUtils/icons/icon_stop.png'))
        stop_button.clicked.connect(self.stop_adc_timer)
        
        # update a progress bar for the bus statistics
        progressLabel = QLabel()
        progressLabel.setText("   ")#Timer load")
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0,n_channels)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        progressHLayout = QHBoxLayout()
        progressHLayout.addWidget(progressLabel)
        progressHLayout.addWidget(self.progressBar)
                
        HBox.addWidget(send_button)
        HBox.addWidget(stop_button)
        
        mainLayout.addWidget(self.FirstGroupBox , 0, 0, 3, 3)
        mainLayout.addWidget(self.ThirdGroupBox, 0, 3, 2, 5)
        mainLayout.addWidget(self.SecondGroupBox, 2, 3, 1, 5)
        mainLayout.addLayout(HBox , 3, 0)
        mainLayout.addLayout(progressHLayout, 3, 3)
        self.tab2.setLayout(mainLayout)
        self.MenuBar.create_statusBar(ChildWindow)
        logframe.setLayout(self.tabLayout)
         
    def adc_values_window(self):
        '''
        The function will create a QGroupBox for ADC Values [it is called by the function device_child_window]
        '''
        # info to read the ADC from the yaml file
        self.FirstGroupBox = QGroupBox("ADC Channels")
        FirstGridLayout = QGridLayout()
        _adc_channels_reg = self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _adc_indices = list(self.__adc_index)
                
        for i in np.arange(len(_adc_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex="subindex_items"))
            labelChannel = [_subIndexItems[k] for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            self.channelValueBox = [_subIndexItems[k] for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            self.trendingBox = [False for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            self.trendingBotton = [_subIndexItems[k] for k in np.arange(len(_subIndexItems) * len(_adc_indices))]
            _start_a = 3  # to start from channel 3
            for subindex in np.arange(_start_a, len(_subIndexItems)+_start_a-1):
                s = subindex-_start_a
                s_correction = subindex-2
                labelChannel[s] = QLabel()
                self.channelValueBox[s] = QLineEdit()
                self.channelValueBox[s].setStyleSheet("background-color: white; border: 1px inset black;")
                self.channelValueBox[s].setReadOnly(True)
                self.channelValueBox[s].setFixedWidth(80)
                subindex_description_item = AnalysisUtils().get_subindex_description_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex=_subIndexItems[s_correction])
                labelChannel[s].setStatusTip('ADC channel %s [index = %s & subIndex = %s]'%(subindex_description_item[25:29], _adc_indices[i], _subIndexItems[s_correction]))  # show when move mouse to the icon
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
                self.trendingBotton[s].setStatusTip('Data Trending for %s'%subindex_description_item[25:29])
                self.trendingBotton[s].clicked.connect(self.show_trendWindow)
#                 self.trendingBox[s] = QCheckBox("")
#                 self.trendingBox[s].setChecked(False)
                col_len = int(len(_subIndexItems)/2)
                if s < col_len:
                    FirstGridLayout.addWidget(icon, s, 0)
                    #FirstGridLayout.addWidget(self.trendingBox[s], s, 1)
                    FirstGridLayout.addWidget(self.trendingBotton[s], s, 2)
                    FirstGridLayout.addWidget(labelChannel[s], s, 3)
                    FirstGridLayout.addWidget(self.channelValueBox[s], s, 4)
                else:
                    FirstGridLayout.addWidget(icon, s - col_len, 5)
                    #FirstGridLayout.addWidget(self.trendingBox[s], s-col_len, 6)
                    FirstGridLayout.addWidget(self.trendingBotton[s], s - col_len, 7)
                    FirstGridLayout.addWidget(labelChannel[s], s - col_len, 8)
                    FirstGridLayout.addWidget(self.channelValueBox[s], s - col_len , 9)         
        self.FirstGroupBox.setLayout(FirstGridLayout)

    def monitoring_values_window(self):
        '''
        The function will create a QGroupBox for Monitoring Values [it is called by the function device_child_window]
        '''
        self.SecondGroupBox = QGroupBox("Monitoring Values")
        labelvalue = [0 for i in np.arange(20)] # 20 is just a hypothetical number
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
                a =a+1
        self.ThirdGroupBox.setLayout(ThirdGridLayout)

    def trend_child_window(self, childWindow=None, subindex = None, n_channels = None):
        '''
        The window starts the child window for the trending data of each ADC channel [it is called by the trending button beside each channel]
        '''
        trendGroupBox = QGroupBox("")   
        childWindow.setObjectName("")
        childWindow.setWindowTitle("Online data monitoring for ADC channel %s" % str(subindex))
        childWindow.resize(600, 300)  # w*h
        logframe = QFrame()
        logframe.setLineWidth(0.6)
        childWindow.setCentralWidget(logframe)
        self.trendLayout = QGridLayout()
        
        # initiate trending data
        self.x = [0]*n_channels
        self.y = [0]*n_channels
        for i in np.arange(0,n_channels):
            self.x[i] = list([0])
            self.y[i] = list([0])
        # initiate trending Figure  
        s = int(subindex)-3
        
        def __disable_figure():
            self.trendingBox[s] = False  
            self.x[s] = list([0])
            self.y[s] = list([0])
            self.graphWidget[s].clear()
            
        Fig = self.graphWidget[s]
        
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        close_button.clicked.connect(__disable_figure)
        close_button.clicked.connect(childWindow.close)
        
        self.trendLayout.addWidget(Fig,0,0)
        self.trendLayout.addWidget(close_button,1,0)
        trendGroupBox.setLayout(self.trendLayout)
        logframe.setLayout(self.trendLayout) 

    '''
    Update blocks with data
    '''        
    def initiate_adc_timer(self, period=0.5):
        '''
        The function will  update the GUI with the ADC data ach period in ms.
        '''  
        self.ADCtimer = QtCore.QTimer(self)
        
        try:
            # Disable the logger when reading ADC values [The exception statement is made to avoid user mistakes]
            self.control_logger.disabled = True
        except Exception:
            pass
        
        self.logger.notice("Reading ADC data...")
        self.__monitoringTime = time.time()
        # A possibility to save the data into a file
        self.logger.notice("Preparing an output file [%s.csv]..." % (lib_dir + "output_data/adc_data"))
        self.out_file_csv = AnalysisUtils().open_csv_file(outname="adc_data", directory=lib_dir + "output_data") 
        
        # Write header to the data
        fieldnames = ['Time', 'Channel', "nodeId", "ADCChannel", "ADCData" , "ADCDataConverted"]
        writer = csv.DictWriter(self.out_file_csv, fieldnames=fieldnames)
        writer.writeheader()            
        
        self.ADCtimer.setInterval(period)
        self.ADCtimer.timeout.connect(self.read_adc_channels)
        self.ADCtimer.timeout.connect(self.read_monitoring_values)
        self.ADCtimer.timeout.connect(self.read_configuration_values)
        self.ADCtimer.timeout.connect(self.update_progressBar)
        self.ADCtimer.start()

    def stop_adc_timer(self,s):
        '''
        The function will  stop the adc_timer.
        '''        
        try:
            self.ADCtimer.stop()
            self.control_logger.disabled = False   
            self.logger.notice("Stop reading ADC data...")
        except Exception:
            pass

    def initiate_random_timer(self, period=5000):
        '''
        The function will  send random CAN messages to the bus each period in ms.
        '''  
        self.Randtimer = QtCore.QTimer(self)
        self.Randtimer.setInterval(period)
        self.Randtimer.timeout.connect(self.send_random_can)
        self.Randtimer.start()

    def stop_random_timer(self):
        '''
        The function will  stop the random can timer.
        '''   
        try:
            self.Randtimer.stop()
        except Exception:
            pass
        
    def initiate_dump_can_timer(self, period=5000):
        '''
        The function will  dump any message in the bus each period in ms.
        '''  
        self.Dumptimer = QtCore.QTimer(self)
        self.Dumptimer.setInterval(period)
        self.Dumptimer.timeout.connect(self.dump_can_message)
        self.Dumptimer.start()

    def stop_dump_can_timer(self):
        '''
        The function will  stop the dump timer.
        '''   
        try:
            self.Dumptimer.stop()
        except Exception:
            pass
           
        
    def initiate_trending_figure(self, subindex=None,n_channels = None):
        '''
        The function defines a PlotWidget [data holder] for all ADC channels, 
        This widget provides a contained canvas on which plots of any type can be added and configured. 
        '''
        # prepare a PlotWidget
        self.graphWidget = [pg.PlotWidget(background="w") for i in np.arange(n_channels)]
        for s in np.arange(n_channels): 
            # Add Title
            self.graphWidget[s].setTitle("Online data monitoring for ADC channel %s" % str(s+3))
            # Add Axis Labels
            self.graphWidget[s].setLabel('left', "<span style=\"color:black; font-size:15px\">Voltage[V]</span>")
            self.graphWidget[s].setLabel('bottom', "<span style=\"color:black; font-size:15px\">Time line [Steps]</span>")
    
            # Add grid
            self.graphWidget[s].showGrid(x=True, y=True)
            self.graphWidget[s].getAxis("bottom").setStyle(tickTextOffset=15)
            #set style
            self.graphWidget[s].setStyleSheet("background-color: black;"
                                    "color: black;"
                                    "border-width: 1.5px;"
                                    "border-color: black;"
                                    "margin:0.0px;"
                                    "solid black;")      
        return self.graphWidget
    
    def update_figure(self, data=None, subindex=None):
        '''
        The function will update the graphWidget with ADC data.
        '''  
        s = int(subindex)-3 # the first ADC channel is channel 3 
        data_line = self.graphWidget[s].plot(self.x[s], self.y[s], pen=pg.mkPen(color=self.get_color(s), width=3), name="Ch%i" % subindex)
        self.x[s] = np.append(self.x[s], self.x[s][-1]+1)  # Add a new value 1 higher than the last
        self.y[s].append(data)  # Add a new value.
        data_line.setData(self.x[s][1:], self.y[s][1:])  # Update the data line.
                    

        
    def read_adc_channels(self):
        '''
        The function will will send a CAN message to read the ADC channels using the function read_sdo_can and
            update the channelValueBox in adc_values_window.
        The calling function is initiate_adc_timer.
        '''   
        _adc_channels_reg = self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _adc_indices = list(self.__adc_index)
        csv_writer = writer(self.out_file_csv)# Add contents of list as last row in the csv file
        data_point = [0]*33
        for i in np.arange(len(_adc_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex="subindex_items"))
            self.set_index(_adc_indices[i])  # set index for later usage
            adc_converted = []
            _start_a = 3  # to ignore the first subindex it is not ADC
            for subindex in np.arange(_start_a, len(_subIndexItems)+_start_a-1):
                s = subindex-_start_a
                s_correction = subindex-2
                self.set_subIndex(_subIndexItems[s])
                #read SDO CAN messages
                data_point[s] = self.read_sdo_can()
                ts = time.time()
                elapsedtime = ts-self.__monitoringTime
                adc_converted = np.append(adc_converted, Analysis().adc_conversion(_adc_channels_reg[str(subindex)], data_point[s],int(self.__resistor_ratio)))
                #update the progression bar to show bus statistics
                self.progressBar.setValue(subindex)
                if adc_converted[s] is not None:
                    self.channelValueBox[s].setText(str(round(adc_converted[s], 3)))
                    csv_writer.writerow((str(round(elapsedtime,1)),
                                         str(self.get_channel()),
                                         str(self.get_nodeId()),
                                         str(subindex),
                                         str(data_point[s]),
                                         str(round(adc_converted[s], 3))))
                    if self.trendingBox[s] == True:
                        if len(self.x[s]) >=800:   #solve some memory issues due to the large length of self.x[s] and self.y[s] the arrays       
                            self.x[s] = list([0])
                            self.y[s] = list([0])
                            self.graphWidget[s].clear()
                        self.update_figure(data=adc_converted[s], subindex=subindex)
                else:
                    self.channelValueBox[s].setText(str(adc_converted[s]))
        return adc_converted

    def read_monitoring_values(self):
        '''
        The function will will send a CAN message to read monitoring values using the function read_sdo_can and
         update the monValueBox in monitoring_values_window.
        The calling function is initiate_adc_timer.
        ''' 
        _dictionary = self.__dictionary_items
        _mon_indices = list(self.__mon_index)
        a = 0
        for i in np.arange(len(_mon_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex="subindex_items"))
            self.set_index(_mon_indices[i])  # set index for later usage
            for s in np.arange(0, len(_subIndexItems)):
                self.set_subIndex(_subIndexItems[s])
                data_point = self.read_sdo_can()
                self.monValueBox[a].setText(str(Analysis().convertion(data_point)))
                a = a + 1
                   
    def read_configuration_values(self):
        '''
        The function will will send a CAN message to read configuration values using the function read_sdo_can and 
         update the confValueBox in configuration_values_window.
        The calling function is initiate_adc_timer.
        ''' 
        _dictionary = self.__dictionary_items
        _conf_indices = list(self.__conf_index)
        a = 0 
        for i in np.arange(len(_conf_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_conf_indices[i], subindex="subindex_items"))
            self.set_index(_conf_indices[i])  # set index for later usage
            for s in np.arange(0, len(_subIndexItems)):
                self.set_subIndex(_subIndexItems[s])
                data_point = self.read_sdo_can()
                self.confValueBox[a].setText(str(Analysis().convertion(data_point)))
                a = a + 1
    
    def error_message(self, text=False):
        '''
        The function will return a MessageBox for Error message
        '''
        QMessageBox.about(self, "Error Message", text)
                    
    '''
    Update ProgressBar
    '''  

    def update_progressBar(self, comunication_object="bus"):
        if comunication_object == "SDO_TX":
            self.TXProgressBar.setValue(0)
            self.TXProgressBar.setValue(1)
        if comunication_object == "SDO_RX":
            self.RXProgressBar.setValue(0)
            self.RXProgressBar.setValue(1)
        if comunication_object == "bus":  
            currentVal = self.progressBar.value() 
            maxVal = self.progressBar.maximum()
            self.progressBar.setValue(currentVal+ (maxVal - currentVal)/33)
    '''
    Show toolBar
    ''' 

    def show_toolBar(self, toolbar, mainwindow): 
        canMessage_action = QAction(QIcon('graphicsUtils/icons/icon_msg.jpg'), '&CAN Message', mainwindow)
        canMessage_action.setShortcut('Ctrl+M')
        canMessage_action.setStatusTip('CAN Message')
        canMessage_action.triggered.connect(self.show_CANMessageWindow)

        settings_action = QAction(QIcon('graphicsUtils/icons/icon_settings.jpeg'), '&CAN Settings', mainwindow)
        settings_action.setShortcut('Ctrl+L')
        settings_action.setStatusTip('CAN Settings')
        settings_action.triggered.connect(self.show_CANSettingsWindow)

        canDumpMessage_action = QAction(QIcon('graphicsUtils/icons/icon_dump.png'), '&CAN Dump', mainwindow)
        canDumpMessage_action.setShortcut('Ctrl+D')
        canDumpMessage_action.setStatusTip('Dump CAN messages from the bus')
        canDumpMessage_action.triggered.connect(self.show_dump_child_window)

        runRandomMessage_action = QAction(QIcon('graphicsUtils/icons/icon_right.jpg'), '&CAN Run', mainwindow)
        runRandomMessage_action.setShortcut('Ctrl+R')
        runRandomMessage_action.setStatusTip('Send Random CAN messages to the bus every 5 seconds')
        runRandomMessage_action.triggered.connect(self.initiate_random_timer)
        
        stopDumpMessage_action = QAction(QIcon('graphicsUtils/icons/icon_stop.png'), '&CAN Stop', mainwindow)
        stopDumpMessage_action.setShortcut('Ctrl+C')
        stopDumpMessage_action.setStatusTip('Stop Sending CAN messages')
        stopDumpMessage_action.triggered.connect(self.stop_random_timer)

        RandomDumpMessage_action = QAction(QIcon('graphicsUtils/icons/icon_random.png'), '&CAN Random', mainwindow)
        RandomDumpMessage_action.setShortcut('Ctrl+G')
        RandomDumpMessage_action.setStatusTip('Send Random Messages to the bus')
        RandomDumpMessage_action.triggered.connect(self.send_random_can)
        # fileMenu.addSeparator()
        clear_action = QAction(QIcon('graphicsUtils/icons/icon_clear.png'), '&Clear', mainwindow)
        clear_action.setShortcut('Ctrl+X')
        clear_action.setStatusTip('Clear All the menus')
        clear_action.triggered.connect(self.clear_textBox_message)
        clear_action.triggered.connect(self.clear_table_content)
        
        toolbar.addAction(canMessage_action)
        toolbar.addAction(settings_action)
        toolbar.addSeparator()
        toolbar.addAction(canDumpMessage_action)
        toolbar.addAction(runRandomMessage_action)
        toolbar.addAction(stopDumpMessage_action)
        toolbar.addAction(RandomDumpMessage_action)                          
        toolbar.addSeparator()
        toolbar.addAction(clear_action)      

    '''
    Define child windows
    '''

    def show_CANMessageWindow(self):
        self.MessageWindow = QMainWindow()
        self.can_message_child_window(self.MessageWindow)
        self.MessageWindow.show()
    
    def show_dump_child_window(self):
        if self.wrapper is not None: 
            interface =self.get_interface()
            if interface =="socketcan":
                self.logger.info("DumpingCAN bus traffic.")
                print_command = "echo ==================== Dumping CAN bus traffic ====================\n"
                candump_command="candump any -x -c -t A"
                os.system("gnome-terminal -e 'bash -c \""+print_command+candump_command+";bash\"'")
            else:
                self.read_can_message_thread(print_sdo=False)
        else:
            pass
        #self.MessageWindow = QMainWindow()
        #self.dump_child_window(self.MessageWindow)
        #self.MessageWindow.show()
                  
    def show_CANSettingsWindow(self):
        MainWindow = QMainWindow()
        self.can_settings_child_window(MainWindow)
        MainWindow.show()

    def show_trendWindow(self):
        trend = QMainWindow(self)
        subindex = self.sender().objectName()
        s = int(subindex)-3     
        self.trendingBox[s] = True  
        n_channels = 33
        for i in np.arange(0,n_channels): self.graphWidget[i].clear()# clear any old plots
        self.trend_child_window(childWindow=trend, subindex = int(subindex),n_channels = n_channels)
        trend.show()
            
    def show_deviceWindow(self):
        self.deviceWindow = QMainWindow()
        try:
            self.device_child_window(self.deviceWindow)
            self.deviceWindow.show()
        except Exception:
            self.error_message("Either the channel is not activated or the CAN interface is not connected")
 
    '''
    Define set/get functions
    '''

    def set_textBox_message(self, comunication_object=None, msg=None, cobid = None):
        if comunication_object == "SDO_RX": 
            color = QColor("black")
            mode = "RX [hex] :"
        if comunication_object == "SDO_TX": 
            color = QColor("blue") 
            mode = "TX [hex] :"
        if comunication_object == "Decoded": 
            color = QColor("green")
            mode = "RX [____] :"
        if comunication_object == "ErrorFrame": 
            color = QColor("red")
            mode = "E:  "
        if comunication_object == "newline":
            color = QColor("green")
            mode = ""        
        self.textBox.setTextColor(color)
        if cobid is None:
            self.textBox.append(mode +msg)
        else:
            self.textBox.append(mode + cobid +msg)
            
    def clear_textBox_message(self):
         self.textBox.clear()
         
    def set_table_content(self, bytes=None, comunication_object=None):
        self.update_progressBar(comunication_object=comunication_object)
        n_bytes = 8 - 1            
        if comunication_object == "SDO_RX":
            # for byte in bytes:
            self.RXTable.clearContents()  # clear cells
            self.hexRXTable.clearContents()  # clear cells
            self.decRXTable.clearContents()  # clear cells  
            for byte in np.arange(len(bytes)):
                self.hexRXTable.setItem(0, byte, QTableWidgetItem(str(hex(bytes[byte]))))
                self.decRXTable.setItem(0, byte, QTableWidgetItem(str(bytes[byte])))
                bits = bin(bytes[byte])[2:]
                slicedBits = bits[::-1]  # slicing 
                for b in np.arange(len(slicedBits)):
                    self.RXTable.setItem(byte, n_bytes - b, QTableWidgetItem(slicedBits[b]))
                    self.RXTable.item(byte, n_bytes - b).setBackground(QColor(self.get_color(int(slicedBits[b]))))
        else:
            self.TXTable.clearContents()  # clear cells
            self.hexTXTable.clearContents()  # clear cells
            self.decTXTable.clearContents()  # clear cells
            # for byte in bytes:
            for byte in np.arange(len(bytes)):
                self.hexTXTable.setItem(0, byte, QTableWidgetItem(str(hex(bytes[byte]))))
                self.decTXTable.setItem(0, byte, QTableWidgetItem(str(bytes[byte])))
                bits = bin(bytes[byte])[2:]
                slicedBits = bits[::-1]  # slicing 
                for b in np.arange(len(slicedBits)):
                    self.TXTable.setItem(byte, n_bytes - b, QTableWidgetItem(slicedBits[b]))
                    self.TXTable.item(byte, n_bytes - b).setBackground(QColor(self.get_color(int(slicedBits[b]))))
    
    def clear_table_content(self):
        self.TXTable.clearContents() 
        self.hexTXTable.clearContents() 
        self.decTXTable.clearContents() 
        self.RXTable.clearContents() 
        self.hexRXTable.clearContents() 
        self.decRXTable.clearContents()
        # clear progress bar
        self.TXProgressBar.setValue(0)
        self.RXProgressBar.setValue(0)
        
                  
    def set_index_value(self):
        index = self.IndexListBox.currentItem().text()
        self.set_index(index)
    
    def set_subIndex_value(self):
        if self.subIndexListBox.currentItem() is not None:
            subindex = self.subIndexListBox.currentItem().text()
            self.set_subIndex(subindex)

    def set_appName(self, x):
        self.__appName = x

    def set_deviceName(self, x):
        self.__deviceName = x
            
    def set_adc_channels_reg(self, x):
        self.__adc_channels_reg = x
    
    def set_version(self, x):
        self.__version = x
        
    def set_icon_dir(self, x):
         self.__appIconDir = x
    
    def set_dictionary_items(self, x):
        self.__dictionary_items = x

    def set_nodeList(self, x):
        self.__nodeIds = x 
    
    def set_channelPorts(self, x):
        self.__channelPorts = x 
               
    def set_interfaceItems(self, x):
        self.__interfaceItems = x  
           
    def set_interface(self, x): 
        self.__interface = x 
                          
    def set_nodeId(self, x):
        self.__nodeId = x

    def set_channel(self, x):
        self.__channel = x
        
    def set_index(self, x):
        self.__index = x
    
    def set_bitrate(self, x):
        self.__bitrate = int(x)       
    
    def set_sjw(self,x):
        self.__sjw = int(x)
        
    def set_sample_point(self,x):
        self.__sample_point = float(x)
            
    def set_ipAddress(self, x):
        self.__ipAddress = x
               
    def set_subIndex(self, x):
        self.__subIndex = x
                
    def set_cobid(self, x):
        self.__cobid = x
    
    def set_dlc(self, x):
        self.__dlc = x
    
    def set_bytes(self, x):
        self.__bytes = x
        
    def get_index_items(self):
        return self.__index_items
               
    def get_nodeId(self):
        return self.__nodeId

    def get_channelPorts(self):
        return self.__channelPorts
            
    def get_index(self):
        return self.__index
          
    def get_dictionary_items(self):
        return self.__dictionary_items  

    def get_icon_dir(self):
        return  self.__appIconDir
    
    def get_appName(self):
        return self.__appName
    
    def get_deviceName(self):
        return self.__deviceName
    
    def get_adc_channels_reg(self):
        return self.__adc_channels_reg

    def get_nodeList(self):
        return self.__nodeIds

    def get_subIndex(self):
        return self.__subIndex
    
    def get_cobid(self):
        return  self.__cobid
    
    def get_dlc(self):
        return self.__dlc

    def get_bytes(self):
        return self.__bytes 
        
    def get_bitrate(self):
        return self.__bitrate

    def get_ipAddress(self):
        return self.__ipAddress    

    def get_interfaceItems(self):
        return self.__interfaceItems
    
    def get_bitrate_items(self):
        return self.__bitrate_items
    
    def get_sample_points(self):
        return self.__sample_points
    
    def get_sample_point(self):
        return self.__sample_point
    
    def get_sjw(self):
        return self.__sjw   
    
    def get_interface(self):
        """:obj:`str` : Vendor of the CAN interface. Possible values are
        ``'Kvaser'`` and ``'AnaGate'``."""
        return self.__interface

    def get_channel(self):
        return self.__channel       

    def get_color(self, i):
        '''
        The function returns named colors supported in matplotlib
        input:
        Parameters
        ----------
        i : :obj:`int`
            The color index
        Returns
        -------
        `string`
            The corresponding color
        '''
        col_row = ["#f7e5b2", "#fcc48d", "#e64e4b", "#984071", "#58307b", "#432776", "#3b265e", "#4f2e6b", "#943ca6", "#df529e", "#f49cae", "#f7d2bb",
                        "#f4ce9f", "#ecaf83", "#dd8a5b", "#904a5d", "#5d375a", "#402b55", "#332d58", "#3b337a", "#365a9b", "#2c4172", "#2f3f60", "#3f5d92",
                        "#4e7a80", "#60b37e", "#b3daa3", "#cfe8b7", "#d2d2ba", "#dd8a5b", "#904a5d", "#5d375a", "#4c428d", "#3a3487", "#31222c", "#b3daa3"]
        return col_row[i]
    

if __name__ == "__main__":
    pass

