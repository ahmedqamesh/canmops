from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from PyQt5 import QtGui
import numpy as np
import os
import time
import csv
import binascii
import yaml
import logging
import sys
try:
    from canmopsGUI          import menu_window, mops_child_window, data_monitoring
    from canmops.analysis       import Analysis
    from canmops.logger_main    import Logger 
    from canmops.analysis_utils  import AnalysisUtils
    from canmops.mops_readout_thread import READMops
except:
    pass

log_format = '%(log_color)s[%(levelname)s]  - %(name)s -%(message)s'
log_call = Logger(log_format = log_format,name = " NET.  GUI ",console_loglevel=logging.INFO, logger_file = False)

rootdir = os.path.dirname(os.path.abspath(__file__)) 
lib_dir = rootdir[:-13]
config_dir = "config/"
config_yaml =config_dir + "mops_config.yml" 

class MultiDeviceWindow(QWidget): 
    def __init__(self, console_loglevel=logging.INFO):
       super(MultiDeviceWindow, self).__init__(None)
       self.logger = log_call.setup_main_logger()
       self.MenuBar = menu_window.MenuWindow(self)
       self.MOPSChildWindow = mops_child_window.MopsChildWindow(self, opcua_config="MOPS_Net_cfg.yaml")
       self.DataMonitoring = data_monitoring.DataMonitoring(self)
       self.update_opcua_config_box()
       # get Default info 
       self.__bus_num = 4
       self.__mops_num = 4

    def update_opcua_config_box(self):
        self.mops_net = AnalysisUtils().open_yaml_file(file=config_dir + "MOPS_Net_cfg.yaml", directory=lib_dir)

    def Ui_ApplicationWindow(self):
        self.mopshubWindow = QMainWindow()
        self.mops_multi_window(childWindow=self.mopshubWindow)
        self.mopshubWindow.show()
        self.initiate_mopshub_timer()
        
    def update_device_box(self):
        '''
        The function Will update the configured device section with the registered devices according to the file main_cfg.yml
        '''
        conf = AnalysisUtils().open_yaml_file(file=config_dir + config_yaml, directory=lib_dir)
        mops_child = mops_child_window.MopsChildWindow()
        deviceName, version, icon_dir,nodeIds, self.__dictionary_items, self.__adc_channels_reg,\
        self.__adc_index, self.__chipId, self.__index_items, self.__conf_index, self.__mon_index, self.__resistor_ratio, self.__refresh_rate, self.__ref_voltage   = mops_child.configure_devices(conf)       
    
    def initiate_adc_timer(self, period=None, mops=None, port=None):
        '''
        The function will  update the GUI with the ADC data ach period in ms.
        '''  
        self.ADCDummytimer = QtCore.QTimer(self)
        self.logger.notice("Reading ADC data...")
        self.__monitoringTime = time.time()         
        self.ADCDummytimer.setInterval(period)
        self.ADCDummytimer.timeout.connect(lambda: self.read_adc_channels(int(port),int(mops)))
        self.ADCDummytimer.start()

    def stop_adc_timer(self):
        '''
        The function will  stop the adc_timer.
        '''        
        try:
            self.ADCDummytimer.stop()
            self.logger.notice("Stopping ADC data reading...")
        except Exception:
            pass
                
    def initiate_mopshub_timer(self, period=1000):
        '''
        The function will  update the GUI with the ADC data ach period in ms.
        '''  
        self.NetDummytimer = QtCore.QTimer(self)
        self.logger.notice("Reading ADC data...")
        self.__monitoringTime = time.time()
        # A possibility to save the data into a file
        self.logger.notice("Preparing an output file [%s.csv]..." % (lib_dir + "output_data/opcua_data"))
        self.out_file_csv = AnalysisUtils().open_csv_file(outname="opcua_data", directory=lib_dir + "output_data") 
        
        # Write header to the data
        fieldnames = ['Time', 'Channel', "nodeId", "ADCChannel", "ADCData" , "ADCDataConverted"]
        writer = csv.DictWriter(self.out_file_csv, fieldnames=fieldnames)
        writer.writeheader()            
        
        self.NetDummytimer.setInterval(period)
       # self.NetDummytimer.timeout.connect(self.set_adc_cic)
        self.NetDummytimer.start()

    def stop_mopshub_timer(self):
        '''
        The function will  stop the adc_timer.
        '''        
        try:
            self.NetDummytimer.stop()
            self.logger.notice("Stopping NET timer...")
        except Exception:
            pass
            
    def mops_multi_window(self, childWindow):
        # create MenuBar
        self.MenuBar = menu_window.MenuWindow(childWindow)
        self.MenuBar.create_opcua_menuBar(childWindow)
        
        childWindow.setObjectName("OPCUA servers")
        childWindow.setWindowTitle("OPCUA servers")
        childWindow.setWindowIcon(QtGui.QIcon("canmopsGUI/icons/icon_opcua.png"))
        childWindow.adjustSize()    
        bus_num = self.__bus_num
        mops_num = self.__mops_num
        plotframe = QFrame()  
        childWindow.setCentralWidget(plotframe)
        mopshubGridLayout = QGridLayout()
        #  Prepare a group window
        self.en_button          = [k for k in np.arange(bus_num)] 
        self.statusBoxVar       = [k for k in np.arange(bus_num)]
        self.bus_alarm_led      = [k for k in np.arange(bus_num)]
       
        self.channelValueBox    = [[ch for ch in np.arange(mops_num)]] * bus_num
        self.trendingBox        = [[ch for ch in np.arange(mops_num)]] * bus_num
        self.monValueBox        = [[ch for ch in np.arange(mops_num)]] * bus_num
        self.confValueBox       = [[ch for ch in np.arange(mops_num)]] * bus_num
        self.mops_alarm_led     = [[m  for m  in np.arange(mops_num)]] * bus_num
    
        NetGridLayout = QGridLayout()
        
        self.mops_alarm_led = self.get_bus_mops_led(bus_num = bus_num)
        for b in np.arange(bus_num): 
            BusGroupBox = QGroupBox("Port " + str(b))
            BusGroupBox.setStyleSheet("QGroupBox { font-weight: bold;font-size: 10px; background-color: #eeeeec; } ")
            self.en_button[b], self.bus_alarm_led[b], self.statusBoxVar[b] = self.def_bus_variables(b = b)
            BusGridLayout = self.def_bus_frame(b)
            BusGroupBox.setLayout(BusGridLayout)
            NetGridLayout.addWidget(BusGroupBox,0, b, 1, 1)

        mopshubGridLayout.addLayout(NetGridLayout, 0, 0)
        # Prepare a log window
        self.textOutputWindow()        

        #close button
        buttonLayout = QHBoxLayout() 
        buttonLayout.addSpacing(800)
        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('canmopsGUI/icons/icon_close.png'))
        close_button.clicked.connect(self.stop_opcua)
        
        buttonLayout.addWidget(close_button)
        mopshubGridLayout.addWidget(self.textGroupBox, 1, 0, 1, 1)
        mopshubGridLayout.addLayout(buttonLayout, 2,0)
        plotframe.setLayout(mopshubGridLayout)
        self.MenuBar.create_statusBar(childWindow)
        QtCore.QMetaObject.connectSlotsByName(childWindow)

    def stop_opcua(self):

        self.logger.warning('Stopping the main OPCUA client')
        self.stop_adc_timer()
        self.stop_mopshub_timer()
        
        self.logger.warning('Closing the GUI.')
        sys.exit()

    def def_bus_variables(self, b):  
        icon = QIcon()
        icon.addPixmap(QPixmap('canmopsGUI/icons/icon_connect.jpg'), QIcon.Normal, QIcon.On)
        icon.addPixmap(QPixmap('canmopsGUI/icons/icon_disconnect.jpg'), QIcon.Normal, QIcon.Off)
        #for b in np.arange(bus_num):
        en_button = QPushButton("")
        en_button.setIcon(icon)
        en_button.setStatusTip("b" + str(b))
        en_button.setObjectName("b" + str(b))
        en_button.setCheckable(True)
        en_button.clicked.connect(lambda: self.set_bus_enable(b))

        bus_alarm_led = self.def_alert_leds(bus_alarm=True, mops=None, icon_state=False)     
        statusBoxVar= QLineEdit()
        statusBoxVar.setStyleSheet("background-color: white; border: 1px inset black;")
        statusBoxVar.setReadOnly(True) 
        statusBoxVar.setFixedWidth(40)
        statusBoxVar.setText("OFF")              
        
        return en_button, bus_alarm_led, statusBoxVar

       
    def def_bus_frame(self, b): 
        icon = QIcon()
        icon.addPixmap(QPixmap('canmopsGUI/icons/icon_connect.jpg'), QIcon.Normal, QIcon.On)
        icon.addPixmap(QPixmap('canmopsGUI/icons/icon_disconnect.jpg'), QIcon.Normal, QIcon.Off)
        BusGridLayout = QGridLayout()  
        StatLayout = QGridLayout()  
        mopsBottonLayout = self.def_mops_frame(0,b)
       
        statusLabelVar = QLabel()
        statusLabelVar.setStyleSheet("QLabel { font-weight: font-size: 8px; background-color:  #eeeeec; } ") 
        statusLabelVar.setText("Bus Status:")   
        
        itemSpacer = QSpacerItem(50, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)            
        StatLayout.addWidget(statusLabelVar, b, 0)
        StatLayout.addWidget(self.statusBoxVar[b], b, 1)
        StatLayout.addWidget(self.bus_alarm_led[b], b, 2)
        StatLayout.addWidget(self.en_button[b], b, 3)   
        StatLayout.addItem(itemSpacer, b, 4) 
        
        BusGridLayout.addLayout(StatLayout, 0, 0, 1, 1)
        BusGridLayout.addLayout(mopsBottonLayout, 1, 0, 1, 1)
        return BusGridLayout

    
    def def_alert_leds(self, bus_alarm=None, mops_alarm=None, mops=None, bus = None, icon_state=False):
        if mops_alarm is True:
            icon_red = "canmopsGUI/icons/icon_disconnected_device.png" #icon_red.gif"
            icon_green = "canmopsGUI/icons/icon_green.gif"
            if icon_state:
                alarm_led = QMovie(icon_green)
            else: 
               alarm_led = QMovie(icon_red)    
            alarm_led.setScaledSize(QSize().scaled(20, 20, Qt.KeepAspectRatio)) 
            alarm_led.start()
            return alarm_led         
        
        if bus_alarm is True:
            icon_red = "canmopsGUI/icons/icon_red.png"
            icon_green = "canmopsGUI/icons/icon_green.png"
            alarm_led = QLabel() 
            if icon_state:
                pixmap = QPixmap(icon_green)
            else: 
                pixmap = QPixmap(icon_red)    
            alarm_led.setPixmap(pixmap.scaled(20, 20))            
            return alarm_led
        
    def def_mops_frame(self, c, b):
        # # Details for each MOPS
        mops_num = 4
        icon_mops = 'canmopsGUI/icons/icon_mops.png'
        mopsBotton = [k for k in np.arange(mops_num)] 
        mopsBottonLayout = QGridLayout()
        self.update_device_box()
        for m in np.arange(mops_num):
            status = self.check_dut(b, m)
            mopsBotton[m] = QPushButton("  [" + str(m) + "]")
            mopsBotton[m].setObjectName("C" + str(c) + "M" + str(m) + "P" + str(b))
            mopsBotton[m].setIcon(QIcon(icon_mops))
            mopsBotton[m].setStatusTip(" MOPS No." + str(m) + " Port No." + str(b))
            mopsBotton[m].clicked.connect(self.get_mops_device)
            if status:        
                pass
            else:
                mopsBotton[m].setEnabled(False)   
            mopsBottonLayout.addWidget(self.mops_alarm_led[b][m], m + 3, 0)
            mopsBottonLayout.addWidget(mopsBotton[m], m + 3, 1) 
        return mopsBottonLayout
    
    def get_bus_mops_led(self,bus_num =     None):
        bus_mops_leds =  [[k for k in np.arange(bus_num)]]*self.__mops_num
        for b in np.arange(bus_num):
            bus_mops_leds[b] = self.def_mops_led(b,0)
        return bus_mops_leds
    
    def def_mops_led(self,b,c):
        mops_num = self.__mops_num
        mops_led = [k for k in np.arange(mops_num)]
        for m in np.arange(mops_num):
            mops_led[m] = QLabel()
            status = self.check_dut(b, m)
            mops_alarm_led = self.def_alert_leds(mops_alarm=True, mops=m, bus = b, icon_state=status)   
            mops_led[m].setMovie(mops_alarm_led)    
        return mops_led 
                                            
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
            
    # show windows
    def show_deviceWindow(self, mops=None, port=None):
        #Fix thread issue        
        mops_readout = READMops(None, None, port, int(mops), None, parent=self)
        #mops_readout.start()
        
        deviceWindow = QMainWindow(self)
        _device_name = "Port:"+port+", MOPS:"+mops
        adc_channels_num = 33
        readout_thread = None
        self.channelValueBox[int(port)][int(mops)], \
        self.trendingBox[int(port)][int(mops)] , \
        self.monValueBox[int(port)][int(mops)] , \
        self.confValueBox[int(port)][int(mops)], _ = self.MOPSChildWindow.device_child_window(deviceWindow,  
                                                                                               device=_device_name, 
                                                                                               cic=str(0), 
                                                                                               mops=mops, 
                                                                                               port=port, 
                                                                                               mainWindow = self, 
                                                                                               readout_thread=readout_thread)

        self.graphWidget = self.DataMonitoring.initiate_trending_figure(n_channels=adc_channels_num)    
        self.initiate_adc_timer(period = 500, mops=mops, port=port)
        deviceWindow.show()

    # Action windows     
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
        self.textBox.append(mode + msg)
    
    def clear_textBox_message(self):
         self.textBox.clear()
        
    def check_dut(self, b, m):
        try:
            port_num = self.mops_net["Port " + str(b)]["MOPS " + str(m)]["Port"]
            if port_num == b:
                status = True
            else:
                status = False
                msg = "MOPS " + str(m), "Port " + str(b), ": Not Found"
                self.set_textBox_message(comunication_object = "ErrorFrame" , msg = str(msg)) 
        except:
            status = False
        return status

    def set_bus_enable(self, b):
        sender = self.sender().objectName()
        print(sender, "is clicked")
        en_button_check = self.en_button[int(b)].isChecked()
        if en_button_check:
            print("Checked")
            self.update_bus_status_box(port_id=b, on=True)
        else:
            self.update_bus_status_box(port_id=b, off=True)

    def set_adc_cic(self):
        for b in np.arange(self.__bus_num):
            for ch in np.arange(5):
                adc_value = np.random.randint(0, 100)
                self.adc_text_box[b][ch].setText(str(adc_value))
                # This will be used later for limits 
                if adc_value >= 90:
                    self.update_alarm_limits(high=True, object=self.adc_text_box[b][ch]) 
                if adc_value <= 5:
                    self.update_alarm_limits(low=True, object=self.adc_text_box[b][ch]) 
                else:
                    self.update_alarm_limits(normal=True, object=self.adc_text_box[b][ch])

    def update_alarm_limits(self, high=None, low=None, normal=None, object=None):
        if high:
            object.setStyleSheet(" background-color: red;")
        if low: 
            object.setStyleSheet(" background-color: yellow;")
        if normal: 
            object.setStyleSheet("color: black;")
        else:
            pass  
                
    def update_bus_status_box(self, port_id=None, on=False, off=False):
        icon_red = "canmopsGUI/icons/icon_red.png"
        icon_green = "canmopsGUI/icons/icon_green.png" 
        if on:
            pixmap = QPixmap(icon_green)
            self.statusBoxVar[int(port_id)].setText("ON")
            self.en_button[int(port_id)].setChecked(True)
            self.bus_alarm_led[int(port_id)]
        else:
            pixmap = QPixmap(icon_red)
            self.statusBoxVar[int(port_id)].setText("OFF")
            self.en_button[int(port_id)].setChecked(False)
            self.bus_alarm_led[int(port_id)]
        self.bus_alarm_led[int(port_id)].setPixmap(pixmap.scaled(20, 20))   
            
    def update_alarm_status(self, on=False, off=False, warning=False, button=None, button_type = "Movie"):
     
        if button_type == "Movie":
            icon_red = "canmopsGUI/icons/icon_red_alarm.gif"
            icon_green = "canmopsGUI/icons/icon_green.gif"
            icon_yellow = "canmopsGUI/icons/icon_yellow.gif"  
        
            if on: 
                alarm_led = QMovie(icon_green)
            if off:
               alarm_led = QMovie(icon_red) 
            if warning:
               alarm_led = QMovie(icon_yellow) 
            alarm_led.setScaledSize(QSize().scaled(20, 20, Qt.KeepAspectRatio)) 
            alarm_led.start()
            button.setMovie(alarm_led) 
            
        if button_type == "Label":
            icon_red = "canmopsGUI/icons/icon_red_alarm.png"
            icon_green = "canmopsGUI/icons/icon_green.png"
            icon_yellow = "canmopsGUI/icons/icon_yellow.png"  
            if on: 
                pixmap = QPixmap(icon_green)
            if off:
               pixmap = QPixmap(icon_red)
            if warning:
               pixmap = QPixmap(icon_yellow) 
            button.setPixmap(pixmap.scaled(20, 20))
        else:
            pass
    
    def get_mops_device(self):
        sender = self.sender().objectName()
        _mops_num = sender[3:-2]
        _port_id = sender[-1]
        status = self.check_dut(b=int(_port_id), m=_mops_num)
        if status:
            self.show_deviceWindow(mops=_mops_num, port=str(_port_id)) 
        else:
            msg =  "MOPS " + _mops_num, "Port " + _port_id, ": Not Found"
            self.set_textBox_message(comunication_object="ErrorFrame" , msg=str(msg)) 

        
    def read_adc_channels(self,b,m):
        _dictionary = self.__dictionary_items
        _adc_indices = list(self.__adc_index)
        for i in np.arange(len(_adc_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_adc_indices[i], subindex="subindex_items"))
            _start_a = 3  # to ignore the first subindex it is not ADC
            
            for subindex in np.arange(_start_a, len(_subIndexItems) + _start_a - 1):
                s = subindex - _start_a
                adc_value = np.random.randint(0,100)     
                #adc_value = "(c%s|b%s|m%s|s%s)"%(c,b,m,s)     
                self.channelValueBox[b][m][s].setText(str(adc_value))   
                if self.trendingBox[b][m][s] == True:
                    if len(self.x[s]) >= 10:# Monitor a window of 100 points is enough to avoid Memory issues 
                        self.DataMonitoring.reset_data_holder(adc_value,s) 
                    self.DataMonitoring.update_figure(data=adc_value, subindex=subindex, graphWidget = self.graphWidget[s])     
            #This will be used later for limits 
            if adc_value >=95:
                self.update_alarm_limits(high=True, low=None, normal=None, object=self.channelValueBox[b][m][s]) 
                self.update_alarm_status(on=False, off=True, warning=False, button=self.mops_alarm_led[b][m],button_type = "Movie")
            elif (adc_value >=50 and adc_value <=80):
                self.update_alarm_limits(high=None, low=True, normal=None, object=self.channelValueBox[b][m][s])
                self.update_alarm_status(on=False, off=False, warning=True, button=self.mops_alarm_led[b][m],button_type = "Movie")
            else:
                self.channelValueBox[b][m][s].setStyleSheet("color: black;")
                self.update_alarm_status(on=True, off=False, warning=False, button=self.mops_alarm_led[b][m],button_type = "Movie")
         
        _conf_indices = list(self.__conf_index)                      
        a = 0 
        for i in np.arange(len(_conf_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_conf_indices[i], subindex="subindex_items"))
            for s in np.arange(0, len(_subIndexItems)):
                adc_value = np.random.randint(0,100)
                self.confValueBox[b][m][a].setText(str(adc_value))      
                if adc_value <=95:
                    self.confValueBox[b][m][a].setStyleSheet("color: black;")
                else:
                    self.confValueBox[b][m][a].setStyleSheet(" background-color: red;")
                a = a + 1    
        
        _mon_indices = list(self.__mon_index)    
        a = 0
        for i in np.arange(len(_mon_indices)):
            _subIndexItems = list(AnalysisUtils().get_subindex_yaml(dictionary=_dictionary, index=_mon_indices[i], subindex="subindex_items"))
            for s in np.arange(0, len(_subIndexItems)):
                adc_value = np.random.randint(0,100)
                self.monValueBox[b][m][a].setText(str(adc_value))
                if adc_value <=95:
                    self.monValueBox[b][m][a].setStyleSheet("color: black;")
                else:
                    self.monValueBox[b][m][a].setStyleSheet(" background-color: red;")
                a = a + 1   
  
        
    def show_trendWindow(self,c,b,m):
        trend = QMainWindow(self)
        subindex = self.sender().objectName()
        s = int(subindex) - 3     
        self.trendingBox[b][m][s] = True  
        n_channels = 33
        for i in np.arange(0, n_channels): self.graphWidget[i].clear()  # clear any old plots
        self.x, self.y = self.DataMonitoring.trend_child_window(childWindow=trend, subindex=int(subindex), n_channels=n_channels)
        trend.show()
               
if __name__ == "__main__":
#self.update_bus_status_box(cic_id=c, port_id=b, off=True)#Special function to update the bus state
    pass
