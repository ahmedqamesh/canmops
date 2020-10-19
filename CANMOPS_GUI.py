# -*- coding: utf-8 -*-
import sys
from matplotlib.backends.qt_compat import  QtWidgets
from graphicsUtils import  mainWindow
if __name__=='__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = mainWindow.MainWindow()
    app.Ui_ApplicationWindow()
    qApp.exec_()