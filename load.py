
from xml.etree.ElementPath import get_parent_map
import requests
from requests.exceptions import ConnectTimeout
import json
import logging
import os
import threading
import time
import unicodedata
from configparser import ConfigParser

from threading import Thread, Event, Timer
from collections import deque


from config import appname
from config import config

from typing import Optional, Tuple
import tkinter as tk
import winsound




# This could also be returned from plugin_start3()
plugin_name = os.path.basename(os.path.dirname(__file__))
#to display text
IFFSQR: Optional[tk.Frame] = None
IFFList = []
OldBounty = 0
dir_path = ''


# A Logger is used per 'found' plugin to make it easy to include the plugin's
# folder name in the logging output format.
# NB: plugin_name here *must* be the plugin's folder name as per the preceding
#     code, else the logger won't be properly set up.
logger = logging.getLogger(f'{appname}.{plugin_name}')

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


# 08/05/22 2.1 : replace userId by cmdname from frontier log
# 11/05/22 2.2 : add squadron name event send to server
# 24/05/22 2.3 : stop read and send frontier log when stopping, add error loop when send to no responding server, set timeout to 10s
# 05/06/22 2.4 : delete read cmdname for config.txt add lock send if erreur and erreur generique
# 08/06/22 2.5 : add event SellExobiologyData, BlackMarketSell, RedeemVouncher
# 14/05/22 2.6 : Add display status and stop working if server not responding, add timer between correct send to server
# 14/05/22 2.7 : change startup logic, change error logic
# 15/05/22 2.8 : change selected event methode to get event name from file, optimize startup
# 28/10/22 3.0 : Add request for scan IFF squadron name.
# 30/10/22 3.1 : fix ecrasement affichage
# 07/11/22 3.2 : fix timer cancel
# 11/11/22 3.3 : reduce sleep to 1 sec between send
# 08/12/22 3.4 : Add wanted status for CMD.
# 15/12/22 3.5 : Fix bad event send in getter (no receive response from server when cyrilic in json ...)
# 20/01/23 3.6 : change in core EDMC for parent.children
# 30/01/23 3.7 : optimize beep when red object
# 16/04/23 3.8 : optional beep in config
# 19/04/23 3.9 : fix cmd username
# 24/04/23 3.10 : renove patch for cyrilic, encod utf-16, add check version >= 4. 
# 11/07/23 3.11 : don't send to SM if cmdr name in config and add config file style ini
# 02/08/23 3.12 : fix hidden cmdr and (no) display squad tag and add missionfailed 
# 04/09/23 3.13 : add special for shutdown because last in file without CR/LF
# 15/02/24 3.20 : change detection crash server et reprise des com
# 16/02/24 3.21 : Fix normal display
# 28/02/24 3.22 : Log Squad if SM is offline
# 11/02/25 3.23 : bip on bounty sup a 1M
# 09103/25 3.30 : cargo management on docked and undocked



PLUGIN_NAME = 'Michelle_3.30'

class This:
    def __init__(self):
        self.system_link: tk.Widget = None
        self.thread = None
        self.threadGet = None
        self.threadCargo = None
        self.userName:str = ""
        self.Market_ID = 0
        self.userNotSend:str = []
        self.isHidden = False
        self.url:str = ""
        self.eventtfm = Event()
        self.eventtfmGet = Event()
        self.eventtfmCargo = Event()
        self.lastlock = threading.Lock()
        self.dequetfm = deque(maxlen=1000)
        self.lastlockGet = threading.Lock()
        self.dequetfmGet = deque(maxlen=1000)
        self.lastlockGetResp = threading.Lock()
        self.dequetfmGetResp = deque(maxlen=1000)
        self.lastlockCargo = threading.Lock()
        self.f = None
        self.LogDir = ""
        self.CurrentLogFile = ""
        self.Continue = True
        self.ComStatus = 0  #0 inconnu, 1 ok, 2 erreur de com
        self.dobeep = False
        self.isCheckedVer = False
        self.checkVer = False     

      
this = This()

