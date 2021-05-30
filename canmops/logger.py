import coloredlogs
import os
import sys
import time
import datetime
import logging
import colorlog
FORMAT = '%(log_color)s%(asctime)s -  [%(levelname)-7s] - %(message)s'
class Logger(object):
    def __init__(self):
        pass
    
    def setup_main_logger(self,name='CANMOPS', console_loglevel=logging.INFO):
        #Set color  
        streamhandler = colorlog.StreamHandler(sys.stderr)
        streamhandler.setLevel(console_loglevel)
        formatter = colorlog.ColoredFormatter(FORMAT)
        streamhandler.setFormatter(formatter)
        logger = logging.getLogger(name)
        if not len(logger.handlers):
            #Add Logger level
            logger.setLevel(console_loglevel)
            self._add_success_level(logger)
            self._add_notice_level(logger)
                
            logger.propagate = False    
            logger.addHandler(streamhandler)    
        return logger
    
    
    
    def setup_derived_logger(self,name, level=logging.INFO):
        logger = logging.getLogger(name)
        logger.setLevel(level)
    
        _setup_coloredlogs(logger)
        _add_success_level(logger)
        _add_notice_level(logger)
    
        _add_logfiles_to(logger)
    
        return logger
    
    
    
    
    def setup_logfile(self,filename, level=logging.INFO):
        fh = logging.FileHandler(filename)
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter(FORMAT))
    
        return fh
    
    
    def add_logfile_to_loggers(self,fh):
        # Add filehandler to all active loggers
        for lg in logging.Logger.manager.loggerDict.values():
            if isinstance(lg, logging.Logger):
                lg.addHandler(fh)
    
    
    def _add_logfiles_to(self,logger):
        fhs = []
        for lg in logging.Logger.manager.loggerDict.values():
            if isinstance(lg, logging.Logger):
                for handler in lg.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        fhs.append(handler)
    
        for fh in fhs:
            logger.addHandler(fh)
    
    
    def close_logfile(self,fh):
        # Remove filehandler from all active loggers
        for lg in logging.Logger.manager.loggerDict.values():
            if isinstance(lg, logging.Logger):
                lg.removeHandler(fh)
    
    
    def _setup_coloredlogs(self,logger):
        loglevel = logger.getEffectiveLevel()
        coloredlogs.DEFAULT_FIELD_STYLES = {'asctime': {},
                                            'hostname': {},
                                            'levelname': {'bold': True},
                                            'name': {},
                                            'programname': {}}
        coloredlogs.DEFAULT_LEVEL_STYLES = {'critical': {'color': 'red', 'bold': True},
                                            'debug': {'color': 'magenta'},
                                            'error': {'color': 'red', 'bold': True},
                                            'info': {},
                                            'success': {'color': 'green'},
                                            'notice': {'color': 'blue'},
                                            'warning': {'color': 'yellow'}}
        coloredlogs.DEFAULT_LOG_LEVEL = loglevel
    
        coloredlogs.install(fmt=FORMAT, milliseconds=True, loglevel=loglevel)
    
    
    def _add_success_level(self,logger):
        logging.SUCCESS = 35
        logging.addLevelName(logging.SUCCESS, 'SUCCESS')
        logger.success = lambda msg, *args, **kwargs: logger.log(logging.SUCCESS, msg, *args, **kwargs)
    
    
    def _add_notice_level(self,logger):
        logging.NOTICE = 25
        logging.addLevelName(logging.NOTICE, 'NOTICE')
        logger.notice = lambda msg, *args, **kwargs: logger.log(logging.NOTICE, msg, *args, **kwargs)
    
    def _reset_all_loggers(self):
        logging.root.handlers = []

    