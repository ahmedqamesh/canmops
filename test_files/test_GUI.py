from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.animation as animation
from typing import *
from PyQt5 import *
from PyQt5.QtCore           import *
from PyQt5.QtGui            import *
from PyQt5.QtWidgets        import *
from PyQt5.QtCore import QDateTime, Qt, QTimer, pyqtSlot
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import random
from random import randint
import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph import *
import time
from IPython import display
import matplotlib as mpl
from matplotlib.figure import Figure
from PyQt5 import QtWidgets, QtCore, uic
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys 
import os
app = QtWidgets.QApplication(sys.argv)
#MessageWindow = QMainWindow()
#mainWindow.MainWindow().adcChannelChildWindow(MessageWindow)
#dataMonitoring.ADCMonitoringData(MessageWindow)
#MessageWindow.show()
def wait_alert_leds():
    v = QVBoxLayout()
    window = QWidget()
    window.setGeometry(200, 200, 250, 250)
    icon_red = "canmopsGUI/icons/icon_red_alarm.gif" #icon_red.gif"
    wait_label = QLabel()
    alarm_led = QMovie(icon_red)    
    #alarm_led.setScaledSize(QSize().scaled(20, 20, Qt.KeepAspectRatio))
    alarm_led.start()
    wait_label.setMovie(alarm_led)
    v.addWidget(wait_label)
    window.setLayout(v)
    return window 

if __name__=='__main__':
    wait_led = wait_alert_leds()
    wait_led.show()
    time.sleep(2)
    app.exit(app.exec_())