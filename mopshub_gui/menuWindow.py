from matplotlib.backends.qt_compat import QtCore, QtWidgets
from PyQt5 import *
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
import logging
from mopshub_gui import mainWindow, childWindow
from canmops.analysisUtils import AnalysisUtils
from canmops.logger import Logger 
from PyQt5.QtWidgets import QMainWindow
import os
import numpy as np
rootdir = os.path.dirname(os.path.abspath(__file__)) 
config_dir = "config/"
lib_dir = rootdir[:-12]
class MenuWindow(QWidget):  
    
    def __init__(self, parent=mainWindow):
        super(MenuWindow, self).__init__(parent)
        self.MainWindow = mainWindow.MainWindow()
        self.logger = Logger().setup_main_logger(name="Menu GUI", console_loglevel=logging.INFO)

    def stop(self):
        return self.MainWindow.stop_server()
    
    def create_device_menuBar(self, mainwindow):
        menuBar = mainwindow.menuBar()
        menuBar.setNativeMenuBar(False)  # only for MacOS   
        self.set_device_settings_menu(menuBar, mainwindow)
        self.set_plotting_menu(menuBar, mainwindow)
        
    def create_opcua_menuBar(self,mainwindow, parent):
        menuBar = mainwindow.menuBar()
        menuBar.setNativeMenuBar(False)  # only for MacOS 
        self.set_file_menu(menuBar, mainwindow)  
        self.set_opcua_settings_menu(menuBar, mainwindow, parent)
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
        exit_action = QAction(QIcon('mopshub_gui/icons/icon_exit.png'), '&Exit', mainwindow)
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
            plottingWindow = childWindow.ChildWindow(parent = self.plotWindow)
            plottingWindow.plot_adc_window(adcItems=[str(k) for k in np.arange(35)],
                                        name_prefix="adc_data_1",
                                        plot_prefix="adc_data")
            plottingWindow.show()
                    
        plotADC = QAction(QIcon('mopshub_gui/icons/icon_curve.png'),'Plot ADC', mainwindow)
        plotADC.setStatusTip("Plot ADC channels")
        plotADC.triggered.connect(show_adc_plotting_window)
        plottingMenu.addAction(plotADC) 

    def set_opcua_settings_menu(self, menuBar, mainwindow, parent):
        settingsMenu = menuBar.addMenu('&Settings')
        self.MainWindow.update_device_box()    
        self.__device = self.MainWindow.get_deviceName()
        conf = AnalysisUtils().open_yaml_file(file=config_dir + self.__device + "_cfg.yml" , directory=lib_dir)
        self.__appIconDir = conf["Application"]["icon_dir"]
                
        def _show_browse_client_child_window():
            self.BrowseClientWindow = QMainWindow()
            BrowseWindow = childWindow.ChildWindow(parent=parent)
            BrowseWindow.browse_client_child_window(self.BrowseClientWindow, conf)
            self.BrowseClientWindow.show()
            
        # def _show_browse_server_child_window():
        #     self.BrowseServerWindow = QMainWindow()
        #     BrowseWindow = childWindow.ChildWindow(parent=self.BrowseServerWindow)
        #     BrowseWindow.browse_server_child_window(self.BrowseServerWindow, conf)
        #     self.BrowseServerWindow.show()
            
        # BrowseServer = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Load Server Configuration', mainwindow)
        # BrowseServer.setStatusTip("Configure OPCUA Server [IP address, server nodes, etc..")
        # BrowseServer.triggered.connect(_show_browse_server_child_window)
        
        BrowseClient = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Server Setting', mainwindow)
        BrowseClient.setStatusTip("Configure OPCUA node browser [IP address, server nodes, etc..")
        BrowseClient.triggered.connect(_show_browse_client_child_window)
        
        # settingsMenu.addAction(BrowseServer)
        settingsMenu.addAction(BrowseClient)
                
    def set_device_settings_menu(self, menuBar, mainwindow):      
        settingsMenu = menuBar.addMenu('&settings')
        self.MainWindow.update_device_box()    
        self.__device = self.MainWindow.get_deviceName()
        conf = AnalysisUtils().open_yaml_file(file=config_dir + self.__device + "_cfg.yml" , directory=lib_dir)
        self.__appIconDir = conf["Application"]["icon_dir"]
        
        def show_edit_device_settings():
            self.NodeWindow = QMainWindow()
            self.edit_device_settings(self.NodeWindow, conf)
            self.NodeWindow.show()
        
        def show_edit_adc():            
            self.adcWindow = QMainWindow()
            self.edit_adc(self.adcWindow, conf)
            self.adcWindow.show()

        DeviceSettings = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Edit Device Settings', mainwindow)
        DeviceSettings.setStatusTip("Add Nodes to the Node menu")
        DeviceSettings.triggered.connect(show_edit_device_settings)

        ADCNodes = QAction(QIcon('graphics_Utils/icons/icon_nodes.png'),'Edit MOPS ADC Settings', mainwindow)
        ADCNodes.setStatusTip("Edit ADC settings [e.g. Parameters]")
        ADCNodes.triggered.connect(show_edit_adc)

        def list_info():
            msg ="<b><h3>CANMoPS:</h3></b> A graphical user interface GUI to read the channels of MOPS chip.<br />"\
            " The package can communicate with a CAN interface and talks CANopen with the connected Controllers."\
            "Currently only CAN interfaces from AnaGate (Ethernet),  Kvaser (USB) and SocketCAN drivers are supported.<br />"\
            "<b>Author</b>: Ahmed Qamesh<br />"\
            "<b>Contact</b>: ahmed.qamesh@cern.ch<br />"\
            "<b>Organization</b>: Bergische Universität Wuppertal<br />"\
            "<b>Gitlab path</b>: <a href='https://gitlab.cern.ch/aqamesh/canmops'>https://gitlab.cern.ch/aqamesh/canmops</a><br />"\
            "<b>Software twiki</b>: <a href='https://gitlab.cern.ch/aqamesh/canmops/-/wikis/home'>https://gitlab.cern.ch/aqamesh/canmops/-/wikis/home</a><br />"
            self.list_device_info(msg)
            
            
        about_action = QAction(QIcon('graphics_Utils/icons/icon_application-settings.png'),'List Bus Info', mainwindow)
        about_action.setStatusTip("List all info about the device")
        about_action.triggered.connect(list_info)
        
        settingsMenu.addAction(about_action)        
        settingsMenu.addAction(DeviceSettings)
        settingsMenu.addAction(ADCNodes)  
        
    # 4. Help menu
    def set_help_main_menu(self, menuBar, mainwindow):
        helpmenu = menuBar.addMenu("&Help")

        about_action = QAction('&About', mainwindow)
        about_action.setStatusTip("About")
        about_action.triggered.connect(self.list_device_info)
        helpmenu.addAction(about_action)
        
    # 5. Interface menu
    def set_interface_menu(self, menuBar, mainwindow):
        interfaceMenu = menuBar.addMenu("&Interface")
        SocketMenu = interfaceMenu.addMenu("&SocketCAN")
        KvaserMenu = interfaceMenu.addMenu("&Kvaser")
        AnagateMenu = interfaceMenu.addMenu("&AnaGate")
        
        # Set the bus
        def _set_socketchannel():
            _arg = "socketcan"
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
                    
        #SetSocketcan = SocketMenu.addMenu('Set CAN Bus')
        
        SetSocketCAN = QAction(QIcon('graphics_Utils/icons/icon_start.png'),'Reset SocketCAN', mainwindow)
        SetSocketCAN.setStatusTip("Set SocketCAN")
        SetSocketCAN.triggered.connect(_set_socketchannel)

        SetVirtualSocketcan = QAction(QIcon('graphics_Utils/icons/icon_start.png'),'Reset Virtual', mainwindow)
        SetVirtualSocketcan.setStatusTip("Set VirtualCAN")
        SetVirtualSocketcan.triggered.connect(_Set_virtual_socketchannel)
        
                    
        SocketMenu.addAction(SetSocketCAN)
        #SetSocketcan.addAction(SetVirtualSocketcan)# to be used later 

        def _restart_kvaserchannel():
            _arg = "restart"
            _interface = "Kvaser"
            self.MainWindow.set_canchannel(arg = _arg, interface = _interface,default_channel =_default_channel)
            
        RestartKvaser = QAction(QIcon('graphics_Utils/icons/icon_reset.png'),'Restart Kvaser Interface', mainwindow)
        RestartKvaser.setStatusTip("Restart Kvaser interface")
        RestartKvaser.triggered.connect(_restart_kvaserchannel)
        
        KvaserMenu.addAction(RestartKvaser)
            
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
            
            
        DumpSocketcan = SocketMenu.addMenu('Dump SocketCAN')
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
        
        
    def create_statusBar(self, mainwindow, msg=" "):
        status = QStatusBar()
        status.showMessage(msg)
        mainwindow.setStatusBar(status)
        

    def list_device_info(self, msg = None, info = "Get Software Info"):
        msgBox = QMessageBox()
        msgBox.setWindowTitle(info) 
        start = "\033[1m"
        end = "\033[0;0m"
        if msg != None:
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
    
    def edit_adc(self, childWindow, conf):
        #check the conf file
        ADCGroup= QGroupBox("ADC details")
        childWindow.setObjectName("Edit ADC settings")
        childWindow.setWindowTitle("ADC Settings")
        #childWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
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
        add_button.setIcon(QIcon('mopshub_gui/icons/icon_add.png'))
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
        clearLayout= QHBoxLayout()  
        clear_button = QPushButton("Clear")
        clear_button.setIcon(QIcon('mopshub_gui/icons/icon_clear.png'))
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
            if (channelListBox.count() != 0 or parameterListBox.count() != 0):
                _adc_channels = [channelListBox.item(x).text() for x in range(channelListBox.count())]
                _parameters = [parameterListBox.item(x).text() for x in range(parameterListBox.count())]
                for i in range(len(_adc_channels)):
                    conf["adc_channels_reg"]["adc_channels"][_adc_channels[i]] = _parameters[i]
                file = config_dir + self.__device + "_cfg.yml"
                AnalysisUtils().dump_yaml_file(file=file,
                                               loaded = conf,
                                               directory=lib_dir)
                self.logger.info("Saving Information to the file %s"%file)
            else:
                self.logger.error("No data to be saved.....")
        add_button.clicked.connect(_add_item)
        clear_button.clicked.connect(_clear_item)
        
        buttonLayout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('mopshub_gui/icons/icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        
        save_button = QPushButton("Save")
        save_button.setIcon(QIcon('mopshub_gui/icons/icon_true.png'))
        save_button.clicked.connect(_save_items)       
        buttonLayout.addWidget(save_button)
        buttonLayout.addWidget(close_button)

        mainLayout.addWidget(ADCGroup , 0,0)
        mainLayout.addLayout(buttonLayout ,1, 0)
        ADCGroup.setLayout(adc_mainLayout)
        plotframe.setLayout(mainLayout) 
        
    def set_socketcan(self,childWindow, arg, interface):
        #check the conf file
        SocketGroup= QGroupBox("Reset SocketCAN ")
        childWindow.setObjectName("Reset SocketCAN ")
        childWindow.setWindowTitle("Reset SocketCAN")
        #childWindow.setWindowIcon(QtGui.QIcon(self.__appIconDir))
        childWindow.setGeometry(200, 200, 100, 100)
        mainLayout = QGridLayout()
        # Define a frame for that group
        plotframe = QFrame()
        plotframe.setLineWidth(0.6)
        childWindow.setCentralWidget(plotframe)
        mainLayout = QGridLayout()
        buttonLayout = QHBoxLayout()  
        _channelPorts =  range(0,8)
        _arg = arg
        _interface = interface

        busComboBox = QComboBox()
        for item in _channelPorts: busComboBox.addItem(str(item))
        
        def _set():
            _default_channel = busComboBox.currentText()
            self.MainWindow.set_canchannel(arg = _arg, interface = _interface,default_channel =_default_channel )        
        add_button = QPushButton("Reset")
        add_button.setIcon(QIcon('mopshub_gui/icons/icon_start.png'))
        add_button.clicked.connect(_set)
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('mopshub_gui/icons/icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        buttonLayout.addWidget(add_button)  
        buttonLayout.addWidget(close_button) 
        mainLayout.addWidget(busComboBox ,0,0)
        mainLayout.addLayout(buttonLayout ,1,0)
        SocketGroup.setLayout(mainLayout)
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
        add_button.setIcon(QIcon('mopshub_gui/icons/icon_add.png'))

        clear_button = QPushButton("Clear")
        clear_button.setIcon(QIcon('mopshub_gui/icons/icon_clear.png'))
                    
        inLayout.addWidget(nodeSpinBox)
        inLayout.addWidget(add_button)
        
        #outputs
        outLayout = QVBoxLayout()
        nodeLabel = QLabel()
        nodeLabel.setText("Added  Nodes [dec]")    
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
        chipIdSpinBox = QSpinBox()
        chipLayout.addWidget(chipIdLabel)
        chipLayout.addWidget(chipIdSpinBox)
        chipLayout.addSpacing(60)

        hardwareLayout = QHBoxLayout()
        hardwareLabel = QLabel()
        hardwareLabel.setText("Resistor ratio")
        hardwareIdSpinBox = QSpinBox()
        hardwareLayout.addWidget(hardwareLabel)
        hardwareLayout.addWidget(hardwareIdSpinBox)
                    
        infoLayout.addLayout(iconLayout)
        infoLayout.addLayout(chipLayout)

        def _add_item():
            node = nodeSpinBox.value()
            nodeListBox.addItem(str(int(node)))
        
        def _clear_item():
            _row = nodeListBox.currentRow()
            nodeListBox.takeItem(_row)
        
        def _save_items():
            if (nodeListBox.count() != 0):
                _nodes = [nodeListBox.item(x).text() for x in range(nodeListBox.count())]
                _chipId = str(chipIdSpinBox.value())
                _resistorRatio = str(hardwareIdSpinBox.value())
                conf["Application"]["nodeIds"] = _nodes
                conf["Application"]["chipId"] = _chipId
                conf["Hardware"]["resistor_ratio"] = _resistorRatio
                file = config_dir + self.__device + "_cfg.yml"
                AnalysisUtils().dump_yaml_file(file=file,
                                               loaded = conf,
                                               directory=lib_dir)
                self.logger.info("Saving Information to the file %s"%file)
            else:
                self.logger.error("No data to be saved.....")
                
        add_button.clicked.connect(_add_item)
        clear_button.clicked.connect(_clear_item)
        buttonLayout = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('mopshub_gui/icons/icon_close.png'))
        close_button.clicked.connect(childWindow.close)
        
        save_button = QPushButton("Save")
        save_button.setIcon(QIcon('mopshub_gui/icons/icon_true.png'))
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
               
if __name__ == "__main__":
    pass
                
