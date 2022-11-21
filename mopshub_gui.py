# -*- coding: utf-8 -*-
import sys
from matplotlib.backends.qt_compat import  QtWidgets
from mopshubGUI import  mopshub_child_window

if __name__ == '__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = mopshub_child_window.mopshubWindow()
    app.Ui_ApplicationWindow()
    qApp.exec_()