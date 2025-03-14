# ADMC plugin from CMDR Laurent Yess to Squadron Manager (BGS tools)

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

import settings
import threaded





#to display text
IFFSQR: Optional[tk.Frame] = None
IFFList = []
OldBounty = 0
dir_path = ''





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
# 09/03/25 3.30 : cargo management on docked and undocked
# 11/03/25 3.31 : split code in modules and fix Deposit timestamp fixinit load Cargo and Market
# 11/03/25 3.32 : fix init Cargo and Market with market fleet bug fix shutdown remove ShutDown
# 14/03/25 3.33 : Add entry in config for bountybeep and traceSend and ShutDown

PLUGIN_NAME = 'Michelle_3.33'
  

      
this = settings.this

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
    settings.logger.info(f'Plungin {PLUGIN_NAME} load from {plugin_dir}') 
    parser = ConfigParser()
    pp = os.path.join( plugin_dir, 'config.ini')
    parser.read(pp)
    this.LogDir = parser.get('UserConfig', 'EliteLogFile')
    this.url = parser.get('UserConfig', 'SM_Adress')
    beppbeep = parser.get('UserConfig', 'HostileBeep')
    this.bountyBeep = parser.get('UserConfig', 'BountyBeep')
    this.traceSend = parser.get('UserConfig', 'TraceSend')
    listofhidden = parser.get('UserConfig', 'HiddenCMDRs').upper()
    this.userNotSend = listofhidden.split(",")
    #settings.logger.info("CMDRs not to send : "+listofhidden)
    if (beppbeep == "Beep"):
        this.dobeep = True
    if (this.url == ""):
        status = tk.Label(IFFSQR, text="Erreur url not set", foreground="red") 
        status.grid(row=0, column=1, sticky='nesw')
        return PLUGIN_NAME
    settings.logger.debug('lancement worker thread...')
    this.thread = Thread(target=threaded.worker, name='EDTFMv2', args = (this.eventtfm, ))
    this.thread.daemon = False 
    this.thread.start()
    this.threadGet = Thread(target=threaded.GetWaitter, name='EDTFMv2GET', args = (this.eventtfmGet, ))
    this.threadGet.daemon = False 
    this.threadGet.start()
    FindLog() 
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return PLUGIN_NAME

def plugin_stop() -> None:
    global this    
    if (this.f):
        this.f.close()

    #this.event = "STOP" 
    # Signal thread to close and wait for it
    this.lastlock.acquire()      
    this.dequetfm.append("STOP")  
    this.Continue = False 
    this.eventtfm.set()  
    this.lastlock.release()
   
    this.lastlockGet.acquire()      
    this.dequetfmGet.append("STOP")      
    this.eventtfmGet.set()  
    this.lastlockGet.release()
    this.thread.join()  # type: ignore
    this.threadGet.join()  # type: ignore
    settings.logger.info('Plugin STOP threads joint')
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
        settings.logger.info("Open new log file "+ this.CurrentLogFile)
    else:
        settings.logger.info("keep old log file "+ this.CurrentLogFile) 

def journal_entry(cmdrname: str, is_beta: bool, system: str, station: str, entry: dict, state: dict) -> None:
    global this
    global IFFSQR

    #settings.logger.info("receive entry "+entry["event"]
    # a tester from monitor import monitor   monitor.is_live_galaxy()

    if (this.isCheckedVer == False):
        this.isCheckedVer = True  
        if 'GameVersion' in state:
            gv = state['GameVersion']
            settings.logger.info('GameVersion ' +gv)
            gvi = int(gv[0])
            if (gvi >= 4):
                this.checkVer = True
        else:
            settings.logger.info('not found GameVersion')

        if ( this.checkVer == False):
            status = tk.Label(IFFSQR, text="Elite release must be >= 4", foreground="red",bg="black") 

    if (this.checkVer == False):
        return

    if (this.url == ""):
        status = tk.Label(IFFSQR, text="Erreur url not set", foreground="red",bg="black") 
        status.grid(row=0, column=1, sticky='nesw')
        return
    if (entry["event"] == "StartUp" or entry["event"] == "LoadGame"):
        #clean global
        settings.clean()
        settings.logger.info("Maybe new log file " +entry["event"])
        FindLog()
        #load Cargo for init : EDMC lauched,  Elite start menu (to be confirme)
        if not this.dockedCargo:
            this.dockedCargo = state['CargoJSON']
            settings.logger.info(f'read Cargo for init {this.dockedCargo}')
    

    if (this.userName != cmdrname):
        this.userName = cmdrname
        if ( cmdrname.upper() in this.userNotSend):
            this.isHidden = True
            status = tk.Label(IFFSQR, text="hidden CMDR", foreground="Yellow",bg="black") 
            status.grid(row=0, column=1, sticky='nesw')
            settings.logger.info("Commandant "+ cmdrname + " NOT SEND") 
        else:
            this.isHidden = False
            settings.logger.info("Commandant "+ this.userName)  
            vidagefile()
    else:      
        if (entry["event"] == "Shutdown"):
             settings.logger.info('receive Shutdown')
             #send shutdown to server
             forceSend(entry["event"])
             #shutdown est la dernier ecriture du log et pas fini par un CRLF donc pas lisible immediatement. 
        elif (entry["event"] == "ShutDown"):
            settings.logger.info('receive ShutDown')
            #crash game, start menu, stop game
            forceSendCrash()
        elif (entry["event"] == "Location") and (not this.MarketID):
            if ("Docked" in entry) and (entry["Docked"] == True):
                  #load marketid for init it in startup
                  this.Market_ID = entry['MarketID']
                  settings.logger.info(f'load market id for init {this.MarketID}')  
        elif (entry["event"] == "Cargo") and (not this.dockedCargo):
            #load Cargo for init : EDMC lauched, start Elite
            #settings.logger.info(f' Entry  Cargo {entry}')
            this.dockedCargo = entry
            settings.logger.info(f'read Cargo for init {this.dockedCargo}')         
            
        if this.bountyBeep:
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
    #settings.logger.info(comstatus)
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
    #settings.logger.info("in addsquad" +statsquad)
    if (lg > 7):
        del IFFList[0]
        #settings.logger.info(IFFList)
        lg =len(IFFList)
        row = int(lg/2)+1
        for i in range(0,lg):
            namesquad, fg = colorSquad(IFFList[i])
            status = tk.Label(IFFSQR, text=namesquad,fg=fg,bg="black") 
            ligne = int(i/2)
            #settings.logger.info(ligne)
            col = i%2
            #settings.logger.info(col)
            #settings.logger.info(namesquad)
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
    settings.logger.info("vidagefile")
    nbtoparse = 0
    for line in this.f:
        llastline = line.strip() 
        nbtoparse = nbtoparse +1
        txt = searchInLine(llastline[0:80])   
        if (txt != None) and (txt!="ShipTargeted"): 
            if (checkStatus(txt)):
                #settings.logger.info(llastline[0:80])
                this.lastlock.acquire()
                this.dequetfm.append(llastline)  
                this.lastlock.release()
                this.eventtfm.set()

    displayTxtok("fin lecture log")            
    settings.logger.info(f"fin vidagefile ({nbtoparse})" )
    if (nbtoparse < 200):
        time.sleep(0.2) 

