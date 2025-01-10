########################################################
"""
    This file is part of the MOPS-Hub project.
    Author: Ahmed Qamesh (University of Wuppertal)
    email: ahmed.qamesh@cern.ch  
    Date: 01.05.2020
"""
########################################################
import subprocess
import time
from threading import Thread
from EventNotifier import Notifier
import logging
try:
    from logger_main import Logger
except:
    from .logger_main import Logger
log_call = Logger(name = " CAN Watch ",console_loglevel=logging.INFO, logger_file = False)
class WATCHCan(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.bus_num = 2
        self.logger_thread = log_call.setup_main_logger()
        self.watchdog_notifier = Notifier(["restart bus_channel"])
        self.running = True
        self.logger_thread.notice(f"Start a CAN bus thread")
    
    def run(self):
        while self.running:
            for bus_channel in range(self.bus_num):
                status = subprocess.run(["cat", f"/sys/class/net/can{bus_channel}/operstate", "/dev/null"], capture_output=True)
                if "up" in status.stdout.decode("utf-8"):
                    pass
                # elif "down" in status.stdout.decode("utf-8"):
                #     if bus_channel == 0:
                #         self.logger_thread.warning(f"CAN bus_channel {bus_channel} is down -  going to restart")
                #         self.watchdog_notifier.raise_event("restart bus_channel", channel=0)
                #     elif bus_channel == 1:
                #         self.logger_thread.warning(f"CAN bus_channel {bus_channel} is down -  going to restart")
                #         self.watchdog_notifier.raise_event("restart bus_channel", channel=1)
                #         time.sleep(0.5)
                    
                else:
                    pass
    def stop(self):
        self.running = False
