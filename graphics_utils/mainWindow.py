
from __future__ import annotations
import signal
from typing import *
import sched, time
import sys
import os
from os import chdir
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
import pyqtgraph as pg
from PyQt5 import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from threading import Thread, Event, Lock
import matplotlib as mpl
import numpy as np
from random import randint
from matplotlib.figure import Figure
from graphics_utils import dataMonitoring , logWindow, childWindow, menuWindow
from controlServer import analysis, analysis_utils , canWrapper
import binascii
from tqdm import tqdm
import tables as tb
import csv
import yaml
# Third party modules
import coloredlogs as cl
import verboselogs
from Cython.Compiler.Naming import self_cname
rootdir = os.path.dirname(os.path.abspath(__file__)) 

class TimeoutException(Exception):
    pass
class MainWindow(QMainWindow):
    
    def __init__(self, parent=None,
                 console_loglevel=logging.INFO,
                 file_loglevel=logging.INFO,
                 logformat='%(asctime)s - %(levelname)s - %(message)s',
                 device_config=["PSPP_cfg.yml"],
                 main_config=["main_cfg.yml"]):
        super(MainWindow, self).__init__(parent)
        self.__device_config = device_config            
        self.child = childWindow.ChildWindow()
        """:obj:`~logging.Logger`: Main logger for this class"""
        verboselogs.install()
        self.logger = logging.getLogger(__name__)
        cl.install(fmt=logformat, level=console_loglevel, isatty=True, milliseconds=True)
         
        # Start with default settings
        self.config_dir = "config/"
        self.logger = logging.getLogger(__name__)
        # Read configurations from a file    
        self.__conf = analysis_utils.open_yaml_file(file=self.config_dir + "main_cfg.yml", directory=rootdir[:-14])
        self.__appName = self.__conf["Application"]["app_name"] 
        self.__appVersion = self.__conf['Application']['app_version']
        self.__appIconDir = self.__conf["Application"]["app_icon_dir"]
        self.__canSettings =  self.__conf["Application"]["can_settings"]
        self._index_items = self.__conf["default_values"]["index_items"]
        self.__bitrate_items = self.__conf['default_values']['bitrate_items']
        self.__bytes = self.__conf["default_values"]["bytes"]
        self.__subIndex = self.__conf["default_values"]["subIndex"]
        self.__cobid = self.__conf["default_values"]["cobid"]
        self.__dlc = self.__conf["default_values"]["dlc"]
        self.__interfaceItems = list(self.__conf['CAN_Interfaces'].keys()) 
        self.__channelPorts = self.__conf["channel_ports"]
        self.__devices = self.__conf["Devices"]
        # Search for predefined CAN settings
        self.__interface = None
        self.__channel = None
        self.__ipAddress = None
        self.__bitrate = None
        self.configure_DeviceBox(None)
        self.index_description_items = None
        self.subIndex_description_items = None
        self.__response = None
        self.wrapper = None
        # Show a textBox
        self.textBoxWindow()


    def configure_devices(self, dev):
        self.__deviceName = dev["Application"]["device_name"] 
        self.__version = dev['Application']['device_version']
        self.__appIconDir = dev["Application"]["icon_dir"]
        self.__nodeIds = dev["Application"]["nodeIds"]
        self.__dictionary_items = dev["Application"]["index_items"]
        self.__index_items = list(self.__dictionary_items.keys())
        self.__adc_channels_reg = dev["adc_channels_reg"]["adc_channels"]
        self.__adc_index = dev["adc_channels_reg"]["adc_index"]
        self.__mon_index = dev["adc_channels_reg"]["mon_index"] 
        self.__conf_index = dev["adc_channels_reg"]["conf_index"] 
        return  self.__deviceName, self.__version,  self.__appIconDir, self.__nodeIds, self.__dictionary_items, self.__adc_channels_reg, self.__adc_index
    
    def Ui_ApplicationWindow(self):
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
        #self.adjustSize()
        
        self.defaultSettingsWindow()
        self.defaultMessageWindow()
        self.tableOutputWindow()
        
        # Create a frame in the main menu for the gridlayout
        mainFrame = QFrame(self)
        mainFrame.setLineWidth(0.6)
        self.setCentralWidget(mainFrame)
        
        line = QFrame()
        line.setGeometry(QRect(320, 150, 118, 3))
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
            
        # SetLayout
        self.mainLayout = QGridLayout()
        
        self.mainLayout.addLayout(self.defaultSettingsWindowLayout,0,0)
        self.mainLayout.addWidget(line, 1, 0)
        self.mainLayout.addLayout(self.defaultMessageWindowLayout, 2, 0)
        self.mainLayout.addWidget(self.textGroupBox, 3, 0)
        self.mainLayout.addWidget(self.monitorGroupBox, 3, 1)
        self.mainLayout.addWidget(line, 4, 0)
        self.mainLayout.addLayout(self.HLayout, 5, 0)
        mainFrame.setLayout(self.mainLayout)
        # 3. Show
        self.show()
        return
            
    def textBoxWindow(self):
        self.textGroupBox = QGroupBox("Output Window")
        plotframe = QFrame(self)
        plotframe.setStyleSheet("QWidget { background-color: #eeeeec; }")
        plotframe.setLineWidth(0.6)
        self.textBox = QTextEdit()
        #self.textBox.setTabStopWidth(12) 
        self.textBox.setReadOnly(True)
        self.textBox.resize(100,20)
        gridLayout = QGridLayout()
        gridLayout.addWidget(self.textBox,1, 0)
        self.setCentralWidget(plotframe)
        plotframe.setLayout(gridLayout)
        self.textGroupBox.setLayout(gridLayout)
        
    def tableOutputWindow(self):
        self.monitorGroupBox = QGroupBox("Bytes Monitoring")
        plotframe = QFrame(self)
        plotframe.setStyleSheet("QWidget { background-color: #eeeeec; }")
        plotframe.setLineWidth(0.6)
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
        
        bitLabel = QLabel()
        bitLabel.setText("Bits")
        bitLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        bitLabel.setAlignment(Qt.AlignCenter)
        
        n_bytes = 8
        self.table = QTableWidget(self)  # Create a table
        self.table.setColumnCount(n_bytes)     #Set n columns
        self.table.setRowCount(n_bytes)        # and n rows
        # Do the resize of the columns by content
        self.table.resizeColumnsToContents()
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Set the table headers
        col = [str(i) for i in np.arange(n_bytes)]
        row = [str(i) for i in np.arange(n_bytes-1,-1,-1)]
        self.table.setHorizontalHeaderLabels(row)
        self.table.setVerticalHeaderLabels(col)
        self.table.setEditTriggers( QAbstractItemView.NoEditTriggers)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.setVisible(False)
        self.table.verticalScrollBar().setValue(0)
        self.table.resizeColumnsToContents()
        self.table.setVisible(True)
        
        # create progressBar 
        #self.progressBar = QProgressBar()
        #self.progressBar.setRange(0, 8)
        #self.progressBar.setValue(0)
        TXLayout = QVBoxLayout()
        TXLabel = QLabel()
        TXLabel.setText("            TX")
        self.TXProgressBar= QProgressBar()
        self.TXProgressBar.setRange(0, 1)
        self.TXProgressBar.setValue(0)
        self.TXProgressBar.setTextVisible(False)
        TXLayout.addWidget(self.TXProgressBar)
        TXLayout.addWidget(TXLabel)
        
             
        RXLayout = QVBoxLayout()
        RXLabel = QLabel()
        RXLabel.setText("            RX")
        self.RXProgressBar= QProgressBar()
        self.RXProgressBar.setRange(0, 1)
        self.RXProgressBar.setValue(0)
        self.RXProgressBar.setTextVisible(False)
        RXLayout.addWidget(self.RXProgressBar)
        RXLayout.addWidget(RXLabel)

        progressLayout = QHBoxLayout()
        progressLayout.addLayout(TXLayout)
        progressLayout.addLayout(RXLayout)
        #self.progressBar.setGeometry(100, 150, 40, 100)
        #self.progressBar.setOrientation()
        #self.progressBar.setOrientation(QtCore.Qt.Vertical)
        
        #timer = QTimer(self)
        #timer.timeout.connect()
        #timer.start(10)
        def setTableWidth():
            width = self.table.verticalHeader().width()
            width += self.table.horizontalHeader().length()
            self.table.setMinimumWidth(width)
        
        def setTableLength():
            length = self.table.verticalHeader().length()
            length += self.table.horizontalHeader().width()
            self.table.setMaximumHeight(length);
            
        setTableWidth()
        setTableLength()
                
        gridLayout = QGridLayout()
        
        gridLayout.addWidget(bitLabel,0,1)
        gridLayout.addWidget(graphicsview,1,0)
        gridLayout.addWidget(self.table,1, 1)
        gridLayout.addLayout(progressLayout,2,1)
        self.setCentralWidget(plotframe)
        plotframe.setLayout(gridLayout)
        self.monitorGroupBox.setLayout(gridLayout)
                
    def defaultSettingsWindow(self):
        self.defaultSettingsWindowLayout = QGridLayout()
        __interfaceItems = self.__interfaceItems
        __channelList = self.__channelPorts
        interfaceLabel = QLabel("interface")
        interfaceLabel.setText("  Interfaces")
                
        self.interfaceComboBox = QComboBox()
        for item in __interfaceItems[:]: self.interfaceComboBox.addItem(item)
        self.interfaceComboBox.activated[str].connect(self.set_interface)
        self.interfaceComboBox.setStatusTip('Select the connected interface')
        self.interfaceComboBox.setCurrentIndex(2)
        
        # if self.trendingBox[i].isChecked():
        self.connectButton = QPushButton("")
        icon = QIcon()
        icon.addPixmap(QPixmap('graphics_utils/icons/icon_connect.jpg'), QIcon.Normal, QIcon.On)
        icon.addPixmap(QPixmap('graphics_utils/icons/icon_disconnect.jpg'), QIcon.Normal, QIcon.Off)
        self.connectButton.setIcon(icon)
        self.connectButton.setStatusTip('Connect the interface and set the channel')
        self.connectButton.setCheckable(True)
        
        channelLabel = QLabel("Channels")
        channelLabel.setText(" Channels")
        self.channelComboBox = QComboBox()
        self.channelComboBox.setStatusTip('Possible ports as defined in the main_cfg.yml file')
        for item in list(__channelList): self.channelComboBox.addItem(item)  
        def on_channelComboBox_currentIndexChanged(channel):
            _interface = self.interfaceComboBox.currentText()
            _channel = self.channelComboBox.currentText()
            _channels = analysis_utils.get_info_yaml(dictionary=self.__conf['CAN_Interfaces'], index=_interface, subindex="channels")
            
            self.set_interface(_interface)
            self.set_channel(int(_channel))
            try:
                _nodeItems = _channels[int(_channel)]
                self.nodeComboBox.clear()
                self.nodeComboBox.addItems(list(map(str,_nodeItems)))
            except Exception:
                self.logger.warning("No interface connected to the selected port")
                self.nodeComboBox.clear()
                pass
        self.channelComboBox.setCurrentIndex(0)  
           
        self.connectButton.clicked.connect(on_channelComboBox_currentIndexChanged)
        self.connectButton.clicked.connect(self.set_connect)
                
        self.defaultSettingsWindowLayout.addWidget(channelLabel, 0, 0)
        self.defaultSettingsWindowLayout.addWidget(self.channelComboBox, 1, 0)
        self.defaultSettingsWindowLayout.addWidget(interfaceLabel, 0, 1)
        self.defaultSettingsWindowLayout.addWidget(self.interfaceComboBox, 1, 1)
        self.defaultSettingsWindowLayout.addWidget(self.connectButton, 1, 3)
               
    def defaultMessageWindow(self):
        self.defaultMessageWindowLayout = QGridLayout()                        
        nodeLabel = QLabel("NodeId", self)
        nodeLabel.setText("NodeId ")
        self.nodeComboBox = QComboBox()
        self.nodeComboBox.setStatusTip('Connected CAN Nodes as defined in the main_cfg.yml file')

        indexLabel = QLabel("Index", self)
        indexLabel.setText("   Index   ")
        self.mainIndexTextBox = QLineEdit("0x1000", self)
        
        subIndexLabel = QLabel("    SubIndex", self)
        subIndexLabel.setText("SubIndex")
        self.mainSubIndextextbox = QLineEdit(self.__subIndex, self)

        def __apply_CANMessageSettings():
            self.set_index(self.mainIndexTextBox.text())
            self.set_subIndex(self.mainSubIndextextbox.text())
            self.set_nodeId(self.nodeComboBox.currentText())
                
        self.startButton = QPushButton("")
        self.startButton.setIcon(QIcon('graphics_utils/icons/icon_start.png'))
        self.startButton.setStatusTip('Send CAN message')
        self.startButton.clicked.connect(__apply_CANMessageSettings)
        self.startButton.clicked.connect(self.send_sdo_can)                 
            
        self.defaultMessageWindowLayout.addWidget(nodeLabel, 0, 1)
        self.defaultMessageWindowLayout.addWidget(self.nodeComboBox, 1, 1)   
        self.defaultMessageWindowLayout.addWidget(indexLabel, 0, 2)
        self.defaultMessageWindowLayout.addWidget(self.mainIndexTextBox, 1, 2)
        self.defaultMessageWindowLayout.addWidget(subIndexLabel, 0, 3)
        self.defaultMessageWindowLayout.addWidget(self.mainSubIndextextbox, 1, 3)       
        self.defaultMessageWindowLayout.addWidget(self.startButton, 1, 4)

    def configure_DeviceBox(self, conf):
        self.HLayout = QHBoxLayout()
        deviceLabel = QLabel("Configure Device", self)
        self.deviceButton = QPushButton("")
        self.deviceButton.setStatusTip('Choose the configuration yaml file')
        if self.__devices[0] == "None":
            deviceLabel.setText("Configure Device")
            self.deviceButton.setIcon(QIcon('graphics_utils/icons/icon_question.png'))
            self.deviceButton.clicked.connect(self.update_deviceBox)
        else:
            deviceLabel.setText("Configured Device [" + self.__devices[0] + "]")
            self.update_deviceBox()
        self.HLayout.addWidget(deviceLabel)
        self.HLayout.addWidget(self.deviceButton)

    def update_deviceBox(self):
        if self.__devices[0] == "None":
            conf = self.child.open()
        else:
            conf = analysis_utils.open_yaml_file(file=self.config_dir + self.__devices[0] + "_cfg.yml", directory=rootdir[:-14])
        
        self.__devices.append(conf["Application"]["device_name"])
        self.deviceButton.deleteLater()
        self.HLayout.removeWidget(self.deviceButton)
        self.deviceButton = QPushButton("")
        deviceName, version, icon_dir, nodeIds, dictionary_items, adc_channels_reg, adc_index = self.configure_devices(conf)
        
        self.set_adc_channels_reg(adc_channels_reg)
       # self.set_adc_index(adc_index)
        self.set_deviceName(deviceName)
        self.set_version(version)
        self.set_icon_dir(icon_dir)
        self.set_nodeList(nodeIds)
        self.set_dictionary_items(dictionary_items)                
        self.deviceButton.setIcon(QIcon(self.get_icon_dir()))
        self.deviceButton.clicked.connect(self.show_deviceWindow)
        self.HLayout.addWidget(self.deviceButton)

    def set_connect(self):
        if self.connectButton.isChecked():
            _interface = self.get_interface()    
            try: 
                filename = rootdir[:-14]+self.config_dir +_interface+"_CANSettings.yml"
                if (os.path.isfile(filename)and self.__canSettings):
                    filename = os.path.join(rootdir[:-14],self.config_dir +_interface+"_CANSettings.yml")
                    test_date =time.ctime(os.path.getmtime(filename))
                    #Load settings from CAN settings file
                    _canSettings = analysis_utils.open_yaml_file(file=self.config_dir +_interface+"_CANSettings.yml", directory=rootdir[:-14])
                    self.logger.notice("Loading CAN settings from the file %s produced on %s"%(filename,test_date))
                    _channels = _canSettings['CAN_Interfaces'][_interface]["channels"]
                    _ipAddress = _canSettings['CAN_Interfaces'][_interface]["ipAddress"]
                    _bitrate = _canSettings['CAN_Interfaces'][_interface]["bitrate"]
                    _nodIds = _canSettings['CAN_Interfaces'][_interface]["nodIds"]
                    
                    #Update settings
                    self.set_nodeList(_nodIds)
                    self.set_channelPorts(list(str(_channels)))                
                    self.set_channel(_channels)
                    #Update buttons
                    self.channelComboBox.clear()
                    self.channelComboBox.addItems(list(str(_channels)))
                    self.nodeComboBox.clear()
                    self.nodeComboBox.addItems(list(map(str,_nodIds)))
                    self.wrapper = canWrapper.CanWrapper(interface=_interface, bitrate = _bitrate, ipAddress = _ipAddress,
                                                                channel = _channels, set_channel=True)
                else:
                    _channel = self.get_channel()
                    _channels = analysis_utils.get_info_yaml(dictionary=self.__conf['CAN_Interfaces'], index=_interface, subindex="channels")
                    _channels[_channel]
                    self.wrapper = canWrapper.CanWrapper(interface=_interface, channel = _channel, set_channel=True)
            except:
                self.connectButton.setChecked(False)
        else:
           self.wrapper.stop()
        self.control_logger =self.wrapper.logger
        
    def stop_server(self):
        try:
            self.wrapper.stop()
        except:
            pass
    def quit(self):
        print("qApp.quit")

    def set_all(self):   
        _bitrate = self.get_bitrate()
        _interface = self.get_interface()
        _channel = self.get_channel()
        _channels = analysis_utils.get_info_yaml(dictionary=self.__conf['CAN_Interfaces'], index=_interface, subindex="channels")
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
        self.nodeComboBox.addItems(list(map(str,_nodeItems)))
        self.connectButton.setChecked(True)
        #Save the settings into a file
        dict_file  = {"CAN_Interfaces":   {_interface  :{"bitrate":_bitrate , "ipAddress":str(_ipAddress),"timeout":_timeout,"channels":int(_channel),"nodIds":_nodeItems}}}
        self.logger.info("Saving CAN settings to the file %s"%rootdir[:-14]+self.config_dir +_interface+"_CANSettings.yml") 
        with open(rootdir[:-14]+self.config_dir +_interface+"_CANSettings.yml", 'w') as yaml_file:
            documents = yaml.dump(dict_file, yaml_file, default_flow_style=False)
        
        # Apply the settings to the main server
        self.wrapper = canWrapper.CanWrapper(interface=_interface, bitrate = _bitrate, ipAddress = str(_ipAddress),
                                            channel = int(_channel), set_channel=True)

        
    '''
    Define can communication messages
    '''
               
    def send_sdo_can(self, trending=False, print_sdo=True,save_sdo =  False):
        try:
            _index = int(self.get_index(), 16)
            _subIndex = int(self.get_subIndex(), 16)
            _nodeId = self.get_nodeId()
            _nodeId = int(_nodeId[0])      
            self.__response = self.wrapper.send_sdo_can(_nodeId, _index, _subIndex, 3000)
            if print_sdo == True:
                self.print_sdo_can(nodeId=_nodeId, index=_index, subIndex=_subIndex, response_from_node=self.__response)
            return self.__response
        except Exception:
            pass

    def error_message(self, text=False):
        QMessageBox.about(self, "Error Message", text)
     
    def print_sdo_can(self, nodeId=None , index=None, subIndex=None, response_from_node=None):
        # printing the read message with cobid = SDO_RX + nodeId
        MAX_DATABYTES = 8
        msg = [0 for i in range(MAX_DATABYTES)]
        msg[0] = 0x40
        msg[1], msg[2] = index.to_bytes(2, 'little')
        msg[3] = subIndex
        self.set_textBox_message(comunication_object="SDO_RX", msg=str(msg))
        # printing response 
        self.set_textBox_message(comunication_object="SDO_TX", msg=str(response_from_node))
        # print decoded response
        if response_from_node is not None:
            decoded_response = f'{response_from_node:03X}\n-----------------------------------------------------------------------'
            self.set_table_content(bytes=msg, comunication_object="SDO_RX")
            b1, b2, b3, b4, b5, b6, b7, b8 = response_from_node.to_bytes(8, 'little')
            bytes = [b1, b2, b3, b4, b5, b6, b7, b8]             
            self.set_table_content(bytes=bytes,comunication_object="SDO_TX" )
        else:
            decoded_response  = f'{response_from_node}\n------------------------------------------------------------------------'
        self.set_textBox_message(comunication_object="Decoded", msg=decoded_response)
            
    def write_can_message(self):
        cobid =self.get_cobid()
        bytes = self.get_bytes()  
        try:
            # Send the can Message
            self.set_textBox_message(comunication_object="SDO_RX", msg=str(bytes))
            self.wrapper.writeCanMessage(cobid, bytes, flag=0, timeout=200)
            self.set_table_content(bytes=bytes, comunication_object="SDO_RX")
            # receive the message
            self.read_can_message()
        except Exception:
            self.error_message(text="Make sure that the CAN interface is connected")
            
    def read_can_message(self,print_sdo = True):
        cobid, data, dlc, flag, t = self.wrapper.read_can_message()
        outtdata = int.from_bytes(data, byteorder=sys.byteorder)
        b1, b2, b3, b4, b5, b6, b7, b8 = outtdata.to_bytes(8, 'little') 
        self.logger.info(f'Got data: [{b1:02x}  {b2:02x}  {b3:02x}  {b4:02x}  {b5:02x}  {b6:02x}  {b7:02x} {b8:02x}]')
        if print_sdo == True:
            self.set_table_content(bytes=data, comunication_object="SDO_TX")
            self.set_textBox_message(comunication_object="SDO_TX", msg=str(data.hex()))
        return cobid, data, dlc, flag, t
    
    def dump_can_message(self, TIMEOUT=2):
        def timeout_handler(signum, frame):
            try:
                raise TimeoutException
            except Exception:
                pass  
  
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(TIMEOUT)    
        try:
            self.read_can_message(print_sdo = False)
            signal.alarm(0)
        except Exception:
            pass

    '''
    Define all child windows
    '''        
               
    def canMessageChildWindow(self, ChildWindow):
        ChildWindow.setObjectName("CANMessage")
        ChildWindow.setWindowTitle("CAN Message")
        ChildWindow.resize(300, 300)  # w*h
        mainLayout = QGridLayout()
        __channelList = self.__channelPorts
        _cobeid =self.get_cobid()
        _bytes = self.get_bytes()
        if type(_cobeid) == int:
            _cobeid =hex(_cobeid)
        # Define a frame for that group
        plotframe = QFrame(ChildWindow)
        plotframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(plotframe)
        # Define First Group
        FirstGroupBox = QGroupBox("")
        # comboBox and label for channel
        FirstGridLayout = QGridLayout() 
        cobidLabel = QLabel("CAN Identifier", ChildWindow)
        cobidLabel.setText("CAN Identifier:")
        cobidtextbox = QLineEdit(str(_cobeid), ChildWindow)
        FirstGridLayout.addWidget(cobidLabel, 0, 0)
        FirstGridLayout.addWidget(cobidtextbox, 0, 1) 
        FirstGroupBox.setLayout(FirstGridLayout) 
        
        SecondGroupBox = QGroupBox("Message Data")
        # comboBox and label for channel
        SecondGridLayout = QGridLayout()
        ByteList = ["Byte0 :", "Byte1 :", "Byte2 :", "Byte3 :", "Byte4 :", "Byte5 :", "Byte6 :", "Byte7 :"] 
        LabelByte = [ByteList[i] for i in np.arange(len(ByteList))]
        self.ByteTextbox = [ByteList[i] for i in np.arange(len(ByteList))]        
        for i in np.arange(len(ByteList)):
            LabelByte[i] = QLabel(ByteList[i], ChildWindow)
            LabelByte[i].setText(ByteList[i])
            self.ByteTextbox[i] = QLineEdit(str(_bytes[i]), ChildWindow)
            if i <= 3:
                SecondGridLayout.addWidget(LabelByte[i], i, 0)
                SecondGridLayout.addWidget(self.ByteTextbox[i], i, 1)
            else:
                SecondGridLayout.addWidget(LabelByte[i], i - 4, 4)
                SecondGridLayout.addWidget(self.ByteTextbox[i], i - 4, 5)
        SecondGroupBox.setLayout(SecondGridLayout) 
        
        def __set_message():
            self.set_cobid(int(cobidtextbox.text(), 16))
            textboxValue = [self.ByteTextbox[i] for i in np.arange(len(self.ByteTextbox))]
            for i in np.arange(len(self.ByteTextbox)):
                textboxValue[i] = self.ByteTextbox[i].text()
            self.set_bytes(list(map(int, textboxValue)))
        
        
        buttonBox = QHBoxLayout()
        send_button = QPushButton("Send")
        send_button.setIcon(QIcon('graphics_utils/icons/icon_true.png'))
        send_button.clicked.connect(__set_message)
        send_button.clicked.connect(self.write_can_message)
        
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphics_utils/icons/icon_close.jpg'))
        close_button.clicked.connect(ChildWindow.close)

        buttonBox.addWidget(send_button)
        buttonBox.addWidget(close_button)
                 
        mainLayout.addWidget(FirstGroupBox , 0, 0)
        mainLayout.addWidget(SecondGroupBox , 1, 0)
        mainLayout.addLayout(buttonBox , 2, 0)

        plotframe.setLayout(mainLayout) 
        self.MenuBar.create_statusBar(ChildWindow)
        QtCore.QMetaObject.connectSlotsByName(ChildWindow)
    
    def canDumpMessageChildWindow(self, ChildWindow):
        ChildWindow.setObjectName("CANDump")
        ChildWindow.setWindowTitle("CAN output window")
        ChildWindow.resize(700, 600)  # w*h        
        mainLayout = QGridLayout()
        
        # Define a frame for that group
        plotframe = QFrame(ChildWindow)
        plotframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(plotframe)
        
        # Define First Group
        FirstGroupBox = QGroupBox("")
        # comboBox and label for channel
        FirstGridLayout = QGridLayout() 
        run_label = QLabel("", ChildWindow)
        run_label.setText(" Start Run")
        run_button = QPushButton()
        run_button.setIcon(QIcon('graphics_utils/icons/icon_right.jpg'))
             
        stop_label = QLabel("Stop", ChildWindow)
        stop_label.setText(" Stop")
        stop_button = QPushButton()
        stop_button.setIcon(QIcon('graphics_utils/icons/icon_stop.png'))

        random_label = QLabel("Randomize", ChildWindow)
        random_label.setText("Randomize")
        random_button = QPushButton()
        random_button.setIcon(QIcon('graphics_utils/icons/icon_random.png'))
        
        FirstGridLayout.addWidget(run_label, 1, 0)
        FirstGridLayout.addWidget(stop_label, 1, 1)
        FirstGridLayout.addWidget(random_label, 1, 2)
                
        FirstGridLayout.addWidget(run_button, 0, 0)
        FirstGridLayout.addWidget(stop_button, 0, 1)        
        FirstGridLayout.addWidget(random_button, 0, 2)
        
        FirstGroupBox.setLayout(FirstGridLayout) 
        
        SecondGroupBox = QGroupBox("")
        SecondGridLayout = QGridLayout()
        ByteList = [" Chn", "  Id", " Flg", " DLC", "D0--D1--D2--D3--D4--D5--D6--D7", " Time"]
        self.textOutputBox = [ByteList[i] for i in np.arange(len(ByteList))] 
        textOutputLabel = [ByteList[i] for i in np.arange(len(ByteList))]        
        for i in np.arange(len(ByteList)):
            self.textOutputBox[i] = QTextEdit("")
            textOutputLabel[i] = QLabel(ByteList[i])
            if i == 0 or i == 1  or i == 2:
                self.textOutputBox[i].setFixedWidth(10) 
            if i == 3:
                self.textOutputBox[i].setFixedWidth(20) 
            if i == 4:
                self.textOutputBox[i].setFixedWidth(210)
            else:
                self.textOutputBox[i].setFixedWidth(60)
            self.textOutputBox[i].setTabStopWidth(12) 
            self.textOutputBox[i].setReadOnly(True)
            SecondGridLayout.addWidget(textOutputLabel[i], 0, i)
            SecondGridLayout.addWidget(self.textOutputBox[i], 1, i)
        SecondGroupBox.setLayout(SecondGridLayout) 
        SecondGroupBox.setStyleSheet("background-color: white ; border-color: white; border-style: outset;border-width: 1px ")
 
        run_button.clicked.connect(self.start_dumptimer)
        stop_button.clicked.connect(self.stop_dumptimer)    
        random_button.clicked.connect(self.dump_can_message) 
        
        HBox = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphics_utils/icons/icon_close.jpg'))
        close_button.clicked.connect(self.stop_dumptimer)
        close_button.clicked.connect(ChildWindow.close)
        HBox.addWidget(close_button)
        
        # mainLayout.addWidget(FirstGroupBox , 0, 0)
        mainLayout.addWidget(SecondGroupBox , 1, 0)
        mainLayout.addLayout(HBox , 2, 0)
        plotframe.setLayout(mainLayout) 
        self.MenuBar.create_statusBar(ChildWindow)
        QtCore.QMetaObject.connectSlotsByName(ChildWindow)
    
    def send_random_can(self): 
        _index = np.random.randint(1000, 2500)
        _subIndex = np.random.randint(0, 8)
        MAX_DATABYTES = 8
        msg = [0 for i in range(MAX_DATABYTES)]
        msg[0] = 0x40
        msg[1], msg[2] = _index.to_bytes(2, 'little')
        msg[3] = _subIndex
        try:
            _nodeId = int(self.nodeComboBox.currentText())
            self.set_table_content(bytes=msg, comunication_object="SDO_RX")
            self.__response = self.wrapper.send_sdo_can(_nodeId, _index, _subIndex, 3000)
            self.print_sdo_can(nodeId=_nodeId, index=_index, subIndex=_subIndex, response_from_node=self.__response)       
        except:
            self.error_message(text="Make sure that the controller is connected")
            
    def canSettingsChildWindow(self, ChildWindow):
        ChildWindow.setObjectName("CANSettings")
        ChildWindow.setWindowTitle("CAN Settings")
        ChildWindow.resize(250, 400)  # w*h
        mainLayout = QGridLayout()
        _channelList = self.__channelPorts
        # Define a frame for that group
        plotframe = QFrame(ChildWindow)
        plotframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(plotframe)
        
        # Define First Group
        FirstGroupBox = QGroupBox("Bus Statistics")
        FirstGridLayout = QGridLayout()
        
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(ChildWindow.close)
        
        FirstGridLayout.addWidget(clear_button, 0, 0)
        FirstGroupBox.setLayout(FirstGridLayout)
        
        # Define the second group
        SecondGroupBox = QGroupBox("Bus Configuration")
        SecondGridLayout = QGridLayout()        
        # comboBox and label for channel
        chLabel = QLabel("CAN Interface:", ChildWindow)
        chLabel.setText("CAN Interface    :")
        
        interfaceLayout = QHBoxLayout()
        __interfaceItems = self.__interfaceItems
        interfaceComboBox = QComboBox(ChildWindow)
        for item in __interfaceItems: interfaceComboBox.addItem(item)
        interfaceComboBox.activated[str].connect(self.set_interface)
        
        interfaceLayout.addWidget(interfaceComboBox)
        # Another group will be here for Bus parameters
        self.BusParametersGroupBox()
        
        channelLabel = QLabel("CAN Channels:", ChildWindow)
        channelLabel.setText("CAN Channels: ")
        channelComboBox = QComboBox(ChildWindow)
        for item in _channelList: channelComboBox.addItem(item)
        channelComboBox.activated[str].connect(self.set_channel)

        # FirstButton
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(ChildWindow.close)

        HGridLayout = QGridLayout()  
        set_button = QPushButton("Set in all")
        set_button.setStatusTip('The button will apply the same settings for all CAN controllers')  # show when move mouse to the icon
        set_button.setIcon(QIcon('graphics_utils/icons/icon_true.png'))
        set_button.clicked.connect(self.set_all)
        
        HGridLayout.addWidget(set_button, 0, 0)
        
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
            _channel =channelComboBox.currentText()
            self.set_channel(_channel)
            self.set_interface(_interface)
            self.BusParametersGroupBox(ChildWindow=ChildWindow , interface=_interface)
            SecondGridLayout.addWidget(self.SubSecondGroupBox, 4, 0)        

        interfaceComboBox.activated[str].connect(_interfaceParameters)
        SecondGridLayout.addLayout(HGridLayout, 5, 0)
        # Define Third Group
        ThirdGroupBox = QGroupBox("Bus Status")
        ThirdGridLayout = QGridLayout()
        
        go_button = QPushButton("Go On Bus")
        go_button.setIcon(QIcon('graphics_utils/icons/icon_reset.png'))
        go_button.clicked.connect(ChildWindow.close)
        
        ThirdGridLayout.addWidget(go_button, 0, 0)
        ThirdGroupBox.setLayout(ThirdGridLayout)
        mainLayout.addWidget(FirstGroupBox, 0, 0)
        mainLayout.addWidget(SecondGroupBox, 1, 0)
        mainLayout.addWidget(ThirdGroupBox, 2, 0)
        plotframe.setLayout(mainLayout) 
        self.MenuBar.create_statusBar(ChildWindow)
        QtCore.QMetaObject.connectSlotsByName(ChildWindow)                
        
    def BusParametersGroupBox(self, ChildWindow=None, interface="Others"):
        # Define subGroup
        self.SubSecondGroupBox = QGroupBox("Bus Parameters")
        SubSecondGridLayout = QGridLayout()
        firstLabel = QLabel("firstLabel", ChildWindow)
        secondLabel = QLabel("secondLabel", ChildWindow)
        thirdLabel = QLabel("thirdLabel", ChildWindow)
        firstComboBox = QComboBox(ChildWindow)
        if (interface == "Kvaser"):
            firstLabel.setText("")
            firstItems = self.get_bitrate_items() 
            for item in firstItems: firstComboBox.addItem(item)
            
            #firstComboBox.activated[str].connect(self.clicked)
            secondLabel.setText("SJW:")
            secondItems = ["1", "2", "3", "4"]
            secondComboBox = QComboBox(ChildWindow)
            for item in secondItems: secondComboBox.addItem(item)
            #secondComboBox.activated[str].connect(self.clicked)
            thirdLabel.setText("Bit Timing:")
            thirdItems = self.get_bitrate_items()
            thirdComboBox = QComboBox(ChildWindow)
            for item in thirdItems: thirdComboBox.addItem(item)
            thirdComboBox.activated[str].connect(self.set_bitrate)

        if (interface == "socketcan"):
            firstLabel.setText("")
            firstItems = self.get_bitrate_items() 
            for item in firstItems: firstComboBox.addItem(item)
            
            #firstComboBox.activated[str].connect(self.clicked)
            secondLabel.setText("SJW:")
            secondItems = ["1", "2", "3", "4"]
            secondComboBox = QComboBox(ChildWindow)
            for item in secondItems: secondComboBox.addItem(item)
            #secondComboBox.activated[str].connect(self.clicked)
            thirdLabel.setText("Bit Timing:")
            thirdItems = self.get_bitrate_items()
            thirdComboBox = QComboBox(ChildWindow)
            for item in thirdItems: thirdComboBox.addItem(item)
            thirdComboBox.activated[str].connect(self.set_bitrate)
                        
        if (interface == "AnaGate"):
            firstLabel.setText("IP address")
            
            self.firsttextbox = QLineEdit('192.168.1.254', ChildWindow)

            secondLabel.setText("SJW:")
            secondItems = ["1", "2", "3", "4"]
            secondComboBox = QComboBox(ChildWindow)
            for item in secondItems: secondComboBox.addItem(item)
            #secondComboBox.activated[str].connect(self.clicked)
            
            thirdLabel.setText("Bit Timing:")
            thirdItems = self.get_bitrate_items()
            thirdComboBox = QComboBox(ChildWindow)
            for item in thirdItems: thirdComboBox.addItem(item)
            thirdComboBox.activated[str].connect(self.set_bitrate)
            SubSecondGridLayout.addWidget(self.firsttextbox, 0, 1)
            
        if (interface == "Others"):        
            firstLabel.setText("Speed:")
            firstItems = [""]
            firstComboBox = QComboBox(ChildWindow)
            for item in firstItems: firstComboBox.addItem(item)
            # firstComboBox.activated[str].connect(self.clicked)
            secondLabel.setText("")
            seconditems = [""]
            secondComboBox = QComboBox(ChildWindow)
            for item in seconditems: secondComboBox.addItem(item)
            #secondComboBox.activated[str].connect(self.clicked)
            thirdLabel.setText("")
            thirdItems = [""]
            thirdComboBox = QComboBox(ChildWindow)
            thirdComboBox.activated[str].connect(self.set_bitrate)
            for item in thirdItems: thirdComboBox.addItem(item)
            SubSecondGridLayout.addWidget(firstComboBox, 0, 1)
        else:
            pass   
        SubSecondGridLayout.addWidget(firstLabel, 0, 0)
        SubSecondGridLayout.addWidget(secondLabel, 1, 0)
        SubSecondGridLayout.addWidget(secondComboBox, 1, 1)
        SubSecondGridLayout.addWidget(thirdLabel, 2, 0)
        SubSecondGridLayout.addWidget(thirdComboBox, 2, 1)
        self.SubSecondGroupBox.setLayout(SubSecondGridLayout)
            
    def deviceChildWindow(self, ChildWindow):
        
        def __status_device():
        #  check if the MOPS is alive or not. MOPS should repond with a CAN message
            cobid = 0x701
            bytes = [0, 0, 0, 0, 0, 0, 0, 0]
            self.wrapper.writeCanMessage(cobid, bytes, flag=0, timeout=200)
            # receive the message
            _, data, _,_,_ = self.read_can_message(print_sdo = False)
            if data is not None: 
               self.logger.info("%s device is in an active state"%(self.__deviceName))
            else: 
                self.logger.error("%s device is in not active"%(self.__deviceName))
        __status_device()
        
        #  Open the window
        ChildWindow.setObjectName("DeviceWindow")
        ChildWindow.setWindowTitle("Device Window [ " + self.__deviceName + "]")
        ChildWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        #ChildWindow.adjustSize()
        w, h = 750,600
        ChildWindow.resize(w, h)  # w*h
        logframe = QFrame()
        logframe.setLineWidth(0.6)
        ChildWindow.setCentralWidget(logframe)
        
        # Initialize tab screen
        self.tabLayout = QGridLayout()
        self.devicetTabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget() 
        
        nodeLabel = QLabel("", self)
        nodeLabel.setText("Connected nodes :")
        
        deviceNodeComboBox = QComboBox(self)
        nodeItems = self.__nodeIds
        self.set_nodeList(nodeItems)
        for item in list(map(str, nodeItems)): deviceNodeComboBox.addItem(item)

        def __set_bus():
            self.set_nodeId(deviceNodeComboBox.currentText())
        
        self.GridLayout = QGridLayout()    
        icon = QLabel(self)
        pixmap = QPixmap(self.get_icon_dir())
        icon.setPixmap(pixmap.scaled(100, 100))
        
        device_title = QLabel("    device", self)
        newfont = QFont("Times", 12, QtGui.QFont.Bold)
        device_title.setFont(newfont)
        device_title.setText("        " + self.get_deviceName())
        BottonHLayout = QHBoxLayout()
        startButton = QPushButton("")
        startButton.setIcon(QIcon('graphics_utils/icons/icon_start.png'))
        startButton.clicked.connect(__set_bus)
        startButton.clicked.connect(self.send_sdo_can)

        def __reset_device():
            self.set_cobid(0x0)
            self.set_bytes([0, 0, 0, 0, 0, 0, 0, 0]) 
            self.write_can_message()
            
        restartButton = QPushButton("")
        restartButton.setIcon(QIcon('graphics_utils/icons/icon_reset.png'))
        restartButton.clicked.connect(__reset_device)

        trendingButton = QPushButton("")
        trendingButton.setIcon(QIcon('graphics_utils/icons/icon_trend.jpg'))
        trendingButton.setStatusTip('Data Trending')  # show when move mouse to the icon
        trendingButton.clicked.connect(self.show_trendWindow)
        
        BottonHLayout.addWidget(startButton)
        #BottonHLayout.addWidget(restartButton)
        #BottonHLayout.addWidget(trendingButton)
        
        firstVLayout = QVBoxLayout()              
        firstVLayout.addWidget(icon)
        firstVLayout.addWidget(device_title)
        firstVLayout.addLayout(BottonHLayout)
        
        VLayout = QVBoxLayout()
        self.indexTextBox = QTextEdit("", self)
        self.indexTextBox.setStyleSheet("background-color: white; border: 2px inset black; min-height: 150px; min-width: 400px;")
        self.indexTextBox.LineWrapMode(1)
        self.indexTextBox.setReadOnly(True)       
        
        VLayout.addWidget(self.indexTextBox)
        #VLayout.addLayout(HLayout)
        
        indexLabel = QLabel("Index", self)
        indexLabel.setText("   Index   ")
        self.IndexListBox = QListWidget(self)
        indexItems = self.__index_items
        
        
        for item in indexItems: self.IndexListBox.addItem(item)
        self.IndexListBox.currentItemChanged.connect(self.set_index_value) 
        self.IndexListBox.currentItemChanged.connect(self.get_subIndex_items)
        self.IndexListBox.currentItemChanged.connect(self.get_index_description)  
        
        subIndexLabel = QLabel("    SubIndex", self)
        subIndexLabel.setText("SubIndex")
        self.subIndexListBox = QListWidget(self)
        self.subIndexListBox.currentItemChanged.connect(self.set_subIndex_value)  
        self.subIndexListBox.currentItemChanged.connect(self.get_subIndex_description)  
        
        #self.GridLayout.addWidget(nodeLabel, 0, 0)
        self.GridLayout.addLayout(firstVLayout, 1, 0)
        
        self.GridLayout.addWidget(indexLabel, 0, 1)
        self.GridLayout.addWidget(self.IndexListBox, 1, 1)
        
        self.GridLayout.addWidget(subIndexLabel, 0, 2)
        self.GridLayout.addWidget(self.subIndexListBox, 1, 2)
        self.GridLayout.addLayout(VLayout, 2, 0,2,3)
        self.tab1.setLayout(self.GridLayout)        

        HLayout = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphics_utils/icons/icon_close.jpg'))
        close_button.clicked.connect(self.stopTimer)
        close_button.clicked.connect(ChildWindow.close)
        HLayout.addSpacing(350)
        HLayout.addWidget(close_button)
        
        # Add Adc channels tab
        self.adcValuesWindow()
        self.monitoringValuesWindow()
        self.configurationValuesWindow()
        
        self.MenuBar.create_statusBar(ChildWindow)
        channelHLayout= QHBoxLayout()
        nodeHLayout= QHBoxLayout()
        nodeHLayout.addWidget(nodeLabel)
        nodeHLayout.addWidget(deviceNodeComboBox)
        nodeHLayout.addSpacing(300)
        
        self.tabLayout.addLayout(channelHLayout,0,0)
        self.tabLayout.addLayout(nodeHLayout,1,0)
        self.tabLayout.addWidget(self.devicetTabs,2,0)
        self.tabLayout.addLayout(HLayout,3,0)

        self.devicetTabs.addTab(self.tab1,"Object Dictionary")
        self.devicetTabs.addTab(self.tab2,"Device Channels") 
        
        def __set_bus():
            self.set_nodeId(deviceNodeComboBox.currentText())
            
        mainLayout = QGridLayout()     
        HBox = QHBoxLayout()
        send_button = QPushButton("run ")
        send_button.setIcon(QIcon('graphics_utils/icons/icon_start.png'))
        send_button.clicked.connect(__set_bus)
        send_button.clicked.connect(self.initiateTimer)
        
        trend_button = QPushButton("Trend ")
        trend_button.setIcon(QIcon('graphics_utils/icons/icon_trend.jpg'))
        trend_button.clicked.connect(self.show_trendWindow)
        
        stop_button = QPushButton("stop ")
        stop_button.setIcon(QIcon('graphics_utils/icons/icon_stop.png'))
        stop_button.clicked.connect(self.stopTimer)
                
        HBox.addWidget(send_button)
        HBox.addWidget(stop_button)
        #HBox.addWidget(trend_button)
        
        mainLayout.addWidget(self.FirstGroupBox ,0,0,3,3)
        mainLayout.addWidget(self.ThirdGroupBox,0,3,2,5)
        mainLayout.addWidget(self.SecondGroupBox,2,3,1,5)
        mainLayout.addLayout(HBox , 3, 0)
        self.tab2.setLayout(mainLayout)
        #self.initiate_trending_data()
        logframe.setLayout(self.tabLayout)
        
    def adcValuesWindow(self):
        # needed info to read the ADC from the yaml file
        self.FirstGroupBox = QGroupBox("ADC Channels")
        FirstGridLayout = QGridLayout()
        _adc_channels_reg = self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _adc_indices =  list(self.__adc_index)
        
        for i in np.arange(len(_adc_indices)):
            _subIndexItems = list(analysis_utils.get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex ="subindex_items"))
            labelChannel = [_subIndexItems[k] for k in np.arange(len(_subIndexItems)*len(_adc_indices))]
            self.ChannelBox = [_subIndexItems[k] for k in np.arange(len(_subIndexItems)*len(_adc_indices))]
            self.trendingBox = [_subIndexItems[k] for k in np.arange(len(_subIndexItems)*len(_adc_indices))]
            self.trendingBotton = [_subIndexItems[k] for k in np.arange(len(_subIndexItems)*len(_adc_indices))]
            _start_a = 1 # to ignore the first subindex
            a =0
            for s in np.arange(_start_a,len(_subIndexItems)): 
                #self.x[s] = list(range(2))  # 10 time points
                #self.y[s] = [0 for _ in range(2)]  # 10 data points
                subindex_description_item = analysis_utils.get_subindex_description_yaml(dictionary=_dictionary, index =_adc_indices[i], subindex= _subIndexItems[s])
                labelChannel[a] = QLabel("Channel", self)
                labelChannel[a].setText("Ch" + str(s+2) + ":")
                self.ChannelBox[a] = QLineEdit("", self)
                self.ChannelBox[a].setStyleSheet("background-color: white; border: 1px inset black;")
                self.ChannelBox[a].setReadOnly(True)
                labelChannel[a].setStatusTip('ADC channel %s [index = %s & subIndex = %s]' % (str(_subIndexItems[s]), _adc_indices[i], _subIndexItems[s]))  # show when move mouse to the icon
                icon = QLabel(self)
                if _adc_channels_reg[str(s)] == "V":  
                    icon_dir = 'graphics_utils/icons/icon_voltage.png'
                else:   
                    icon_dir = 'graphics_utils/icons/icon_thermometer.png'
                pixmap = QPixmap(icon_dir)
                icon.setPixmap(pixmap.scaled(20, 20))
                self.trendingBotton[a] = QPushButton("")
                self.trendingBotton[a].setObjectName(str(a))
                self.trendingBotton[a].setIcon(QIcon('graphics_utils/icons/icon_trend.jpg'))
                self.trendingBotton[a].setStatusTip('Data Trending')
                self.trendingBotton[a].clicked.connect(self.show_trendWindow)
                self.trendingBox[a] = QCheckBox(str(s))
                self.trendingBox[a].setStatusTip('Data Trending')
                self.trendingBox[a].setChecked(False)
                self.trendingBox[a].stateChanged.connect(self.stateBox)
                grid_location = s-1 # to relocate the boxes
                col_len =int(len(_subIndexItems)/2)
                if grid_location < col_len:
                    FirstGridLayout.addWidget(icon, grid_location, 0)
                    # FirstGridLayout.addWidget(self.trendingBox[s], s, 1)
                    #FirstGridLayout.addWidget(self.trendingBotton[a], grid_location, 2)
                    FirstGridLayout.addWidget(labelChannel[a], grid_location, 3)
                    FirstGridLayout.addWidget(self.ChannelBox[a], grid_location, 4)
                else:
                    FirstGridLayout.addWidget(icon, grid_location - col_len, 5)
                    #FirstGridLayout.addWidget(self.trendingBox[s], i-16, 6)
                    #FirstGridLayout.addWidget(self.trendingBotton[a], grid_location - col_len, 7)
                    FirstGridLayout.addWidget(labelChannel[a], grid_location - col_len, 8)
                    FirstGridLayout.addWidget(self.ChannelBox[a], grid_location - col_len , 9)
                a =a+1          
        self.FirstGroupBox.setLayout(FirstGridLayout)

    def monitoringValuesWindow(self):
        self.SecondGroupBox = QGroupBox("Monitoring Values")
        labelvalue = [0 for i in np.arange(20)]
        self.monValueBox = [0 for i in np.arange(20)]
        SecondGridLayout = QGridLayout()
        _dictionary = self.__dictionary_items
        _mon_indices = list(self.__mon_index)
        a = 0
        for i in np.arange(len(_mon_indices)):
            _subIndexItems = list(analysis_utils.get_subindex_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex ="subindex_items"))
            for s in np.arange(len(_subIndexItems)):
                subindex_description_item = analysis_utils.get_subindex_description_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex= _subIndexItems[s])
                labelvalue[a] = QLabel()
                labelvalue[a].setText(subindex_description_item+ ":")
                labelvalue[a].setStatusTip('%s [index = %s & subIndex = %s]' % (subindex_description_item[9:-11], _mon_indices[i], _subIndexItems[s])) 
                self.monValueBox[a] = QLineEdit("")
                self.monValueBox[a].setStyleSheet("background-color: white; border: 1px inset black;")
                self.monValueBox[a].setReadOnly(True)
                SecondGridLayout.addWidget(labelvalue[a], a, 0)
                SecondGridLayout.addWidget(self.monValueBox[a], a, 1)
                a = a+1
        self.SecondGroupBox.setLayout(SecondGridLayout)
    

    def configurationValuesWindow(self):
        self.ThirdGroupBox = QGroupBox("Configuration Values")
        labelvalue = [0 for i in np.arange(20)] # 20 is just a hypothetical number
        self.confValueBox = [0 for i in np.arange(20)]
        ThirdGridLayout = QGridLayout()
        _dictionary = self.__dictionary_items
        _conf_indices = list(self.__conf_index)
        a = 0
        for i in np.arange(len(_conf_indices)):
            _subIndexItems = list(analysis_utils.get_subindex_yaml(dictionary=_dictionary, index=_conf_indices[i], subindex ="subindex_items"))
            for s in np.arange(len(_subIndexItems)):
                subindex_description_item = analysis_utils.get_subindex_description_yaml(dictionary=_dictionary, index=_conf_indices[i], subindex= _subIndexItems[s])
                labelvalue[a] = QLabel()
                labelvalue[a].setText(subindex_description_item + ":")
                self.confValueBox[a] = QLineEdit("")
                self.confValueBox[a].setStyleSheet("background-color: white; border: 1px inset black;")
                self.confValueBox[a].setReadOnly(True)
                labelvalue[a].setStatusTip('%s [index = %s & subIndex = %s]' % (subindex_description_item[9:-11], _conf_indices[i], _subIndexItems[s])) 
                ThirdGridLayout.addWidget(labelvalue[a], a, 0)
                ThirdGridLayout.addWidget(self.confValueBox[a], a, 1)
                a = a+1
        self.ThirdGroupBox.setLayout(ThirdGridLayout)

    def trend_child_window(self,childWindow=None, index=None):
        childWindow.setObjectName("TrendingWindow")
        childWindow.setWindowTitle("Trending Window")
        childWindow.resize(800, 500)  # w*h
        logframe = QFrame()
        logframe.setLineWidth(0.6)
        childWindow.setCentralWidget(logframe)
        trendLayout = QHBoxLayout()
        self.WindowGroupBox = QGroupBox("")
        self.initiate_trending_data()
        self.Fig = self.initiate_trending_figure(index = index)
        
        def _initiate_trend_timer(index= None, period = 1000):
            self.trend_timer = QtCore.QTimer()
            self.trend_timer.start(period)
            try:
                data = float(self.ChannelBox[int(str(index))].text())
                self.trend_timer.timeout.connect(lambda: self.update_figure(data = data, i = index, index = index))
            except Exception:
                pass      
                      
        def _stop_trend_timer():
            try:
                self.trend_timer.stop() 
            except Exception:
                pass
        #_initiate_trend_timer(index=int(str(index)))
        self.Fig.setStyleSheet("background-color: black;"
                                        "color: black;"
                                        "border-width: 1.5px;"
                                        "border-color: black;"
                                        "margin:0.0px;"
                                        # "border: 1px "
                                        "solid black;")

        indexLabel = QLabel("Index", self)
        indexLabel.setText("ADC channels")
        self.IndexListBox = QListWidget(self)
        indexItems = self.__index_items
        
        #self.distribution = dataMonitoring.LiveMonitoringDistribution(data = data)
        #trendLayout.addWidget(self.distribution)
        trendLayout.addWidget(indexLabel)
        trendLayout.addWidget(self.Fig)
        
        self.WindowGroupBox.setLayout(trendLayout)
        logframe.setLayout(trendLayout) 
        
    def initiate_trending_data(self):
        self.x = list(range(2))  # 100 time points
        self.y = list(range(2)) #[0 for _ in range(2)]  # 100 data points
           
    def initiate_trending_figure(self, index = None):
        self.graphWidget = pg.PlotWidget(background="w")
        #n_channels = np.arange(3, 35)
        #self.data_line = [0 for i in np.arange(len(n_channels))]
