from logging import Logger
import asyncua
import re
import logging
import sys
from yaml import load, dump
from itertools import product
from asyncua import Node
from PEconfig import power_signal
from analysisUtils import AnalysisUtils
from CANconfig import can_config

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
sys.path.insert(0, "..")


class MOPSHUBCrate:
    def __init__(self, endpoint: str = 'opc.tcp://0.0.0.0:4840/freeopcua/server/',
                 namespace: str = 'http://examples.freeopcua.github.io'):
        """Constructor for MOPSHUBCrate

        :type namespace: str
        :type endpoint: str
        :param endpoint: The server endpoint (hint: 127.0.0.1 hosts on YOUR machine, 0.0.0.0 exposes the server to the network as well)
        :param namespace: The namespace
        """
        self.endpoint = endpoint
        self.namespace = namespace
        self.Server = asyncua.Server()
        self.idx = 0
        self.CICs = [None for _ in range(4)]
        self.Bus = [None for _ in range(32)]
        self.Mops = [[None for _ in range(2)] for _ in range(len(self.Bus))]
        self.can_attr = ['Channel', 'Bitrate', 'SamplePoint', 'SJW', 'tseg1', 'tseg2', 'Timeout']
        self.can_config = [[None for _ in range(len(self.can_attr))] for _ in range(2)]

        self.logger = logging.getLogger('mopshub_log.crate')
        self._logger: Logger = logging.getLogger('asyncua')

        logging.basicConfig(level=logging.DEBUG)

        self.defaults = {
            "ADC Channel Default Converter": 'Raw',
            "MOPS Default Location": 'Unknown',
            "MOPS Default Status": 0,
            "MOPS Default Port": 0,
            "MOPS Configuration Default Trimming": 0
        }
        self.converters = {
            "Raw": (lambda x: x),
            "Voltage": (lambda x: x / 2 ** 12 * 1.2),
            "Temperature": (lambda x: x / 2 ** 12 * 2.4)
        }

    async def disable_power(self, parent):
        logging.warning('Power OFF')
        node = self.Server.get_node(f"{parent}")
        browse_name = await node.read_browse_name()
        browse_name = (str(browse_name).split("CANBus"))[-1:]
        result = re.findall('([0-9]*)', str(browse_name))
        try:
            for i in range(len(result)):
                num = str(result[i])
                if num.isdigit():
                    channel = int(num)
                    # status = [status, locked_by_sys, locked_by_user]
                    status = power_signal.check_status(channel)
                    if bool(status[1]) is False:
                        power_signal.addressable_latch_mode(channel, 1, True)
                        status = power_signal.check_status(channel)
                        self.logger.info("Power of Channel %s was switched to OFF by User(Data,Locked: %s, %s)",
                                         channel, str(status[0]), str(status[2]))
                    elif bool(status[1]) is True:
                        self.logger.error("Power of the Channel was locked from sys while start up", channel)
        except Exception as e:
            self.logger.error(e)
            self.logger.error("An Error occurred by switching OFF Channel")
            return

    async def enable_power(self, parent):
        logging.warning('Power ON')
        node = self.Server.get_node(f"{parent}")
        browse_name = await node.read_browse_name()
        browse_name = (str(browse_name).split("CANBus"))[-1:]
        result = re.findall('([0-9]*)', str(browse_name))
        try:
            for i in range(len(result)):
                num = str(result[i])
                if num.isdigit():
                    channel = int(num)
                    # status = [status, locked_by_sys, locked_by_user]
                    status = power_signal.check_status(channel)
                    if bool(status[1]) is False:
                        power_signal.addressable_latch_mode(channel, 0, False)
                        status = power_signal.check_status(channel)
                        self.logger.info("Power of Channel %s was switched to OFF by User(Data,Locked: %s, %s)",
                                         channel, str(status[0]), str(status[2]))
                    elif bool(status[1]) is True:
                        self.logger.error("Power of Channel %s was locked from sys while start up", channel)
                    return
        except Exception as e:
            self.logger.error(e)
            self.logger.error("An Error occurred by switching ON Channel")
            return

    async def configure_can(self, parent):
        node = self.Server.get_node(f"{parent}")
        children = await node.get_children()
        try:
            for child in children:
                desc = await child.read_description()
                if desc.Text == "Channel":
                    channel = await child.get_value()
                    print(channel)
                else:
                    raise Exception
        except Exception as e:
            self.logger.exception(e)

        new_config = [None for _ in range(len(self.can_attr))]
        for attr in range(len(self.can_attr)):
            new_config[attr] = await self.can_config[channel][attr].get_value()

        config_dict = {}

        for i in range(len(self.can_attr)):
            config_dict[self.can_attr[i]] = new_config[i]

        if config_dict['Channel'] == can_config.can_0_settings['Channel']:
            can_config.can_0_settings.update(config_dict)
        elif config_dict['Channel'] == can_config.can_1_settings['Channel']:
            can_config.can_1_settings.update(config_dict)

    async def init(self, config_file: str, can_config_file: str, directory: str):
        """Setup the server and populate the address space

        :type config_file: str
        :param config_file: Configuration YAML containing active MOPS and custom init values, converter, aliases, etc.
        :rtype: None
        """
        await self.Server.init()
        self.Server.set_endpoint(self.endpoint)
        self.idx = await self.Server.register_namespace(self.namespace)
        await self._populate(config_file, can_config_file, directory)

    async def _find_in_node(self, node: Node, search_string: str):
        """Search for a variable by name in a node

        :type node: asyncua Node
        :type search_string: str
        :param node: Node that contains the variable
        :param search_string: Part of the variable name
        :return: Array of all variables that matched to the search string
        """

        async def is_string(node, string):
            return string in (await node.read_browse_name()).__str__()

        return [v for v in (await node.get_variables()) if (await is_string(v, search_string))]

    def load_configuration(self, config_file: str):
        """Load configuration YAML and insert the system defaults where the user didn't specify them. Give warning where user didn't specify a default.

        :type config_file: str
        :param config_file: Configuration YAML containing active MOPS and custom init values, converter, aliases, etc.
        :return: Dict populated with necessary default values
        """
        # Get configuration data
        fstream = open(config_file, 'r')
        data = load(fstream, Loader=Loader)
        fstream.close()
        if logging.DEBUG >= logging.root.level:
            output = dump(data, Dumper=Dumper)
            self._logger.info(f"Configured with {config_file}")
        if "Crate ID" not in data:
            self._logger.error(f"No crate ID specified in {config_file}")
            raise KeyError(f"No crate ID specified in {config_file}")
        # Check defaults
        for k in self.defaults:
            if k not in data:
                self._logger.warning(f"No {k} specified in {config_file}, using {self.defaults[k]}")
                data[k] = self.defaults[k]
        return data

    async def write_adc(self, cic_index: int, bus_index: int, adc_value: int,
                        mops_index=None, channel_index=None, cic_adc_channel=None):
        """Asynchronous write to a single ADC channel
        :rtype: None
        :type cic_index: int
        :param cic_index: Index of the CIC
        :type bus_index: int
        :param bus_index: Index of the Bus on the CIC
        :type mops_index: int
        :param mops_index: Index of the MOPS
        :type channel_index: int
        :param channel_index: Channel Index (0...31)
        :type adc_value: int
        :param adc_value: ADC value to write (int, conversion happens according to the converter field)
        :type cic_adc_channel: int
        :param cic_adc_channel: Channel of the ADC CIC
        """
        if None not in (mops_index, channel_index):
            if int in (type(mops_index), type(channel_index)):
                try:
                    adc_object = await self.find_object(
                        f"CIC {cic_index}:CANBus {bus_index}:MOPS {mops_index}:ADCChannel {channel_index:02}")
                    value_var = (await self._find_in_node(adc_object, "monitoringValue"))[0]
                    await value_var.write_value(adc_value)
                except KeyError:
                    return 0
        elif cic_adc_channel is not None:
            if type(cic_adc_channel) is int:
                try:
                    adc_object = await self.find_object(
                        f"CIC {cic_index}:CANBus {bus_index}:ADC CANBus {bus_index}:ADCChannel {cic_adc_channel:02}")
                    value_var = (await self._find_in_node(adc_object, "monitoringValue"))[0]
                    await value_var.write_value(adc_value)
                except KeyError:
                    return 0

    async def find_object(self, search_string: str) -> Node:
        """Find a server object in the node tree. Objects have to exist, otherwise a KeyError exception is raised.

        :param search_string: Search string (e.g "CIC 2:MOPS 1:ADCChannel 01")
        :return:
        """

        def error(issue):
            """Raise a KeyError exception

            :param issue: The Key that was unable to match
            """
            self._logger.error(f"Invalid key {issue} in {search_string}")
            raise KeyError(f"Invalid key {issue}")

        async def is_string(node: Node, string: str) -> bool:
            """Check if the node name matches to a search string

            :rtype: bool
            :type node: asyncua Node
            :type string: str
            :param node: The node to be search for the pattern
            :param string: The pattern to match
            :return: True if the pattern is in the browse name, else False
            """
            return string in (await node.read_browse_name()).__str__()

        search = search_string.split(":")

        cic_search = search[0]
        if "CIC" not in cic_search:
            error(cic_search)
        cic_index = int(cic_search.replace("CIC", ""))
        if self.CICs[cic_index] is None:
            error(cic_search)
        cic = self.CICs[cic_index]
        if len(search) == 1:
            return cic

        bus_search = search[1]
        if "CANBus" not in bus_search:
            error(bus_search)
        bus_index = int(bus_search.replace("CANBus", "")) - 1
        if self.Bus[bus_index] is None:
            error(bus_search)
        bus = self.Bus[bus_index]
        if len(search) == 2:
            return bus

        mops_search = search[2]
        # noinspection PyUnresolvedReferences
        mops = [node for node in await bus.get_children() if (await is_string(node, mops_search))]
        if len(mops) != 1:
            return error(mops_search)
        mops = mops[0]
        if len(search) == 2:
            return bus
        if len(search) == 3:
            return mops
        if len(search) == 4:
            result = [node for node in await mops.get_children() if (await is_string(node, search[3]))]
            if not len(result) == 1:
                error({search[3]})
            else:
                return result[0]
        error(search)

    async def _populate(self, config_file: str, can_config_file: str, directory: str):
        """Populate the address space with the server objects implied in the configuration file.

        :type config_file: str
        :rtype: None
        :param config_file: Configuration YAML containing active MOPS and custom init values, converter, aliases, etc.
        """

        # Create MOPSHUB crate object
        self.mobshub_crate_object = await self.Server.nodes.objects.add_object(self.idx, "MOPSHUB Crate")

        data = self.load_configuration(config_file)
        can_settings = AnalysisUtils().open_yaml_file(file=can_config_file, directory=directory)

        # Create crate ID variable
        await self.mobshub_crate_object.add_variable(self.idx, "Crate ID", data["Crate ID"])

        # Create Objects for configure CAN settings
        for i in range(0, 2):
            can_obj = await self.mobshub_crate_object.add_object(self.idx, f"Config CAN{i}")
            for attr in range(len(self.can_attr)):
                self.can_config[i][attr] = await can_obj.add_variable(self.idx, self.can_attr[attr],
                                                                      int(can_settings[f'channel{i}'][
                                                                              self.can_attr[attr]]))
                if self.can_attr[attr] == 'Channel':
                    await self.can_config[i][attr].set_writable(False)
                else:
                    await self.can_config[i][attr].set_writable(True)
            await can_obj.add_method(self.idx, f"Configure CAN{i}", self.configure_can)

        # Create CIC card objects
        for cic_id in range(len(self.CICs)):
            if f"CIC {cic_id}" in data:
                self.CICs[cic_id] = await self.mobshub_crate_object.add_object(self.idx, f"CIC {cic_id}")

        # Create Can Bus objects
        for cic_id, bus_id in product(range(len(self.CICs)), range(1, len(self.Bus) + 1)):
            if (self.CICs[cic_id] is not None) and (f"Bus {bus_id}" in data[f"CIC {cic_id}"]):
                cic_data = data[f"CIC {cic_id}"]
                self.Bus[bus_id - 1] = await self.CICs[cic_id].add_object(self.idx, f"CANBus {bus_id}")
                # bus_data = cic_data[f"Bus {bus_id}"]

                # Create Power Enable Child for every Bus
                pe_object = await self.Bus[bus_id - 1].add_object(self.idx, f"PE Signal CANBus {bus_id}", True)
                await pe_object.add_variable(self.idx, "Description", f"Control of th Power of Bus {bus_id}")
                await pe_object.add_variable(self.idx, "Current Status", "OFF")

                await pe_object.add_method(self.idx, f"Power Disable Bus {bus_id}",
                                           self.disable_power)

                await pe_object.add_method(self.idx, f"Power Enable Bus {bus_id}",
                                           self.enable_power)

                # Create CIC ADC Child for every Bus
                cic_adc_object = await self.Bus[bus_id - 1].add_object(self.idx, f"ADC CANBus {bus_id}")

                for channel_id in range(5):
                    channel_object = await cic_adc_object.add_object(self.idx, f"ADCChannel {channel_id:02}")

                    if channel_id == 0:
                        await channel_object.add_variable(self.idx, "Description", "UH for Current Monitoring")
                    elif channel_id == 1:
                        await channel_object.add_variable(self.idx, "Description", "UL for Current Monitoring")
                    elif channel_id == 2:
                        await channel_object.add_variable(self.idx, "Description", "Voltage Monitoring")
                    elif channel_id == 3:
                        await channel_object.add_variable(self.idx, "Description", "Temperature Monitoring")
                    elif channel_id == 4:
                        await channel_object.add_variable(self.idx, "Description", "GND Monitoring")

                    await channel_object.add_variable(self.idx, "Physical Unit", "Voltage")
                    await channel_object.add_variable(self.idx, "monitoringValue", 0.0)

        # Create MOPS objects
        for cic_id, bus_id, mops_id in product(range(len(self.CICs)), range(1, len(self.Bus) + 1), range(2)):
            if (self.CICs[cic_id] is not None) and (f"Bus {bus_id}" in data[f"CIC {cic_id}"]) and (
                    f"MOPS {mops_id}" in data[f"CIC {cic_id}"][f"Bus {bus_id}"]):

                bus_data = data[f"CIC {cic_id}"][f"Bus {bus_id}"]
                self.Mops[bus_id - 1][mops_id] = await self.Bus[bus_id - 1].add_object(self.idx, f"MOPS {mops_id}")
                mops_data = bus_data[f"MOPS {mops_id}"]

                # Specify location
                if "Location" in mops_data:
                    await self.Mops[bus_id - 1][mops_id].add_variable(self.idx, "location", mops_data["Location"])
                else:
                    await self.Mops[bus_id - 1][mops_id].add_variable(self.idx, "location",
                                                                      data["MOPS Default Location"])

                # Status and portNumber variables
                if "Status" in mops_data:
                    status_var = await self.Mops[bus_id - 1][mops_id].add_variable(self.idx, "status",
                                                                                   mops_data["Status"])
                    await status_var.set_writable()
                else:
                    status_var = await self.Mops[bus_id - 1][mops_id].add_variable(self.idx, "status",
                                                                                   data["MOPS Default Status"])
                    await status_var.set_writable()
                if "Port" in mops_data:
                    port_var = await self.Mops[bus_id - 1][mops_id].add_variable(self.idx, "portNumber",
                                                                                 mops_data["Port"])
                    await port_var.set_writable()
                else:
                    port_var = await self.Mops[bus_id - 1][mops_id].add_variable(self.idx, "portNumber",
                                                                                 data["MOPS Default Port"])
                    await port_var.set_writable()

                # Add MOPSMonitoring Object
                monitoring_object = await self.Mops[bus_id - 1][mops_id].add_object(self.idx, "MOPSMonitoring")
                await monitoring_object.add_variable(self.idx, "numberOfEntries", 0)
                await monitoring_object.add_variable(self.idx, "VBANDGAP", 0.0)
                await monitoring_object.add_variable(self.idx, "VGNDSEN", 0.0)
                await monitoring_object.add_variable(self.idx, "VCANSEN", 0.0)

                # Add MOPSConfiguration Object
                configuration_object = await self.Mops[bus_id - 1][mops_id].add_object(self.idx, "MOPSConfiguration")
                await configuration_object.add_variable(self.idx, "readFEMonitoringValues", 0.0)
                if "Trimming" in mops_data:
                    trimming_var = await configuration_object.add_variable(self.idx, "ADCTrimmingBits",
                                                                           mops_data["Trimming"])
                    await trimming_var.set_writable()
                else:
                    trimming_var = await configuration_object.add_variable(self.idx, "ADCTrimmingBits",
                                                                           data["MOPS Configuration Default Trimming"])
                    await trimming_var.set_writable()

                # Add ADC Channels
                for channel_id in range(32):
                    channel_object = await self.Mops[bus_id - 1][mops_id].add_object(self.idx,
                                                                                     f"ADCChannel {channel_id:02}")

                    if f"ADC Channel {channel_id}" in mops_data:
                        channel_data = mops_data[f"ADC Channel {channel_id}"]
                        if "Converter" not in channel_data:
                            channel_data["Converter"] = data["ADC Channel Default Converter"]
                        if "Alias" not in channel_data:
                            channel_data["Alias"] = channel_data["Converter"]

                        await channel_object.add_variable(self.idx, "Converter", channel_data["Converter"])
                        await channel_object.add_variable(self.idx, "physicalParameter", channel_data["Alias"])
                        if channel_data["Converter"] == 'Raw':
                            await channel_object.add_variable(self.idx, "monitoringValue", 0)
                        else:
                            await channel_object.add_variable(self.idx, "monitoringValue", 0.0)
                    else:
                        await channel_object.add_variable(self.idx, "Converter", data["ADC Channel Default Converter"])
                        await channel_object.add_variable(self.idx, "physicalParameter",
                                                          data["ADC Channel Default Converter"])
                        if data["ADC Channel Default Converter"] == 'Raw':
                            await channel_object.add_variable(self.idx, "monitoringValue", 0)
                        else:
                            await channel_object.add_variable(self.idx, "monitoringValue", 0.0)

    async def __aenter__(self):
        """Start server when entering a context.

        :rtype: None
        """
        await self.Server.start()

    async def __aexit__(self, exc_type=None, exc_value=None, traceback=None):
        """Stop server when exiting a context.

        :rtype: None
        """
        await self.Server.stop()
