from threading import Thread
from opcuaClient.opcua_client import OPCClient
import time
import re


class READCicAdc(Thread, OPCClient):

    def __init__(self, client, server_dict, parent):
        OPCClient.__init__(self, client=client)
        Thread.__init__(self)
        self.parent = parent
        self.cic_adc_readout = [[None for _ in range(self.cicADCChannel_count)] for _ in range(self.maxBUS_count)]
        self.cic_adc_nodes = [[None for _ in range(self.cicADCChannel_count)] for _ in range(self.maxBUS_count)]
        self.running = True
        self.server_dict = server_dict

    def run(self) -> None:
        self.parent.textBox.append("CIC ADC Readout started")
        for cics in self.server_dict:
            if "CIC" in cics:
                cic_id = re.findall("\d+", cics)
                cic_id = int(cic_id[0])
                for bus in self.server_dict[cics]:
                    if "CANBus" in bus:
                        bus_id = self.server_dict[cics][bus][f"PE Signal {bus}"]["Bus ID"]
                        self.cic_adc_nodes[bus_id - 25] = self.get_cic_adc_nodes(cic_id, bus_id)
        while self.running:
            for cics in self.server_dict:
                if "CIC" in cics:
                    cic_id = re.findall("\d+", cics)
                    cic_id = int(cic_id[0])
                    for bus in self.server_dict[cics]:
                        if "CANBus" in bus:
                            bus_id = self.server_dict[cics][bus][f"PE Signal {bus}"]["Bus ID"]
                            self.cic_adc_readout[bus_id - 25] = self.read_bus_adc(cic_id, bus_id, self.cic_adc_nodes[bus_id-25])
            time.sleep(0.25)

    def stop(self):
        self.parent.textBox.append("CIC ADC Readout finished")
        self.running = False