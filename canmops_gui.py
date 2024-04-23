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
    