def forceSend(shutdown):
    global this 
    if (this.isHidden == False):
       if (this.shutdown == False): 
            checkStatus(shutdown)
            this.shutdown = True
            #lline = this.f.readline()
            lline = this.f.read()
            settings.logger.info(f' ForceSend {lline}')   
            this.lastlock.acquire()
            this.dequetfm.append(lline)
            this.lastlock.release()
            if (this.eventtfm.is_set()):
                time.sleep(3)
            this.eventtfm.set() 
def forceSendCrash():
    global this 
    if (this.isHidden == False):
       if (this.shutdown == False): 
            checkStatus('ShutDown')
            this.shutdown = True
            lline = this.f.readline()
            llineC = lline[0:46] + 'Shutdown'
            settings.logger.info(f' ForceSend crash  {llineC}')  
            this.lastlock.acquire()
            this.dequetfm.append(llineC)
            this.lastlock.release()
            if (this.eventtfm.is_set()):
                time.sleep(3)
            this.eventtfm.set() 

def checkbounty(entry):
    global OldBounty
    global dir_path
    #settings.logger.info(entry)
    if "Bounty" in entry:
        settings.logger.info(f'Bounty  :  {entry["Bounty"]}')
        bounty = entry["Bounty"]
        if bounty > 1000000:
            if OldBounty != bounty :
                OldBounty = bounty
                winsound.PlaySound(dir_path+'\\bounty.wav',winsound.SND_FILENAME|winsound.SND_ASYNC)
                #winsound.PlaySound(dir_path+'\\bounty.wav',winsound.SND_FILENAME)

def cestpartie():
    global this 
    global IFFList
    #settings.logger.info("cestpartie")
    for line in this.f:
        llastline = line.strip()
        txt = searchInLine(llastline[0:80])  
        #settings.logger.info(txt) 
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
                            #settings.logger.debug(pname +"( "+ squadName+ " ) -> "+  PilotName_Localised_N)
                            if (not asklocal( squadName, PilotName_Localised_N )):
                                if this.isHidden:
                                    #add directly to status and exit
                                    squad = squadName,"Unkwown"
                                    addSquadStat(squad)
                                else: 
                                    if checkStatus("Search cmdr "+pname):
                                        #settings.logger.debug("Pilote Name / Squad recherche : "+pname+ " " + squadName)
                                        this.lastlockGet.acquire()
                                        this.dequetfmGet.append(llastlineN)
                                        lng = len(this.dequetfmGet)
                                        this.lastlockGet.release()
                                        if (this.eventtfmGet.is_set()):
                                            settings.logger.debug("Getset event set, add to list")
                                            settings.logger.debug(lng)
                                            return
                                        else:
                                            this.eventtfmGet.set() 
                                    else:
                                        #add directly to status and exit
                                        squad = squadName,"Unkwown"
                                        addSquadStat(squad)
                            else:
                                settings.logger.debug("Pilote Name / Squad already here: "+PilotName_Localised_N+ " " + squadName)

            elif (checkStatus(txt)): 
                #settings.logger.info(f'read from file {llastline}')
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
            #settings.logger.info("Find " + txt)
            return ev
    #settings.logger.info("NOT Find " + txt)    
    return None




  
