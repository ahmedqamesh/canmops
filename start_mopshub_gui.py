# -*- coding: utf-8 -*-
import sys
from matplotlib.backends.qt_compat import  QtWidgets
from mopshub_gui import opcuaWindow

if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = opcuaWindow.OpcuaWindow()
    app.Ui_ApplicationWindow()
    qApp.setStyle('Fusion')
    qApp.exec_()