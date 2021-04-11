from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from graphicsUtils import mainWindow
import os

class MenuBar(QWidget):  
    
    def __init__(self, parent=mainWindow):
        super(MenuBar, self).__init__(parent)
        self.MainWindow = mainWindow.MainWindow()

    def stop(self):
        return self.MainWindow.stop_server()
           
    def create_menuBar(self, mainwindow):
        menuBar = mainwindow.menuBar()
        menuBar.setNativeMenuBar(False)  # only for MacOS
        self._fileMenu(menuBar, mainwindow)
        #self._viewMenu(menuBar, mainwindow)
        self._interfaceMenu(menuBar, mainwindow)
        self._helpMenu(menuBar, mainwindow)
        
    # 1. File menu
    def _fileMenu(self, menuBar, mainwindow):
               
        fileMenu = menuBar.addMenu('&File')
        exit_action = QAction(QIcon('graphicsUtils/icons/icon_exit.png'), '&Exit', mainwindow)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit program')
        # exit_action.triggered.connect(self.stop)
        exit_action.triggered.connect(qApp.quit)
        fileMenu.addAction(exit_action)
    
    # 1. View menu
    def _viewMenu(self, menuBar, mainwindow):
               
        viewMenu = menuBar.addMenu('&View')
        view_action = QAction(QIcon('graphicsUtils/icons/icon_view.png'), '&View', mainwindow)
        view_action.setShortcut('Ctrl+V')
        view_action.setStatusTip('Exit program')
        # exit_action.triggered.connect(self.stop)
        #view_action.triggered.connect(qApp.quit)
        viewMenu.addAction(view_action)
        
    # 4. Help menu
    def _helpMenu(self, menuBar, mainwindow):
        helpmenu = menuBar.addMenu("&Help")

        about_action = QAction('&About', mainwindow)
        about_action.setStatusTip("About")
        about_action.triggered.connect(self.about)
        helpmenu.addAction(about_action)
        
    # 5. Interface menu
    def _interfaceMenu(self, menuBar, mainwindow):
        interfaceMenu = menuBar.addMenu("&Interface")
        SocketMenu = interfaceMenu.addMenu("&SocketCAN")
        KvaserMenu = interfaceMenu.addMenu("&Kvaser")
        AnagateMenu = interfaceMenu.addMenu("&AnaGate")
        
        # Set the bus
        def _set_socketchannel():
            _arg = "socketcan"
            _interface = "socketcan"
            self.MainWindow.set_socketchannel(arg = _arg, interface = _interface)
        
        def _Set_virtual_socketchannel():
            _arg = "virtual"
            _interface = "virtual"
            self.MainWindow.set_socketchannel(arg = _arg, interface = _interface)
                    
        #SetSocketcan = SocketMenu.addMenu('Set CAN Bus')
        
        SetNativeInterface = QAction(QIcon('graphics_Utils/icons/icon_start.png'),'Set SocketCAN', mainwindow)
        SetNativeInterface.setStatusTip("Set SocketCAN")
        SetNativeInterface.triggered.connect(_set_socketchannel)

        SetVirtualSocketcan = QAction(QIcon('graphics_Utils/icons/icon_start.png'),'Set Virtual', mainwindow)
        SetVirtualSocketcan.setStatusTip("Set VirtualCAN")
        SetVirtualSocketcan.triggered.connect(_Set_virtual_socketchannel)
                
        SocketMenu.addAction(SetNativeInterface)
        #SetSocketcan.addAction(SetVirtualSocketcan)# to be used later 
        
        # Restart the bus
        def _restart_socketchannel():
            _arg = "restart"
            _interface = "socketcan"
            os.system("sudo ip link set can0 type can restart-ms 100")
            #self.MainWindow.set_socketchannel(arg = _arg, interface =_interface)
            
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
        
    def about(self):
        QMessageBox.about(self, "About", "CANMoPS is a graphical user interface GUI to read the channels of MOPS chip.\n"+
                                         " The package can communicate with a CAN interface and talks CANopen with the connected Controllers. Currently only CAN interfaces from AnaGate (Ethernet),  Kvaser (USB) and SocketCAN drivers are supported.\n"+
                                         "Author: Ahmed Qamesh\n"+
                                         "Contact: ahmed.qamesh@cern.ch\n"+
                                         "Organization: Bergische Universität Wuppertal")
 
        
if __name__ == "__main__":
    pass
                
