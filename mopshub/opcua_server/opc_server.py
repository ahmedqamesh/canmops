import asyncua
import logging
import sys

from logging import Logger
from asyncua import Node
from EventNotifier import Notifier

from additional_scripts import logger_setup
from opcua_server.populate_address_space import POPULATEAddressSpace
from opcua_server.find_node_id import FINDNodeID

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
sys.path.insert(0, "../..")


class MOPSHUBCrate(POPULATEAddressSpace, FINDNodeID):
    def __init__(self, endpoint: str = 'opc.tcp://0.0.0.0:4840/freeopcua/server/',
                 namespace: str = 'http://examples.freeopcua.github.io', *args, **kwargs):
        """Constructor for MOPSHUBCrate
        :type namespace: str
        :type endpoint: str
        :param endpoint: The server endpoint (hint: 127.0.0.1 hosts on YOUR machine,
                         0.0.0.0 exposes the server to the network as well)
        :param namespace: The namespace
        """

        self.Server = asyncua.Server()
        POPULATEAddressSpace.__init__(self, self.Server)
        FINDNodeID.__init__(self, self.CICs, self.Bus, self.Mops)
        self.endpoint = endpoint
        self.namespace = namespace

        self.logger = logging.getLogger('mopshub_log.crate')
        self._logger: Logger = logging.getLogger('asyncua')

        logging.basicConfig(level=logging.DEBUG)

    async def init(self, config_file: str, can_config_file: str, directory: str):
        """Setup the server and populate the address space
        :type config_file: str
        :param config_file: Configuration YAML containing active MOPS and custom init values, converter, aliases, etc.
        :type can_config_file: str
        :param can_config_file: Configuration YAML containing the settings of the CAN interfaces
        :type directory: str
        :param directory: Directory of the YAML configuration file for the CAN interfaces
        :rtype: None
        """

        await self.Server.init()
        self.Server.set_endpoint(self.endpoint)
        self.idx = await self.Server.register_namespace(self.namespace)
        await self.populate(config_file, can_config_file, directory)

    async def write_mops_adc(self, cic_index, bus_index, mops_index, channel_index, adc_value):
        try:
            adc_object = await self.find_object(
                f"CIC {cic_index}:CANBus {bus_index}:MOPS {mops_index}:ADCChannel {channel_index:02}")
            value_var = (await self.find_in_node(adc_object, "monitoringValue"))[0]
            await value_var.write_value(adc_value)
        except KeyError:
            return 0

    async def write_cic_adc(self, cic_index, bus_index, channel_index, adc_value):
        try:
            adc_object = await self.find_object(f"CIC {cic_index}:CANBus {bus_index}:ADC CANBus {bus_index}:ADCChannel "
                                                f"{channel_index:02}")
            value_var = (await self.find_in_node(adc_object, "monitoringValue"))[0]
            await value_var.write_value(adc_value)
        except KeyError:
            return 0

    async def write_pe_status(self, cic_index, bus_index, status: str):
        try:
            pe_object = await self.find_object(f"CIC {cic_index}:CANBus {bus_index}:PE Signal CANBus {bus_index}")
            status_var = (await self.find_in_node(pe_object, "Current Status"))[0]
            await status_var.write_value(status)
        except KeyError:
            return 0

    async def write_mops_monitoring(self, cic_index, bus_index, mops_index, channel_name, adc_value):
        try:
            adc_object = await self.find_object(
                f"CIC {cic_index}:CANBus {bus_index}:MOPS {mops_index}:MOPSMonitoring")
            value_var = (await self.find_in_node(adc_object, channel_name))[0]
            await value_var.write_value(adc_value)
        except KeyError:
            return 0

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
