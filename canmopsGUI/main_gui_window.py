#from __future__ import annotations
from matplotlib.backends.qt_compat import QtCore, QtWidgets

import signal
import time
import sys
import os
import csv
import yaml
import logging
import numpy as np
import pyqtgraph as pg
import pandas as pd
import asyncio
import keyboard
import atexit
from csv                    import writer
from PyQt5 import *
from PyQt5.QtCore           import *
from PyQt5.QtGui            import *
from PyQt5.QtWidgets        import *
from typing                 import *
from random                 import randint
from canmopsGUI          import menu_window,child_window, data_monitoring, mops_child_window, multi_device_window
from mopshubGUI          import mopshub_child_window
from canmops.analysis       import Analysis
from canmops.logger_main         import Logger 
from canmops.analysis_utils  import AnalysisUtils
from canmops.can_wrapper_main     import CanWrapper
log_call = Logger(name = " Main  GUI ",console_loglevel=logging.INFO, logger_file = False)


rootdir = os.path.dirname(os.path.abspath(__file__)) 
lib_dir = rootdir[:-11]
output_dir = lib_dir+"/output_data/"
config_dir = "config_files/"
config_yaml = config_dir + "gui_mainSettings.yml"
icon_location = "canmopsGUI/icons/"

class MainWindow(QMainWindow):

    def __init__(self, console_loglevel=logging.INFO):
        super(MainWindow, self).__init__(None)
        """:obj:`~logging.Logger`: Main logger for this class"""
        self.logger = log_call.setup_main_logger()
        
        # Start with default settings
        # Read configurations from a file    
        conf = AnalysisUtils().open_yaml_file(file=config_yaml, directory=lib_dir)
        self.__appName      = conf["Application"]["app_name"] 
        self.__devices      = conf["Application"]["Devices"]
        self.__wait_time      = conf["Application"]["wait_time"]
        self.__appVersion   = conf['Application']['app_version']
        self.__appIconDir   = conf["Application"]["app_icon_dir"]
        self.__multi_mode   = conf["Application"]["multi_mode"]
        self.__refresh_rate = conf["Application"]["refresh_rate"] #millisecondsrefresh_rate
        self.__mopshub_mode = conf["Application"]["mopshub_mode"]
        self.__mopshub_communication_mode = conf["Application"]["mopshub_communication_mode"]

        self.__canId_rx = 0x580
        self.__canId_tx = 0x600        
        self.__CANID_list = ['0x600','0x700','0x000'] 
        self.__bytes = ["40", "0", "10", "0", "0", "0", "0", "0"]
        self.__interfaceItems = list(["AnaGate", "Kvaser", "socketcan"]) 
        self.__channelPorts = list(conf["channel_ports"])
        self.__interface = None
        self.__channel = None
        self.__ipAddress = None
        self.__bitrate = None
        self.__sample_point = None
        self.__deviceName = None
        self.__adc_converted = None
        self.index_description_items = None
        self.__subIndex = None
        self.__dlc = 8
        self.__busid = 0
        self.rx_msgs_counter  = 0
        self.tx_msgs_counter =0
        self.error_frames_counter = 0
        self.timeout_counter = 0
        self.inactive_bus_counter = 0
        self.wrapper = None
        self.adcItems= [str(k) for k in np.arange(3,35)]      
          
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
        self.MenuBar = menu_window.MenuWindow(self)
        self.MenuBar.create_main_menuBar(self)
        
        #
        self.DataMonitoring = data_monitoring.DataMonitoring(self)
        # create statusBar
        self.MenuBar.create_statusBar(self)
        
        # create toolBar
        toolBar = self.addToolBar("tools")
        self.show_toolBar(toolBar, self)
        

        # 1. Window settings
        self.setWindowTitle(self.__appName + "_" + self.__appVersion)
        self.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        #self.adjustSize()
        self.setFixedSize(850, 900)#x,y
        self.setGeometry(10, 10, 900, 700)
        
        logo_layout = QHBoxLayout()
        uni_logo_label = QLabel()
        pixmap = QPixmap(icon_location+"icon_wuppertal_banner.png")
        uni_logo_label.setPixmap(pixmap.scaled(180, 70)) 
        icon_spacer = QSpacerItem(150, 50, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        logo_layout.addItem(icon_spacer) 
        logo_layout.addWidget(uni_logo_label)    
        
        self.defaultSettingsWindow()
        self.default_message_window()
        self.textOutputWindow()
        self.tableOutputWindow()
        self.configure_device_box()
        self.create_bus_progress_box()

            
        # Create a frame in the main menu for the gridlayout
        mainFrame = QFrame()
        mainFrame.setLineWidth(1)
        self.setCentralWidget(mainFrame)
            
        # SetLayout
        mainLayout = QGridLayout()
        mainLayout.addWidget(self.defaultSettingsGroupBox, 0, 0)
        mainLayout.addLayout(logo_layout,0,1)
        mainLayout.addWidget(self.defaultMessageGroupBox, 1, 0) 
        mainLayout.addWidget(self.defaultprogressGroupBox,2,0)
        
        
         
        mainLayout.addWidget(self.textGroupBox, 1, 1, 2, 1)
        mainLayout.addWidget(self.monitorGroupBox, 3, 0, 2, 2)
        mainLayout.addWidget(self.configureDeviceBoxGroupBox, 5, 0, 1, 1)

        if self.__multi_mode is True:
            self.multi_window = multi_device_window.MultiDeviceWindow()
            self.multi_device_box()
            mainLayout.addWidget(self.configureMultiBoxGroupBox, 5, 1, 1, 1)
            
        #moopshub child window
        if self.__mopshub_mode is True:   
            self.mopshubWindow = mopshub_child_window.mopshubWindow()
            self.configure_cic_box()
            mainLayout.addWidget(self.configureCICBoxGroupBox, 5, 1, 1, 1)

                            
        mainFrame.setLayout(mainLayout)
        # 3. Show
        self.show()
    
    def create_bus_progress_box(self):
        self.defaultprogressGroupBox = QGroupBox("Bus Statistics")      
        # Create bus_progress_layout
        bus_progress_layout = QGridLayout()

        # Create progress bars
        self.bus_statistics_progress = QProgressBar()
        self.bus_statistics_progress.setTextVisible(False)
        self.bus_statistics_progress.setFixedHeight(10)
        self.bus_statistics_progress.setFixedWidth(200)
        # Create labels
        # Initialize counters
        self.bus_statistics_progress_label = QLabel("Bus Status:")
        self.tx_msgs_label = QLabel("TX Messages:")
        self.rx_msgs_label = QLabel("RX Messages:")
        self.error_frames_label = QLabel("Error Frames:")
        self.timeout_label = QLabel("Timeout response:")
        self.inactive_bus_label = QLabel("Bus passive:")
        
        self.rx_msgs_counter_label = QLabel(str(self.rx_msgs_counter))
        self.tx_msgs_counter_label = QLabel(str(self.tx_msgs_counter))
        self.error_frames_counter_label = QLabel(str(self.error_frames_counter))
        self.timeout_counter_label = QLabel(str(self.timeout_counter))
        self.inactive_bus_counter_label = QLabel(str(self.inactive_bus_counter))
        

        # Add progress bars and labels to layout
        bus_progress_layout.addWidget(self.bus_statistics_progress_label,0,0)
        bus_progress_layout.addWidget(self.bus_statistics_progress,0,1)
        
        bus_progress_layout.addWidget(self.tx_msgs_label,1,0)
        bus_progress_layout.addWidget(self.tx_msgs_counter_label,1,1)
        
        bus_progress_layout.addWidget(self.rx_msgs_label,2,0)
        bus_progress_layout.addWidget(self.rx_msgs_counter_label,2,1)
        
        bus_progress_layout.addWidget(self.error_frames_label,3,0)
        bus_progress_layout.addWidget(self.error_frames_counter_label,3,1)
        
        bus_progress_layout.addWidget(self.timeout_label,4,0)
        bus_progress_layout.addWidget(self.timeout_counter_label,4,1)
        
        bus_progress_layout.addWidget(self.inactive_bus_label,5,0)
        bus_progress_layout.addWidget(self.inactive_bus_counter_label,5,1)        
        
        # Set bus_progress_layout
        self.defaultprogressGroupBox.setLayout(bus_progress_layout)

    def update_bus_progress(self, reset_progress =False, clear_all = False ):
        # Update progress values based on counters
        message_percentage = 0
        counter = self.wrapper.cnt
        if clear_all: 
            self.wrapper.reset_counters()
            self.rx_msgs_counter  = 0
            self.tx_msgs_counter =0
            self.error_frames_counter = 0
            self.timeout_counter = 0   
            self.inactive_bus_counter = 0        
        else:
            counter = self.wrapper.cnt
            self.rx_msgs_counter  = counter['rx_msg']
            self.tx_msgs_counter =counter['tx_msg']
            self.error_frames_counter = counter["error_frame"]
            self.timeout_counter = counter['SDO_read_response_timeout']
            self.inactive_bus_counter = counter['Not_active_bus']
        
        if self.rx_msgs_counter+self.inactive_bus_counter+self.timeout_counter !=0:
            if reset_progress: message_percentage = 0
            else: message_percentage =  100 - (self.tx_msgs_counter/(self.rx_msgs_counter+self.inactive_bus_counter+self.timeout_counter) *100)
        else: pass
        message_percentage = int(message_percentage)
        
        if message_percentage > 0 and message_percentage < 50:
            self.bus_statistics_progress.setStyleSheet("QProgressBar::chunk { background-color: green; }")        
        if message_percentage >= 50 and message_percentage < 90:
            self.bus_statistics_progress.setStyleSheet("QProgressBar::chunk { background-color: yellow; }")
        if message_percentage >= 90: self.bus_statistics_progress.setStyleSheet("QProgressBar::chunk { background-color: red; }")
        
        self.bus_statistics_progress.setValue(message_percentage)
        # Update counter labels
        self.tx_msgs_counter_label.setText(str(self.tx_msgs_counter))
        self.rx_msgs_counter_label.setText(str(self.rx_msgs_counter))
        self.error_frames_counter_label.setText(str(self.error_frames_counter))        
        self.timeout_counter_label.setText(str(self.timeout_counter))  
        self.inactive_bus_counter_label.setText(str(self.inactive_bus_counter)) 
    def clear_bus_progress(self): 
        self.update_bus_progress(reset_progress = True, clear_all = True)        
        
    def defaultSettingsWindow(self):
        '''
        The function defines the GroupBox for the default bus settings
        e.g. for Communication purposes the user needs to define   
        1. The CAN Bus [e.g. channel 0, 2, 3,....] 
        2. The Interface [e.g. socketcan, kvaser, Anagate]
        All the options in every widget are defined in the file main_cfg.yml
        '''    
        self.defaultSettingsGroupBox = QGroupBox("Bus Settings")      
        defaultSettingsWindowLayout = QGridLayout()
        __interfaceItems = self.__interfaceItems
        __channelList = self.get_channelPorts()
        
        channelLabel = QLabel()
        channelLabel.setText(" CAN Channels")
        self.channelComboBox = QComboBox()
        self.channelComboBox.setStatusTip('Possible ports as defined in the main_cfg.yml file')
        for port in list(__channelList): self.channelComboBox.addItem(str(port))  
        self.channelComboBox.setCurrentIndex(0)
        
        interfaceLabel = QLabel()
        interfaceLabel.setText("  Interfaces")
        self.interfaceComboBox = QComboBox()
        for item in __interfaceItems[:]: self.interfaceComboBox.addItem(item)
        self.interfaceComboBox.activated[str].connect(self.set_interface)
        self.interfaceComboBox.setStatusTip('Select the connected interface')
        self.interfaceComboBox.setCurrentIndex(2)
        
        self.connectButton = QPushButton("")
        icon = QIcon()
        icon.addPixmap(QPixmap(icon_location+'icon_connect.jpg'), QIcon.Active, QIcon.On)
        icon.addPixmap(QPixmap(icon_location+'icon_disconnect.jpg'), QIcon.Normal, QIcon.Off)
        self.connectButton.setIcon(icon)
        #self.connectButton.setIconSize(QtCore.QSize(20,20))
        self.connectButton.setCheckable(True)
        self.connectButton.setStatusTip('Connect the interface and set the channel')
        self.bus_alarm_led = self.def_alert_leds(bus_alarm=True, mops=None, icon_state=False)   
        
        self.statusBoxVar = QLineEdit()
        self.statusBoxVar.setStyleSheet("background-color: white; border: 1px inset black;")
        self.statusBoxVar.setReadOnly(True) 
        self.statusBoxVar.setFixedWidth(50)
        self.statusBoxVar.setText("OFF") 
                
        def on_channelComboBox_currentIndexChanged():
            _interface = self.interfaceComboBox.currentText()
            _channel = self.channelComboBox.currentText()
            self.set_interface(_interface)
            self.set_channel(int(_channel))
                        
        self.connectButton.clicked.connect(on_channelComboBox_currentIndexChanged)
        self.connectButton.clicked.connect(self.connect_server)
        
        defaultSettingsWindowLayout.addWidget(channelLabel,   0, 0)
        defaultSettingsWindowLayout.addWidget(interfaceLabel, 0, 1)
        defaultSettingsWindowLayout.addWidget(self.channelComboBox, 1, 0)
        defaultSettingsWindowLayout.addWidget(self.interfaceComboBox, 1, 1,1,2)
        defaultSettingsWindowLayout.addWidget(self.bus_alarm_led, 1, 3)
        defaultSettingsWindowLayout.addWidget(self.statusBoxVar, 1, 4)
        defaultSettingsWindowLayout.addWidget(self.connectButton, 1, 5,1,3)
        self.defaultSettingsGroupBox.setLayout(defaultSettingsWindowLayout)
    
    def def_alert_leds(self, bus_alarm=None, mops_alarm=None, mops=None, bus = None, icon_state=False):
        if mops_alarm is True:
            icon_red = icon_location+"icon_disconnected_device.png" #icon_red.gif"
            icon_green = icon_location+"icon_green.gif"
            if icon_state:
                alarm_led = QMovie(icon_green)
            else: 
               alarm_led = QMovie(icon_red)    
            alarm_led.setScaledSize(QSize().scaled(20, 20, Qt.KeepAspectRatio)) 
            alarm_led.start()
            return alarm_led         
        
        if bus_alarm is True:
            icon_red = icon_location+"icon_red.png"
            icon_green = icon_location+"icon_green.png"
            alarm_led = QLabel() 
            if icon_state:
                pixmap = QPixmap(icon_green)
            else: 
                pixmap = QPixmap(icon_red)    
            alarm_led.setPixmap(pixmap.scaled(20, 20))            
            return alarm_led
                               
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
        self.defaultMessageGroupBox = QGroupBox("SDO Message Settings")
        defaultMessageWindowLayout = QGridLayout()                        
        nodeLabel = QLabel()
        nodeLabel.setText("NodeId [H]")
        self.nodetextBox = QLineEdit("0")
        self.nodetextBox.setStatusTip('Connected CAN Nodes as defined in the main_cfg.yml file')
        self.nodetextBox.setFixedSize(70, 25)
        
        oDLabel = QLabel()
        oDLabel.setText("   CAN Id   ")
        self.CANIdComboBox = QComboBox()
        self.CANIdComboBox.setStatusTip('CAN Identifier')
        self.CANIdComboBox.setFixedSize(70, 25)
        self.CANIdComboBox.addItems(self.__CANID_list)
        
        indexLabel = QLabel()
        indexLabel.setText("Index [H]")
        self.mainIndexTextBox = QLineEdit("0x1000")
        self.mainIndexTextBox.setFixedSize(65, 25)
        
        subIndexLabel = QLabel()
        subIndexLabel.setText("SubIndex [H]")
        self.mainSubIndextextbox = QLineEdit("0")
        self.mainSubIndextextbox.setFixedSize(70, 25)

        busIdLabel = QLabel()
        busIdLabel.setText("   Bus Id")
        self.busIdbox = QLineEdit("0")
        self.busIdbox.setFixedSize(60, 25)
                
        def __set_bus():
            try:
                self.set_index(self.mainIndexTextBox.text())
                self.set_subIndex(self.mainSubIndextextbox.text())
                self.set_nodeId(self.nodetextBox.text())
                self.set_canId_tx(self.CANIdComboBox.currentText())
                self.set_busId(self.busIdbox.text())
            except Exception:
                self.error_message(text="Make sure that the CAN interface is connected")
                
        self.startButton = QPushButton("")
        self.startButton.setIcon(QIcon(icon_location+'icon_start.png'))
        self.startButton.setStatusTip('Send CAN message')
        self.startButton.clicked.connect(__set_bus)
        self.startButton.clicked.connect(self.read_sdo_can_thread)                 
        defaultMessageWindowLayout.addWidget(nodeLabel, 3, 0)
        defaultMessageWindowLayout.addWidget(self.nodetextBox, 4, 0)   
        
        defaultMessageWindowLayout.addWidget(oDLabel, 3, 1)
        defaultMessageWindowLayout.addWidget(self.CANIdComboBox, 4, 1)
        
        defaultMessageWindowLayout.addWidget(indexLabel, 3, 2)
        defaultMessageWindowLayout.addWidget(self.mainIndexTextBox, 4, 2)        
        
        defaultMessageWindowLayout.addWidget(subIndexLabel, 3, 3)
        defaultMessageWindowLayout.addWidget(self.mainSubIndextextbox, 4, 3) 
        
        defaultMessageWindowLayout.addWidget(busIdLabel, 3, 4)
        defaultMessageWindowLayout.addWidget(self.busIdbox, 4, 4)         
              
        defaultMessageWindowLayout.addWidget(self.startButton, 4, 5)
        
        
        self.defaultMessageGroupBox.setLayout(defaultMessageWindowLayout)
                    
    def textOutputWindow(self):
        '''
        The function defines the GroupBox output window for the CAN messages
        '''  
        self.textGroupBox = QGroupBox("   Output Window")
        self.textBox = QTextEdit()
        self.textBox.setReadOnly(True)
        self.textBox.resize(20, 20)
        textOutputWindowLayout = QGridLayout()
        textOutputWindowLayout.addWidget(self.textBox, 1, 0)
        self.textGroupBox.setLayout(textOutputWindowLayout)
        
    def tableOutputWindow(self):
        '''
        The function defines the GroupBox output table for Bytes monitoring for RX and TX messages
        '''  
        self.monitorGroupBox = QGroupBox("Bytes Monitoring")
        def __graphic_view():
            byteLabel = QLabel()
            byteLabel.setText("Bytes")
            byteLabel.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
            graphicsview = QtWidgets.QGraphicsView()
            graphicsview.setStyleSheet("background-color: rgba(255, 255, 255, 10);  margin:0.0px;")
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
        self.hexRXTable.setStyleSheet("font-size: 12px;")
        self.hexRXTable.setColumnCount(1)  # Set n columns
        self.hexRXTable.setRowCount(n_bytes)  # and n rows
        self.hexRXTable.resizeColumnsToContents()  # Do the resize of the columns by content
        self.hexRXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.hexRXTable.setHorizontalHeaderLabels(["Hex"])
        self.hexRXTable.verticalHeader().hide()
        self.hexRXTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        #self.hexRXTable.resizeColumnsToContents()
        self.hexRXTable.clearContents()  # clear cells
        self.hexRXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexRXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexRXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.decRXTable = QTableWidget()  # Create a table
        self.decRXTable.setStyleSheet("font-size: 12px;")
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
        #self.decRXTable.resizeColumnsToContents()
        self.decRXTable.clearContents()  # clear cells
          
        self.RXTable = QTableWidget()  # Create a table
        self.RXTable.setStyleSheet("font-size: 12px;")
        self.RXTable.setColumnCount(n_bytes)  # Set n columns
        self.RXTable.setRowCount(n_bytes)  # and n rows
        
        self.RXTable.resizeColumnsToContents()
        self.RXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.RXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.RXTable.setHorizontalHeaderLabels(row)
        self.RXTable.setVerticalHeaderLabels(col)
        self.RXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.RXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.RXTable.setVisible(False)
        self.RXTable.verticalScrollBar().setValue(0)
        #self.RXTable.resizeColumnsToContents()
        self.RXTable.setVisible(True)
        
        line = QFrame()
        line.setGeometry(QtCore.QRect(320, 150, 118, 3))
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        
        # TXTables
        self.hexTXTable = QTableWidget()  # Create a table
        self.hexTXTable.setStyleSheet("font-size: 12px;")
        self.hexTXTable.setColumnCount(1)  # Set n columns
        self.hexTXTable.setRowCount(n_bytes)  # and n rows
        self.hexTXTable.resizeColumnsToContents()  # Do the resize of the columns by content
        self.hexTXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.hexTXTable.setHorizontalHeaderLabels(["Hex"])
        self.hexTXTable.verticalHeader().hide()
        self.hexTXTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        #self.hexTXTable.resizeColumnsToContents()
        self.hexTXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexTXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hexTXTable.clearContents()  # clear cells
        self.hexTXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.decTXTable = QTableWidget()  # Create a table
        self.decTXTable.setStyleSheet("font-size: 12px;")
        self.decTXTable.setColumnCount(1)  # Set n columns
        self.decTXTable.setRowCount(n_bytes)  # and n rows
        self.decTXTable.resizeColumnsToContents()  # Do the resize of the columns by content
        self.decTXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.decTXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.decTXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.decTXTable.setHorizontalHeaderLabels(["Decimal"])
        self.decTXTable.verticalHeader().hide()
        self.decTXTable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        #self.decTXTable.resizeColumnsToContents()
        self.decTXTable.clearContents()  # clear cells
        self.decTXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)  
        
        self.TXTable = QTableWidget()  # Create a table
        self.TXTable.setStyleSheet("font-size: 12px;")
        self.TXTable.setColumnCount(n_bytes)  # Set n columns
        self.TXTable.setRowCount(n_bytes)  # and n rows
        self.TXTable.resizeColumnsToContents()
        self.TXTable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.TXTable.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.TXTable.setHorizontalHeaderLabels(row)
        self.TXTable.setVerticalHeaderLabels(col)
        self.TXTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.TXTable.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.TXTable.setVisible(False)
        self.TXTable.verticalScrollBar().setValue(0)
        #self.TXTable.resizeColumnsToContents()
        self.TXTable.setVisible(True)
        
        TXLayout = QHBoxLayout()
        TXLabel = QLabel()
        TXLabel.setText("TX Messages:")
        TXLayout.addWidget(TXLabel)

        RXLayout = QHBoxLayout()
        RXLabel = QLabel()
        RXLabel.setText("RX Messages:")
        RXLayout.addWidget(RXLabel)
        
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
        gridLayout.addWidget(TXbitLabel, 1, 1)
        gridLayout.addWidget(TXgraphicsview, 2, 0)
        gridLayout.addWidget(self.TXTable, 2, 1)
        gridLayout.addWidget(self.hexTXTable, 2, 2)
        gridLayout.addWidget(self.decTXTable, 2, 3)
        
        gridLayout.addWidget(line, 2, 4, 2, 4)
                
        gridLayout.addLayout(RXLayout, 0 , 6)        
        gridLayout.addWidget(RXbitLabel, 1,6)
        gridLayout.addWidget(RXgraphicsview, 2, 5)
        
        gridLayout.addWidget(self.RXTable, 2, 6)
        gridLayout.addWidget(self.hexRXTable, 2, 7)
        gridLayout.addWidget(self.decRXTable, 2, 8)
        self.monitorGroupBox.setLayout(gridLayout)
   
    def configure_cic_box(self):
        '''
        The function provides a frame for the configured devices  according to the file main_cfg.yml
        '''
        self.configureCICBoxGroupBox = QGroupBox("MOPSHUB network")
        configureCICBoxGroupBoxLayout = QHBoxLayout()
        multiLabel = QLabel()
        self.multiButton = QPushButton("")
        self.multiButton.setStatusTip('Open MOPSHUB window')
        multiLabel.setText("")
        self.multiButton.setIcon(QIcon(icon_location+'icon_nodes.png'))
        self.multiButton.clicked.connect(lambda: self.mopshubWindow.Ui_ApplicationWindow(mainWindow = self))
        configureCICBoxGroupBoxLayout.addWidget(self.multiButton)
        configureCICBoxGroupBoxLayout.addWidget(multiLabel)
        self.configureCICBoxGroupBox.setLayout(configureCICBoxGroupBoxLayout)
            
    def multi_device_box(self):
        '''
        The function provides a frame for the configured devices  according to the file main_cfg.yml
        '''
        self.configureMultiBoxGroupBox = QGroupBox("CAN network")
        configureCICBoxGroupBoxLayout = QHBoxLayout()
        multiLabel = QLabel()
        self.multiButton = QPushButton("")
        self.multiButton.setStatusTip('MUlti MOPS connected to several buses')
        multiLabel.setText("")
        self.multiButton.setIcon(QIcon(icon_location+'icon_nodes.png'))
        self.multiButton.clicked.connect(self.multi_window.Ui_ApplicationWindow)
        configureCICBoxGroupBoxLayout.addWidget(self.multiButton)
        configureCICBoxGroupBoxLayout.addWidget(multiLabel)
        self.configureMultiBoxGroupBox.setLayout(configureCICBoxGroupBoxLayout)
      
                
    def configure_device_box(self):
        '''
        The function provides a frame for the configured devices  according to the file main_cfg.yml
        '''
        mops_child = mops_child_window.MopsChildWindow()
        self.configureDeviceBoxGroupBox = QGroupBox("Configured Devices")       
        self.configureDeviceBoxLayout = QHBoxLayout()
        deviceLabel = QLabel()
        self.deviceButton = QPushButton("")
        self.deviceButton.setStatusTip('Choose the configuration yaml file')
        if self.__devices[0] == "None":
            deviceLabel.setText("Configure Device")
            self.deviceButton.setIcon(QIcon(icon_location+'icon_question.png'))
            self.deviceButton.clicked.connect(lambda: mops_child.update_device_box(device = "None", mainWindow = self))
        else:
            deviceLabel.setText("[" + self.__devices[0] + "]")
            deviceName, version, icon_dir, nodeIds, dictionary_items, adc_channels_reg,\
            self.__adc_index, self.__chipId, self.__index_items, self.__conf_index, \
            self.__mon_index,self.__resistor_ratio, self.__ref_voltage =  mops_child.update_device_box(device = self.__devices[0], mainWindow = self)
        
        self.set_deviceName(deviceName)
        self.configureDeviceBoxLayout.addWidget(deviceLabel)
        self.configureDeviceBoxLayout.addWidget(self.deviceButton)
        self.configureDeviceBoxGroupBox.setLayout(self.configureDeviceBoxLayout)

    def load_settings_file(self, interface = None, channel = None):
        filename = os.path.join(lib_dir, config_dir + interface + "_CANSettings.yml")
        test_date = time.ctime(os.path.getmtime(filename))
        # Load settings from CAN settings file
        self.logger.notice("Loading CAN settings from the file %s produced on %s" % (filename, test_date))
        try:
            _canSettings = AnalysisUtils().open_yaml_file(file=config_dir + interface + "_CANSettings.yml", directory=lib_dir)
            _channel = _canSettings['channel' + str(channel)]["channel"]
            _ipAddress = _canSettings['channel' + str(channel)]["ipAddress"]
            _bitrate = _canSettings['channel' + str(channel)]["bitrate"]
            _sample_point = _canSettings['channel' + str(channel)]["samplePoint"]
            _sjw = _canSettings['channel' + str(channel)]["SJW"]
            _tseg1 = _canSettings['channel' + str(channel)]["tseg1"]
            _tseg2 = _canSettings['channel' + str(channel)]["tseg2"] 
            return _channel,_ipAddress, _bitrate,_sample_point, _sjw,_tseg1, _tseg2
        except:
          self.logger.error("Channel %s settings for %s interface Not found" % (str(channel),interface)) 
          return None,None, None,None, None,None, None 
              
    def connect_server(self):
        '''
        The function is starts calling the CANWrapper [called by the connectButton].
        First: if the option settings in the file main_cfg.yaml is True. The function will search for any stored settings
               from the previous run for the chosen interface [the file socketcan__CANSettings.yml], Otherwise The settings in the file main_cfg.yaml will be taken
            e.g [bitrate, Sjw, Sample point,....]
        Second: Communication with CAN wrapper will begin
        ''' 
        icon_red = icon_location+"icon_red.png"
        icon_green = icon_location+"icon_green.png" 
        if self.connectButton.isChecked():
            _interface = self.get_interface()   
            _default_channel = self.get_channel()
            try: 
                # Default settings from yml file
                _channel,_ipAddress, _bitrate,_sample_point, _sjw,_tseg1, _tseg2 =  self.load_settings_file(interface = _interface, channel = _default_channel)              
                # Update settings
                self.wrapper = CanWrapper(interface=_interface,
                                          bitrate=_bitrate,
                                          samplePoint=_sample_point,
                                          sjw=_sjw,
                                          tseg1=_tseg1,
                                          tseg2=_tseg2,
                                          ipAddress=_ipAddress,
                                          channel=int(_channel),
                                          load_config = True)
                self.control_logger = self.wrapper.logger  
                self.connectButton.setChecked(True) 
                self.connectButton.setEnabled(True)
                self.update_bus_status_box(on=True)
                self.statusBoxVar.setText("ON") 
                self.connectButton.setIcon(QIcon(icon_location+'icon_connect.jpg'))          
            except:
                self.connectButton.setIcon(QIcon(icon_location+'icon_disconnect.jpg'))
                self.update_bus_status_box(on=False)
                self.statusBoxVar.setText("OFF")  
                self.logger.error("Cannot Connect to the CAN bus")  
                self.connectButton.setChecked(False)
        else:
           self.update_bus_status_box(on=False)
           self.statusBoxVar.setText("OFF")  
           self.connectButton.setIcon(QIcon(icon_location+'icon_disconnect.jpg'))
           self.connectButton.setChecked(False)
           self.stop_server()
           self.stop_random_timer()

    def update_bus_status_box(self, port_id=None, on=False, off=False):
        icon_red = icon_location+"icon_red.png"
        icon_green = icon_location+"icon_green.png" 
        if on:
            pixmap = QPixmap(icon_green)
        else:
            pixmap = QPixmap(icon_red)
        self.bus_alarm_led.setPixmap(pixmap.scaled(20, 20))   

    def stop_server(self):
        '''
        Stop the communication with CAN wrapper
        ''' 
        try:
            self.logger.notice("Closing the Graphical Interface...") 
            self.clear_bus_progress()
            self.stop_adc_timer()
            self.wrapper.stop()
            self.MessageWindow.close()
            self.SettingsWindow.close()
        except:
            pass

    def set_bus_settings(self): 
        '''
        The function will set all the required parameters for the CAN communication
        1. get the required parameters for the CAN communication e.g. bitrate, interface, channel,.......
        2. Save the settings to a file _CANSettings.yaml
        3. Initialize the main server CANWrapper 
        ''' 
       # try: 
        _bitrate = self.get_bitrate()
        _interface = self.get_interface()
        _channels = self.get_channelPorts()
        _channel = self.get_channel()
        _sample_point = self.get_sample_point()
        _sjw = self.get_sjw()
        _tseg1 = self.get_tseg1()
        _tseg2 = self.get_tseg2()
        if _interface == "AnaGate":
             self.set_ipAddress(self.firsttextbox.text()) 
             _ipAddress = self.get_ipAddress()
        else:
            _ipAddress = None
            pass
        # Change the buttons view in the main GUI
        self.logger.info("Applying changes to the main server") 
        self.interfaceComboBox.SelectedText = _interface
        self.channelComboBox.SelectedText = str(_channel)
        # Save the settings into a file
        self.logger.info("Saving CAN settings to the file %s" % lib_dir + config_dir + _interface + "_CANSettings.yml") 
        #Load current settings
        _canSettings = AnalysisUtils().open_yaml_file(file=config_dir + _interface + "_CANSettings.yml", directory=lib_dir)
        #    Apply New settings
        _canSettings["channel" + str(_channels[0])]["bitrate"] = _bitrate
        _canSettings["channel" + str(_channels[0])]["channel"] =int(_channels[0]) 
        _canSettings["channel" + str(_channels[0])]["samplePoint"]=_sample_point
        _canSettings["channel" + str(_channels[0])]["SJW"]= _sjw
        _canSettings["channel" + str(_channels[0])]["tseg1"] = _tseg1
        _canSettings["channel" + str(_channels[0])]["tseg2"]=_tseg2
        _canSettings["channel" + str(_channels[0])]["ipAddress"] = str(_ipAddress)
        _canSettings["channel" + str(_channels[0])]["timeout"] = self.__wait_time
        
        AnalysisUtils().dump_yaml_file(directory=lib_dir, file=config_dir+_interface + "_CANSettings.yml", loaded=_canSettings)
        # Set the channel
        #self.logger.info("Please restart your bus from the tools menu (Interface >> %s >> Reset_%s_interface )to apply the new settings " % (_interface, _interface))
        
        self.hardware_config(bitrate=int(_bitrate),
                                     interface=_interface,
                                     sjw=int(_sjw),
                                     samplepoint=_sample_point,
                                     tseg1=int(_tseg1),
                                     tseg2=int(_tseg2),
                                     channel=str(_channel))
        if self.connectButton.isChecked():
            pass
        else:
            time.sleep(1)
            # Apply the settings to the main server
            self.wrapper = CanWrapper(interface=_interface,
                          bitrate=_bitrate,
                          samplePoint=_sample_point,
                          sjw=_sjw,
                          tseg1=_tseg1,
                          tseg2=_tseg2,
                          ipAddress=str(_ipAddress),
                          channel=int(_channel),
                          load_config = True)            
            # the the connect button to checked
            self.connectButton.setChecked(True)
        #except Exception:
        #    self.error_message(text="Please choose an interface or close the window")
            
    def hardware_config(self, bitrate, channel, interface, sjw,samplepoint,tseg1,tseg2):
        '''
        Pass channel string (example 'can0') to configure OS level drivers and interface.
        '''
        self.logger.info("Applying Hardware configurations")
        if interface == "socketcan":
            _bus_type = "can"
            _can_channel = _bus_type + channel
            self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
            os.system(". " + lib_dir + "/canmops/socketcan_wrapper_enable.sh %i %s %s %s %s %i %i" % (bitrate, samplepoint, sjw, _can_channel, _bus_type,tseg1,tseg2))
        elif interface == "virtual":
            _bus_type = "vcan"
            _can_channel = _bus_type + channel
            self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
            os.system(". " + lib_dir + "/canmops/socketcan_wrapper_enable.sh %i %s %s %s %s %i %i" % (bitrate, samplepoint, sjw, _can_channel, _bus_type,tseg1,tseg2))
        else:
            _can_channel = channel
            
        self.logger.info('%s[%s] Interface is initialized....' % (interface,_can_channel))
        
    def set_canchannel(self, arg=None, interface=None, default_channel=None):
        '''
        The function will restart the van channel
        '''
        try:
            if interface is not None: 
                #_channel = default_channel
                _channel,_ipAddress, _bitrate,_sample_point, _sjw,_tseg1, _tseg2 =  self.load_settings_file(interface = interface, channel = default_channel) 
                if (arg == "socketcan" and interface == "socketcan"):
                    _bus_type = "can"
                    _can_channel = _bus_type + str(_channel)
                    self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
                    os.system(". " + rootdir[:-14] + "/canmops/socketcan_wrapper_enable.sh %i %s %s %s %s %s %s" % (_bitrate, _sample_point, _sjw, _can_channel, _bus_type, _tseg1, _tseg2))
                    self.logger.info('SocketCAN[%s] is initialized....' % _can_channel)
                    
                if (arg == "virtual" and interface == "virtual"):
                    _bus_type = "vcan"             
                    _can_channel = _bus_type + str(_channel)
                    self.logger.info('Configure CAN hardware drivers for channel %s' % _can_channel)
                    os.system(". " + rootdir[:-14] + "/canmops/socketcan_wrapper_enable.sh %i %s %s %s %s %s %s" % (_bitrate, _sample_point, _sjw, _can_channel, _bus_type, _tseg1, _tseg2))
                    self.logger.info('SocketCAN[%s] is initialized....' % _can_channel)
                    
                if (arg == "restart" and interface == "socketcan"):
                    # This is An automatic bus-off recovery if too many errors occurred on the CAN bus
                    _bus_type = "restart" 
                    _can_channel = "can" + str(_channel)       
                    os.system(". " + rootdir[:-14] + "/canmops/socketcan_wrapper_enable.sh %s %s %s %s %s %s %s" % (_bitrate, _sample_point, _sjw, _can_channel, _bus_type, _tseg1, _tseg2))
                

                self.wrapper = CanWrapper(interface=interface,
                              bitrate=_bitrate,
                              samplePoint=_sample_point,
                              sjw=_sjw,
                              tseg1=_tseg1,
                              tseg2=_tseg2,
                              ipAddress=_ipAddress,
                              channel=int(_channel),
                              load_config = True)
                if (arg == "restart" and interface == "Kvaser"):
                    self.wrapper.restart_channel_connection(interface="Kvaser")
                                                
        except:
            self.logger.error("Cannot Connect to the CAN bus interface")
            pass
                
    def dump_socketchannel(self, channel):
        self.logger.info("Dumping socketCan channels")
        print_command = "echo ==================== Dumping %s bus traffic ====================\n" % channel
        candump_command = "candump %s -x -c -t A" % channel
        os.system("sudo gnome-terminal -e 'bash -c \"" + print_command + candump_command + ";bash\"'")

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
           b) read_monitoring_values    
           c) read_configuration_values
        """
        data_RX = None
        _index = int(self.get_index(), 16)
        _subIndex = int(self.get_subIndex(), 16)
        _nodeId = int(self.get_nodeId())
        #_interface = self.get_interface()
        _busId = self.get_busId()

        data_RX,_,_,_,_,_,_ = asyncio.run(self.wrapper.read_sdo_can(nodeId = _nodeId,
                                                                  index = _index, 
                                                                  subindex = _subIndex, 
                                                                  bus =  int(_busId)))
        self.update_bus_progress(reset_progress =False)
        return data_RX
    
    def trim_nodes(self): 
         _channel = self.get_channel()
         asyncio.run(self.wrapper.trim_nodes(channel=int(_channel))) 
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
            _nodeId = int(self.get_nodeId())
            SDO_TX = int(self.get_canId_tx(), 16)
            SDO_RX = self.get_canId_rx()
            _cobid_TX = SDO_TX + _nodeId
            _busId = self.get_busId()
            _cobid_RX, data_RX = asyncio.run(self.wrapper.read_sdo_can_thread(nodeId=_nodeId,
                                                                      index=_index,
                                                                      subindex=_subIndex,
                                                                      SDO_TX=SDO_TX,
                                                                      SDO_RX=SDO_RX,
                                                                      cobid=_cobid_TX,
                                                                      bus = int(_busId)))
            if print_sdo == True:
                # self.control_logger.disabled = False
                self.print_sdo_can(index=_index, subIndex=_subIndex, response_from_node=data_RX, cobid_TX=_cobid_TX, cobid_RX=_cobid_RX, bus = int(_busId))
                self.update_bus_progress(reset_progress =False )
            return data_RX
        except Exception:
           self.logger.warning("Either the bus or the interface is not connected") 
        
    def print_sdo_can(self , index=None, subIndex=None, response_from_node=None, cobid_TX=None, cobid_RX=None, bus = 0):
        # printing the read message with cobid = SDO_RX + nodeId
        max_data_bytes = 8
        msg = [0 for i in range(max_data_bytes)]
        msg[0] = 0x40  # Defines a read (reads data only from the node) dictionary object in CANOPN standard
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subIndex
        msg[7] = bus
        #  fill the Bytes/bits table
        self.set_table_content(bytes=msg, comunication_object="SDO_TX")
        # printing RX     
        self.set_textBox_message(comunication_object="SDO_TX", msg=str([hex(m)[2:] for m in msg]), cobid=str(hex(cobid_TX) + " "))
        # print decoded response
        if response_from_node is not None:
            # printing response 
            b1, b2, b3, b4 = response_from_node.to_bytes(4, 'little')
            RX_response = [0x43] + msg[1:4] + [b1, b2, b3, b4]
            # fill the Bytes/bits table       
            self.set_table_content(bytes=RX_response, comunication_object="SDO_RX")
            # printing TX   
            self.set_textBox_message(comunication_object="SDO_RX", msg=str([hex(m)[2:] for m in RX_response]), cobid=str(hex(cobid_RX) + " "))
            # print decoded response
            converted_response = Analysis().adc_conversion("V", response_from_node, self.__resistor_ratio, self.__ref_voltage)
            decoded_response = f'{response_from_node:03X}'
            self.set_textBox_message(comunication_object="Decoded", msg=decoded_response, cobid=str(hex(cobid_RX) + ": Hex value = "))
            self.set_textBox_message(comunication_object="ADC", msg=f'{round(converted_response,3)}', cobid=str(hex(cobid_RX) + ": ADC value = "))
        else:
            RX_response = "No Response Message"
            self.set_textBox_message(comunication_object="ErrorFrame", msg=RX_response, cobid=str("NONE" + "  "))
            # fill the Bytes/bits table       
            self.set_table_content(bytes=RX_response, comunication_object="ErrorFrame")
                # fill the textBox
        decoded_response = f'------------------------------------------------------------------------'
        self.set_textBox_message(comunication_object="newline", msg=decoded_response, cobid=None)   
        
    def send_random_can(self): 
        """
        The function will send random messages to the bus with random index and random subindex 
        The function is called by the following functions: 
           a)  RandomDumpMessage_action button
           b)  initiate_random_timer
        """
        # get OD Index
        _canIdentifier = self.CANIdComboBox.currentText()
        # Generate random indices and sub indices
        _index = np.random.randint(1000, 2500)
        _subIndex = np.random.randint(0, 5)
        _nodeId = self.nodetextBox.text()
        
        # Set the indices and the sub indices
        self.set_nodeId(_nodeId)
        self.set_index(str(_index))
        self.set_subIndex(str(_subIndex))
        self.set_canId_tx(_canIdentifier)
        
        # clear cells
        self.TXTable.clearContents()  
        self.hexTXTable.clearContents()
        self.decTXTable.clearContents()
        
        # send SDO can
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
        _dlc = self.get_dlc() 
        _index = hex(int.from_bytes([_bytes[1], _bytes[2]], byteorder=sys.byteorder))
        _subIndex = hex(int.from_bytes([_bytes[3]], byteorder=sys.byteorder))
        # fill the Bytes table     
        self.set_table_content(bytes=_bytes, comunication_object="SDO_TX")
        # fill the textBox     
        self.set_textBox_message(comunication_object="SDO_TX", msg=str([hex(b)[2:] for b in _bytes]), cobid=str(_cobid_TX) + " ")  
        
        try: 
                # Send the can Message
            asyncio.run(self.wrapper.write_can_message(cobid = int(_cobid_TX, 16),data =  _bytes, flag=0, dlc =_dlc))
            #go back to the default dlc
            self.set_dlc(8)
            # receive the message
            nodeList = self.get_nodeList()
            def hideIcon():
                # Hide the label
                self._wait_label.setVisible(False)
    
            if _cobid_TX == "0x00":
                for i in np.arange(len(nodeList)):
                    self.read_can_message_thread(comunication_object="SDO_RX")
            elif int(_cobid_TX, 16) >= 0x700:
                self._wait_label.setVisible(True)
                self.read_can_message_thread(comunication_object="SDO_RX")       
                timer = QTimer(self)
                timer.singleShot(500, hideIcon)  # 3000 milliseconds (3 seconds)
            
            else:
                self.read_can_message_thread(comunication_object="SDO_RX")
        except Exception:
           self.logger.warning("Either the bus or the interface is not connected") 
        self.update_bus_progress(reset_progress =False)
        return None
    
    def read_can_message_thread(self, print_sdo=True,comunication_object="SDO_RX"):
        """Read an object in a thread
        1. Request messages in the bus
        2. Communicate with the read_can_message_thread function in the CANWrapper to read the message
        3. Print the result if print_sdo is True
        The function is called by the following functions: 
           a) write_can_message
           b) show_dump_child_window
           c) dump_child_window
        """
        readCanMessage = self.wrapper.read_can_message_thread()
        response = any(readCanMessage)
        if response: 
           cobid_ret, data_ret , dlc, flag, t, _ = readCanMessage
           data_ret_int = int.from_bytes(data_ret, byteorder=sys.byteorder)
           # get the data in Bytes
           b1, b2, b3, b4, b5, b6, b7, b8 = data_ret_int.to_bytes(8, 'little') 
           # make an array of the bytes data
           data_ret_bytes = [b1, b2, b3, b4, b5, b6, b7, b8]
           # get the hex form of each byte
           data_ret_hex = [hex(b)[2:] for b in data_ret_bytes]
           if print_sdo == True:
               # fill the Bytes table     
               self.set_table_content(bytes=data_ret, comunication_object=comunication_object)
               # fill the textBox
               self.set_textBox_message(comunication_object=comunication_object, msg=str(data_ret_hex), cobid=str(hex(cobid_ret) + " "))
        else:
            cobid_ret, data_ret, dlc, flag, t = None, None, None, None, None
            RX_response = "No Response Message"
            self.set_textBox_message(comunication_object="ErrorFrame", msg=RX_response, cobid=str("NONE" + "  "))
        # fill the textBox
        decoded_response = f'------------------------------------------------------------------------'
        self.set_textBox_message(comunication_object="newline", msg=decoded_response, cobid=None) 
        self.update_bus_progress(reset_progress =False )
        
        return cobid_ret, data_ret, dlc, flag, t

    '''
    Update blocks with data
    '''        

    def initiate_adc_timer(self):
        '''
        The function will  update the GUI with the ADC data ach period in ms.
        ''' 
        self.stop_adc_reading = True
  
        try:
            # Disable the logger when reading ADC values [The exception statement is made to avoid user mistakes]
            self.control_logger.disabled = True
        except Exception:
            pass
            
        self.logger.notice("Reading ADC data...")
        self.__mon_time = time.time()
        # A possibility to save the data into a file
        self.__default_file = self.get_default_file()
        
        if len(self.__default_file) != 0:
            self.logger.notice("Preparing an output file [%s]..." % (output_dir+self.__default_file))
            fieldnames = ['Time', 'Channel', "nodeId", "ADCChannel", "ADCData" , "ADCDataConverted"]
            secondary_fieldnames = [f"resistor_ratio:{self.__resistor_ratio}",f"ref_voltage:{self.__ref_voltage}V"]
            self.csv_writer, self.out_file_csv = AnalysisUtils().build_data_base(fieldnames=fieldnames,
                                                                                 outputname=self.__default_file[:-4],
                                                                                  directory=output_dir,
                                                                                  secondary_fieldnames = secondary_fieldnames)   
            eventTimer = mops_child_window.EventTimer()
            self.adc_timer = eventTimer.initiate_timer()
            self.adc_timer.setInterval(int(self.__refresh_rate))
            self.adc_timer.timeout.connect(self.update_adc_channels)
            self.adc_timer.timeout.connect(self.update_monitoring_values)
        else:
            self.error_message("Please add an output file name")
             
    def stop_adc_timer(self):
        '''
        The function will  stop the adc_timer.
        '''        
        def exit_handler():
        # This function will be called on script termination
            self.logger.warning("Script interrupted. Closing the program.")
            sys.exit(0)
        atexit.register(exit_handler)  
        try:
            self.stop_adc_reading = False
            self.adc_timer.stop()
            self.logger.warning("User interrupted. Closing the program.")       
                  
            # self.csv_writer.writerow((str(None),
            #              str(None),
            #              str(None),
            #              str(None), 
            #              str(None), 
            #              "End of Test") ) 
            # self.out_file_csv.flush() # Flush the buffer to update the file
            self.out_file_csv.close()
            self.logger.notice("ADC data are saved to %s" % (output_dir))
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
        
                     
    def update_adc_channels(self):
        '''
        The function will will send a CAN message to read the ADC channels using the function read_sdo_can and
            update the channelValueBox in adc_values_window.
        The calling function is initiate_adc_timer.
        '''   
        _adc_channels_reg = self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _adc_indices = list(self.__adc_index)
        #data_point = [0] * 33
        try:
            for i in np.arange(len(_adc_indices)):
                _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex="subindex_items"))
                self.set_index(_adc_indices[i])  # set index for later usage
                _start_a = 3  # to ignore the first subindex it is not ADC
                for subindex in np.arange(_start_a, len(_subIndexItems) + _start_a - 1):
                    s = subindex - _start_a
                    s_correction = subindex - 2
                    self.set_subIndex(_subIndexItems[s_correction])
                    # read SDO CAN messages
                    #self.update_bus_progress(reset_progress =False)
                    data_point = self.read_sdo_can()  # _thread(print_sdo=False)
                    time.sleep(self.__wait_time )
                    ts = time.time()
                    if data_point is None: 
                        #self.logger.warning(f"No responses in the Bus for subindex {_subIndexItems[s_correction]}")
                        #self.stop_adc_timer()
                        self.__adc_converted = None
                        self.channelValueBox[s].setText(str(self.__adc_converted))
                    else:
                        self.__adc_converted = Analysis().adc_conversion(_adc_channels_reg[str(subindex)], 
                                                                                       data_point, 
                                                                                       self.__resistor_ratio,
                                                                                       self.__ref_voltage)
                        self.set_adc_converted(self.__adc_converted)
                        self.channelValueBox[s].setText(str(round(self.__adc_converted, 3)))
                    
                    elapsedtime = ts - self.__mon_time
                    # update the progression bar to show bus statistics
                    self.progressBar.setValue(subindex)    
                    self.csv_writer.writerow((str(round(elapsedtime, 1)),
                                         str(self.get_channel()),
                                         str(self.get_nodeId()),
                                         str(subindex),
                                         str(data_point),
                                         str(self.__adc_converted)))
                    self.out_file_csv.flush() # Flush the buffer to update the file
                    if self.trendingBox[s] == True and self.__adc_converted is not None:
                        # Monitor a window of 100 points is enough to avoid Memory issues
                        if len(self.x[s]) >= 100:
                            self.DataMonitoring.reset_data_holder(self.__adc_converted,s)
                        self.DataMonitoring.update_figure(data=self.__adc_converted, subindex=subindex, graphWidget = self.graphWidget[s])

        except (KeyboardInterrupt):
            #Handle Ctrl+C to gracefully exit the loop
            
            self.logger.warning("User interrupted. Closing the program.")
            self.stop_adc_timer()
            sys.exit(1) 
        return self.__adc_converted

    def update_monitoring_values(self):
        '''
        The function will will send a CAN message to read monitoring values using the function read_sdo_can and
         update the monValueBox in monitoring_values_window.
        The calling function is initiate_adc_timer.
        ''' 
        _dictionary = self.__dictionary_items
        _mon_indices = list(self.__mon_index)
        for i in np.arange(len(_mon_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex="subindex_items"))
            self.set_index(_mon_indices[i])  # set index for later usage
            for s in np.arange(0, len(_subIndexItems)):
                self.set_subIndex(_subIndexItems[s])
                #self.update_bus_progress(reset_progress =True)
                data_point = self.read_sdo_can()  # _thread(print_sdo=False)
                time.sleep(self.__wait_time )
                if data_point is None: 
                    #self.stop_adc_timer()
                    self.__adc_converted = None
                    self.monValueBox[s].setText(str(self.__adc_converted))
                    #break
                else:
                    if   s == 0: resistor_ratio = 1
                    elif s == 1: resistor_ratio = 2.5
                    elif s == 2: resistor_ratio = 1  
                    self.__adc_converted = Analysis().adc_conversion(adc_channels_reg = "V", 
                                                                     value = data_point,
                                                                     resistor_ratio = resistor_ratio,
                                                                     ref_voltage = self.__ref_voltage)
                    self.set_adc_converted(self.__adc_converted)
                    self.monValueBox[s].setText(str(round(self.__adc_converted, 3)))
    
    def error_message(self, text=False):
        '''
        The function will return a MessageBox for Error message
        '''
        QMessageBox.about(self, "Error Message", text)
    '''
    Show toolBar
    ''' 

    def show_toolBar(self, toolbar, mainwindow): 
        
        toolbar.isMovable()
        
        canMessage_action = QAction(QIcon(icon_location+'icon_msg.jpg'), '&CAN Message', mainwindow)
        canMessage_action.setShortcut('Ctrl+M')
        canMessage_action.setStatusTip('CAN Message')
        canMessage_action.triggered.connect(self.show_CANMessageWindow)

        settings_action = QAction(QIcon(icon_location+'icon_settings.jpeg'), '&CAN Settings', mainwindow)
        settings_action.setShortcut('Ctrl+L')
        settings_action.setStatusTip('CAN Settings')
        settings_action.triggered.connect(self.show_CANSettingsWindow)

        dump_can_message_action = QAction(QIcon(icon_location+'icon_dump.png'), '&CAN Dump', mainwindow)
        dump_can_message_action.setShortcut('Ctrl+D')
        dump_can_message_action.setStatusTip('Dump CAN messages from the bus')
        dump_can_message_action.triggered.connect(self.show_dump_child_window)

        run_random_message_action = QAction(QIcon(icon_location+'icon_right.jpg'), '&CAN Run', mainwindow)
        run_random_message_action.setShortcut('Ctrl+R')
        run_random_message_action.setStatusTip('Send Random CAN messages to the bus every 5 seconds')
        run_random_message_action.triggered.connect(self.initiate_random_timer)
        
        stop_dump_message_action = QAction(QIcon(icon_location+'icon_stop.png'), '&CAN Stop', mainwindow)
        stop_dump_message_action.setShortcut('Ctrl+C')
        stop_dump_message_action.setStatusTip('Stop Sending CAN messages')
        stop_dump_message_action.triggered.connect(self.stop_random_timer)

        dump_random_message_action = QAction(QIcon(icon_location+'icon_random.png'), '&CAN Random', mainwindow)
        dump_random_message_action.setShortcut('Ctrl+G')
        dump_random_message_action.setStatusTip('Send Random Messages to the bus')
        dump_random_message_action.triggered.connect(self.send_random_can)
        # fileMenu.addSeparator()
        clear_action = QAction(QIcon(icon_location+'icon_clear.png'), '&Clear', mainwindow)
        clear_action.setShortcut('Ctrl+X')
        clear_action.setStatusTip('Clear All the menus')
        clear_action.triggered.connect(self.clear_textBox_message)
        clear_action.triggered.connect(self.clear_table_content)
        clear_action.triggered.connect(self.clear_bus_progress)
        
        plot_adc__action = QAction(QIcon(icon_location+'icon_curve.png'), '&Plotting', mainwindow)
        plot_adc__action.setShortcut('Ctrl+p')
        plot_adc__action.setStatusTip('Plotting feature')
        plot_adc__action.triggered.connect(self.show_adc_plotting_window)        

        toolbar.addAction(canMessage_action)
        toolbar.addAction(settings_action)
        toolbar.addSeparator()
        toolbar.addAction(dump_can_message_action)
        toolbar.addAction(run_random_message_action)
        toolbar.addAction(stop_dump_message_action)
        toolbar.addAction(dump_random_message_action)                          
        toolbar.addSeparator()
        toolbar.addAction(clear_action)      
        toolbar.addAction(plot_adc__action)

    '''
    Define child windows
    '''
    def show_adc_plotting_window(self):
        self.plotWindow = QMainWindow()
        ChildWindow = child_window.ChildWindow(parent = self.plotWindow)
        ChildWindow.plot_adc_window(adcItems=self.adcItems,
                                    name_prefix="adc__1",
                                    plot_prefix="adc_data")
        ChildWindow.show()
        
    def show_CANMessageWindow(self):
        #try:
        self.MessageWindow = QMainWindow()
        child = child_window.ChildWindow(parent = self.MessageWindow)
        _od_index = self.CANIdComboBox.currentText()
        _nodeId = self.nodetextBox.text()
        _bytes = self.get_bytes()
        child.can_message_child_window(self.MessageWindow, 
                        od_index = _od_index,
                        nodeId = _nodeId,
                        bytes = _bytes,
                        mainWindow = self)
        self.MessageWindow.show()


        #except:
        #    pass

    def show_dump_child_window(self):
        #if self.wrapper is not None: 
        interface = self.get_interface()
        if interface == "socketcan" or interface == "virtual":
            self.logger.info("DumpingCAN bus traffic.")
            print_command = "echo ============================ Dumping CAN bus traffic ============================\n"
            candump_command = "candump any -x -c -t A -e"
            os.system("gnome-terminal -e 'bash -c \"" + print_command + candump_command + ";bash\"'")
        else:
            self.read_can_message_thread(print_sdo=False)
        #else:
        #    pass
            # self.DumpMessageWindow = QMainWindow()
            # child = childWindow.ChildWindow(parent = self.DumpMessageWindow)
            # self.dumptextBox = self.dump_child_window(self.DumpMessageWindow, mainWindow = self)
            # self.MessageWindow.show()
         
    def show_CANSettingsWindow(self):
        self.SettingsWindow = QMainWindow()
        _interfaceItems = self.__interfaceItems
        _channelList = self.get_channelPorts()
        child = child_window.ChildWindow(parent = self.SettingsWindow)
        #self.interfaceComboBox, self.channelSettingsComboBox , self.ipBox = 
        child.can_settings_child_window(self.SettingsWindow, 
                                        interfaceItems = _interfaceItems,
                                        channelPorts = _channelList,
                                        mainWindow = self)
        self.SettingsWindow.show()
    
    def show_trendWindow(self):
        trend = QMainWindow(self)
        subindex = self.sender().objectName()
        s = int(subindex) - 3     
        self.trendingBox[s] = True  
        n_channels = 33
        for i in np.arange(0, n_channels): self.graphWidget[i].clear()  # clear any old plots
        self.x, self.y = self.DataMonitoring.trend_child_window(childWindow=trend, subindex=int(subindex), n_channels=n_channels)
        trend.show()
            
    def show_deviceWindow(self):
        self.deviceWindow = QMainWindow()
        _channel = self.get_channel()
        _nodeItems = self.get_nodeList()
        n_channels = 33
        device_config = "mops"
        self.set_busId(self.busIdbox.text())
        _busId = self.get_busId()
        self.channelValueBox, self.trendingBox , self.monValueBox , self.progressBar,  self._wait_label = mops_child_window.MopsChildWindow(mainWindow = self).device_child_window(childWindow=self.deviceWindow, 
                                                                                                                                                                  device =self.__deviceName,
                                                                                                                                                                  device_config =device_config,
                                                                                                                                                                  mainWindow= self,
                                                                                                                                                                  mopshub_mode = self.__mopshub_mode,
                                                                                                                                                                  mopshub_communication_mode = self.__mopshub_communication_mode)
        self.graphWidget = self.DataMonitoring.initiate_trending_figure(n_channels=n_channels)
        self.deviceWindow.show()
    '''
    Define set/get functions
    '''

    def set_textBox_message(self, comunication_object=None, msg=None, cobid=None):
        if comunication_object == "SDO_RX": 
            color = QColor("black")
            mode = "RX [hex] :"
        if comunication_object == "SDO_TX": 
            color = QColor("blue") 
            mode = "TX [hex] :"
        if comunication_object == "Decoded": 
            color = QColor("green")
            mode = "RX [dec] :"
        if comunication_object == "ADC": 
            color = QColor("green")
            mode = "RX [  V ] :"
        if comunication_object == "ErrorFrame": 
            color = QColor("red")
            mode = "E:  "
        if comunication_object == "newline":
            color = QColor("green")
            mode = ""        
        self.textBox.setTextColor(color)
        if cobid is None:
            self.textBox.append(mode + msg)
        else:
            self.textBox.append(mode + cobid + msg)
            
    def clear_textBox_message(self):
         self.textBox.clear()
         
    def set_table_content(self, bytes=None, comunication_object=None):
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
        if comunication_object == "ErrorFrame": 
            self.RXTable.clearContents()  # clear cells
            self.hexRXTable.clearContents()  # clear cells
            self.decRXTable.clearContents()  # clear cells            
        if comunication_object == "SDO_TX":
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
        else:
            pass
        
    def clear_table_content(self):
        self.TXTable.clearContents() 
        self.hexTXTable.clearContents() 
        self.decTXTable.clearContents() 
        self.RXTable.clearContents() 
        self.hexRXTable.clearContents() 
        self.decRXTable.clearContents()
                  
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

    def set_busList(self, x):
        self.__busids = x 
            
    def set_channelPorts(self, x):
        self.__channelPorts = x 
               
    def set_interfaceItems(self, x):
        self.__interfaceItems = x  
           
    def set_interface(self, x): 
        self.__interface = x 

                           
    def set_adc_converted(self, x):
        self.__adc_converted = x
        
    def set_nodeId(self, x):
        self.__nodeId = x

    def set_channel(self, x):
        self.__channel = x
        
    def set_index(self, x):
        self.__index = x
    
    def set_bitrate(self, x):
        self.__bitrate = int(x)       
    
    def set_sjw(self, x):
        self.__sjw = int(x)
        
    def set_tseg1(self, x):
        self.__tseg1 = int(x)
    
    def set_tseg2(self, x):
        self.__tseg2 = int(x)
    
    def set_sample_point(self, x):
        self.__sample_point = float(x) / 100
            
    def set_ipAddress(self, x):
        self.__ipAddress = x
    
    def set_refresh_rate(self, x):
        self.__refresh_rate = x

    def set_dlc(self, x):
        self.__dlc = x
                               
    def set_subIndex(self, x):
        self.__subIndex = x
                
    def set_cobid(self, x):
        self.__cobid = x
    
    def set_busId(self,x):
        self.__busid = x
        
    def set_canId_tx(self, x):
        self.__canId_tx = x
    
    def set_bytes(self, x):
        self.__bytes = x

    def set_canId_rx(self, x):
        self.__canId_rx = x
            
    def set_default_file(self,x):
        self.__default_file = x
    
    
    def get_default_file(self):
        return self.__default_file
    
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
    
    def get_refresh_rate(self):
        return self.__refresh_rate
      
    def get_appName(self):
        return self.__appName
    
    def get_deviceName(self):
        return self.__deviceName

    def get_adc_converted(self):
        return self.__adc_converted
    
        
    def get_adc_channels_reg(self):
        return self.__adc_channels_reg

    def get_busId(self):
        return self.__busid
        
    def get_nodeList(self):
        return self.__nodeIds

    def get_busList(self):
        return self.__busids
    
    def get_subIndex(self):
        return self.__subIndex
    
    def get_cobid(self):
        return  self.__cobid
    
    def get_canId_tx(self):
        return self.__canId_tx
    
    def get_canId_rx(self):
        return self.__canId_rx

    def get_bytes(self):
        return self.__bytes 
        
    def get_bitrate(self):
        return self.__bitrate

    def get_ipAddress(self):
        return self.__ipAddress    

    def get_interfaceItems(self):
        return self.__interfaceItems
    
    def get_sample_points(self):
        return self.__sample_points
    
    def get_sample_point(self):
        return self.__sample_point
    
    def get_sjw(self):
        return self.__sjw   
    
    def get_tseg1(self):
        return self.__tseg1

    def get_dlc(self):
        return self.__dlc
       
           
    def get_tseg2(self):
        return self.__tseg2
        
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

