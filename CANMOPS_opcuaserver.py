import asyncio
import logging
from logging import Logger
from canmops.mopshubCrate import MopsHubCrate
import numpy as np
#python CANMOPS_opcuaserver.py start config/config.yaml
async def main(config_file, endpoint, namespace):
    _logger: Logger = logging.getLogger('asyncua')
    mobshub_crate = MopsHubCrate(endpoint=endpoint, namespace=namespace)
    _logger.info('Starting server!')
    await mobshub_crate.init(config_file)
    async with mobshub_crate:
        while True:
            # The main CAN + SPI loop goes here!
            #cic_index [Bus] , mops_index [Node], channel_index, ADC_value
            for a in np.arange(0,32):
                await mobshub_crate.write_adc(3, 0, 31, a)
            await asyncio.sleep(0.1)


def start(configFile, endpoint='opc.tcp://0.0.0.0:4841/freeopcua/server/',
          namespace='http://examples.freeopcua.github.io'):
    """Start an OPC UA server for a given crate configuration file"""
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main(configFile, endpoint, namespace), debug=True)


if __name__ == '__main__':
    import argh
    parser = argh.ArghParser()
    parser.add_commands([start])
    parser.dispatch()
