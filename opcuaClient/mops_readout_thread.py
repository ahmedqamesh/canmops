from threading import Thread
from opcuaClient.opcua_client import OPCClient
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

    def run(self) -> None:
        self.parent.textBox.append(f"Thread for Mops {self.mops_id} Readout started (CIC: {self.cic_id}, BUS: {self.bus_id})")
        self.readout_conf_mops = self.read_mops_conf(self.cic_id, self.bus_id, self.mops_id)
        while self.running:
            self.readout_adc_mops = self.read_mops_adc(self.cic_id, self.bus_id, self.mops_id)
            self.readout_mon_mops = self.read_mops_monitoring(self.cic_id, self.bus_id, self.mops_id)
            time.sleep(0.5)

    def stop(self):
        self.parent.textBox.append(f"Thread for Mops {self.mops_id} Readout stopped (CIC: {self.cic_id}, BUS: {self.bus_id})")
        self.running = False