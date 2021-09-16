from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as Navi
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
from canmops.logger_main         import Logger 
from canmops.analysis_utils import AnalysisUtils
from graphicsUtils import main_gui_window, menu_window, data_monitoring, plotting_canvas, design_diagram
import numpy as np
import time
import os
import sys
import binascii
import yaml
import logging
rootdir = os.path.dirname(os.path.abspath(__file__)) 
lib_dir = rootdir[:-13]
config_dir = "config/"
output_dir = "output_data/"
class ChildWindow(QtWidgets.QMainWindow):  

    def __init__(self,parent = None, console_loglevel=logging.INFO):
       super().__init__(parent)
       self.logger = Logger().setup_main_logger(name="Child GUI", console_loglevel=console_loglevel)
       self.MenuBar = menu_window.MenuWindow(self)

    def ip_address_window(self, childWindow):
        childWindow.setWindowTitle("Set Ip address")
        childWindow.show()        
        childWindow.setObjectName("")
        childWindow.setWindowTitle("Add IP address to the list")
        childWindow.setWindowIcon(QtGui.QIcon('graphicsUtils/icons/icon_ip.png'))
        mainLayout = QGridLayout()
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        #current endpoint
        ipLabel = QLabel()
        ipLabel.setText("Set Ip address:")  
        
        ipLineEdit = QLineEdit()
        ipLineEdit.setStyleSheet("background-color: white; border: 1px inset black;")
        ipLineEdit.setReadOnly(True)
        ipLineEdit.setFixedWidth(150)
        ipLineEdit.setStatusTip('Current Configuration name of the OPCUA server')  # show when move mouse to the icon
        ip_name = self.get_ip_address()
        ipLineEdit.setText(ip_name)  
        def _add_ip():
            ip = ipLineEdit.text()
            self.ipListBox.addItem(ip)
            self.set_ip_address(ip)
            
        #Buttons section           
        add_button = QPushButton("")
        add_button.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
        add_button.setStatusTip('Add the IP address to the list') 
        add_button.clicked.connect(_add_ip)   

        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.png'))
        close_button.clicked.connect(childWindow.close)
                
        mainLayout.addWidget(ipLabel ,0,0)
        mainLayout.addWidget(ipLineEdit ,0, 1,1,3)              
        mainLayout.addWidget(add_button ,0, 4)
        mainLayout.addWidget(close_button ,1, 4)
        self.MenuBar.create_statusBar(childWindow)
        plotframe.setLayout(mainLayout)                 

                                      
    def browse_client_child_window(self, childWindow, conf):
        childWindow.setWindowTitle("OPCUA Server settings")
        childWindow.setWindowIcon(QtGui.QIcon('graphicsUtils/icons/icon_nodes.png'))
        #childWindow.setGeometry(200, 200, 100, 100)
        #childWindow.adjustSize() 
        childWindow.setFixedSize(850, 300)
        mainLayout = QGridLayout()
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        #current endpoint
        endpointLabel = QLabel()
        endpointLabel.setText("Endpoint name:")  
        
        endpointLineEdit = QLineEdit()
        endpointLineEdit.setStyleSheet("background-color: white; border: 1px inset black;")
        endpointLineEdit.setReadOnly(True)
        endpointLineEdit.setFixedWidth(250)
        
        endpointLineEdit.setStatusTip('Current Configuration name of the OPCUA server')  # show when move mouse to the icon
        endpoint_name = self.get_endpoint_url()
        endpointLineEdit.setText(endpoint_name)   
        
        IPGroup = self.def_ip_server_group()
        BrowseGroup = self.def_browser_client_group()
        
        def _save_items(hi = None):
            if hi:
                file = config_dir + self.__device + "_cfg.yml"

                self.logger.info("Saving Information to the file %s"%file)
            else:
                self.logger.error("No data to be saved.....")

        buttonLayout = QHBoxLayout() 
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        
        save_button = QPushButton("Save")
        save_button.setIcon(QIcon('graphicsUtils/icons/icon_true.png'))
        save_button.clicked.connect(_save_items)       
       # buttonLayout.addWidget(save_button)
        buttonLayout.addWidget(close_button)
        
        mainLayout.addWidget(endpointLabel,0,0,1,1)
        mainLayout.addWidget(endpointLineEdit,0,1,1,4)
        mainLayout.addWidget(IPGroup , 1, 0,1,2)
        mainLayout.addWidget(BrowseGroup, 1,2,1,3)
        mainLayout.addLayout(buttonLayout ,3, 4)
        self.MenuBar.create_statusBar(childWindow)
        plotframe.setLayout(mainLayout) 

    def def_ip_server_group(self):
        IPGroup= QGroupBox("IP address Info")
        def _get_ip_list():
            ip_device_address = AnalysisUtils().get_ip_device_address()
            ip_from_subnet = AnalysisUtils().get_ip_from_subnet(ip_device_address)
            return ip_from_subnet
        
        def _add_ip_server():
            #_show_ip_address_window():
            self.ipWindow = QMainWindow()
            self.ip_address_window(self.ipWindow)
            self.ipWindow.show()
            
        
        def _set_ip_server():
            try:
               current_ip = self.ipListBox.currentItem().text()  
            except:    
                self.ipListBox.setCurrentRow(0)
                current_ip = self.ipListBox.currentItem().text()  
                print(current_ip,"is set")          
        
        def _remove_ip_server():
            try:
                _row = self.ipListBox.currentRow()
                self.ipListBox.takeItem(_row)
            except:
                self.ipListBox.setCurrentRow(0)
                _row = self.ipListBox.currentRow()
                self.ipListBox.takeItem(_row)   
                             
        def _get_ip_item():
            _ip_address = self.ipListBox.currentItem().text()  


        #Ip list
        ipLabel = QLabel()
        ipLabel.setText("IP List:")  
        ip_from_subnet = _get_ip_list()
        self.ipListBox = QListWidget()
        self.ipListBox.setFixedWidth(120)
        self.ipListBox.setCurrentRow(0)
        for item in ip_from_subnet: self.ipListBox.addItem(item)
            
        #Buttons section
        butteonLayout = QVBoxLayout()               
        add_button = QPushButton("")
        add_button.setIcon(QIcon('graphicsUtils/icons/icon_plus.png'))
        add_button.setStatusTip('Add the IP address to the list') 
        
        set_button = QPushButton("")
        set_button.setIcon(QIcon('graphicsUtils/icons/icon_start.png'))
        set_button.setStatusTip('Set the IP address')  # show when move mouse to the icon
        
        remove_button = QPushButton("")
        remove_button.setIcon(QIcon('graphicsUtils/icons/icon_minus.jpg'))
        remove_button.setStatusTip('Remove IP address from the List')  # show when move mouse to the icon
        
        set_button.clicked.connect(_set_ip_server)   
        add_button.clicked.connect(_add_ip_server)
        remove_button.clicked.connect(_remove_ip_server)
        
        serverButtonLayout = QVBoxLayout() 
        serverButtonLayout.addWidget(add_button)
        serverButtonLayout.addWidget(set_button)
        serverButtonLayout.addWidget(remove_button)
        
        #outputs
        ipLayout= QGridLayout()
        ipLayout.addWidget(ipLabel,0,0)
        ipLayout.addWidget(self.ipListBox,1,0,5,2)     
        ipLayout.addLayout(serverButtonLayout,2,1,1,1)
        IPGroup.setLayout(ipLayout)
        return IPGroup
    
    def def_browser_client_group(self):
        BrowseGroup= QGroupBox("Browse Server")
        BrowseLayout = QGridLayout() 
        confLayout = QHBoxLayout()
        confLabel = QLabel()
        confLabel.setText("Server Configuration:")  
        confLineEdit = QLineEdit()
        confLineEdit.setStyleSheet("background-color: white; border: 1px inset black;")
        confLineEdit.setReadOnly(True)
        confLineEdit.setFixedWidth(300)
        confLineEdit.setStatusTip('Current Configuration name of the OPCUA server')  # show when move mouse to the icon
        server_config_yaml = self.get_server_config_yaml()
        confLineEdit.setText(server_config_yaml)   
                
        directoryButton = QPushButton("")
        directoryButton.setIcon(QIcon('graphicsUtils/icons/icon_open.png'))
        directoryButton.setStatusTip('Select Server Configuration file [The file should follow a specific standard format]') 
        directoryButton.clicked.connect(lambda: self.get_config_file(confLineEdit,config_dir))
        
        def _set_yaml():
            server_file = confLineEdit.text()
            client_file = self.match_client_to_server(server_config=server_file)
            count = 0
            TIME_LIMIT = 100
            while count < TIME_LIMIT:
                count += 1
                time.sleep(0.01)
                self.progress.setValue(count)
                if count >=90:
                    doneLabel.setText("Done")  
                    
        doneLabel = QLabel()
        doneLabel.setText("          ")
        doneLabel.setStyleSheet("color: green;")
        progress = self.progress_window()
        icon_spacer = QSpacerItem(10, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        save_button = QPushButton("Match client configurations")
        save_button.setIcon(QIcon('graphicsUtils/icons/icon_true.png'))
        save_button.clicked.connect(_set_yaml)   
                
        confLayout.addWidget(confLabel)
        confLayout.addWidget(confLineEdit)
        confLayout.addWidget(directoryButton)
        BrowseLayout.addLayout(confLayout, 0, 0,1,2)       
        BrowseLayout.addWidget(progress ,2, 0)
        BrowseLayout.addWidget(doneLabel ,2, 1)
        BrowseLayout.addWidget(save_button ,3,1)
        BrowseGroup.setLayout(BrowseLayout)
        return BrowseGroup
    
    def browse_server_child_window(self, childWindow, conf):
        childWindow.setObjectName("")
        childWindow.setWindowTitle("OPCUA Server settings")
        childWindow.setWindowIcon(QtGui.QIcon('graphicsUtils/icons/icon_nodes.png'))
        #childWindow.setGeometry(200, 200, 100, 100)
        childWindow.setFixedSize(500, 120)
        mainLayout = QGridLayout()
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        #current endpoint
        confLayout = QHBoxLayout()
        confLabel = QLabel()
        confLabel.setText("Configuration name:")  
        confLineEdit = QLineEdit()
        confLineEdit.setStyleSheet("background-color: white; border: 1px inset black;")
        confLineEdit.setReadOnly(True)
        confLineEdit.setFixedWidth(300)
        confLineEdit.setStatusTip('Current Configuration name of the OPCUA server')  # show when move mouse to the icon
        server_config_yaml = self.get_server_config_yaml()
        confLineEdit.setText(server_config_yaml)   
                
        directoryButton = QPushButton("")
        directoryButton.setIcon(QIcon('graphicsUtils/icons/icon_open.png'))
        directoryButton.setStatusTip('Select Server Configuration file [The file should follow a specific standard format]') 
        directoryButton.clicked.connect(lambda: self.get_config_file(confLineEdit,config_dir))
        doneLabel = QLabel()
        doneLabel.setText("          ")
        doneLabel.setStyleSheet("color: green;")
        progress = self.progress_window()
        
        confLayout.addWidget(confLabel)
        confLayout.addWidget(confLineEdit)
        confLayout.addWidget(directoryButton)
        
        buttonLayout = QHBoxLayout() 
        icon_spacer = QSpacerItem(100, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        
        def _set_yaml():
            file = confLineEdit.text()
            self.logger.notice("Setting OPCUA Server Configurations fom the file %s"%file)
            self.set_server_config_yaml(file)
            count = 0
            TIME_LIMIT = 100
            while count < TIME_LIMIT:
                count += 1
                time.sleep(0.01)
                self.progress.setValue(count)
                if count >=90:
                    doneLabel.setText("Done")  
            
            
        save_button = QPushButton("set configurations")
        save_button.setIcon(QIcon('graphicsUtils/icons/icon_true.png'))
        save_button.clicked.connect(_set_yaml)   
            
        buttonLayout.addItem(icon_spacer)
        buttonLayout.addWidget(save_button)
        buttonLayout.addWidget(close_button)
        
        mainLayout.addLayout(confLayout ,0, 0,1,5)
        mainLayout.addWidget(progress ,1, 0)
        mainLayout.addWidget(doneLabel ,1, 1,1,2)
        mainLayout.addLayout(buttonLayout ,3, 0)
        
         
        self.MenuBar.create_statusBar(childWindow)
        plotframe.setLayout(mainLayout) 
        
    def progress_window(self):
        self.progress = QProgressBar()
        self.progress.setMaximum(100)         
        return self.progress
        
           
    def can_message_child_window(self, ChildWindow, od_index = None, nodeId = None, bytes = None, mainWindow = None):
        ChildWindow.setObjectName("CAN Message")
        ChildWindow.setWindowTitle("CAN Message")
        ChildWindow.setGeometry(915, 490, 250, 315)
        mainLayout = QGridLayout()
        _cobeid = int(od_index, 16) + int(nodeId, 16)
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
        ByteTextbox = [ByteList[i] for i in np.arange(len(ByteList))]        
        for i in np.arange(len(ByteList)):
            LabelByte[i] = QLabel(ByteList[i])
            LabelByte[i].setText(ByteList[i])
            ByteTextbox[i] = QLineEdit(str(bytes[i]))
            if i <= 3:
                SecondGridLayout.addWidget(LabelByte[i], i, 0)
                SecondGridLayout.addWidget(ByteTextbox[i], i, 1)
            else:
                SecondGridLayout.addWidget(LabelByte[i], i - 4, 4)
                SecondGridLayout.addWidget(ByteTextbox[i], i - 4, 5)
        SecondGroupBox.setLayout(SecondGridLayout) 
        
        def _set_bus():
            _cobid = cobidtextbox.text() 
            textboxValue = [ByteTextbox[i] for i in np.arange(len(ByteTextbox))]
            
            for i in np.arange(len(ByteTextbox)):
                textboxValue[i] = ByteTextbox[i].text()
            bytes_int = [int(b, 16) for b in textboxValue]
            _index = hex(int.from_bytes([bytes_int[1], bytes_int[2]], byteorder=sys.byteorder))
            _subIndex = hex(int.from_bytes([bytes_int[3]], byteorder=sys.byteorder))
            
            mainWindow.set_cobid(_cobid)
            mainWindow.set_bytes(bytes_int)
            mainWindow.set_subIndex(_subIndex)
            mainWindow.set_index(_index)
            # self.read_sdo_can_thread()
        
        buttonBox = QHBoxLayout()
        send_button = QPushButton("Send")
        send_button.setIcon(QIcon('graphicsUtils/icons/icon_true.png'))
        send_button.clicked.connect(_set_bus)
        send_button.clicked.connect(mainWindow.write_can_message)
        
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
        
               
    def can_settings_child_window(self, childWindow, interfaceItems = None, channelPorts = None, mainWindow = None):
        '''
        The function defines the GroupBox for the default bus settings
        e.g. for Communication purposes the user needs to define   
        1. The CAN Bus [e.g. channel 0, 2, 3,....] 
        2. The Interface [e.g. socketcan, kvaser, Anagate]
        All the options in every widget are defined in the file main_cfg.yml
        '''  
        
        childWindow.setObjectName("CAN Settings")
        childWindow.setWindowTitle("CAN Settings")
        childWindow.setGeometry(915, 10, 250, 100)
        # childWindow.resize(250, 400)  # w*h
        mainLayout = QGridLayout()
        _channelList = channelPorts
        # Define a frame for that group
        plotframe = QFrame(childWindow)
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        
        # Define the second group
        SecondGroupBox = QGroupBox("Bus Configuration")
        SecondGridLayout = QGridLayout()        
        # comboBox and label for channel
        chLabel = QLabel()
        chLabel.setText("CAN Interface    :")
        
        interfaceLayout = QHBoxLayout()
        __interfaceItems = [""] + interfaceItems
        interfaceComboBox = QComboBox()
        for item in __interfaceItems: interfaceComboBox.addItem(item)
        interfaceComboBox.activated[str].connect(mainWindow.set_interface)
        interfaceLayout.addWidget(chLabel)
        interfaceLayout.addWidget(interfaceComboBox)
        
        channelLayout = QHBoxLayout()
        channelLabel = QLabel()
        channelLabel.setText("CAN Bus: ")
        self.channelSettingsComboBox = QComboBox()
        for item in _channelList: self.channelSettingsComboBox.addItem(str(item))
        self.channelSettingsComboBox.activated[str].connect(mainWindow.set_channel)
        channelLayout.addWidget(channelLabel)
        channelLayout.addWidget(self.channelSettingsComboBox)
        
        # Another group will be here for Bus parameters
        self.BusParametersGroupBox( mainWindow = mainWindow)
        
        
        # FirstButton
        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(childWindow.close)
        
        SecondGroupBox.setLayout(SecondGridLayout)
        SecondGridLayout.addLayout(interfaceLayout, 1, 0)
        SecondGridLayout.addLayout(channelLayout, 2, 0)
        SecondGridLayout.addWidget(self.SubSecondGroupBox, 3, 0)
        
        def _interfaceParameters():
            _interface = interfaceComboBox.currentText()
            _channel = self.channelSettingsComboBox.currentText()
            mainWindow.set_interface(_interface)
            mainWindow.set_channel(_channel)
            if _interface == "AnaGate":
                self.ipBox.setStyleSheet(" background-color: lightgray;")
                self.ipBox.setReadOnly(False)
            else:
                self.ipBox.setStyleSheet(" background-color: white;")
                self.ipBox.setReadOnly(True)
            _channel,_ipAddress, _bitrate,_samplePoint, _sjw,_tseg1, _tseg2 =  mainWindow.load_settings_file(interface = _interface, channel = _channel) 
            self.bitSpeedTextBox.setText(str(_bitrate))
            self.sampleTextBox.setText(str(_samplePoint*100))
            self.tseg1TextBox.setText(str(_tseg1))
            self.tseg2TextBox.setText(str(_tseg2))
            self.sjwComboBox.setCurrentText(str(_sjw))
           

        interfaceComboBox.activated[str].connect(_interfaceParameters)
        # Define Third Group
        ThirdGridLayout = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        ThirdGridLayout.addSpacing(100)
        ThirdGridLayout.addWidget(close_button)
         
        mainLayout.addWidget(SecondGroupBox, 1, 0)
        mainLayout.addLayout(ThirdGridLayout, 3, 0)
        plotframe.setLayout(mainLayout) 
        self.MenuBar.create_statusBar(childWindow)
        plotframe.setStatusTip("")
        QtCore.QMetaObject.connectSlotsByName(childWindow)                
        #return interfaceComboBox, self.channelSettingsComboBox, self.ipBox
                
    def BusParametersGroupBox(self, mainWindow = None):
        '''
        The window holds all the parameters needed  for the target bus, the CAN bus properties must be configured first[e.g bitrate, sample_point, SJW]
        '''
        # Define subGroup
        self.SubSecondGroupBox = QGroupBox("Bus Parameters")
        SubSecondGridLayout = QGridLayout()

        sjwLabel = QLabel("")
        sjwLabel.setText("SJW:")
        
        self.sjwComboBox = QComboBox()
        self.sjwComboBox.setStatusTip("Synchronization Jump Width, it  adjusts the bit clock by a specific time in 1-4 times the Time Quanta (TQ)")
        sjwItems = ["1", "2", "3", "4"]
        for item in sjwItems: self.sjwComboBox.addItem(item)
        
        bitSpeedLabel = QLabel("")
        bitSpeedLabel.setText("Bit Speed [bit/s]:")
        self.bitSpeedTextBox = QLineEdit("125000")
        self.bitSpeedTextBox.setFixedSize(95, 25) 
                
        sampleLabel = QLabel("")
        sampleLabel.setText("Sample point [%]:")
        self.sampleTextBox = QLineEdit("50")
        self.sampleTextBox.setStatusTip('The location of Sample point in percentage inside each bit period')                  
        
        tseg1Label = QLabel("")
        tseg1Label.setText("tseg1:")
        self.tseg1TextBox = QLineEdit("0")
        self.tseg1TextBox.setStatusTip('Time Segment 1 = [Prop_Seg + Phase_Seg1]')   
        
        tseg2Label = QLabel("")
        tseg2Label.setText("tseg2:")
        self.tseg2TextBox = QLineEdit("0")
        self.tseg2TextBox.setStatusTip('Time Segment2 = [Phase_Seg2]')   
        
        ipLabel = QLabel("ipLabel")
        ipLabel.setText("IP address:")
        
        self.ipBox = QLineEdit('192.168.1.254')
        self.ipBox.setFixedSize(95,25) 

        def _set_bus():
            mainWindow.set_sjw(self.sjwComboBox.currentText())
            mainWindow.set_bitrate(self.bitSpeedTextBox.text())  
            mainWindow.set_sample_point(self.sampleTextBox.text())
            mainWindow.set_tseg1(self.tseg1TextBox.text())
            mainWindow.set_tseg2(self.tseg2TextBox.text())
                    
        set_button = QPushButton("Set in all")
        set_button.setStatusTip('The button will apply the same settings for all CAN controllers')  # show when move mouse to the icon
        set_button.setIcon(QIcon('graphicsUtils/icons/icon_true.png'))
        set_button.clicked.connect(_set_bus)
        set_button.clicked.connect(mainWindow.set_bus_settings)
        
        SubSecondGridLayout.addWidget(sjwLabel, 1, 0)
        SubSecondGridLayout.addWidget(self.sjwComboBox, 1, 1)
        SubSecondGridLayout.addWidget(bitSpeedLabel, 2, 0)
        SubSecondGridLayout.addWidget(self.bitSpeedTextBox, 2, 1)
        SubSecondGridLayout.addWidget(sampleLabel, 3, 0)
        SubSecondGridLayout.addWidget(self.sampleTextBox, 3, 1)
        SubSecondGridLayout.addWidget(tseg1Label, 4, 0)
        SubSecondGridLayout.addWidget(self.tseg1TextBox, 4, 1)
        SubSecondGridLayout.addWidget(tseg2Label, 5, 0)
        SubSecondGridLayout.addWidget(self.tseg2TextBox, 5, 1) 
        SubSecondGridLayout.addWidget(ipLabel, 6, 0)
        SubSecondGridLayout.addWidget(self.ipBox, 6, 1)
        SubSecondGridLayout.addWidget(set_button, 7, 1)            
        self.SubSecondGroupBox.setLayout(SubSecondGridLayout)

              
    def dump_child_window(self, ChildWindow, mainWindow = None):
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
        
        # dump can messages
        mainWindow.initiate_dump_can_timer(5000)
        
        buttonBox = QHBoxLayout()
        close_button = QPushButton("close")
        close_button.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        close_button.clicked.connect(ChildWindow.close)
        buttonBox.addWidget(close_button)
                 
        mainLayout.addWidget(dumpGroupBox , 0, 0)
        mainLayout.addLayout(buttonBox , 2, 0)
        plotframe.setLayout(mainLayout) 
        QtCore.QMetaObject.connectSlotsByName(ChildWindow)
            
    def plot_adc_window(self, adcItems=None, plot_prefix = None, name_prefix = None):
        MenuBar = menu_window.MenuWindow(self)
        MenuBar.create_statusBar(self)
        test_file =output_dir +name_prefix +".csv"
        self.setObjectName("")
        self.setWindowTitle("ADC Plot") 
        w, h = 800, 800
        self.setGeometry(QtCore.QRect(0, 0,w, h))
        #self.setFixedSize(w, h)
        #self.setGeometry(10, 10, 900, 700)
       # self.resize(w, h)
        self.setAcceptDrops(True)
        MainLayout = QGridLayout()
        #Define a frame for that group
        self.plotframe = QFrame()
        self.plotframe.setLineWidth(0.6)
        self.setCentralWidget(self.plotframe)
        #List and label for ADC channel
        adcLayout = QVBoxLayout()
        adcLabel = QLabel(" ")
        adcLabel.setText("ADC channel:")

        self.adcListBox = QListWidget()
        self.adcListBox.setFixedWidth(70)
        
        
        for item in adcItems: self.adcListBox.addItem(item)
        adcLayout.addWidget(adcLabel)
        adcLayout.addWidget(self.adcListBox) 

        adcGroupBox= QGroupBox("")
        self.adcPlotGridLayout =  QGridLayout()

        closeButton = QPushButton("close")
        closeButton.setIcon(QIcon('graphicsUtils/icons/icon_close.jpg'))
        closeButton.setStatusTip('close session')
        closeButton.clicked.connect(self.close)
        
        fileLabel = QLabel("")
        fileLabel.setText("File Name:")
        
        dateLabel = QLabel("" )
        dateLabel.setText("Test Date:")
        
        modifiedLabel = QLabel("")
        modifiedLabel.setText("Last Modified:")
                            
 
        def _activate_adc(b):
            if b.isChecked() == True:
                self.adcListBox.setEnabled(True) 
            else:
                self.adcListBox.setEnabled(False)                    
        directoryButton = QPushButton("")
        directoryButton.setIcon(QIcon('graphicsUtils/icons/icon_open.png'))
        directoryButton.setStatusTip('Select ADC data file [The file should follow a specific standard format]') 
        directoryButton.clicked.connect(lambda: self.get_file(self.filetextbox, output_dir))
        
        self.activeAdcCheckBox = QCheckBox("")
        self.activeAdcCheckBox.setChecked(True)
        self.activeAdcCheckBox.toggled.connect(lambda:_activate_adc(self.activeAdcCheckBox))
            
        test_date =time.ctime(os.path.getmtime(test_file))
        test_modify = time.ctime(os.path.getctime(test_file))

        self.filetextbox = QLineEdit(test_file)
        self.filetextbox.setStyleSheet("background-color: lightgray; border: 1px inset black;")
        self.filetextbox.setReadOnly(True) 
        
        self.datetextbox = QLineEdit(test_date)  
        self.datetextbox.setStyleSheet("background-color: lightgray; border: 1px inset black;")
        self.datetextbox.setReadOnly(True) 
        
        self.modifiedtextbox = QLineEdit(test_modify)
        self.modifiedtextbox.setStyleSheet("background-color: lightgray; border: 1px inset black;")
        self.modifiedtextbox.setReadOnly(True) 
        self.itemSpacer = QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.adcListBox.currentItemChanged.connect(lambda:self.plot_adc_file(plot_prefix)) 
        
        self.adcPlotGridLayout.addWidget(fileLabel,1,0)
        self.adcPlotGridLayout.addWidget(self.filetextbox,1,1) 
        
        self.adcPlotGridLayout.addWidget(directoryButton,1,2) 
                
        self.adcPlotGridLayout.addWidget(dateLabel,2,0)
        self.adcPlotGridLayout.addWidget(self.datetextbox,2,1)
        
        self.adcPlotGridLayout.addWidget(modifiedLabel,3,0)
        self.adcPlotGridLayout.addWidget(self.modifiedtextbox,3,1)        
        self.adcPlotGridLayout.addWidget(self.activeAdcCheckBox,4,0)

        self.adcPlotGridLayout.addLayout(adcLayout,5,0)        
        self.adcPlotGridLayout.addItem(self.itemSpacer,5,1,4,4)
        self.adcPlotGridLayout.addWidget(closeButton,10,4)
        adcGroupBox.setLayout(self.adcPlotGridLayout)

        MainLayout.addWidget(adcGroupBox, 0, 0)
        self.plotframe.setLayout(MainLayout) 
        QtCore.QMetaObject.connectSlotsByName(self) 
    
    def plot_yaml_file(self,yaml_or_yml = "yaml"):
        adc_state = False
        self.filetextboxValue = self.filetextbox.text()
        file_path = os.path.dirname(os.path.realpath(self.filetextboxValue))
        file_name = os.path.basename(self.filetextboxValue)
        
        self.adcPlotGridLayout.removeItem(self.itemSpacer)   
        if "yaml" in  file_name:  
            design = design_diagram.DesignDiagram(file_path =file_path, file_name = file_name[:-5])
            fig_path = design.process_yaml(path=file_path,file_name =file_name[:-5],graphid_name = "MopsHub", file_end = ".yaml")
        else:
            design = design_diagram.DesignDiagram(file_path =file_path, file_name = file_name[:-4])
            fig_path = design.process_yaml(path=file_path,file_name =file_name[:-4],graphid_name = "MopsHub", file_end = ".yml")
        
        fig = QLabel()
        #self.resize(pixmap.width(),pixmap.height())
        pixmap = QPixmap(fig_path)
        fig.setPixmap(pixmap)#.scaled(800,600))
        scroll = QScrollArea()    
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll.setWidgetResizable(True)
        scroll.setFixedSize(800,800)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setWidget(fig)
        self.adcPlotGridLayout.addWidget(scroll,5,1,4,4)
        
    def plot_adc_file(self,plot_prefix = "adc_data"):    
        self.filetextboxValue = self.filetextbox.text()
        self.adcPlotGridLayout.removeItem(self.itemSpacer)
        #to avoid the NonType value in case the user preferred to drag and drop directly
        try:
            adc_value = self.adcListBox.currentItem().text()
        except:
           self.adcListBox.setCurrentRow(0)
           adc_value = self.adcListBox.currentItem().text()
            
        try:
            fig =  plotting_canvas.PlottingCanvas(test_file=self.filetextboxValue, tests=[int(adc_value)], plot_prefix = plot_prefix)
            adc_state = True 
            toolbar = Navi(fig,self.plotframe)
            self.adcPlotGridLayout.addWidget(toolbar,4,1,1,1)
            self.activeAdcCheckBox.setChecked(adc_state)
            self.adcListBox.setEnabled(adc_state)
        except:
            if self.filetextboxValue.endswith('.csv'):
                adc_state = False    
                fig =  plotting_canvas.PlottingCanvas(test_file=self.filetextboxValue, plot_prefix = "trial_plot")
                toolbar = Navi(fig,self.plotframe)
                self.adcPlotGridLayout.addWidget(toolbar,4,1,1,1)                
            elif self.filetextboxValue.endswith('.yaml'):
                adc_state = False
                fig = self.plot_yaml_file(yaml_or_yml = "yaml")     
                   
            elif self.filetextboxValue.endswith('.yml'):
                adc_state = False
                fig = self.plot_yaml_file(yaml_or_yml = "yml")  
            else:
                adc_state = False
                fig = QLabel() 
                pass
            
            self.activeAdcCheckBox.setChecked(adc_state)
            self.adcListBox.setEnabled(adc_state)
        self.adcPlotGridLayout.addWidget(fig,5,1,4,4)
    
    def get_config_file(self, object = None, directory =None):
        file_to_open = QFileDialog.getOpenFileName(directory = directory)[0]#filter = "csv (*.csv)",
        object.setText(file_to_open)
        return file_to_open
        
    def get_file(self,object,directory):
        """ This function will get the address of the csv file location
        """
        file_to_open = self.get_config_file(object,directory)
        if file_to_open.endswith('.csv'):
            self.plot_adc_file()
        else:
            self.plot_yaml_file()    
        return file_to_open
               
    def dragEnterEvent(self, e):
        """
        This function will detect the drag enter event from the mouse on the main window
        """
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()
    
    def dragMoveEvent(self,e):
        """
        This function will detect the drag move event on the main window
        """
        if e.mimeData().hasUrls:
            e.accept()
        else:
            e.ignore()
    
    def dropEvent(self,e):
        """
        This function will enable the drop file directly on to the 
        main window. The file location will be stored in the self.filename
        """
        if e.mimeData().hasUrls:
            e.setDropAction(QtCore.Qt.CopyAction)
            e.accept()
            for url in e.mimeData().urls():
                fname = str(url.toLocalFile())
            test_file = fname
            
            #Update file details into the GUI
            test_date =time.ctime(os.path.getmtime(test_file))
            test_modify = time.ctime(os.path.getctime(test_file))
            self.datetextbox.setText(test_date)
            self.modifiedtextbox.setText(test_modify)
            self.filetextbox.setText(test_file)
            self.plot_adc_file()
        else:
            e.ignore()   
        
    
    def match_client_to_server(self,server_config = None):
        self.logger.notice("Matching Client Configurations to the Server Configurations")
        client_file = server_config.replace("server", "client")
        self.set_client_config_yaml(client_file)
        self.logger.info("Saving Information to the file %s"%client_file)
        return client_file
            
    def get_server_config_yaml(self):
        self.__server_config_yaml =lib_dir+config_dir + "opcua_server_config_cfg.yml"
        return self.__server_config_yaml
            
    def get_client_config_yaml(self):
        self.__client_config_yaml =lib_dir+config_dir + "opcua_client_config_cfg.yml"
        return self.__client_config_yaml
    
    def get_endpoint_url(self):
        self.__endpoint_url = "opc.tcp://localhost.localdomain:4841/"
        return self.__endpoint_url

    def set_endpoint_url(self,x):
        self.__endpoint_url = x

    def set_client_config_yaml(self,x):
        self.__client_config_yaml = x
                
    def set_server_config_yaml(self,x):
        self.__server_config_yaml = x

    def get_ip_address(self):
        self.__ip_address = "opc.tcp://localhost.localdomain:4841/"
        return self.__ip_address

    def set_ip_address(self,x):
        self.__ip_address = x                
if __name__ == "__main__":
    pass
     