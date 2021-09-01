import logging
from yaml import load, dump
import time
from opcuaClient.browse_server_structure import BROWSEServer
from canmops.analysisUtils import AnalysisUtils
# from browse_server_structure import BROWSEServer
# from analysisUtils import AnalysisUtils
from datetime import date
from datetime import datetime
import opcua
import re
import yaml
from opcua import ua
from opcua.common import node

_logger = logging.getLogger('asyncua')


class OPCClient(BROWSEServer):

    def __init__(self, url="opc.tcp://localhost:4840/freeopcua/server/", parent=None, client=None):

        if parent is not None:
            self.parent = parent
        if client is None:
            self.server_url = url
            self.client = opcua.Client(self.server_url, timeout=1500)
        else:
            self.client = client
        self.maxBUS_count = 8
        self.maxCIC_count = 4
        self.cicADCChannel_count = 5
        BROWSEServer.__init__(self)

    def start_connection(self, url=None):
        if url is not None:
            self.client = opcua.Client(url)
        opcua.Client.connect(self.client)
        if self.parent is not None:
            self.parent.textBox.append("Connection started")

    def close_connection(self):
        opcua.Client.disconnect(self.client)
        if self.parent is not None:
            self.parent.textBox.append("Connection closed")

    def read_mops_adc(self, cic_id: int, bus_id: int, node_id: int):
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    if f"MOPS {node_id}" in self.server_dict[entry][f"CANBus {bus_id}"]:
                        values = []
                        for channel_id in range(3, 35):
                            try:
                                node = self.client.get_node(
                                    self.server_dict[entry][f"CANBus {bus_id}"][f"MOPS {node_id}"]
                                    [f"ADCChannel {channel_id:02}"]["monitoringValue"])
                                values.append(node.get_value())
                            except Exception as e:
                                print(e)
                                return None
                        return values

    def read_bus_adc(self, cic_id: int, bus_id: int, channel: int):
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    try:
                        node = self.client.get_node(self.server_dict[entry][f"CANBus {bus_id}"][f"ADC CANBus {bus_id}"]
                                                    [f"ADCChannel {channel:02}"]["monitoringValue"])
                        value = node.get_value()
                        return value
                    except Exception as e:
                        print(e)
                        return None

    def read_mops_monitoring(self, cic_id: int, bus_id: int, node_id: int):
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    if f"MOPS {node_id}" in self.server_dict[entry][f"CANBus {bus_id}"]:
                        mon_list = []
                        try:
                            for mon_item in self.server_dict[entry][f"CANBus {bus_id}"][f"MOPS {node_id}"]["MOPSMonitoring"]:
                                node = self.client.get_node(self.server_dict[entry][f"CANBus {bus_id}"]
                                                        [f"MOPS {node_id}"]["MOPSMonitoring"][mon_item])
                                mon_list.append([node.get_value(), mon_item])
                        except Exception as e:
                            print(e)
                            return None
                        return mon_list

    def read_mops_conf(self, cic_id: int, bus_id: int, node_id: int):
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    if f"MOPS {node_id}" in self.server_dict[entry][f"CANBus {bus_id}"]:
                        conf_list = []
                        try:
                            for conf_item in self.server_dict[entry][f"CANBus {bus_id}"][f"MOPS {node_id}"]["MOPSInfo"]:
                                node = self.client.get_node(self.server_dict[entry][f"CANBus {bus_id}"]
                                                            [f"MOPS {node_id}"]["MOPSInfo"][conf_item])
                                conf_list.append((node.get_value(), conf_item))
                        except Exception as e:
                            print(e)
                            return None
                        return conf_list

    def disable_power(self, cic_id, bus_id):
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    if f"PE Signal CANBus {bus_id}" in self.server_dict[entry][f"CANBus {bus_id}"]:
                        try:
                            methode = self.client.get_node(self.server_dict[entry][f"CANBus {bus_id}"]
                                                           [f"PE Signal CANBus {bus_id}"][f"Power Disable Bus {bus_id}"])
                            parent = methode.get_parent()
                            parent.call_method(methode)
                            return True
                        except Exception as e:
                            print(e)
                            return False
        else:
            return False

    def enable_power(self, cic_id, bus_id):
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    if f"PE Signal CANBus {bus_id}" in self.server_dict[entry][f"CANBus {bus_id}"]:
                        try:
                            methode = self.client.get_node(self.server_dict[entry][f"CANBus {bus_id}"]
                                                           [f"PE Signal CANBus {bus_id}"][f"Power Enable Bus {bus_id}"])
                            parent = methode.get_parent()
                            parent.call_method(methode)
                            return True
                        except Exception as e:
                            print(e)
                            return False
        else:
            return False

    def check_power_status(self, cic_id, bus_id):
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    if f"PE Signal CANBus {bus_id}" in self.server_dict[entry][f"CANBus {bus_id}"]:
                        try:
                            node = self.client.get_node(self.server_dict[entry][f"CANBus {bus_id}"]
                                                        [f"PE Signal CANBus {bus_id}"][f"Current Status"])
                            value = node.get_value()
                            return value
                        except Exception as e:
                            print(e)
                            return None
        else:
            return "N/A"

    def search_endpoints(self, cic_id, bus_id):
        mops_list = []
        for entry in self.server_dict:
            if f"CIC {cic_id}" in entry:
                if f"CANBus {bus_id}" in self.server_dict[entry]:
                    for CANBusChild in self.server_dict[entry][f"CANBus {bus_id}"]:
                        if "MOPS" in CANBusChild:
                            mops_list.append(self.server_dict[entry][f"CANBus {bus_id}"][CANBusChild]["NodeID"])
        if not mops_list:
            return []
        else:
            return mops_list

    def load_configuration(self, file):
        with open(file, 'r') as stream:
            self.server_dict = yaml.safe_load(stream)
        # self.server_dict = AnalysisUtils().open_yaml_file(file='setup.yml', directory='opcuaClient\config')
        # self.server_dict = AnalysisUtils().open_yaml_file(file='setup.yml', directory='config')

    def browse_server_structure(self, directory=None):
        self.browse_server(self.client)
        print(self.server_dict)
        if directory == None:
            with open('opcuaClient/config/setup.yml', 'w') as ymlfile:
            # with open('config/setup.yml', 'w') as ymlfile:
                dump(self.server_dict, ymlfile, sort_keys=False)
        elif directory:
            now = datetime.now()
            current_time = now.strftime("%H-%M-%S")
            file_path = directory + f'/setup_Date-{date.today()}_Time-{current_time}.yml'
            with open(file_path, 'w') as ymlfile:
                dump(self.server_dict, ymlfile, sort_keys=False)

# if __name__ == "__main__":
#     gui = OPCClient()
#     gui.start_connection()
    # gui.browse_server_structure()
    # gui.load_configuration()
    # gui.cic_view_readout_threaded()
    # print(gui.read_mops_conf(0, 31, 1))
    # print(gui.read_mops_monitoring(0, 31, 1))
#     gui.load_configuration()
#     print(gui.read_bus_adc(0, 31, 0))
#     print(gui.read_bus_adc(0, 32, 0))
#     print(gui.read_mops_adc(0, 31, 0))
#     print(gui.check_power_status(0, 31))
#     print(gui.disable_power(0, 31))
#     print(gui.check_power_status(0, 31))
#     print(gui.enable_power(0, 31))
#     print(gui.check_power_status(0, 31))
#     gui.close_connection()
