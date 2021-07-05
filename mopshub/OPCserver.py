import asyncio
import logging
import logger_setup
import argh
from itertools import product
import time

from MOPSHUBCrate import MOPSHUBCrate
from CICreadout import CICreadout
from CANWrapper import CANWrapper, can_config
from PEconfig import PEconfig, power_signal


class OPCServer:
    """description of class"""

    def __init__(self):

        self.cic_card = CICreadout()
        self.maxRatings = [100, 100, 100, 100, 100]
        self.minRatings = [-1, -1, -1, -1, -1]

        self.logger = logging.getLogger('mopshub_log.opc')

    async def main(self, config_file, can_config_file, directory, endpoint, namespace):

        mopshub_crate = MOPSHUBCrate(endpoint=endpoint, namespace=namespace)
        wrapper = CANWrapper()
        data = mopshub_crate.load_configuration(config_file)

        self.logger.info('Starting Server')
        # _logger.info('Starting server!')
        await mopshub_crate.init(config_file, can_config_file, directory)

        # Confirming Nodes
        confirmed_nodes = [[None for x in range(2)] for y in range(len(mopshub_crate.Bus))]

        for cic_id, bus_id, mops_id in product(range(4), range(1, 33), range(2)):
            if (mopshub_crate.CICs[cic_id] is not None) and (
                    f"Bus {bus_id}" in data[f"CIC {cic_id}"]) and (
                    f"MOPS {mops_id}" in data[f"CIC {cic_id}"][f"Bus {bus_id}"]) and \
                    power_signal.locked_by_sys[bus_id - 25] is False:

                wrapper.mp_switch(bus_id, 1)
                confirmed_nodes[bus_id - 1][mops_id] = wrapper.confirm_nodes(1, mops_id)

        async with mopshub_crate:
            while True:
                for cic_id, bus_id, mops_id in product(range(4), range(1, 33), range(2)):
                    if (mopshub_crate.CICs[cic_id] is not None) and (
                            f"Bus {bus_id}" in data[f"CIC {cic_id}"]) and (
                            f"MOPS {mops_id}" in data[f"CIC {cic_id}"][f"Bus {bus_id}"]) and (
                            power_signal.locked_by_sys[bus_id - 25] is False) and (
                            power_signal.locked_by_user[bus_id - 25] is False):

                        # confirmed_nodes[bus_id - 1][mops_id] is False) and (

                        can_channel = 1  # it is important to specify when we want to use which can channel as
                        # there is no difference between can1 and can2 at the end

                        # exact specification for: mops_index, channel_index, adc_value, cic_adc_channel, cic_adc_value
                        readout_mops = wrapper.read_adc_channels("mops_config.yml", "config", mops_id,
                                                                 bus_id, can_channel)
                        readout_adc = self.cic_card.read_adc(0, bus_id, 1)

                        if readout_mops is not None:
                            self.logger.info('Writing MOPS Readout to their nodes')
                            for i in range(len(readout_mops)):
                                if readout_mops[i][0] < 32:
                                    adc_index = readout_mops[i][0]
                                    value = readout_mops[i][1]
                                    # exact specification for: mops_index, channel_index, cic_adc_channel
                                    await mopshub_crate.write_adc(cic_id, bus_id, mops_index=mops_id,
                                                                  channel_index=adc_index, adc_value=value)
                        if readout_adc is not None:
                            self.logger.info('Writing CIC Readout to their nodes')
                            for i in range(len(readout_adc)):
                                value = readout_adc[i]
                                # exact specification for: mops_index, channel_index, cic_adc_channel
                                await mopshub_crate.write_adc(cic_id, bus_id, cic_adc_channel=i, adc_value=value)

                self.logger.info('Readout finished')
                await asyncio.sleep(0.1)

    def start_system(self):
        """
        Start the System by first checking all CIC cards and check their Power status.
        After that we going to confirm all Mops Nodes by their given ID
        :return: STATUS: Good = True, Bad = False
        """

        power_signal.set_power_off()
        power_signal.memory_mode()
        power_signal.mp_switch(27, 1)
        for i in range(len(power_signal.current_status_table)):
            error_cnt = 0
            # power_signal.addressable_latch_mode(i, 0)
            if i < 6 or i == 7:
                power_signal.addressable_latch_mode(i, 0)
                print(f"Power Bus {i + 25} ON")
            elif i == 6:
                power_signal.addressable_latch_mode(i, 1)
                print(f"Power Bus {i + 25} ON")
            power_signal.memory_mode()
            time.sleep(0.1)
            readout_adc = self.cic_card.read_adc(0, i, 1)
            time.sleep(0.1)
            for j in range(len(readout_adc)):
                if error_cnt == 0:
                    if readout_adc[j] >= self.maxRatings[j] or readout_adc[j] < 0:
                        self.logger.error(f"On Bus {i + 25} the ADC Value of Channel {j} is out of "
                                          f"the recommended specification")
                        print(f"ADC CHANNEL {j}: {self.cic_card.channel_value[j]}={readout_adc[j]} is not GOOD ERROR "
                              f"Bus {i + 25}")
                        # power_signal.addressable_latch_mode(i, 1)
                        if i < 6 or i == 7:
                            power_signal.addressable_latch_mode(i, 1)
                            power_signal.locked_by_sys[i] = True
                        elif i == 6:
                            power_signal.addressable_latch_mode(i, 0)
                            power_signal.locked_by_sys[i] = True
                        power_signal.memory_mode()
                        error_cnt += 1
                    elif readout_adc[j] == 0 and j in range(0, len(readout_adc) - 1):
                        self.logger.warning(f"Could not connect to ADC on Bus {i + 25}")
                        power_signal.addressable_latch_mode(i, 1)
                        if i < 8 or i == 7:
                            power_signal.addressable_latch_mode(i, 1)
                            power_signal.locked_by_sys[i] = True
                        elif i == 6:
                            power_signal.addressable_latch_mode(i, 0)
                            power_signal.locked_by_sys[i] = True
                        power_signal.memory_mode()
                        error_cnt += 1

            if error_cnt == 0:
                self.logger.info(f"Bus {i} was approved and can be used")
                power_signal.locked_by_sys[i] = False
                print(readout_adc)
            else:
                self.logger.info(f"Bus {i} failed approving process and is locked")
                power_signal.locked_by_sys[i] = True

        print(power_signal.current_status_table)
        print("Locked by sys:", power_signal.locked_by_sys)
        print("Locked by user:", power_signal.locked_by_user)


def start(config_file, can_config_file, directory, endpoint='opc.tcp://0.0.0.0:4840/freeopcua/server/',
          namespace='http://examples.freeopcua.github.io'):
    """Start an OPC UA server for a given crate configuration file"""
    asyncio.run(opc.main(config_file, can_config_file, directory,  endpoint, namespace), debug=True)


if __name__ == '__main__':
    # subprocess.call(['setup.sh'])
    opc = OPCServer()

    opc.start_system()

    parser = argh.ArghParser()
    parser.add_commands([start])
    parser.dispatch()
    start('config/server_config.yaml', 'can_config.yml', 'config')
