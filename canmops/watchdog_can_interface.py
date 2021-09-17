import subprocess
import time
from threading import Thread
from EventNotifier import Notifier
import logging
from .logger_main import Logger


class WATCHCan(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.interface_num = 2
        self.logger_thread = Logger().setup_main_logger(name = "CAN Watch  ",console_loglevel=logging.INFO, logger_file = False)
        self.watchdog_notifier = Notifier(["restart Interface"])
        self.running = True

    def run(self):
        while self.running:
            for interface in range(self.interface_num):
                status = subprocess.run(["cat", f"/sys/class/net/can{interface}/operstate", "/dev/null"],
                                        capture_output=True)
                if "up" in status.stdout.decode("utf-8"):
                    pass
                elif "down" in status.stdout.decode("utf-8"):
                    pass
                    # if interface == 0:
                    #     self.logger_thread.warning(f"CAN Interface {interface} is down -  going to restart")
                    #     self.watchdog_notifier.raise_event("restart Interface", channel=0)
                    # elif interface == 1:
                    #     self.logger_thread.warning(f"CAN Interface {interface} is down -  going to restart")
                    #     self.watchdog_notifier.raise_event("restart Interface", channel=1)
                    #     time.sleep(0.5)

    def stop(self):
        self.running = False