def plugin_app(parent: tk.Frame) -> tk.Frame:
    """
    Create a pair of TK widgets for the EDMarketConnector main window
    """
    global PLUGIN_NAME
    global IFFSQR
    IFFSQR = tk.Frame(parent)
   
    label = tk.Label(IFFSQR, text=PLUGIN_NAME+" : ")  # By default widgets inherit the current theme's colors
    label.grid(row=0, column=0, sticky=tk.W)
    status = tk.Label(IFFSQR, text="Lecture log", foreground="yellow")  # Override theme's foreground color
    status.grid(row=0, column=1, sticky='nesw')
    this.system_link = parent.nametowidget(f".{appname.lower()}.system")
    this.system_link.bind_all('<<RETIFF>>', ret_event)
    this.system_link.bind_all('<<RETERNO>>', ret_erno)
    return IFFSQR

def plugin_start3(plugin_dir: str) -> str: 
    global this
    global PLUGIN_NAME
    global IFFSQR
    global dir_path
    logger.info(f'Plungin {PLUGIN_NAME} load from {plugin_dir}') 
    parser = ConfigParser()
    pp = os.path.join( plugin_dir, 'config.ini')
    parser.read(pp)
    this.LogDir = parser.get('UserConfig', 'EliteLogFile')
    this.url = parser.get('UserConfig', 'SM_Adress')
    beppbeep = parser.get('UserConfig', 'HostileBeep')
    listofhidden = parser.get('UserConfig', 'HiddenCMDRs').upper()
    this.userNotSend = listofhidden.split(",")
    #logger.info("CMDRs not to send : "+listofhidden)
    if (beppbeep == "Beep"):
        this.dobeep = True
    if (this.url == ""):
        status = tk.Label(IFFSQR, text="Erreur url not set", foreground="red") 
        status.grid(row=0, column=1, sticky='nesw')
        return PLUGIN_NAME
    logger.debug('lancement worker thread...')
    this.thread = Thread(target=worker, name='EDTFMv2', args = (this.eventtfm, ))
    this.thread.daemon = False 
    this.thread.start()
    this.threadGet = Thread(target=GetWaitter, name='EDTFMv2GET', args = (this.eventtfmGet, ))
    #this.threadGet = Thread(target=GetWaitterForTest, name='EDTFMv2GET', args = (eventtfmGet, ))
    this.threadGet.daemon = False 
    this.threadGet.start()
    this.threadCargo = Thread(target=workerCargo, name='EDTFMv2Cargo', args = (this.eventtfmCargo, ))
    this.threadCargo.daemon = False 
    this.threadCargo.start()
    FindLog() 
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return PLUGIN_NAME

def plugin_stop() -> None:
    global this    
    if (this.f):
        this.f.close()

    # Signal thread to close and wait for it
    this.lastlock.acquire()      
    this.dequetfm.append("STOP")  
    this.Continue = False 
    this.eventtfm.set()  
    this.lastlock.release()

    this.lastlockCargo.acquire()      
    this.dequetfmCargo.append("STOP")  
    this.eventtfmCargo.set()  
    this.lastlockCargo.release()

    this.lastlockGet.acquire()      
    this.dequetfmGet.append("STOP")      
    this.eventtfmGet.set()  
    this.lastlockGet.release()
    this.thread.join()  # type: ignore
    this.threadGet.join()  # type: ignore
    logger.info('Plugin STOP threads joint')
    this.thread = None
    this.threadGet = None
    return 

def FindLog():
    global this
    this.userName = ""
    this.isCheckedVer = False
    files = [os.path.join(this.LogDir, x) for x in os.listdir(this.LogDir) if x.endswith(".log")]
    newest = max(files , key = os.path.getctime)
    if (newest != this.CurrentLogFile):
        # close old log , open new
        if (this.f):
            this.f.close
        this.f = open(newest,"r")
        this.CurrentLogFile = newest
        logger.info("Open new log file "+ this.CurrentLogFile)
    else:
        logger.info("keep old log file "+ this.CurrentLogFile) 

