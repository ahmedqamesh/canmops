########################################################
"""
    This file is part of the MOPS-Hub project.
    Author: Ahmed Qamesh (University of Wuppertal)
    email: ahmed.qamesh@cern.ch  
    Date: 01.05.2020
"""
########################################################
# -*- coding: utf-8 -*-
import sys
import os
os.environ["QT_API"] = "pyqt5"
from matplotlib.backends.qt_compat import QtWidgets
from canmopsGUI import  main_gui_window

qApp =None

def main():
    global qApp
    qApp = QtWidgets.QApplication(sys.argv)
    app_widget = main_gui_window.MainWindow()
    app_widget.Ui_ApplicationWindow()
    qApp.exec_()

if __name__ == '__main__':
    main()
    