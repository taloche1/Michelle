import logging
from config import appname
import os
import threading
from threading import Thread, Event
from collections import deque
import tkinter as tk

# This could also be returned from plugin_start3()
plugin_name = os.path.basename(os.path.dirname(__file__))
# A Logger is used per 'found' plugin to make it easy to include the plugin's
# folder name in the logging output format.
# NB: plugin_name here *must* be the plugin's folder name as per the preceding
#     code, else the logger won't be properly set up.
logger = logging.getLogger(f'{appname}.{plugin_name}')

class This:
    def __init__(self):
        self.system_link: tk.Widget = None
        self.thread = None
        self.threadGet = None
        self.userName:str = ""
        self.dockedCargo = None
        self.MarketID = None
        self.userNotSend:str = []
        self.isHidden = False
        self.url:str = ""
        self.eventtfm = Event()
        self.eventtfmGet = Event()
        self.lastlock = threading.Lock()
        self.dequetfm = deque(maxlen=1000)
        self.lastlockGet = threading.Lock()
        self.dequetfmGet = deque(maxlen=1000)
        self.lastlockGetResp = threading.Lock()
        self.dequetfmGetResp = deque(maxlen=1000)
        self.f = None
        self.LogDir = ""
        self.CurrentLogFile = ""
        self.Continue = True
        self.ComStatus = 0  #0 inconnu, 1 ok, 2 erreur de com
        self.dobeep = False
        self.isCheckedVer = False
        self.checkVer = False 
        self.shutdown = False

this = This()


def init():
    # If the Logger has handlers then it was already set up by the core code, else
    # it needs setting up here.
    if not logger.hasHandlers():
        level = logging.INFO  # So logger.info(...) is equivalent to print()

        logger.setLevel(level)
        logger_channel = logging.StreamHandler()
        logger_formatter = logging.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')
        logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
        logger_formatter.default_msec_format = '%s.%03d'
        logger_channel.setFormatter(logger_formatter)
        logger.addHandler(logger_channel)

def clean():
     this.dockedCargo = None
     this.MarketID = None
     this.userName = ""
     this.shutdown = False
