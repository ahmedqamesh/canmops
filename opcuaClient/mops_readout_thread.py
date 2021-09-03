from threading import Thread
from opcuaClient.opcua_client import OPCClient
from datetime import date
from datetime import datetime
from pathlib import Path
import time


class READMops(Thread, OPCClient):

    def __init__(self, client, cic_id, bus_id, node_id, server_dict, parent):
        OPCClient.__init__(self, client=client)
        Thread.__init__(self)
        self.parent = parent
        self.bus_id = bus_id
        self.cic_id = cic_id
        self.mops_id = node_id
        self.server_dict = server_dict
        self.readout_adc_mops = [None for _ in range(34)]
        self.readout_conf_mops = None
        self.readout_mon_mops = None
        self.running = True
        self.data_path = None
        self.save_flag = False
        self.stream = None

    def run(self) -> None:
        self.parent.textBox.append(f"Thread for Mops {self.mops_id} Readout started (CIC: {self.cic_id}, BUS: {self.bus_id})")
        self.readout_conf_mops = self.read_mops_conf(self.cic_id, self.bus_id, self.mops_id)
        while self.running:
            self.readout_adc_mops = self.read_mops_adc(self.cic_id, self.bus_id, self.mops_id)
            self.readout_mon_mops = self.read_mops_monitoring(self.cic_id, self.bus_id, self.mops_id)
            if self.save_flag:
                now = datetime.now()
                current_time = now.strftime("%H-%M-%S")
                if not Path(self.data_path).is_file():
                    self.stream = open(self.data_path, "w")
                    self.stream.write("Channel No.")
                    for i in range(3, 40):
                        self.stream.write(f", Channel {i:02}")
                    self.stream.write("\n")
                    self.stream.write(f"Readout {current_time}")
                    for item in self.readout_adc_mops:
                        self.stream.write(f", {item}")
                    self.stream.write("\n")
                    self.stream.close()
                else:
                    self.stream = open(self.data_path, "a")
                    self.stream.write(f"Readout {current_time}")
                    for item in self.readout_adc_mops:
                        self.stream.write(f", {item}")
                    self.stream.write("\n")
            time.sleep(0.25)

    def stop(self):
        self.parent.textBox.append(f"Thread for Mops {self.mops_id} Readout stopped (CIC: {self.cic_id}, BUS: {self.bus_id})")
        self.running = False