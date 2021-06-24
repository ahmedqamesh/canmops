import asyncio
import logging
from logging import Logger

from MOPSHUBCrate import MOPSHUBCrate


async def main(config_file, endpoint, namespace):
    _logger: Logger = logging.getLogger('asyncua')
    mobshub_crate = MOPSHUBCrate(endpoint=endpoint, namespace=namespace)
    _logger.info('Starting server!')
    await mobshub_crate.init(config_file)
    async with mobshub_crate:
        while True:
            #Here will be the main SPI/CAN LOOP
            await asyncio.sleep(0.1)


def start(configFile, endpoint='opc.tcp://0.0.0.0:4840/freeopcua/server/',
          namespace='http://examples.freeopcua.github.io'):
    """Start an OPC UA server for a given crate configuration file"""
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main(configFile, endpoint, namespace), debug=True)


if __name__ == '__main__':
    import argh

    parser = argh.ArghParser()
    parser.add_commands([start])
    parser.dispatch()
    start('config/config.yaml')