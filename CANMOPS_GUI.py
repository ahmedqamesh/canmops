# -*- coding: utf-8 -*-
import sys
import os
import time
import logging
from matplotlib.backends.qt_compat import QtCore, QtWidgets
from PyQt5.QtCore    import *
from PyQt5.QtGui     import *
from PyQt5.QtWidgets import *
from graphics_utils import  mainWindow
rootdir = os.path.dirname(os.path.abspath(__file__))
if __name__=='__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = mainWindow.MainWindow()
    app.Ui_ApplicationWindow()
    qApp.exec_()