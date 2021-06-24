from logging import Logger
import asyncua
import asyncio
import logging
import sys
from yaml import load, dump
from itertools import product
from asyncua import Node
from CANWrapper import CANWrapper, wrapper
from CICreadout import CICreadout, adc

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
sys.path.insert(0, "..")


class MOPSHUBCrate(CANWrapper, CICreadout):
    def __init__(self, endpoint: str = 'opc.tcp://127.0.0.1:4840/freeopcua/server/',
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
        self._logger: Logger = logging.getLogger('asyncua')
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

    async def init(self, config_file: str):
        """Setup the server and populate the address space

        :type config_file: str
        :param config_file: Configuration YAML containing active MOPS and custom init values, converter, aliases, etc.
        :rtype: None
        """
        await self.Server.init()
        self.Server.set_endpoint(self.endpoint)
        self.idx = await self.Server.register_namespace(self.namespace)
        await self._populate(config_file)

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
            self._logger.info(output)
        if "Crate ID" not in data:
            self._logger.error(f"No crate ID specified in {config_file}")
            raise KeyError(f"No crate ID specified in {config_file}")
        # Check defaults
        for k in self.defaults:
            if k not in data:
                self._logger.warning(f"No {k} specified in {config_file}, using {self.defaults[k]}")
                data[k] = self.defaults[k]
        return data

    async def write_adc(self, cic_index: int, mops_index: int, channel_index: int, adc_value: int):
        """Asynchronous write to a single ADC channel

        :rtype: None
        :type cic_index: int
        :param cic_index: Index of the CIC
        :type mops_index: int
        :param mops_index: Index of the MOPS
        :type channel_index: int
        :param channel_index: Channel Index (0...31)
        :type adc_value: int
        :param adc_value: ADC value to write (int, conversion happens according to the converter field)
        """
        adc_object = await self.find_object(f"CIC {cic_index}:MOPS {mops_index}:ADCChannel {channel_index:02}")
        value_var = (await self._find_in_node(adc_object, "monitoringValue"))[0]
        # converter = await (await self._find_in_node(adc_object, "Converter"))[0].get_value()
        # await value_var.write_value(self.converters[converter](adc_value))
        await value_var.write_value(adc_value)

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
        mops_search = search[1]
        # noinspection PyUnresolvedReferences
        mops = [node for node in await cic.get_children() if (await is_string(node, mops_search))]
        if len(mops) != 1:
            return error(mops_search)
        mops = mops[0]
        if len(search) == 2:
            return mops
        if len(search) == 3:
            result = [node for node in await mops.get_children() if (await is_string(node, search[2]))]
            if not len(result) == 1:
                error({search[2]})
            else:
                return result[0]
        error(search)

    async def _populate(self, config_file: str):
        """Populate the address space with the server objects implied in the configuration file.

        :type config_file: str
        :rtype: None
        :param config_file: Configuration YAML containing active MOPS and custom init values, converter, aliases, etc.
        """
        # Create MOPSHUB crate object
        self.mobshub_crate_object = await self.Server.nodes.objects.add_object(self.idx, "MOPSHUB Crate")

        data = self.load_configuration(config_file)
        # Create crate ID variable
        await self.mobshub_crate_object.add_variable(self.idx, "Crate ID", data["Crate ID"])

        # Create CIC card objects
        for cic_id in range(4):
            if f"CIC {cic_id}" in data:
                self.CICs[cic_id] = await self.mobshub_crate_object.add_object(self.idx, f"CIC {cic_id}")

        # Create Can Bus objects
        for cic_id, bus_id in product(range(4), range(1,33)):
            if (self.CICs[cic_id] is not None) and (f"Bus {bus_id}" in data[f"CIC {cic_id}"]):
                cic_data = data[f"CIC {cic_id}"]
                self.Bus[bus_id-1] = await self.CICs[cic_id].add_object(self.idx, f"CANBus {bus_id}")
                bus_data = cic_data[f"Bus {bus_id}"]

                cic_adc_object = await self.Bus[bus_id-1].add_object(self.idx, f"ADC CANBus {bus_id}")

                pe_object = await cic_adc_object.add_object(self.idx, "Power Enable")
                #await pe_object.add_variable(self.idx, "Description", "Power Enable Signal CIC.")
                #await pe_object.add_variable(self.idx, "Datatype", "Boolean")
                await pe_object.add_variable(self.idx, "Monitoring Value", True)

                current_object = await cic_adc_object.add_object(self.idx, "Current Monitoring")
                #await current_object.add_variable(self.idx, "Description", "Current Monitoring UI = UH - UL")
                #await current_object.add_variable(self.idx, "Physical Parameter", "V")
                await current_object.add_variable(self.idx, "Monitoring Value UH", 0.0)
                await current_object.add_variable(self.idx, "Monitoring Value UL", 0.0)

                voltage_object = await cic_adc_object.add_object(self.idx, "Voltage Monitoring")
                #await voltage_object.add_variable(self.idx, "Description", "Voltage Monitoring")
                #await voltage_object.add_variable(self.idx, "Physical Parameter", "V")
                await voltage_object.add_variable(self.idx, "Monitoring Value", 0.0)

                gnd_object = await cic_adc_object.add_object(self.idx, "GND")
                #await gnd_object.add_variable(self.idx, "Description", "GND Monitoring")
                await gnd_object.add_variable(self.idx, "Monitoring Value", 0.0)

                temperature_object = gnd_object = await cic_adc_object.add_object(self.idx, "Temperature")
                #await temperature_object.add_variable(self.idx, "Description", "Temperature Monitoring")
                #await temperature_object.add_variable(self.idx, "Physical Parameter", "V")
                await temperature_object.add_variable(self.idx, "Monitoring Value", 0.0)
                #await temperature_object.add_variable(self.idx, "Converted Value Unit", "°C")
                await temperature_object.add_variable(self.idx, "Converted Value", 0.0)


        # Create MOPS objects
        for cic_id, bus_id, mops_id in product(range(4), range(1,33), range(2)):
            if (self.CICs[cic_id] is not None) and (f"Bus {bus_id}" in data[f"CIC {cic_id}"]) and (f"MOPS {mops_id}" in data[f"CIC {cic_id}"][f"Bus {bus_id}"]):

                bus_data = data[f"CIC {cic_id}"][f"Bus {bus_id}"]
                mops_object = await self.Bus[bus_id-1].add_object(self.idx, f"MOPS {mops_id}")
                mops_data = bus_data[f"MOPS {mops_id}"]

                # Specify location
                if "Location" in mops_data:
                    await mops_object.add_variable(self.idx, "location", mops_data["Location"])
                else:
                    await mops_object.add_variable(self.idx, "location", data["MOPS Default Location"])

                # Status and portNumber variables
                if "Status" in mops_data:
                    status_var = await mops_object.add_variable(self.idx, "status", mops_data["Status"])
                    await status_var.set_writable()
                else:
                    status_var = await mops_object.add_variable(self.idx, "status", data["MOPS Default Status"])
                    await status_var.set_writable()
                if "Port" in mops_data:
                    port_var = await mops_object.add_variable(self.idx, "portNumber", mops_data["Port"])
                    await port_var.set_writable()
                else:
                    port_var = await mops_object.add_variable(self.idx, "portNumber", data["MOPS Default Port"])
                    await port_var.set_writable()

                # Add MOPSMonitoring Object
                monitoring_object = await mops_object.add_object(self.idx, "MOPSMonitoring")
                await monitoring_object.add_variable(self.idx, "numberOfEntries", 0)
                await monitoring_object.add_variable(self.idx, "VBANDGAP", 0.0)
                await monitoring_object.add_variable(self.idx, "VGNDSEN", 0.0)
                await monitoring_object.add_variable(self.idx, "VCANSEN", 0.0)

                # Add MOPSConfiguration Object
                configuration_object = await mops_object.add_object(self.idx, "MOPSConfiguration")
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
                    channel_object = await mops_object.add_object(self.idx, f"ADCChannel {channel_id:02}")

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

    async def __aexit__(self, exc_type, exc_value, traceback):
        """Stop server when exiting a context.

        :rtype: None
        """
        await self.Server.stop()


async def main(config_file):
    """Setup a MOBSHUBCrate and start the main asynchronous loop

    :type config_file: str
    :rtype: None
    :param config_file: Configuration YAML containing active MOPS and custom init values, converter, aliases, etc.
    """
    _logger: Logger = logging.getLogger('asyncua')
    mobshub_crate = MOPSHUBCrate()
    _logger.info('Starting server!')
    res = adc.read_adc(0, 31, 1)
    await mobshub_crate.init(config_file)
    async with mobshub_crate:
        i = 0
        while True:
            crate_index = 0
            cic_index = 0
            mops_index = 1
            mp_channel = 31
            can_channel = 1
            logging.info('Reading from MOPS with NodeID %s on Crate %s and CIC %s', mops_index, crate_index, cic_index)

            #         SDO_TX = 0x600
            #         SDO_RX = 0x580
            #         nodeId = 1
            #         wrapper.read_sdo_can_thread(nodeId, index=0x1000, subindex=0, timeout=3000, SDO_TX=SDO_TX,
            #                                    SDO_RX=SDO_RX, cobid = SDO_TX+nodeId)

            readout = wrapper.read_adc_channels("MOPS_cfg.yml", "config", mops_index, mp_channel, can_channel)
            # This Function writes to the Nodes of the OPC UA Server
            # cic_index: int, mops_index: int, channel_index: int, adc_value: int
            if readout is not None:
                for i in range(len(readout)):
                    adc_index = readout[i][0]
                    value = readout[i][1]
                    print(readout[i])
                    await mobshub_crate.write_adc(cic_index, mops_index, adc_index, value)
            logging.info('Readout finished')
            await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(main("config/config.yaml"), debug=True)
