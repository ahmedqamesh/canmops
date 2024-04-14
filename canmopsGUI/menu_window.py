from matplotlib.backends.qt_compat import QtCore, QtWidgets
from PyQt5 import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
import logging
from canmopsGUI import main_gui_window, child_window
from canmops.analysis_utils import AnalysisUtils
from canmops.logger_main import Logger 
from PyQt5.QtWidgets import QMainWindow
import os
import numpy as np
rootdir = os.path.dirname(os.path.abspath(__file__)) 
log_call = Logger(name = " Main  GUI ",console_loglevel=logging.INFO, logger_file = False)

config_dir = "config_files/"
lib_dir = rootdir[:-11]
icon_location='canmopsGUI/icons/'
class MenuWindow(QWidget):  
    
    def __init__(self, parent=main_gui_window):
        super(MenuWindow, self).__init__(parent)
        self.MainWindow = main_gui_window.MainWindow()
        self.logger = log_call.setup_main_logger()
    
    def stop(self):
        return self.MainWindow.stop_server()
    
    def create_device_menuBar(self, mainwindow,device_config):
        menuBar = mainwindow.menuBar()
        menuBar.setNativeMenuBar(False)  # only for MacOS   
        self.set_device_settings_menu(menuBar, mainwindow,device_config)
        self.set_plotting_menu(menuBar, mainwindow)
        
    def create_opcua_menuBar(self,mainwindow,config_yaml):
        menuBar = mainwindow.menuBar()
        menuBar.setNativeMenuBar(False)  # only for MacOS 
        self.set_file_menu(menuBar, mainwindow)  
        self.set_opcua_settings_menu(menuBar, mainwindow,config_yaml)
        self.set_help_main_menu(menuBar, mainwindow)         
       
    
    def create_main_menuBar(self, mainwindow):
        menuBar = mainwindow.menuBar()
        menuBar.setNativeMenuBar(False)  # only for MacOS
        self.set_file_menu(menuBar, mainwindow)
        self.set_interface_menu(menuBar, mainwindow)
        self.set_help_main_menu(menuBar, mainwindow)
        
    # 1. File menu
    def set_file_menu(self, menuBar, mainwindow):
               
        fileMenu = menuBar.addMenu('&File')
        exit_action = QAction(QIcon(icon_location+'icon_exit.png'), '&Exit', mainwindow)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit program')
        exit_action.triggered.connect(self.stop)
        exit_action.triggered.connect(qApp.quit)
        fileMenu.addAction(exit_action)
    
            
    # 1. setting menu
    def set_plotting_menu(self, menuBar, mainwindow):
        plottingMenu = menuBar.addMenu('&plotting')

        def show_adc_plotting_window():
            self.plotWindow = QMainWindow()
            plottingWindow = child_window.ChildWindow(parent = self.plotWindow)
            plottingWindow.plot_adc_window(adcItems=[str(k) for k in np.arange(35)],
                                        name_prefix="adc_data_1",
                                        plot_prefix="adc_data")
            plottingWindow.show()
                    
        plotADC = QAction(QIcon(icon_location+'icon_curve.png'),'Plot ADC', mainwindow)
        plotADC.setStatusTip("Plot ADC channels")
        plotADC.triggered.connect(show_adc_plotting_window)
        plottingMenu.addAction(plotADC) 

    def set_opcua_settings_menu(self, menuBar, mainwindow,config_yaml):      
        settingsMenu = menuBar.addMenu('&settings')
        #self.MainWindow.update_device_box()    
        #self.__device = device#self.MainWindow.get_deviceName()
        conf = AnalysisUtils().open_yaml_file(file= config_yaml , directory=lib_dir)
        self.__appIconDir = conf["Application"]["icon_dir"]
                
        def _show_browse_client_child_window():
            self.BrowseClientWindow = QMainWindow()
            BrowseWindow = child_window.ChildWindow(parent = self.BrowseClientWindow)
            BrowseWindow.browse_client_child_window(self.BrowseClientWindow, conf)
            self.BrowseClientWindow.show()
            
        def _show_browse_server_child_window():
            self.BrowseServerWindow = QMainWindow()
            BrowseWindow = child_window.ChildWindow(parent = self.BrowseServerWindow)
            BrowseWindow.browse_server_child_window(self.BrowseServerWindow ,conf)
            self.BrowseServerWindow.show()
            
        BrowseServer = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Browse Server', mainwindow)
        BrowseServer.setStatusTip("Configure OPCUA Server [IP address, server nodes, etc..")
        BrowseServer.triggered.connect(_show_browse_server_child_window)
        
        BrowseClient = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Browse Client', mainwindow)
        BrowseClient.setStatusTip("Configure OPCUA node browser [IP address, server nodes, etc..")
        BrowseClient.triggered.connect(_show_browse_client_child_window)
        
        settingsMenu.addAction(BrowseServer)
        settingsMenu.addAction(BrowseClient)
                
    def set_device_settings_menu(self, menuBar, mainwindow,device_config):      
        settingsMenu = menuBar.addMenu('&settings')
        conf = AnalysisUtils().open_yaml_file(file=config_dir + device_config + "_config.yml" , directory=lib_dir)
        self.__appIconDir = conf["Application"]["icon_dir"]
        self.__device = conf["Application"]["device_name"].lower()
        def show_edit_device_settings():
            self.NodeWindow = QMainWindow()
            self.edit_device_settings(self.NodeWindow, conf)
            self.NodeWindow.show()
        
        def show_edit_adc():            
            self.adcWindow = QMainWindow()
            self.edit_adc_window(self.adcWindow, conf)
            self.adcWindow.show()

        DeviceSettings = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Edit Device Settings', mainwindow)
        DeviceSettings.setStatusTip("Add Nodes to the Node menu")
        DeviceSettings.triggered.connect(show_edit_device_settings)

        ADCNodes = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Edit MOPS ADC Settings', mainwindow)
        ADCNodes.setStatusTip("Edit ADC settings [e.g. Parameters]")
        ADCNodes.triggered.connect(show_edit_adc)
    
        settingsMenu.addAction(DeviceSettings)
        settingsMenu.addAction(ADCNodes)  
        
    # 4. Help menu
    def set_help_main_menu(self, menuBar, mainwindow):
        helpmenu = menuBar.addMenu("&Help")

        about_action = QAction('&About', mainwindow)
        about_action.setStatusTip("About")
        about_action.triggered.connect(lambda: self.list_device_info(msg = None))
        helpmenu.addAction(about_action)
        
    # 5. Interface menu
    def set_interface_menu(self, menuBar, mainwindow):
        interfaceMenu = menuBar.addMenu("&Interface")
        SocketMenu = interfaceMenu.addMenu("&SocketCAN")
        KvaserMenu = interfaceMenu.addMenu("&Kvaser")
        
        #bus Info
        def list_info(channel =  0, interface = None):
            msg = self.load_bus_settings_file(interface = interface, channel = str(channel))
            self.list_device_info(msg = msg)
        
        # Set the bus
        def _set_socketchannel(arg = "socketcan"):
            _arg = arg
            _interface = "socketcan"
            _default_channel = "0"
            self.socketWindow = QMainWindow()
            self.set_socketcan(self.socketWindow, _arg, _interface)
            self.socketWindow.show()
        
        def _Set_virtual_socketchannel():
            _arg = "virtual"
            _interface = "virtual"
            _default_channel = "0"
            self.MainWindow.set_canchannel(arg = _arg, interface = _interface, default_channel =_default_channel)
                    
        #######################Socketcan settings#############################
        can0_info = QAction('can0', mainwindow)
        can0_info.setStatusTip("can0")
        can0_info.triggered.connect(lambda: list_info(channel = 0, interface = "socketcan"))
        
        can1_info = QAction('can1', mainwindow)
        can1_info.setStatusTip("can1")
        can1_info.triggered.connect(lambda: list_info(channel = 1, interface = "socketcan"))
        
        list_socketinfo_menu = SocketMenu.addMenu('List Bus Info')        
        list_socketinfo_menu.addAction(can0_info)
        list_socketinfo_menu.addAction(can1_info)
                   
        #SetSocketcan = SocketMenu.addMenu('Set CAN Bus')
        
        SetSocketCAN = QAction(QIcon('graphics_Utils/icons/icon_start.png'),'Reset SocketCAN', mainwindow)
        SetSocketCAN.setStatusTip("Set SocketCAN")
        SetSocketCAN.triggered.connect(_set_socketchannel)

        SetVirtualSocketcan = QAction(QIcon('graphics_Utils/icons/icon_start.png'),'Reset Virtual', mainwindow)
        SetVirtualSocketcan.setStatusTip("Set VirtualCAN")
        SetVirtualSocketcan.triggered.connect(_Set_virtual_socketchannel)
        SocketMenu.addAction(SetSocketCAN)
        #SetSocketcan.addAction(SetVirtualSocketcan)# to be used later         
        # Restart the bus
        def _restart_socketchannel():
            _arg = "restart"
            _interface = "socketcan"
            os.system("sudo ip link set can0 type can restart-ms 100")
            #self.MainWindow.set_canchannel(arg = _arg, interface =_interface)
            
        RestartSocketcan = QAction(QIcon('graphics_Utils/icons/icon_reset.png'),'Restart CAN channel', mainwindow)
        RestartSocketcan.setStatusTip("Restart CAN channel")
        RestartSocketcan.triggered.connect(_restart_socketchannel)
        #SocketMenu.addAction(RestartSocketcan)# to be used later 
        
        #Dump Messages in the Bus
        def _dump_can0():
            self.MainWindow.dump_socketchannel(can0.text())

        def _dump_can1():
            self.MainWindow.dump_socketchannel(can1.text())
        
        def _dump_vcan0():
            self.MainWindow.dump_socketchannel(vcan0.text())

        DumpSocketcan = SocketMenu.addMenu('Dump SocketCAN msg')
        can0 = QAction('can0', mainwindow)
        can0.setStatusTip("can0")
        can0.triggered.connect(_dump_can0)
        
        can1 = QAction('can1', mainwindow)
        can1.setStatusTip("can1")
        can1.triggered.connect(_dump_can1)
                
        vcan0 = QAction('vcan0', mainwindow)
        vcan0.setStatusTip("vcan0")
        vcan0.triggered.connect(_dump_vcan0)
        
        DumpSocketcan.addAction(can0)
        DumpSocketcan.addAction(can1)
        #DumpSocketcan.addAction(vcan0)
                   

        #######################Kvaser settings#############################
        can0_kvinfo = QAction('can0', mainwindow)
        can0_kvinfo.setStatusTip("can0")
        can0_kvinfo.triggered.connect(lambda: list_info(channel = 0, interface = "Kvaser"))
        
        can1_kvinfo = QAction('can1', mainwindow)
        can1_kvinfo.setStatusTip("can1")
        can1_kvinfo.triggered.connect(lambda: list_info(channel = 1, interface = "Kvaser"))
        
        list_kvaserinfo_menu = KvaserMenu.addMenu('List Bus Info')        
        list_kvaserinfo_menu.addAction(can0_kvinfo)
        list_kvaserinfo_menu.addAction(can1_kvinfo)
        
        def _restart_kvaserchannel():
            _arg = "restart"
            _interface = "Kvaser"
            _default_channel = 0
            self.MainWindow.set_canchannel(arg = _arg, interface = _interface,default_channel =_default_channel)
            
        RestartKvaser = QAction(QIcon('graphics_Utils/icons/icon_reset.png'),'Restart Kvaser Interface', mainwindow)
        RestartKvaser.setStatusTip("Restart Kvaser interface")
        RestartKvaser.triggered.connect(_restart_kvaserchannel)
        
        KvaserMenu.addAction(RestartKvaser)

    def create_statusBar(self, mainwindow, msg=" "):
        status = QStatusBar()
        status.showMessage(msg)
        mainwindow.setStatusBar(status)
        
                
    def load_bus_settings_file(self, interface = None, channel = None):
        _channel,_ipAddress, _bitrate,_samplePoint, _sjw,_tseg1, _tseg2 = self.MainWindow.load_settings_file(interface = interface, channel = channel) 
        _ipAddress_msg = "<br /><b>IP Address</b>: %s"%(_ipAddress)
        msg ="<b><h3>Bus Info:</h3></b><b>Interface</b>: %s<br /><b>Channel</b>:%s\
         <br /><b>Bitrate</b>: %s<br /><b>SamplePoint</b>: %s<br /><b>SJW</b>:%s\
         <br /><b>tseg1</b>: %s<br /><b>tseg2</b>: %s"%(interface,_channel,_bitrate,_samplePoint,_sjw,_tseg1,_tseg2) 
        return msg
    
    def list_device_info(self, msg = None, info = "Get Software Info"):
        msgBox = QMessageBox()
        msgBox.setWindowTitle(info) 
        if msg == None:
            msg ="<b><h3>CANMoPS:</h3></b> A graphical user interface GUI to read the channels of MOPS chip.<br />"\
            " The package can communicate with a CAN interface and talks CANopen with the connected Controllers."\
            "Currently only CAN interfaces from AnaGate (Ethernet),  Kvaser (USB) and SocketCAN drivers are supported.<br />"\
            "<b>Author</b>: Ahmed Qamesh<br />"\
            "<b>Contact</b>: ahmed.qamesh@cern.ch<br />"\
            "<b>Organization</b>: Bergische Universität Wuppertal<br />"\
            "<b>Gitlab path</b>: <a href='https://gitlab.cern.ch/aqamesh/canmops'>https://gitlab.cern.ch/aqamesh/canmops</a><br />"\
            "<b>Software twiki</b>: <a href='https://gitlab.cern.ch/aqamesh/canmops/-/wikis/home'>https://gitlab.cern.ch/aqamesh/canmops/-/wikis/home</a><br />"
            msgBox.setText(msg);
        else:
            msgBox.setText(msg)
        msgBox.setStandardButtons(QMessageBox.Close)
        msgBox.exec()
    
    def edit_adc_window(self, childWindow, conf):
        #check the conf file
        ADCGroup= QGroupBox("ADC details")
        childWindow.setObjectName("Edit ADC settings")
        childWindow.setWindowTitle("ADC Settings")
        #def_refreshRate = conf["Application"]["refresh_rate"]
        def_adc_channels = list(conf["adc_channels_reg"]["adc_channels"])
        childWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        childWindow.setGeometry(200, 200, 100, 100)
        mainLayout = QGridLayout()
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        #ADC part
        adcLayout= QHBoxLayout()
        channelLabel = QLabel("")
        channelLabel.setText("ADC channel")
        adcComboBox = QComboBox()
        adc_items =np.arange(3,35)
        for item in adc_items: adcComboBox.addItem(str(item))
        adcLayout.addWidget(channelLabel)
        adcLayout.addWidget(adcComboBox)   
        
        #parameters part
        parameterLayout= QHBoxLayout()
        parameterLabel = QLabel("")
        parameterLabel.setText("Parameter")
        parametersComboBox = QComboBox()
        parameter_items =["T","V"]
        for item in parameter_items: parametersComboBox.addItem(str(item))
        parameterLayout.addWidget(parameterLabel)
        parameterLayout.addWidget(parametersComboBox)                           
          
        adc_mainLayout= QVBoxLayout()
        #Inputs        
        inLayout = QVBoxLayout()  
        addLayout= QHBoxLayout()  
        add_button = QPushButton("Add")
        add_button.setIcon(QIcon(icon_location+'icon_add.png'))
        addLayout.addSpacing(80)
        addLayout.addWidget(add_button)
        
        outLabel = QLabel()
        outLabel.setText("Edited settings")                
        inLayout.addLayout(adcLayout)
        inLayout.addLayout(parameterLayout)
        inLayout.addLayout(addLayout)
        inLayout.addWidget(outLabel)
        #outputs
        outLayout = QHBoxLayout()
        channelListBox = QListWidget()
        fullListBox = QListWidget()
        parameterListBox = QListWidget()
        #set the default values
        for i in range(len(def_adc_channels)):
            def_channel =str(i+3)
            def_parameter = conf["adc_channels_reg"]["adc_channels"][def_adc_channels[i]]
            channelListBox.addItem(def_channel)
            parameterListBox.addItem(def_parameter)
            fullListBox.addItem(def_channel+" : "+def_parameter)
            
        clearLayout= QHBoxLayout()  
        clear_button = QPushButton("Clear")
        clear_button.setIcon(QIcon(icon_location+'icon_clear.png'))
        clearLayout.addSpacing(80)
        clearLayout.addWidget(clear_button)
        outLayout.addWidget(fullListBox)
        
        
        adc_mainLayout.addLayout(inLayout)
        adc_mainLayout.addLayout(outLayout)       
        adc_mainLayout.addLayout(clearLayout)

        def _add_item():
            adc_channel = adcComboBox.currentText()
            parameter_channel = parametersComboBox.currentText()
            channelListBox.addItem(adc_channel)
            parameterListBox.addItem(parameter_channel)
            fullListBox.addItem(adc_channel+" : "+parameter_channel)
        
        def _clear_item():
            _row = channelListBox.currentRow()
            _parameter_channel = parameterListBox.currentRow()
            _full = fullListBox.currentRow()
            channelListBox.takeItem(_row)
            parameterListBox.takeItem(_parameter_channel)
            fullListBox.takeItem(_full)
            
        def _save_items():
            #_refreshRate = refreshLineEdit.text()
            #conf["Application"]["refresh_rate"] = _refreshRate 
            if (channelListBox.count() != 0 or parameterListBox.count() != 0):
                _adc_channels = [channelListBox.item(x).text() for x in range(channelListBox.count())]
                _parameters = [parameterListBox.item(x).text() for x in range(parameterListBox.count())]
                for i in range(len(_adc_channels)):
                    conf["adc_channels_reg"]["adc_channels"][_adc_channels[i]] = _parameters[i]
                file = config_dir + self.__device + "_config.yml"
                AnalysisUtils().dump_yaml_file(file=file,
                                               loaded = conf,
                                               directory=lib_dir)
                self.logger.info("Saving Information to the file %s"%file)
            else:
                self.logger.error("No ADC Info to be saved.....")
        add_button.clicked.connect(_add_item)
        clear_button.clicked.connect(_clear_item)
       
               
        # refreshLayout = QHBoxLayout()
        # refreshLabel = QLabel()
        # refreshLabel.setText("Refresh Rate:")
        # refreshLineEdit = QLineEdit()
        # refreshLineEdit.setFixedSize(70, 25)
        # refreshLineEdit.setText(str(def_refreshRate))
        # refreshLayout.addWidget(refreshLabel)
        # refreshLayout.addWidget(refreshLineEdit)
         
        buttonLayout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon(icon_location+'icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        
        save_button = QPushButton("Save")
        save_button.setIcon(QIcon(icon_location+'icon_true.png'))
        save_button.clicked.connect(_save_items)       
        buttonLayout.addWidget(save_button)
        buttonLayout.addWidget(close_button)

        mainLayout.addWidget(ADCGroup , 0,0)
        #mainLayout.addLayout(refreshLayout,1,0)
        mainLayout.addLayout(buttonLayout ,1, 0)
        ADCGroup.setLayout(adc_mainLayout)
        plotframe.setLayout(mainLayout) 

    def edit_device_settings(self, childWindow, conf):
        #check the conf file
        NodeGroup= QGroupBox("Node Info")
        ChipGroup= QGroupBox("Chip Info")
        HardwareGroup= QGroupBox("Hardware Info")
        self.__appIconDir = conf["Application"]["icon_dir"]
        childWindow.setObjectName("Edit Device Settings")
        childWindow.setWindowTitle("Edit Device Settings")
        childWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        childWindow.setGeometry(200, 200, 100, 100)
        def_chipId = conf["Application"]["chipId"]
        def_resistorRatio = conf["Hardware"]["resistor_ratio"]
        mainLayout = QGridLayout()
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        
        nodeLayout= QVBoxLayout()
        #Inputs
        inLayout = QHBoxLayout()  
        nodeSpinBox = QSpinBox()
        
        add_button = QPushButton("Add")
        add_button.setIcon(QIcon(icon_location+'icon_add.png'))

        clear_button = QPushButton("Clear")
        clear_button.setIcon(QIcon(icon_location+'icon_clear.png'))
                    
        inLayout.addWidget(nodeSpinBox)
        inLayout.addWidget(add_button)
        
        #outputs
        outLayout = QVBoxLayout()
        nodeLabel = QLabel()
        nodeLabel.setText("Added Nodes [dec]")    
        nodeListBox = QListWidget()
        outLayout.addWidget(nodeLabel)
        outLayout.addWidget(nodeListBox)
        outLayout.addWidget(clear_button)
        
        nodeLayout.addLayout(inLayout)
        nodeLayout.addLayout(outLayout)       
        #Icon
        infoLayout = QVBoxLayout()
        
        iconLayout = QHBoxLayout()
        icon = QLabel(self) 
        pixmap = QPixmap(self.__appIconDir)
        icon.setPixmap(pixmap.scaled(100, 100))
        iconLayout.addSpacing(30)
        iconLayout.addWidget(icon)    
        
        chipLayout = QHBoxLayout()
        chipIdLabel = QLabel()
        chipIdLabel.setText("Chip Id:")
        chipIdLineEdit = QLineEdit()
        chipIdLineEdit.setText(def_chipId)
        chipLayout.addWidget(chipIdLabel)
        chipLayout.addWidget(chipIdLineEdit)
        chipLayout.addSpacing(60)

        hardwareLayout = QHBoxLayout()
        hardwareLabel = QLabel()
        hardwareLabel.setText("Resistor ratio")
        hardwareLineEdit = QLineEdit()
        
        hardwareLineEdit.setText(def_resistorRatio)
        hardwareLayout.addWidget(hardwareLabel)
        hardwareLayout.addWidget(hardwareLineEdit)
                    
        infoLayout.addLayout(iconLayout)
        infoLayout.addLayout(chipLayout)

        def _add_item():
            node = nodeSpinBox.value()
            nodeListBox.addItem(str(int(node)))
        
        def _clear_item():
            _row = nodeListBox.currentRow()
            nodeListBox.takeItem(_row)
        
        def _save_items():
            _chipId = str(chipIdLineEdit.text())
            _resistorRatio = str(hardwareLineEdit.text())
            conf["Application"]["chipId"] = _chipId
            conf["Hardware"]["resistor_ratio"] = _resistorRatio
            if (nodeListBox.count() != 0):
                _nodes = [nodeListBox.item(x).text() for x in range(nodeListBox.count())]
                conf["Application"]["nodeIds"] = _nodes
                file = config_dir + self.__device + "_config.yml"
                AnalysisUtils().dump_yaml_file(file=file,
                                               loaded = conf,
                                               directory=lib_dir)
                self.logger.info("Saving Information to the file %s"%file)
            else:
                self.logger.error("No Node Info to be saved.....")
                
        add_button.clicked.connect(_add_item)
        clear_button.clicked.connect(_clear_item)
        buttonLayout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon(icon_location+'icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        
        save_button = QPushButton("Save")
        save_button.setIcon(QIcon(icon_location+'icon_true.png'))
        save_button.clicked.connect(_save_items)       
        buttonLayout.addWidget(save_button)
        buttonLayout.addWidget(close_button)

        mainLayout.addWidget(NodeGroup , 0, 0,1,1)
        mainLayout.addWidget(ChipGroup, 0, 1,1,1)
        mainLayout.addWidget(HardwareGroup,1,1,1,1)
        mainLayout.addLayout(buttonLayout ,2, 1)
        NodeGroup.setLayout(nodeLayout)
        ChipGroup.setLayout(infoLayout)
        HardwareGroup.setLayout(hardwareLayout)
        plotframe.setLayout(mainLayout) 

                   
    def set_socketcan(self,childWindow, arg, interface):
        #check the conf file
        SocketGroup= QGroupBox("Reset SocketCAN ")
        childWindow.setObjectName("Reset SocketCAN ")
        childWindow.setWindowTitle("Reset SocketCAN")
        childWindow.setGeometry(200, 200, 100, 100)
        mainLayout = QGridLayout()
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        mainLayout = QGridLayout()
        buttonLayout = QHBoxLayout()  
        _channelPorts =  range(0,2)
        _arg = arg
        _interface = interface
        msg =  self.load_bus_settings_file(interface = _interface, channel = str(0)) 
        VLayout = QVBoxLayout()
        busInfoBox = QTextEdit()
        busInfoBox.setStyleSheet("background-color: white; border: 2px inset black; min-height: 150px; min-width: 400px;")
        busInfoBox.LineWrapMode(1)
        busInfoBox.setReadOnly(True)      
        busInfoBox.setText(msg)  
        VLayout.addWidget(busInfoBox)
        busComboBox = QComboBox()
        busComboBox.addItem("")
        for item in _channelPorts: busComboBox.addItem(str(item))
        
        def _busComboBox_changed():
            channel = busComboBox.currentText()
            msg =  self.load_bus_settings_file(interface = _interface, channel = channel) 
            busInfoBox.setText(msg)  
        
        def _set():
            _default_channel = busComboBox.currentText()
            self.MainWindow.set_canchannel(arg = _arg, interface = _interface,default_channel =_default_channel )        
        
        busComboBox.currentTextChanged.connect(_busComboBox_changed)
        add_button = QPushButton("Reset")
        add_button.setIcon(QIcon(icon_location+'icon_start.png'))
        add_button.clicked.connect(_set)
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon(icon_location+'icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        buttonLayout.addWidget(add_button)  
        buttonLayout.addWidget(close_button) 
        mainLayout.addLayout(VLayout,0,0)
        mainLayout.addWidget(busComboBox ,1,0)
        mainLayout.addLayout(buttonLayout ,2,0)
        SocketGroup.setLayout(mainLayout)
        plotframe.setLayout(mainLayout) 
                     

               
if __name__ == "__main__":
    pass
                