def journal_entry(cmdrname: str, is_beta: bool, system: str, station: str, entry: dict, state: dict) -> None:
    global this
    global IFFSQR

    logger.debug("receive "+entry["event"])

    # a tester from monitor import monitor   monitor.is_live_galaxy()

    if (this.isCheckedVer == False):
        this.isCheckedVer = True  
        if 'GameVersion' in state:
            gv = state['GameVersion']
            logger.info('GameVersion ' +gv)
            gvi = int(gv[0])
            if (gvi >= 4):
                this.checkVer = True
        else:
            logger.info('not found GameVersion')

        if ( this.checkVer == False):
            status = tk.Label(IFFSQR, text="Elite release must be >= 4", foreground="red",bg="black") 

    if (this.checkVer == False):
        return

    if (this.url == ""):
        status = tk.Label(IFFSQR, text="Erreur url not set", foreground="red",bg="black") 
        status.grid(row=0, column=1, sticky='nesw')
        return
    if (entry["event"] == "StartUp" or entry["event"] == "LoadGame"):
        logger.info("Maybe new log file " +entry["event"])
        this.userName = ""
        FindLog()

    if (this.userName != cmdrname):
        this.userName = cmdrname
        if ( cmdrname.upper() in this.userNotSend):
            this.isHidden = True
            status = tk.Label(IFFSQR, text="hidden CMDR", foreground="Yellow",bg="black") 
            status.grid(row=0, column=1, sticky='nesw')
            logger.info("Commandant "+ cmdrname + " NOT SEND") 
        else:
            this.isHidden = False
            logger.info("Commandant "+ this.userName)  
            vidagefile()
    else:
        if (entry["event"].lower() == "shutdown"):
            forceSend(entry["event"])
            #shutdown est la dernier ecriture du log et pas fini par un CRLF donc pas lisible immediatement.
        else:
           if (entry["event"].lower() == "docked"):
                this.eventtfmCargo.set() 
           checkbounty(entry)
           cestpartie()

def displayTxtok(txt):
    global IFFSQR

    status = tk.Label(IFFSQR, text=txt, foreground="green", bg="black") 
    status.grid(row=0, column=1, sticky='nesw')
          
def checkStatus(txt):
    global this

    if (this.isHidden == True):
            return False
    this.lastlock.acquire()
    comstatus = this.ComStatus
    this.lastlock.release()
    #logger.info(comstatus)
    if (comstatus == 0):
        return True
    elif (comstatus == 1):       
        if (txt != None):
            displayTxtok("Send "+txt)
        return True
    return False

#for IFF display
def beep():
    global this
    if (this.dobeep):
        frequency = 1250  # Set Frequency in Hertz
        duration = 150  # Set Duration in ms
        winsound.Beep(frequency, duration)  
def colorSquad(squad):
    namesquad, statsquad = squad
    if (statsquad == "Ally"):
        fg = "green"
    elif (statsquad == "Enemy") or (statsquad == "Wanted"):
        fg = "red"
    else:
        fg = "yellow"
    return namesquad, fg
def asklocal(squadname, piloteName):
    global IFFList
    for squad in IFFList:
        namesquad, fg = colorSquad(squad)
        if (namesquad == squadname ) or (namesquad == piloteName):
            return True
    return False  
def askdouble(squadname):
    global IFFList
    for squad in IFFList:
        namesquad, fg = colorSquad(squad)
        if (namesquad == squadname ):
            return True
    return False            
def addSquadStat(squad):
    global IFFSQR
    global IFFList
    #row = IFFSQR.grid_size()[1]
    lg =len(IFFList)
    row = int(lg/2)+1
    namesquad, statsquad = squad
    # pour eviter que le meme squad/name soit prit en double entre cestpartie et le thread de requete
    if (askdouble(namesquad)):
        return
    #logger.info("in addsquad" +statsquad)
    if (lg > 7):
        del IFFList[0]
        #logger.info(IFFList)
        lg =len(IFFList)
        row = int(lg/2)+1
        for i in range(0,lg):
            namesquad, fg = colorSquad(IFFList[i])
            status = tk.Label(IFFSQR, text=namesquad,fg=fg,bg="black") 
            ligne = int(i/2)
            #logger.info(ligne)
            col = i%2
            #logger.info(col)
            #logger.info(namesquad)
            status.grid(row=ligne+1, column=col, sticky='nesw')
        namesquad, fg = colorSquad(squad)
        status = tk.Label(IFFSQR, text=namesquad,fg=fg,bg="black") 
        status.grid(row=row, column=(lg)%2, sticky='nesw')        
    else:
        namesquad, fg = colorSquad(squad)
        status = tk.Label(IFFSQR, text=namesquad,fg=fg,bg="black") 
        status.grid(row=row, column=lg%2, sticky='nesw') 
    IFFList.append(squad)
    if (fg == "red"):
        beep()  