#         for i in np.arange(len(n_channels)):
#             if self.trendingBox[i].isChecked():
#                 self.data_line[i] = self.graphWidget.plot(name="Ch%i" % i)
        # Add legend
        self.graphWidget.addLegend()#offset=(10,10* 20))        
        # Add Title
        self.graphWidget.setTitle("Online data monitoring for ADC channel %s"%str(index+3))
        # Add Axis Labels
        self.graphWidget.setLabel('left', "<span style=\"color:black; font-size:15px\">CAN Data</span>")
        self.graphWidget.setLabel('bottom', "<span style=\"color:black; font-size:15px\">Time [s]</span>")

        # Add grid
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.getAxis("bottom").setStyle(tickTextOffset=10)
        # Set Range
        self.graphWidget.setXRange(-2, 100, padding=0)
        # self.graphWidget.setYRange(00, 55, padding=0)
        return self.graphWidget
    
    def update_figure(self, data=None, i=None, index = None):
        self.data_line = self.graphWidget.plot(self.x, self.y, pen=pg.mkPen(color=self.get_color(i), width=3), name="Ch%i" % index)
        self.x= self.x[1:]  # Remove the first x element.
        self.x= np.append(self.x, self.x[-1] + 1)  # Add a new value 1 higher than the last
        self.y = self.y[2:]  # Remove the first   y element.
        self.y.append(data)  # Add a new value.
        self.y.append(data)  # Add a new value.
        self.data_line.setData(self.x, self.y)  # Update the data.

    def initiateTimer(self, period=50000):
        self.timer = QtCore.QTimer(self)
        self.control_logger.disabled = True
        self.logger.notice("Processing data...")

        def __open_csv(outname=None, directory=None):
            if not os.path.exists(directory):
                os.mkdir(directory)
            filename = os.path.join(directory, outname) 
            self.logger.notice("Preparing an output file [%s.csv]..."%(filename))
            out_file_csv = open(filename+'.csv', 'w+')
            # Write header to the data
            out_file_csv.write("TimeStamp, Channel, Id, Flg, DLC, ADCChannel, ADCData , ADCDataConverted \n")
            return out_file_csv

        def __read_csv(outname=None, directory=None):
            filename = os.path.join(directory, outname) 
            in_file_csv = open(filename+'.csv', 'r')  
            if in_file_csv.mode == 'r':  
                contents = in_file_csv.read()
                print(contents)
                      
        self.out_file_csv = __open_csv(outname="adc_data", directory=rootdir[:-14]+"output_data")         
       # __read_csv(outname="adc_data", directory=rootdir[:-14]+"/output_data")
        
        # Save data to a file
        self.timer.timeout.connect(self.read_adc_channels)
        self.timer.timeout.connect(self.read_monitoring_values)
        self.timer.timeout.connect(self.read_configuration_values)
        self.timer.start(period)

    def stopTimer(self):
        try:
            self.logger.notice("Stop data processing...")
            self.control_logger.disabled = False
            self.timer.stop()
            self.logger.notice("Closing the output file...")
            self.out_file_csv.close()
        except Exception:
            pass

    def read_adc_channels(self):
        _adc_index = self.__adc_index
        _adc_channels_reg = self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _adc_indices =  list(self.__adc_index)
        a =0
        for i in np.arange(len(_adc_indices)):
            _subIndexItems = list(analysis_utils.get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex ="subindex_items"))
            self.set_index(_adc_indices[i])# set index for later usage
            self.adc_converted = []
            #pbar = tqdm(total=len(_subIndexItems)*10,desc="ADC channels",iterable=True)
            _start_a = 1 # to ignore the first subindex it is not ADC
            for s in np.arange(_start_a, len(_subIndexItems)):
                self.set_subIndex(_subIndexItems[s])
                data_point = self.send_sdo_can(print_sdo=False)
                #self.out_file_csv.write("%i, %i, %i, %i,%i, %i, %i, %i\n"%(i,2,3,4,5,6,7,8))
                correction = s-1 # to relocate the boxes
                self.adc_converted = np.append(self.adc_converted, analysis.Analysis().adc_conversion(_adc_channels_reg[str(s+2)], data_point))
                if self.adc_converted[correction] is not None:
                    self.ChannelBox[a].setText(str(round(self.adc_converted[correction], 3)))
                    #if self.trendingBox[s].isChecked():
                    #    self.update_figure(data=self.adc_converted[correction], i=s)
                else:
                    self.ChannelBox[a].setText(str(self.adc_converted[correction]))
                a =a+1
             #   pbar.update(10)
            #pbar.close()
        return self.adc_converted


    def read_monitoring_values(self):
        _mon_index = self.__mon_index
        _adc_channels_reg = self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _mon_indices =  list(self.__mon_index)
        a = 0
        #pbar = tqdm(total=len(_mon_indices)*20,desc="Monitoring Values",iterable=True)
        for i in np.arange(len(_mon_indices)):
            _subIndexItems = list(analysis_utils.get_subindex_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex ="subindex_items"))
            self.set_index(_mon_indices[i])# set index for later usage
            for s in np.arange(0, len(_subIndexItems)):
                self.set_subIndex(_subIndexItems[s])
                data_point = self.send_sdo_can(print_sdo=False)
                self.monValueBox[a].setText(str(analysis.Analysis().convertion(data_point)))
                a =a+1
              #  pbar.update(1)
           # pbar.close()
            
    def read_configuration_values(self):
        _conf_index = self.__conf_index
        _adc_channels_reg = self.get_adc_channels_reg()
        _dictionary = self.__dictionary_items
        _conf_indices =  list(self.__conf_index)
        a = 0 
       # pbar = tqdm(total=len(_conf_indices)*2,desc="Configuration Values",iterable=True)
        for i in np.arange(len(_conf_indices)):
            _subIndexItems = list(analysis_utils.get_subindex_yaml(dictionary=_dictionary, index=_conf_indices[i], subindex ="subindex_items"))
            self.set_index(_conf_indices[i])# set index for later usage
            for s in np.arange(0, len(_subIndexItems)):
                self.set_subIndex(_subIndexItems[s])
                data_point = self.send_sdo_can(print_sdo=False)
                self.confValueBox[a].setText(str(analysis.Analysis().convertion(data_point)))
                a =a+1
              #  pbar.update(2)
          #  pbar.close()
                
    def stateBox(self, checked):
        # if state == QtCore.Qt.Checked:
        checkBox = self.sender() 
        if checked:
            print(checkBox.text())
        else:
            print(checkBox.text())
            
    '''
    Show ProgressBar
    '''  
    def update_progressBar(self, comunication_object=None):
        #curVal = self.progressBar.value() 
        #maxVal = self.progressBar.maximum()
        #self.progressBar.setValue(curVal + (maxVal - curVal) / 8)
        if comunication_object=="SDO_TX":
            self.TXProgressBar.setValue(1)
            self.RXProgressBar.setValue(0)
        if comunication_object=="SDO_RX":
            self.TXProgressBar.setValue(0)
            self.RXProgressBar.setValue(1)
            
        
        
    '''
    Show toolBar
    ''' 

    def show_toolBar(self, toolbar, mainwindow):        
        canMessage_action = QAction(QIcon('graphics_utils/icons/icon_msg.jpg'), '&CAN Message', mainwindow)
        canMessage_action.setShortcut('Ctrl+M')
        canMessage_action.setStatusTip('CAN Message')
        canMessage_action.triggered.connect(self.show_CANMessageWindow)

        settings_action = QAction(QIcon('graphics_utils/icons/icon_settings.jpeg'), '&CAN Settings', mainwindow)
        settings_action.setShortcut('Ctrl+L')
        settings_action.setStatusTip('CAN Settings')
        settings_action.triggered.connect(self.show_CANSettingsWindow)

        canDumpMessage_action = QAction(QIcon('graphics_utils/icons/icon_dump.png'), '&CAN Dump', mainwindow)
        canDumpMessage_action.setShortcut('Ctrl+D')
        canDumpMessage_action.setStatusTip('Dump CAN messages from the bus')
        canDumpMessage_action.triggered.connect(self.dump_can_message)

        runDumpMessage_action = QAction(QIcon('graphics_utils/icons/icon_right.jpg'), '&CAN Run', mainwindow)
        runDumpMessage_action.setShortcut('Ctrl+R')
        runDumpMessage_action.setStatusTip('start reading CAN messages')
        runDumpMessage_action.triggered.connect(self.show_CANDumpMessageWindow)
        
        stopDumpMessage_action = QAction(QIcon('graphics_utils/icons/icon_stop.png'), '&CAN Stop', mainwindow)
        stopDumpMessage_action.setShortcut('Ctrl+C')
        stopDumpMessage_action.setStatusTip('Stop reading CAN messages')
        #stopDumpMessage_action.triggered.connect(self.stop_dumptimer)

        RandomDumpMessage_action = QAction(QIcon('graphics_utils/icons/icon_random.png'), '&CAN Random', mainwindow)
        RandomDumpMessage_action.setShortcut('Ctrl+G')
        RandomDumpMessage_action.setStatusTip('Send Random Messages to the bus')
        RandomDumpMessage_action.triggered.connect(self.send_random_can)
                
        toolbar.addAction(canMessage_action)
        toolbar.addAction(settings_action)
        toolbar.addSeparator()
        #toolbar.addAction(canDumpMessage_action)
        # toolbar.addAction(runDumpMessage_action)
        # toolbar.addAction(stopDumpMessage_action)
        toolbar.addAction(RandomDumpMessage_action)                          

    '''
    Define child windows
    '''
    def show_CANMessageWindow(self):
        self.MessageWindow = QMainWindow()
        self.canMessageChildWindow(self.MessageWindow)
        self.MessageWindow.show()

    def show_CANDumpMessageWindow(self):
        self.MessageDumpWindow = QMainWindow()
        self.canDumpMessageChildWindow(self.MessageDumpWindow)
        self.MessageDumpWindow.show()
        
    def show_CANSettingsWindow(self):
        MainWindow = QMainWindow()
        self.canSettingsChildWindow(MainWindow)
        MainWindow.show()

    def show_trendWindow(self):
        trend = QMainWindow(self)
        sending_button = self.sender()
        self.trend_child_window(childWindow=trend, index=1)
        trend.show()
            
    def show_deviceWindow(self):
        self.deviceWindow = QMainWindow()
        self.deviceChildWindow(self.deviceWindow)
        self.deviceWindow.show()

    '''
    Define set/get functions
    '''
    def set_textBox_message(self, comunication_object=None, msg=None):
        if comunication_object == "SDO_RX"  :   
            color = QColor("green")
            mode = "W    :"
        if comunication_object == "SDO_TX"  :   
            color = QColor("red") 
            mode = "R    :"
        if comunication_object == "Decoded" :   
            color = QColor("blue")
            mode = "D    :"
        
        self.textBox.setTextColor(color)
        self.textBox.append(mode + msg)
        
    def set_table_content(self, bytes = None,comunication_object=None):
        self.update_progressBar(comunication_object=comunication_object)
        self.table.clearContents() # clear cells
        n_bytes = 8-1
        #for byte in bytes:
        for byte in np.arange(len(bytes)):
            bits = bin(bytes[byte])[2:]
            slicedBits=bits[::-1]# slicing 
            for b in np.arange(len(slicedBits)):
                self.table.setItem(byte, n_bytes- b, QTableWidgetItem(slicedBits[b]))
                self.table.item(byte,n_bytes- b).setBackground(QColor(self.get_color(int(slicedBits[b]))))
  
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
    
    def set_data_point(self, data):
        self.__response = data
    
    def get_data_point(self):
        return self.__response
        
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
        if self.__interface == 'Kvaser':
            raise AttributeError('You are using a Kvaser CAN interface!')
        return self.__ipAddress    

    def get_interfaceItems(self):
        return self.__interfaceItems
    
    def get_bitrate_items(self):
        return self.__bitrate_items
    
    def get_interface(self):
        """:obj:`str` : Vendor of the CAN interface. Possible values are
        ``'Kvaser'`` and ``'AnaGate'``."""
        return self.__interface

    def get_channel(self):
        return self.__channel    

    def get_subIndex_items(self):
        index = self.get_index()
        dictionary = self.__dictionary_items
        subIndexItems = list(analysis_utils.get_subindex_yaml(dictionary=dictionary, index=index, subindex= "subindex_items"))
        self.subIndexListBox.clear()
        for item in subIndexItems: self.subIndexListBox.addItem(item)
    
    def get_index_description(self):
        dictionary = self.__dictionary_items
        if self.IndexListBox.currentItem() is not None:
            index = self.IndexListBox.currentItem().text()
            self.index_description_items = analysis_utils.get_info_yaml(dictionary=dictionary , index=index,subindex = "description_items")
            self.indexTextBox.setText(self.index_description_items)
    
    def get_color(self, i):
        col_row = ["#f7e5b2", "#fcc48d", "#e64e4b", "#984071", "#58307b", "#432776", "#3b265e", "#4f2e6b", "#943ca6", "#df529e", "#f49cae", "#f7d2bb",
                "#f4ce9f","#ecaf83", "#dd8a5b", "#904a5d", "#5d375a", "#402b55", "#332d58", "#3b337a", "#365a9b", "#2c4172", "#2f3f60", "#3f5d92", 
                "#4e7a80", "#60b37e", "#b3daa3","#cfe8b7", "#d2d2ba", "#dd8a5b", "#904a5d", "#5d375a","#4c428d", "#3a3487", "#31222c", "#b3daa3"]
        return col_row[i]
    
    def get_subIndex_description(self):
        dictionary = self.__dictionary_items
        index = self.IndexListBox.currentItem().text()
        if self.subIndexListBox.currentItem() is not None:
            subindex = self.subIndexListBox.currentItem().text()
            self.subindex_description_items = analysis_utils.get_subindex_description_yaml(dictionary=dictionary, index=index, subindex=subindex)
            description_text = self.index_description_items + "<br>" + self.subindex_description_items
            self.indexTextBox.setText(description_text)    

if __name__ == "__main__":
    pass

