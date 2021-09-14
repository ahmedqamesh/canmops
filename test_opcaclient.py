# -*- coding: utf-8 -*-
import sys
from matplotlib.backends.qt_compat import  QtWidgets
from graphicsUtils import  opcua_window

if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = opcua_window.OpcuaWindow()
    app.Ui_ApplicationWindow()
    qApp.exec_()