def ret_event(event=None) -> None: 
    squadlist = []
    this.lastlockGetResp.acquire()
    while (True):
        squadlist.append(this.dequetfmGetResp.popleft())
        if (len(this.dequetfmGetResp) == 0):
            break
    this.lastlockGetResp.release() 
    for squad in squadlist:
        addSquadStat(squad)
#fin IFF display
        
#for display error com
def ret_erno(event=None) -> None:
    global IFFSQR
    global this

    this.lastlock.acquire()
    comstatus = this.ComStatus
    this.lastlock.release()
    if (comstatus == 2):
        status = tk.Label(IFFSQR, text="Erreur "+this.url, foreground="red",bg="black") 
        status.grid(row=0, column=1, sticky='nesw')
    if (comstatus == 1):
        status = tk.Label(IFFSQR, text="Reprise des communications", foreground="green",bg="black") 
        status.grid(row=0, column=1, sticky='nesw')  
#fin display erreur com

def vidagefile():
    global this 
    logger.info("vidagefile")
    nbtoparse = 0
    for line in this.f:
        llastline = line.strip() 
        nbtoparse = nbtoparse +1
        txt = searchInLine(llastline[0:80])   
        if (txt != None) and (txt!="ShipTargeted"): 
            if (checkStatus(txt)):
                #logger.info(llastline[0:80])
                this.lastlock.acquire()
                this.dequetfm.append(llastline)  
                this.lastlock.release()
                this.eventtfm.set()

    displayTxtok("fin lecture log")            
    logger.info(f"fin vidagefile ({nbtoparse})" )
    if (nbtoparse < 200):
        time.sleep(0.2) 
    #Test()

def forceSend(shutdown):
    global this 
    logger.info("force send "+shutdown)
    if this.isHidden == False: 
        checkStatus(shutdown)
        lline = this.f.readline()
        #logger.info("1 "+lline)   
        this.lastlock.acquire()
        this.dequetfm.append(lline)
        this.lastlock.release()
        if (this.eventtfm.is_set()):
            return
        else:
            this.eventtfm.set() 

def checkbounty(entry):
    global OldBounty
    global dir_path
    #logger.info(entry)
    if "Bounty" in entry:
        logger.info(f'Bounty  :  {entry["Bounty"]}')
        bounty = entry["Bounty"]
        if bounty > 10000:
            if OldBounty != bounty :
                OldBounty = bounty
                winsound.PlaySound(dir_path+'\\bounty.wav',winsound.SND_FILENAME|winsound.SND_ASYNC)
                #winsound.PlaySound(dir_path+'\\bounty.wav',winsound.SND_FILENAME)

def cestpartie():
    global this 
    global IFFList
    #logger.info("cestpartie")
    for line in this.f:
        llastline = line.strip()
        txt = searchInLine(llastline[0:80])  
        logger.info(txt) 
        if (txt != None):
            if (txt == "ShipTargeted"):
                j = json.loads(llastline)
                #if (j["TargetLocked"] == True) and (j["ScanStage"] == 1):
                if (j["TargetLocked"] == True) and (j["ScanStage"] > 0):
                    if ("PilotName_Localised") in j : 
                        pname = j["PilotName_Localised"]
                        if (pname.startswith("CMD")):
                            llastlineN = llastline
                            PilotName_Localised_N = pname
                            #search for squadron name or cmd name
                            if ("SquadronID" in j):
                                squadName = j["SquadronID"]
                            else:
                                squadName = "None"
                            #logger.debug(pname +"( "+ squadName+ " ) -> "+  PilotName_Localised_N)
                            if (not asklocal( squadName, PilotName_Localised_N )):
                                if this.isHidden:
                                    #add directly to status and exit
                                    squad = squadName,"Unkwown"
                                    addSquadStat(squad)
                                else: 
                                    if checkStatus("Search cmdr "+pname):
                                        #logger.debug("Pilote Name / Squad recherche : "+pname+ " " + squadName)
                                        this.lastlockGet.acquire()
                                        this.dequetfmGet.append(llastlineN)
                                        lng = len(this.dequetfmGet)
                                        this.lastlockGet.release()
                                        if (this.eventtfmGet.is_set()):
                                            logger.debug("Getset event set, add to list")
                                            logger.debug(lng)
                                            return
                                        else:
                                            this.eventtfmGet.set() 
                                    else:
                                        #add directly to status and exit
                                        squad = squadName,"Unkwown"
                                        addSquadStat(squad)
                            else:
                                logger.info("Pilote Name / Squad already here: "+PilotName_Localised_N+ " " + squadName)

            elif (checkStatus(txt)):             
                this.lastlock.acquire()
                this.dequetfm.append(llastline)
                this.lastlock.release()
                if (this.eventtfm.is_set()):
                    return
                else:
                    this.eventtfm.set() 
            
