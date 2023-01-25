# -*- coding: utf-8 -*-
import sys
from matplotlib.backends.qt_compat import QtWidgets
from canmopsGUI import  main_gui_window
if __name__=='__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = main_gui_window.MainWindow()
    app.Ui_ApplicationWindow()
    qApp.exec_()