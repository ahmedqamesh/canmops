# -*- coding: utf-8 -*-
import sys
from matplotlib.backends.qt_compat import  QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
import PyQt5
from mopshubGUI import  mopshub_child_window

if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = mopshub_child_window.mopshubWindow()
    app.Ui_ApplicationWindow(mainWindow = QMainWindow())
    qApp.exec_()