def searchInLine(line):
    #MyList = ["FSDJump", "Docked", "Undocked","ShipTargeted", "ShipyardSwap", "MarketSell", "MissionAccepted", "MissionCompleted", "MultiSellExplorationData", "SellExplorationData", "SearchAndRescue", "SellMicroResources", "SellOrganicData", "RedeemVoucher", "CommitCrime", "Died", "PVPKill", "Missions", "Location", "SquadronStartup" ]
    MyList = [ "FSDJump", "ShipTargeted", "Docked", "Undocked", "Embark", "Disembark", "ShipyardSwap", "ShipLocker", "MarketSell", "MissionAccepted", "MissionCompleted", "MissionFailed", "MultiSellExplorationData", "RedeemVoucher", "SellExplorationData", "SearchAndRescue", "CommitCrime", "CarrierJumpCancelled", "CarrierJumpRequest", "CarrierStats", "Died", "PVPKill", "LauchDrone", "Materials", "Rank", "Progress", "Reputation", "EngineerProgress", "SquadronStartup", "LoadGame", "Location", "Powerplay", "Missions","StoredShips" ] 
    #MyList = [ "fsdjump", "shiptargeted", "docked", "undocked", "embark", "disembark", "shipyardswap", "shiplocker", "marketsell", "missionaccepted", "missioncompleted", "missionfailed", "multisellexplorationdata", "redeemvoucher", "sellexplorationdata", "searchandrescue", "commitcrime", "carrierjumpcancelled", "carrierjumprequest", "carrierstats", "died", "pvpkill", "lauchdrone", "materials", "rank", "progress", "reputation", "engineerprogress", "squadronstartup", "loadgame", "location", "powerplay", "missions","storedships", "shutdown" ] 
   
   
    indicedeb = line.find("event")
    if (indicedeb == -1):
        return None
    indicedeb = indicedeb + 8
    sub = line[indicedeb:]
    indicefin = sub.find(",")
    if (indicefin == -1):
        return None
    indicefin = indicefin -1
    txt = sub[:indicefin]
    for ev in MyList:
        if (ev == txt):
            #logger.info("Find " + txt)
            return ev
    #logger.info("NOT Find " + txt)    
    return None

def SendToServer(lline):
    Erreur = False
    global this
    #logger.info("SendTo server" + lline)
    try:           
        params = {'userName': this.userName}  
        newHeaders = {'Content-type': 'application/json; charset=UTF-8', 'Accept': 'application/json'}
        x = requests.post(this.url,params=params,data=lline.encode('utf-8'),headers=newHeaders, timeout=(3,6))  #10 second timeout
        if (x is None):
            logger.error("Pas de reponse")
            erreur = True
        else:
            logger.info(f"return status : {x.status_code}")
            if (x.status_code != 200):
                erreur = True
            else:
                erreur = False
                time.sleep(1) 
    except requests.ConnectionError as err:
        logger.error("Cannot connected to "+ this.url)
        erreur = True
    except requests.Timeout as errt:
        logger.error("Timeout Error") 
        erreur = True
    except requests.exceptions.RequestException as e:
        logger.error(f'Erreur a la transmission vers le serveur EDTFM {e.args}')
        erreur = True
    except requests.exceptions.RequestException as e:
        logger.error(f'Erreur générique')
        erreur = True   
    return erreur

