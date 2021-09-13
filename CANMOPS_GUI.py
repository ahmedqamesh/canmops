# -*- coding: utf-8 -*-
import sys
from matplotlib.backends.qt_compat import  QtWidgets
from graphicsUtils import  main_window
if __name__=='__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = main_window.MainWindow()
    app.Ui_ApplicationWindow()
    qApp.exec_()