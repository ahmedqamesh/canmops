# -*- coding: utf-8 -*-
#pip install event-notifier
# pip install BeautifulSoup4
#pip install pytest-asyncio
import sys
from matplotlib.backends.qt_compat import  QtWidgets
from canmopsGUI import  main_gui_window
if __name__=='__main__':
    qApp = QtWidgets.QApplication(sys.argv)
    app = main_gui_window.MainWindow()
    app.Ui_ApplicationWindow(mopshub = True)
    qApp.exec_()