def worker(in_s):
    global this
    local_loop = 0
    logger.info(this.url)
    logger.info("worker init")
    Continue = True
    Erreur = False
    while Continue :
        logger.info(f'worker waiting')
        if this.eventtfm.wait():
            logger.info(f'worker running')
            llinelist = []  
            this.lastlock.acquire()
            while (len(this.dequetfm) > 0):
                llinelist.append(this.dequetfm.popleft())
            this.lastlock.release() 
            this.eventtfm.clear()
            for lline in llinelist: 
                #logger.info(f'receive : {lline[0:80]}')
                if (lline == ""):  
                    logger.debug("None")
                    erreur = False
                elif (lline=="STOP"):
                    logger.info('Stop worker')
                    erreur = False
                    Continue = False
                    break
                else :
                    erreur = True
                    while (erreur == True and this.Continue == True):
                        #logger.info("SendTo server" + lline)   
                        this.lastlock.acquire()
                        comstatusl = this.ComStatus
                        this.lastlock.release() 
                        erreur = SendToServer(lline)
                        if erreur: 
                            if comstatusl != 2:
                                this.lastlock.acquire()
                                this.ComStatus = 2
                                this.lastlock.release()  
                                comstatusl = 2
                                this.system_link.event_generate('<<RETERNO>>', when='now' )                    
                            #stop send to serveur for 10 seconds x 6 (10 sec for permit stop app) try resend lline after
                            for number in range(6):
                                time.sleep(10)
                                local_loop = local_loop +1
                            # on ne sort jamais sauf correction de erreur de com du while
                            if config.shutting_down:
                                erreur = False
                        else:
                            if comstatusl != 1:
                                this.lastlock.acquire()
                                this.ComStatus = 1
                                this.lastlock.release() 
                                if comstatusl == 2:
                                    this.system_link.event_generate('<<RETERNO>>', when='now' )   
                                comstatusl =1
                                #logger.info("comstatus set to 1 ")              
    logger.info('fin worker')

def workerCargo(in_s):
    global this
    local_loop = 0
    logger.info("workerCargo init")
    Continue = True
    Erreur = False
    while Continue :
        logger.info(f'workerCargo waiting')
        if this.eventtfmCargo.wait():
            logger.info(f'workerCargo running')
            this.eventtfmCargo.clear()
            if config.shutting_down:
                Continue = False
            else : 
                #if docked take marketid and cargo.json
                with open('C:\Users\Laurent\Saved Games\Frontier Developments\Elite Dangerous', 'r') as file:
                    dockedCargo = json.load(file)
                    logger.info(f'old json : {dockedCargo}')
                #if undocked compare old json with new one
                #erreur = SendToServerCargo(lline)
                  
                                  
    logger.info('fin workerCargo')
def GetSendToServer(lline):
    global this
    #logger.info("GetSendToServer " + lline )
    try:        
        paramse = {'userName': this.userName}  
        newHeaders = {'Content-type': 'application/json', 'Accept': 'application/json'}
        #newHeaders = {'Content-type': 'application/text; charset=UTF-8', 'Accept': 'application/json'}
        logger.debug("request")
        x = requests.get(this.url, params=paramse,data=lline.encode('utf-8'),headers=newHeaders, timeout=(1,3))
        logger.debug("end request")
        time.sleep(1)
        if (x is None):
            logger.debug("Pas de reponse")
            x.close()
            return True, "None"
        else:
            logger.info(f"Response GET : {x.text}")
            rep = x.text
            #x.close()
            if (x.status_code != 200):
                return True, rep
            else:
                return False, rep
    except requests.ConnectionError as err:
        logger.debug("Cannot connected to "+ this.url)
        return True, "None"
    except requests.Timeout as errt:
        logger.debug("Timeout Error") 
        return True, "None"
    except requests.exceptions.RequestException as e:
        logger.debug(f'Erreur a la transmission vers le serveur EDTFM {e.args}')
        return True, "None"
    return True, "None"

