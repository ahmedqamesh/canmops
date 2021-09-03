import threading
from threading import Thread
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.backends.backend_qt5agg import FigureCanvas
from PyQt5.QtCore import *
from PyQt5.QtGui import *
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
import re
from bs4 import BeautifulSoup

try:
    from opcuaClient import mops_readout_thread
    from opcuaClient import cic_readout_thread
    from opcuaClient import opcua_client
    from mopshub_gui import menuWindow, mopsChildWindow, dataMonitoring, childWindow
    from canmops.analysis import Analysis
    from canmops.logger import Logger
    from canmops.analysisUtils import AnalysisUtils
except Exception as e:
    print(e)
rootdir = os.path.dirname(os.path.abspath(__file__))
lib_dir = rootdir[:-12]
config_dir = "config/"


class OpcuaWindow(QWidget):

    def __init__(self, console_loglevel=logging.INFO):
        super(OpcuaWindow, self).__init__(None)
        self.logger = Logger().setup_main_logger(name=" OPCUA GUI ", console_loglevel=console_loglevel)
        self.MenuBar = menuWindow.MenuWindow(self)
        self.MOPSChildWindow = mopsChildWindow.MopsChildWindow(self, opcua_config="opcua_config.yaml")
        self.ConfigWindow = childWindow
        self.DataMonitoring = dataMonitoring.DataMonitoring(self)
        self.update_opcua_config_box()
        # get Default info
        self.__cic_num = 4
        self.__bus_num = 2
        self.__mops_num = 4

        self.server_connection = False
        self.communication_running = False
        self.config_file_loaded = False
        self.opcua_client = opcua_client.OPCClient(parent=self)
        self.cic_thread = threading.Thread()

    def update_opcua_config_box(self):
        self.conf_cic = AnalysisUtils().open_yaml_file(file=config_dir + "opcua_config.yaml", directory=lib_dir)

    def Ui_ApplicationWindow(self):
        self.mopshubWindow = QMainWindow()
        self.mopshub_for_beginner_window(childWindow=self.mopshubWindow)
        self.mopshubWindow.show()
        # dummy way of producing a fake opcua
        self.initiate_mopshub_timer()

    def update_device_box(self):
        '''
        The function Will update the configured device section with the registered devices according to the file main_cfg.yml
        '''
        conf = AnalysisUtils().open_yaml_file(file=config_dir + "MOPS_cfg.yml", directory=lib_dir)
        mops_child = mopsChildWindow.MopsChildWindow()
        deviceName, version, icon_dir, nodeIds, self.__dictionary_items, adc_channels_reg, self.__adc_index, self.__chipId, self.__index_items, self.__conf_index, self.__mon_index, self.__resistor_ratio = mops_child.configure_devices(
            conf)

    def initiate_adc_timer(self, period=None, cic=None, mops=None, port=None, readout_thread=None):
        '''
        The function will  update the GUI with the ADC data ach period in ms.
        '''
        self.ADCDummytimer = QtCore.QTimer(self)
        self.logger.notice("Reading ADC data...")
        self.__monitoringTime = time.time()
        self.ADCDummytimer.setInterval(period)
        self.ADCDummytimer.timeout.connect(lambda: self.read_adc_channels(int(cic), int(port), int(mops), readout_thread))
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
        self.CicDummytimer = QtCore.QTimer(self)
        self.logger.notice("Reading ADC data...")
        self.__monitoringTime = time.time()
        # A possibility to save the data into a file
        self.logger.notice("Preparing an output file [%s.csv]..." % (lib_dir + "output_data/opcua_data"))
        self.out_file_csv = AnalysisUtils().open_csv_file(outname="opcua_data", directory=lib_dir + "output_data")

        # Write header to the data
        fieldnames = ['Time', 'Channel', "nodeId", "ADCChannel", "ADCData", "ADCDataConverted"]
        writer = csv.DictWriter(self.out_file_csv, fieldnames=fieldnames)
        writer.writeheader()

        self.CicDummytimer.setInterval(period)
        self.CicDummytimer.timeout.connect(self.set_adc_cic)
        self.CicDummytimer.start()

    def stop_mopshub_timer(self):
        '''
        The function will  stop the adc_timer.
        '''
        try:
            self.CicDummytimer.stop()
            self.logger.notice("Stopping CIC timer...")
        except Exception:
            pass

    def mopshub_for_beginner_window(self, childWindow):
        # create MenuBar
        self.MenuBar = menuWindow.MenuWindow(childWindow)
        self.MenuBar.create_opcua_menuBar(childWindow, self)

        childWindow.setObjectName("OPCUA servers")
        childWindow.setWindowTitle("OPCUA servers")
        childWindow.setWindowIcon(QtGui.QIcon("mopshub_gui/icons/icon_opcua.png"))
        childWindow.adjustSize()
        # childWindow.setFixedSize(900, 800)
        # childWindow.setGeometry(200, 100, 50, 200)
        plotframe = QFrame()
        childWindow.setCentralWidget(plotframe)
        logo_layout = QHBoxLayout()
        uni_logo_label = QLabel()
        pixmap = QPixmap("mopshub_gui/icons/icon_wuppertal_banner.png")
        uni_logo_label.setPixmap(pixmap.scaled(150, 50))
        icon_spacer = QSpacerItem(250, 50, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        logo_layout.addItem(icon_spacer)
        logo_layout.addWidget(uni_logo_label)

        mopshubGridLayout = QGridLayout()
        #  Prepare a cic window
        bus_num = self.__bus_num
        cic_num = self.__cic_num
        mops_num = self.__mops_num

        self.en_button = [[k for k in np.arange(bus_num)]] * cic_num
        self.statusBoxVar = [[k for k in np.arange(bus_num)]] * cic_num
        self.bus_alarm_led = [[k for k in np.arange(bus_num)]] * cic_num
        self.Adc_cic_channel = ["    UH", "    UL", " VCAN", " Temp", "  GND"]
        self.adc_text_box = [[[ch for ch in self.Adc_cic_channel]] * bus_num] * cic_num
        self.channelValueBox = [[[ch for ch in np.arange(mops_num)]] * bus_num] * cic_num
        self.trendingBox = [[[ch for ch in np.arange(mops_num)]] * bus_num] * cic_num
        self.monValueBox = [[[ch for ch in np.arange(mops_num)]] * bus_num] * cic_num
        self.confValueBox = [[[ch for ch in np.arange(mops_num)]] * bus_num] * cic_num
        self.conf_labelvalue = [[[ch for ch in np.arange(mops_num)]] * bus_num] * cic_num
        self.mon_labelvalue = [[[ch for ch in np.arange(mops_num)]] * bus_num] * cic_num

        self.mops_alarm_led = [[[m for m in np.arange(mops_num)]] * bus_num] * cic_num

        self.mops_button_ref = [[[None for _ in range(self.__mops_num)]for _ in range(self.__bus_num)]for _ in range(self.__cic_num)]

        self.CiCGroupBoxList = [QWidget for _ in range(self.__cic_num)]

        cic_row_len = int(cic_num / 2)
        for c in np.arange(cic_num):
            self.CiCGroupBoxList[c] = self.def_cic_frame(c)
            if (c) < cic_row_len:
                mopshubGridLayout.addWidget(self.CiCGroupBoxList[c], 1, cic_row_len + (c - cic_row_len))
            else:
                mopshubGridLayout.addWidget(self.CiCGroupBoxList[c], 2, c - cic_row_len)
                # Prepare a log window
        self.textOutputWindow()

        # close button
        buttonLayout = QHBoxLayout()

        restore_button = QPushButton("Restore last session")
        restore_button.setIcon(QIcon('mopshub_gui/icons/icon_restart.png'))
        restore_button.clicked.connect(self.restore_session)

        connect_button = QPushButton("Server Settings")
        connect_button.setIcon(QIcon('mopshub_gui/icons/icon_settings.png'))
        connect_button.clicked.connect(self.connect_to_server)

        close_button = QPushButton("Close")
        close_button.setIcon(QIcon('mopshub_gui/icons/icon_close.png'))
        close_button.clicked.connect(self.stop_opcua)

        buttonLayout.addSpacing(50)
        buttonLayout.addWidget(restore_button)
        buttonLayout.addWidget(connect_button)
        buttonLayout.addWidget(close_button)

        mopshubGridLayout.addLayout(logo_layout, 0, 1)
        mopshubGridLayout.addWidget(self.textGroupBox, cic_num + 2, 0, cic_row_len, cic_row_len)
        mopshubGridLayout.addLayout(buttonLayout, cic_num + 4, 1, cic_row_len, cic_row_len)
        plotframe.setLayout(mopshubGridLayout)
        self.MenuBar.create_statusBar(childWindow)
        QtCore.QMetaObject.connectSlotsByName(childWindow)

    def stop_opcua(self):

        self.logger.warning('Stopping the main OPCUA client')
        self.stop_adc_timer()
        self.stop_mopshub_timer()
        time.sleep(1)
        if self.communication_running:
            self.cic_thread.stop()
            self.communication_running = False
        time.sleep(1)
        if self.server_connection:
            self.opcua_client.close_connection()
            self.server_connection = False
        self.logger.warning('Closing the GUI.')
        sys.exit()

    def def_cic_frame(self, c):
        # Define CIC Layout
        bus_num = self.__bus_num
        cic_num = self.__cic_num
        CICGridLayout = QGridLayout()
        CICGroupBox = QGroupBox("        CIC" + str(c))
        CICGroupBox.setStyleSheet("QGroupBox { font-weight: bold;font-size: 16px; background-color: #eeeeec; } ")
        _, self.en_button[c], self.bus_alarm_led[c], self.statusBoxVar[c] = self.def_bus_variables(c, bus_num)
        self.adc_text_box[c] = self.get_bus_adc_text_box()
        self.mops_alarm_led[c] = self.get_bus_mops_led(c)
        for b in np.arange(bus_num):
            true_bus_number = self.get_true_bus_number(b, c)
            BusGroupBox = self.def_bus_frame(c, b, true_bus_number)
            CICGridLayout.addWidget(BusGroupBox, 3, b, 1, 1)
        CICGroupBox.setLayout(CICGridLayout)
        return CICGroupBox

    def def_bus_frame(self, c, b, true_bus_number):
        icon = QIcon()
        icon.addPixmap(QPixmap('mopshub_gui/icons/icon_connect.jpg'), QIcon.Normal, QIcon.On)
        icon.addPixmap(QPixmap('mopshub_gui/icons/icon_disconnect.jpg'), QIcon.Normal, QIcon.Off)
        BusGridLayout = QGridLayout()
        StatLayout = QGridLayout()
        ADCGroupBox = self.def_adc_frame(c, b)
        mopsBottonLayout = self.def_mops_frame(c, b, true_bus_number)

        BusGroupBox = QGroupBox("Port " + str(true_bus_number))
        BusGroupBox.setStyleSheet("QGroupBox { font-weight: bold;font-size: 10px; background-color: #eeeeec; } ")

        statusLabelVar = QLabel()
        statusLabelVar.setStyleSheet("QLabel { font-weight: font-size: 8px; background-color:  #eeeeec; } ")
        statusLabelVar.setText("Bus Status:")
        itemSpacer = QSpacerItem(50, 10, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        StatLayout.addWidget(statusLabelVar, b, 0)
        StatLayout.addWidget(self.statusBoxVar[c][b], b, 1)
        StatLayout.addWidget(self.bus_alarm_led[c][b], b, 2)
        StatLayout.addWidget(self.en_button[c][b], b, 3)
        StatLayout.addItem(itemSpacer, b, 4)

        BusGridLayout.addWidget(ADCGroupBox, 0, 0, 1, 2)
        BusGridLayout.addLayout(StatLayout, 1, 0, 1, 2)
        BusGridLayout.addLayout(mopsBottonLayout, 2, 0, 1, 1)
        BusGroupBox.setLayout(BusGridLayout)
        if self.opcua_client.check_power_status(c, true_bus_number) == "ON":
            self.update_bus_status_box(cic_id=c, port_id=b, on=True)
        elif self.opcua_client.check_power_status(c, true_bus_number) == "OFF":
            self.update_bus_status_box(cic_id=c, port_id=b, off=True)
        elif self.opcua_client.check_power_status(c, true_bus_number) == "N/A":
            self.update_bus_status_box(cic_id=c, port_id=b, off=True)
        return BusGroupBox

    def def_alert_leds(self, bus_alarm=None, mops_alarm=None, cic=None, mops=None, bus=None, icon_state=False):
        cic_num = self.__cic_num
        if mops_alarm is True:
            icon_red = "mopshub_gui/icons/icon_disconnected_device.png"  # icon_red.gif"
            icon_green = "mopshub_gui/icons/icon_green.gif"
            if icon_state:
                alarm_led = QMovie(icon_green)
            else:
                alarm_led = QMovie(icon_red)
            alarm_led.setScaledSize(QSize().scaled(20, 20, Qt.KeepAspectRatio))
            alarm_led.start()
            return alarm_led

        if bus_alarm is True:
            icon_red = "mopshub_gui/icons/icon_red.png"
            icon_green = "mopshub_gui/icons/icon_green.png"
            alarm_led = [0] * cic_num
            alarm_led[cic] = QLabel()
            if icon_state:
                pixmap = QPixmap(icon_green)
            else:
                pixmap = QPixmap(icon_red)
            alarm_led[cic].setPixmap(pixmap.scaled(20, 20))
            return alarm_led[cic]

    def def_mops_frame(self, c, b, true_bus_number):
        # Details for each MOPS
        mops_num = 4
        icon_mops = 'mopshub_gui/icons/icon_mops.png'
        mopsBotton = [k for k in np.arange(mops_num)]
        mopsBottonLayout = QGridLayout()
        mopsBottonLayout.setObjectName("Mops")
        self.update_device_box()
        if self.server_connection and self.config_file_loaded:
            connected_mops = self.opcua_client.search_endpoints(c, true_bus_number)
        else:
            connected_mops = []
        for m in np.arange(mops_num):
            if m < len(connected_mops):
                status = True
                mopsBotton[m] = QPushButton("  [" + str(connected_mops[m]) + "]")
                mopsBotton[m].setObjectName("C" + str(c) + "M" + str(connected_mops[m]) + "P" + str(b))
                mopsBotton[m].setIcon(QIcon(icon_mops))
                mopsBotton[m].setStatusTip(
                    "CIC NO." + str(c) + " MOPS No." + str(connected_mops[m]) + " Port No." + str(true_bus_number))
                mopsBotton[m].clicked.connect(self.get_mops_device)
            else:
                status = False
                mopsBotton[m] = QPushButton("  [" + str("-") + "]")
                mopsBotton[m].setObjectName("C" + str(c) + "M" + str("-") + "P" + str(b))
                mopsBotton[m].setIcon(QIcon(icon_mops))
                mopsBotton[m].setStatusTip(
                    "CIC NO." + str(c) + " MOPS No." + str("-") + " Port No." + str(true_bus_number))
                mopsBotton[m].clicked.connect(self.get_mops_device)
            if status:
                pass
            else:
                mopsBotton[m].setEnabled(False)
            mopsBottonLayout.addWidget(self.mops_alarm_led[c][b][m], m + 3, 0, 1, 1)
            mopsBottonLayout.addWidget(mopsBotton[m], m + 3, 1, 1, 1)
            self.mops_button_ref[m][b][c] = mopsBotton[m]
        return mopsBottonLayout

    def def_adc_frame(self, c, b):
        self.Adc_cic_channel = ["I0[mA]", "VCan[V]", "Temp[°C]", " I1[mA]", "I2[mA]"]
        Adc_cic_description = ["[ADC ch0]", "[ADC ch1]", "[ADC ch2]", "[ADC ch3]", "[ADC ch4]"]
        adclabels = [ch for ch in self.Adc_cic_channel]
        ADCLayout = QGridLayout()
        ADCGroupBox = QGroupBox("ADC CAN Bus")
        ADCGroupBox.setStyleSheet("QGroupBox { font-weight: bold;font-size: 10px; background-color: #eeeeec; } ")
        for ch in np.arange(len(self.Adc_cic_channel)):
            adclabels[ch] = QLabel()
            adclabels[ch].setStyleSheet("QLabel { font-weight: font-size: 8px; background-color:  #eeeeec; } ")
            adclabels[ch].setText(self.Adc_cic_channel[ch])
            adclabels[ch].setStatusTip(Adc_cic_description[ch])
            adclabels[ch].setAlignment(Qt.AlignCenter)
            ADCLayout.addWidget(adclabels[ch], 0, ch)
            ADCLayout.addWidget(self.adc_text_box[c][b][ch], 1, ch)
        ADCGroupBox.setLayout(ADCLayout)
        return ADCGroupBox

    def get_bus_mops_led(self, c):
        bus_num = self.__bus_num
        bus_mops_leds = [[k for k in np.arange(bus_num)]] * self.__mops_num
        for b in np.arange(bus_num):
            bus_mops_leds[b] = self.def_mops_led(b, c)
        return bus_mops_leds

    def def_mops_led(self, b, c):
        mops_num = self.__mops_num
        mops_led = [k for k in np.arange(mops_num)]
        true_bus_number = self.get_true_bus_number(b, c)
        connected_mops = self.opcua_client.search_endpoints(c, true_bus_number)
        for m in np.arange(mops_num):
            if m < len(connected_mops):
                mops_led[m] = QLabel()
                status = True
                mops_alarm_led = self.def_alert_leds(mops_alarm=True, cic=c, mops=m, bus=b, icon_state=status)
                mops_led[m].setMovie(mops_alarm_led)
            else:
                mops_led[m] = QLabel()
                status = False
                mops_alarm_led = self.def_alert_leds(mops_alarm=True, cic=c, mops=m, bus=b, icon_state=status)
                mops_led[m].setMovie(mops_alarm_led)
        return mops_led

    def get_bus_adc_text_box(self):
        bus_num = self.__bus_num
        adctextBox = [[k for k in np.arange(bus_num)]] * len(self.Adc_cic_channel)
        for b in np.arange(bus_num):
            adctextBox[b] = self.def_adc_text_box()
        return adctextBox

    def def_adc_text_box(self):
        adctextBox = [k for k in np.arange(len(self.Adc_cic_channel))]
        for ch in np.arange(len(self.Adc_cic_channel)):
            adctextBox[ch] = QLineEdit("")
            adctextBox[ch].setStyleSheet("background-color: white; border: 1px inset black;")
            adctextBox[ch].setReadOnly(True)
            adctextBox[ch].setFixedWidth(60)
            adctextBox[ch].setAlignment(Qt.AlignCenter)
        return adctextBox

    def def_bus_variables(self, cic, bus_num):
        en_button = [k for k in np.arange(bus_num)]
        statusBoxVar = [k for k in np.arange(bus_num)]
        bus_alarm_led = [k for k in np.arange(bus_num)]
        statusLabelVar = [k for k in np.arange(bus_num)]
        icon = QIcon()
        icon.addPixmap(QPixmap('mopshub_gui/icons/icon_connect.jpg'), QIcon.Normal, QIcon.On)
        icon.addPixmap(QPixmap('mopshub_gui/icons/icon_disconnect.jpg'), QIcon.Normal, QIcon.Off)
        for b in np.arange(bus_num):
            true_bus_number = self.get_true_bus_number(b, cic)
            en_button[b] = QPushButton("")
            en_button[b].setIcon(icon)
            en_button[b].setStatusTip("C" + str(cic) + "_b" + str(true_bus_number))
            en_button[b].setObjectName("C" + str(cic) + "_b" + str(true_bus_number))
            en_button[b].setCheckable(True)
            en_button[b].clicked.connect(lambda: self.set_bus_enable(cic, true_bus_number))

            bus_alarm_led[b] = self.def_alert_leds(bus_alarm=True, cic=b, mops=None, icon_state=False)
            statusBoxVar[b] = QLineEdit()
            statusBoxVar[b].setStyleSheet("background-color: white; border: 1px inset black;")
            statusBoxVar[b].setReadOnly(True)
            statusBoxVar[b].setFixedWidth(40)
            statusBoxVar[b].setText("OFF")

            statusLabelVar[b] = QLabel()
            statusLabelVar[b].setStyleSheet("QLabel { font-weight: font-size: 8px; background-color:  #eeeeec; } ")
            statusLabelVar[b].setText("Bus Status:")
        return statusLabelVar, en_button, bus_alarm_led, statusBoxVar

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
    def show_deviceWindow(self, cic=None, mops=None, port=None):
        true_bus_number = self.get_true_bus_number(int(port), int(cic))

        mops_readout = mops_readout_thread.READMops(self.opcua_client.client, int(cic), true_bus_number, int(mops), self.opcua_client.server_dict, parent=self)
        mops_readout.start()

        deviceWindow = QMainWindow(self)
        _device_name = "CIC:" + cic + ", Port:" + port + ", MOPS:" + mops
        adc_channels_num = 33
        self.channelValueBox[int(cic)][int(port)][int(mops)], self.trendingBox[int(cic)][int(port)][int(mops)], \
        self.monValueBox[int(cic)][int(port)][int(mops)], self.mon_labelvalue[int(cic)][int(port)][int(mops)], \
        self.confValueBox[int(cic)][int(port)][int(mops)], self.conf_labelvalue[int(cic)][int(port)][
            int(mops)], _ = self.MOPSChildWindow.device_child_window(deviceWindow,
                                                                     device=_device_name,
                                                                     cic=cic,
                                                                     mops=mops,
                                                                     port=port,
                                                                     mainWindow=self,
                                                                     readout_thread=mops_readout)
        self.graphWidget = self.DataMonitoring.initiate_trending_figure(n_channels=adc_channels_num)
        self.initiate_adc_timer(period=250, cic=cic, mops=mops, port=port, readout_thread=mops_readout)
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

    def get_true_bus_number(self, bus_id, cic_id):
        true_bus_number = (33 - (bus_id + 1) - (2 * cic_id))
        return true_bus_number

    def get_reverse_bus_number(self, true_bus_number, cic_id):
        bus_id = -1 - (true_bus_number + (2 * cic_id) - 33)
        return str(bus_id)

    def set_bus_enable(self, c, b):
        sender = self.sender().objectName()
        _cic_id = sender[1:-4]
        _true_port_id = sender[4:]
        _port_id = self.get_reverse_bus_number(int(_true_port_id), int(_cic_id))
        # print(sender, "is clicked")
        # en_button_check = self.en_button[int(_cic_id)][int(_port_id)].isChecked()
        if self.opcua_client.check_power_status(c, _true_port_id) == "ON":
            result = self.opcua_client.disable_power(_cic_id, _true_port_id)
            if result:
                self.update_bus_status_box(cic_id=_cic_id, port_id=_port_id, off=True)
        elif self.opcua_client.check_power_status(c, _true_port_id) == "OFF":
            result = self.opcua_client.enable_power(_cic_id, _true_port_id)
            if result:
                self.update_bus_status_box(cic_id=_cic_id, port_id=_port_id, on=True)
        elif self.opcua_client.check_power_status(c, _true_port_id) == "N/A":
            self.update_bus_status_box(cic_id=_cic_id, port_id=_port_id, off=True)

    def set_adc_cic(self):
        if self.communication_running:
            for c in np.arange(self.__cic_num):
                if f"CIC {c}" in self.opcua_client.server_dict:
                    for b in np.arange(self.__bus_num):
                        true_bus_number = self.get_true_bus_number(b, c)
                        if f"CANBus {true_bus_number}" in self.opcua_client.server_dict[f"CIC {c}"]:
                            for ch in np.arange(5):
                                adc_value = self.cic_thread.cic_adc_readout[true_bus_number - 25][ch]
                                if adc_value is not None:
                                    if ch == 0:
                                        adc_value = round(adc_value*1000, 3)
                                    if ch == 3:
                                        adc_value = round((adc_value * 1000) / 20, 3)
                                    if ch == 4:
                                        adc_value = round(((adc_value * 1000) / 10.1 * 0.4), 3)
                                    if ch == 2:
                                        r_ntc = adc_value*(20/3.1)
                                        adc_value = round((298.15 / (1 - (298.15 / 3435) * np.log(10 / r_ntc))) - 273.15, 3)
                                    self.adc_text_box[c][b][ch].setText(str(adc_value))
                                    # This will be used later for limits
                                    if adc_value >= 90:
                                        self.update_alarm_limits(high=True, object=self.adc_text_box[c][b][ch])
                                    if adc_value <= 5:
                                        self.update_alarm_limits(low=True, object=self.adc_text_box[c][b][ch])
                                    else:
                                        self.update_alarm_limits(normal=True, object=self.adc_text_box[c][b][ch])
                        else:
                            for ch in np.arange(5):
                                adc_value = "-"
                                self.adc_text_box[c][b][ch].setText(str(adc_value))
                else:
                    for b in np.arange(self.__bus_num):
                        for ch in np.arange(5):
                            adc_value = "-"
                            self.adc_text_box[c][b][ch].setText(str(adc_value))

    def update_alarm_limits(self, high=None, low=None, normal=None, object=None):
        if high:
            object.setStyleSheet(" background-color: red;")
        if low:
            object.setStyleSheet(" background-color: yellow;")
        if normal:
            object.setStyleSheet("color: black;")
        else:
            pass

    def update_bus_status_box(self, cic_id=None, port_id=None, on=False, off=False):
        icon_red = "mopshub_gui/icons/icon_red.png"
        icon_green = "mopshub_gui/icons/icon_green.png"
        if on:
            pixmap = QPixmap(icon_green)
            self.statusBoxVar[int(cic_id)][int(port_id)].setText("ON")
            self.en_button[int(cic_id)][int(port_id)].setChecked(True)
            # self.bus_alarm_led[int(cic_id)][int(port_id)]
        else:
            pixmap = QPixmap(icon_red)
            self.statusBoxVar[int(cic_id)][int(port_id)].setText("OFF")
            self.en_button[int(cic_id)][int(port_id)].setChecked(False)
            # self.bus_alarm_led[int(cic_id)][int(port_id)]
        self.bus_alarm_led[int(cic_id)][int(port_id)].setPixmap(pixmap.scaled(20, 20))

    def update_alarm_status(self, on=False, off=False, warning=False, button=None, button_type="Movie"):

        if button_type == "Movie":
            icon_red = "mopshub_gui/icons/icon_red_alarm.gif"
            icon_green = "mopshub_gui/icons/icon_green.gif"
            icon_yellow = "mopshub_gui/icons/icon_yellow.gif"

            alarm_led = QMovie()
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
            icon_red = "mopshub_gui/icons/icon_red_alarm.png"
            icon_green = "mopshub_gui/icons/icon_green.png"
            icon_yellow = "mopshub_gui/icons/icon_yellow.png"
            pixmap = QPixmap()
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
        _cic_id = sender[1:-4]
        _mops_num = sender[3:-2]
        _port_id = sender[-1]
        status = True
        # status = self.check_dut(c=_cic_id, b=int(_port_id), m=_mops_num)
        if status:
            self.show_deviceWindow(cic=_cic_id, mops=_mops_num, port=str(_port_id))
        else:
            msg = "CIC " + _cic_id, "MOPS " + _mops_num, "Port " + _port_id, ": Not Found"
            self.set_textBox_message(comunication_object="ErrorFrame", msg=str(msg))

    def read_adc_channels(self, c, b, m, readout_thread):
        readout = readout_thread.readout_adc_mops
        for subindex in range(0, len(readout)):
            adc_value = readout[subindex]
            if adc_value is not None:
                self.channelValueBox[c][b][m][subindex].setText(str(adc_value))
                if self.trendingBox[c][b][m][subindex] is True:
                    if len(self.x[subindex]) >= 10:  # Monitor a window of 100 points is enough to avoid Memory issues
                        self.DataMonitoring.reset_data_holder(adc_value, subindex)
                    self.DataMonitoring.update_figure(data=adc_value, subindex=subindex,
                                                      graphWidget=self.graphWidget[subindex])
                # This will be used later for limits
                if adc_value >= 95:
                    self.update_alarm_limits(high=True, low=None, normal=None,
                                             object=self.channelValueBox[c][b][m][subindex])
                    self.update_alarm_status(on=False, off=True, warning=False, button=self.mops_alarm_led[c][b][m],
                                             button_type="Movie")
                elif 50 <= adc_value <= 80:
                    self.update_alarm_limits(high=None, low=True, normal=None,
                                             object=self.channelValueBox[c][b][m][subindex])
                    self.update_alarm_status(on=False, off=False, warning=True, button=self.mops_alarm_led[c][b][m],
                                             button_type="Movie")
                else:
                    self.channelValueBox[c][b][m][subindex].setStyleSheet("color: black;")
                    self.update_alarm_status(on=True, off=False, warning=False, button=self.mops_alarm_led[c][b][m],
                                             button_type="Movie")

        readout_conf = readout_thread.readout_conf_mops

        for i in range(len(self.conf_labelvalue[c][b][m])):
            if self.conf_labelvalue[c][b][m][i] != 0:
                label_text = BeautifulSoup(self.conf_labelvalue[c][b][m][i].text(), features="lxml")
                if readout_conf is not None:
                    for j in range(len(readout_conf)):
                        if label_text.get_text() == readout_conf[j][1]:
                            if readout_conf[j][0] is not None:
                                self.confValueBox[c][b][m][i].setText(str(readout_conf[j][0]))
                                self.confValueBox[c][b][m][i].setStyleSheet("color: black;")

        readout_mon = readout_thread.readout_mon_mops

        for i in range(len(self.mon_labelvalue[c][b][m])):
            if self.mon_labelvalue[c][b][m][i] != 0:
                label_text = BeautifulSoup(self.mon_labelvalue[c][b][m][i].text(), features="lxml")
                if readout_mon is not None:
                    for j in range(len(readout_mon)):
                        if label_text.get_text() == readout_mon[j][1]:
                            if readout_mon[j][0] is not None:
                                self.monValueBox[c][b][m][i].setText(str(readout_mon[j][0]))
                                if readout_mon[j][0] <= 95:
                                    self.monValueBox[c][b][m][i].setStyleSheet("color: black;")
                                else:
                                    self.monValueBox[c][b][m][i].setStyleSheet(" background-color: red;")

    def show_trendWindow(self, c, b, m):
        trend = QMainWindow(self)
        subindex = self.sender().objectName()
        s = int(subindex) - 3
        self.trendingBox[c][b][m][s] = True
        n_channels = 33
        for i in np.arange(0, n_channels): self.graphWidget[i].clear()  # clear any old plots
        self.x, self.y = self.DataMonitoring.trend_child_window(childWindow=trend, subindex=int(subindex),
                                                                n_channels=n_channels)
        trend.show()

    def connect_to_server(self):
        self.BrowseServerWindow = QMainWindow()
        BrowseWindow = childWindow.ChildWindow(parent=self)
        BrowseWindow.browse_client_child_window(self.BrowseServerWindow)
        self.BrowseServerWindow.show()

    def start_communication(self):
        self.textBox.append("Starting Communication")
        for c in range(self.__cic_num):
            for b in range(self.__bus_num):
                true_bus_number = self.get_true_bus_number(b, c)
                if self.opcua_client.check_power_status(c, true_bus_number) == "ON":
                    self.update_bus_status_box(cic_id=c, port_id=b, on=True)
                elif self.opcua_client.check_power_status(c, true_bus_number) == "OFF":
                    self.update_bus_status_box(cic_id=c, port_id=b, off=True)
                elif self.opcua_client.check_power_status(c, true_bus_number) == "N/A":
                    self.update_bus_status_box(cic_id=c, port_id=b, off=True)
                connected_mops = self.opcua_client.search_endpoints(c, true_bus_number)
                for m in range(self.__mops_num):
                    if m < len(connected_mops):
                        self.mops_button_ref[m][b][c].setObjectName("C" + str(c) + "M" + str(connected_mops[m])
                                                                    + "P" + str(b))
                        self.mops_button_ref[m][b][c].setStatusTip("CIC NO." + str(c) + " MOPS No." +
                                                                   str(connected_mops[m]) + " Port No." +
                                                                   str(true_bus_number))
                        self.mops_button_ref[m][b][c].setText(f"[Mops: {connected_mops[m]}]")
                        self.mops_button_ref[m][b][c].setEnabled(True)
                        mops_alarm_led = self.def_alert_leds(mops_alarm=True, cic=c, mops=m, bus=b, icon_state=True)
                        self.mops_alarm_led[c][b][m].setMovie(mops_alarm_led)
        self.cic_thread = cic_readout_thread.READCicAdc(self.opcua_client.client, self.opcua_client.server_dict, parent=self)
        self.cic_thread.start()

    def restore_session(self):
        with open("mopshub_gui/session_config/config", 'r') as fstream:
            ip_addr = fstream.readline()
            ip_addr = re.sub(r"\n", "", ip_addr)
            server_file = fstream.readline()
            server_file = re.sub(r"\n", "", server_file)
            endpoint_url = f"opc.tcp://{ip_addr}:4840/freeopcua/server/"
            status = self.opcua_client.start_connection(url=endpoint_url)
            if status is True:
                self.server_connection = True
                self.textBox.append("Connection started")
            else:
                self.textBox.append("Can't restore last Session. Server is not available")
                return
            self.opcua_client.load_configuration(server_file)
            self.config_file_loaded = True
            self.textBox.append("Config File was loaded. Communication is ready to start.")
            self.communication_running = True
            self.start_communication()


if __name__ == "__main__":
    pass