def GetWaitter(in_s):
    global this
    local_loop = 0
    logger.info("GetWaitter init")
    Continue = True
    Erreur = False

    while Continue :
        logger.info(f'GetWaitter waiting')
        if this.eventtfmGet.wait():
            logger.info(f'GetWaitter running')  
            llinelist = []
            this.lastlockGet.acquire()
            while (len(this.dequetfmGet) > 0):
                llinelist.append(this.dequetfmGet.popleft())
            this.lastlockGet.release()
            #mis ici car parfois pas dereponse a request et donc pas de debloquage du event
            logger.debug("release get sem")
            this.eventtfmGet.clear()

            Currentlist =[]  
            #nb = 0         
            for lline in llinelist:
                logger.info(f'receive : {lline[0:80]}')
                logger.debug(len(llinelist))
                #nb = nb+1
                #logger.debug(nb)
                if (lline == ""):  
                    logger.debug("None")
                    erreur = False
                elif (lline=="STOP"):
                    logger.info('Stop GetWaitter')
                    erreur = False
                    Continue = False
                    break
                else :
                    j = json.loads(lline)
                    if (j["PilotName_Localised"] in Currentlist):
                        logger.debug("skip "+ j["PilotName_Localised"]+ "already in list")
                    else:
                        Currentlist.append(j["PilotName_Localised"])
                        erreur, answere = GetSendToServer(lline)
                        if erreur: 
                            logger.info("error GetSendToServer")
                            # this.lastlockGet.acquire()
                            # this.ComStatus = 2
                            # this.lastlockGet.release()                        
                        else:
                            #logger.debug(answere)
                            toGo = False
                            if (answere == "Wanted"):
                                logger.info(j["PilotName_Localised"] + " Wanted")
                                squad = (j["PilotName_Localised"], answere)
                                toGo = True
                            elif ("SquadronID" in j):
                                squad = (j["SquadronID"], answere)
                                toGo = True
                            if (toGo):
                                this.lastlockGetResp.acquire()
                                this.dequetfmGetResp.append(squad)
                                this.lastlockGetResp.release()
                                this.system_link.event_generate('<<RETIFF>>', when='now' )  
                                #logger.info("GetWaitter send to IHM "+ answere)
            #logger.debug("fin du traitement lline")
           
            #in_s.clear() 
            # if (Continue):                                                        
    logger.info('fin GetWaitter') 



def Test():
    global eventtfmGet
    test_event_generate("LOSP", "Ally")
    
    test_event_generate("LOSP1", "Unkwown")
   
    test_event_generate("LOSP2", "Enemy")
   
    test_event_generate("LOSP3", "Ally")
   
    test_event_generate("LOSP4", "Unkwown")
    
    test_event_generate("LOSP5", "Enemy")
   
    test_event_generate("LOSP6", "Ally")
   
    test_event_generate("LOSP7", "Unkwown")
   
    test_event_generate("LOSP8", "Enemy")
def test_event_generate(stat, iff):
    global this 
    global eventtfmGet
   
    logger.info("Test "+ stat + " " + iff)
    if (asklocal(stat)):
        logger.info("found "+ stat) 
    else:   
        logger.info("not found "+ stat)
        this.lastlockGet.acquire()
        squad = stat, iff
        this.dequetfmGet.append(squad)
        this.lastlockGet.release()
        if (eventtfmGet.is_set()):
            return
        else:
            eventtfmGet.set()         
def GetWaitterForTest(in_s):
    global this
    global ws
    local_loop = 0
    logger.info("GetWaitterForTest init")
    Erreur = False
    Continu = True
    while Continu:
        logger.info(f'GetWaitterForTest waitting')
        if in_s.wait():
            logger.info(f'GetWaitterForTest running')  
            llinelist = []
            this.lastlockGet.acquire()
            while (len(this.dequetfmGet) > 0):
                llinelist.append(this.dequetfmGet.popleft())
            this.lastlockGet.release() 
          
        for lline in llinelist:
                    if (lline == ""):  
                        logger.debug("None")
                        erreur = False
                    elif (lline=="STOP"):
                        logger.info('Stop GetWaitterForTest')
                        Continu = False
                        break 
                    else :
                        erreur = False
                        name, stat = lline
                        squad = name, stat
                        this.lastlockGetResp.acquire()
                        this.dequetfmGetResp.append(squad)
                        this.lastlockGetResp.release()
        if (Continu):
            in_s.clear()  
            #this.system_link.event_generate('<<RETIFF>>', when='tail' )  
            this.system_link.event_generate('<<RETIFF>>')  
           
           
    logger.info('fin GetWaitterForTest')
  
