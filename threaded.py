#from load import this
import os
import time
import json
import unicodedata
import requests
from requests.exceptions import ConnectTimeout
import settings
#from config import config
from datetime import datetime
#from settings import This
import autoupdater

this = settings.this

def check_version():
    global this
    auto_updater = autoupdater.AutoUpdater()
    last_version = auto_updater.get_version()
    settings.logger.info(f'current version {this.currentversion} server : {last_version}')
    if this.currentversion < last_version:
        settings.logger.info('Update pending')
    #if this.currentversion != last_version:
        this.updatepending = True

def SendToServer(lline):
    Erreur = False
    global this
    #settings.logger.info("SendTo server" + lline)
    try:           
        params = {'userName': this.userName}  
        newHeaders = {'Content-type': 'application/json; charset=UTF-8', 'Accept': 'application/json'}
        x = requests.post(this.url,params=params,data=lline.encode('utf-8'),headers=newHeaders, timeout=(3,6))  #10 second timeout
        if (x is None):
            settings.logger.error("Pas de reponse")
            erreur = True
        else:
            if (x.status_code != 200):
                erreur = True
                settings.logger.info(f"return status : {x.status_code}")
            else:
                erreur = False
                time.sleep(1) 
    except requests.ConnectionError as err:
        settings.logger.error("Cannot connected to "+ this.url)
        erreur = True
    except requests.Timeout as errt:
        settings.logger.error("Timeout Error") 
        erreur = True
    except requests.exceptions.RequestException as e:
        settings.logger.error(f'Erreur a la transmission vers le serveur EDTFM {e.args}')
        erreur = True
    except requests.exceptions.RequestException as e:
        settings.logger.error(f'Erreur generique')
        erreur = True   
    return erreur

def SendLine(lline):
    global this
    erreur = True
    this.lastlock.acquire()
    comstatusl = this.ComStatus
    this.lastlock.release() 
    while (erreur == True and this.Continue == True):
        #settings.logger.info("SendTo server" + lline)       
        erreur = SendToServer(lline)
        if erreur: 
            settings.logger.warning("Cannot connect to server retry in 30s")
            if comstatusl != 2:
                this.lastlock.acquire()
                this.ComStatus = 2
                this.lastlock.release()  
                comstatusl = 2
                this.system_link.event_generate('<<RETERNO>>', when='now' )                    
            #stop send to serveur for 10 seconds x 3 (10 sec for permit stop app) try resend lline after
            for number in range(3):
                time.sleep(10)
                #settings.logger.warning("waite 10s")
            # on ne sort jamais sauf correction de erreur de com du while
                if  this.Continue == False:
                    erreur = False
                    break
        else:
            if comstatusl == 2:
                this.lastlock.acquire()
                this.ComStatus = 1
                this.lastlock.release() 
                if comstatusl != 1:
                    this.system_link.event_generate('<<RETERNO>>', when='now' )   
                comstatusl =1
                #settings.logger.info("comstatus set to 1 ")         
            elif comstatusl == 0:
                this.lastlock.acquire()
                this.ComStatus = 1
                this.lastlock.release() 

def worker(in_s):
    global this
    check_version()
    fname = os.path.join(this.LogDir,'Cargo.json')
    local_loop = 0
    #settings.logger.info(this.url)
    settings.logger.info("worker init")
    Continue = True
    Erreur = False
    loadjson = False
    locationfirst = True
    #TEST log in file
    if this.traceSend:
        testname =  os.path.join(this.LogDir,'logSend.txt')
        #open(testname, 'w').close()
        now = datetime.now()
        dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
        logt = open(testname, 'a')
        logt.write(f'New session {dt_string}\n\n\n')
    while Continue :
        settings.logger.info(f'worker waiting')
        if this.eventtfm.wait():
            settings.logger.info(f'worker running')
            llinelist = []  
            this.lastlock.acquire()
            while (len(this.dequetfm) > 0):
                llinelist.append(this.dequetfm.popleft())
            this.lastlock.release() 
            this.eventtfm.clear()
            settings.logger.info(f'{len(llinelist)} items to send')
            for lline in llinelist: 
                match lline:
                    case "":
                        #settings.logger.debug("None")
                        erreur = False
                    case "STOP":
                        settings.logger.info('Stop worker')
                        erreur = False
                        Continue = False
                        break
                    case "RESTART":
                        loadjson = False
                        settings.logger.info('Restart debut vidage file')
                        if this.traceSend:
                            logt.write('Restart debut vidage file'+"\n")
                    case "FINFILE":
                        loadjson = True
                        locationfirst = True
                        #prend ici pour le retour start menu mais marche pas pour le start du jeux
                        time.sleep(2)
                        try:
                            filej = open(fname, 'r') 
                            this.dockedCargo = json.load(filej)
                            filej.close()
                        except:
                            settings.logger.error('Erreur loading Cargo.json') 
                        if this.traceSend:
                            logt.write('Fin vidage file'+"\n")
                            logt.write(f'dockedCargo (finfile) {this.dockedCargo} '+"\n")
                            logt.flush() 
                        settings.logger.info("Fin vidagefile")
                    case _:  
                        if loadjson:
                            try:
                                jj = json.loads(lline)
                            except:
                                settings.logger.error(f'Cannot load {lline} in json')
                                continue
                            #settings.logger.info(f'receive from q : {jj}')
                            settings.logger.debug(jj['event']) 
                            match jj['event']:
                                case 'Location':
                                    if ('Docked' in jj):
                                        if (jj["Docked"] == True):
                                            #load marketid for init it in startup
                                            this.MarketID = jj['MarketID']
                                            #settings.logger.info(f'load market id for init {this.MarketID}')   
                                            if this.traceSend:
                                                logt.write(f'Marketid {this.MarketID}'+"\n")
                                                logt.flush()
                                    #settings.logger.info(f'load market id for init {this.MarketID}') 
                                    #prend ici pour le pour le start du jeux, apres finFile
                                    # c'est finfile ou premier location pares si il existe
                                    if (locationfirst):
                                        locationfirest = False
                                        time.sleep(4)
                                        try:
                                            filej = open(fname, 'r') 
                                            this.dockedCargo = json.load(filej)
                                            filej.close()
                                        except:
                                            settings.logger.error('Erreur loading Cargo.json') 
                                        if this.traceSend:
                                            logt.write(f'dockedCargo (location)  {this.dockedCargo} '+"\n")
                                            logt.flush() 
                                case 'Docked':
                                    #if docked take cargo.json
                                    ## le fichier json n'est pas encore pret, il peut contenir les ancienne valeur
                                    time.sleep(2)
                                    try:
                                        filej = open(fname, 'r') 
                                        this.dockedCargo = json.load(filej)
                                        filej.close()
                                    except:
                                        settings.logger.info('Erreur loading Cargo.json') 
                                        continue
                                    this.MarketID = jj['MarketID']
                                    if this.traceSend:
                                        logt.write(f'dockedCargo Marketid {this.dockedCargo} {this.MarketID}'+"\n")
                                        logt.flush()
                                case 'Undocked' | 'Shutdown':
                                    #if undocked compare old json with new one
                                    # si pas vide au depart
                                    #settings.logger.info(f'avant {dockedCargo}')
                                    if this.traceSend:
                                        logt.write('Cargo avant  '+json.dumps(this.dockedCargo)+"\n")
                                        logt.flush()
                                    if this.dockedCargo:
                                        cc = this.dockedCargo["Count"]
                                        table = []
                                        if (cc > 0):
                                            ## le fichier json n'est pas encore pret, il peut contenir les ancienne valeur
                                            time.sleep(2)
                                            try:
                                                filej = open(fname, 'r') 
                                                undockedCargo = json.load(filej)
                                                filej.close()
                                            except:
                                                settings.logger.error('worker Cargo Erreur loading Cargo.json')
                                                continue
                                            #settings.logger.info(f'apres {undockedCargo}')
                                            if (undockedCargo):
                                                tete = {}
                                    
                                                tete['timestamp'] = jj['timestamp']
                                                tete['event'] = 'Deposit'
                                                if ('MarketID' in jj) :
                                                    tete['marketId'] = jj['MarketID']
                                                else:
                                                    tete['marketId'] = this.MarketID
                                                    if (not this.MarketID):
                                                        settings.logger.warning('cannot read MarketID from memory')
                                                table.append(tete)
                                                transactions = [] 
                                                transactions = get_diff(this.dockedCargo, undockedCargo)
                                                if this.traceSend:
                                                    logt.write('Cargo apres  '+json.dumps(undockedCargo)+"\n")
                                                    logt.write('MarketID apres  '+str(tete['marketId'])+"\n")
                                                    logt.write('transactions  '+json.dumps(transactions)+"\n")
                                                if (transactions):
                                                    #settings.logger.info(transactions)
                                                    tete['commodities'] = transactions  
                                                    jsonout = json.dumps(tete)
                                                    #jsonoutstrip = jsonout.replace('"','')
                                                    settings.logger.info(jsonout)
                                                    if this.traceSend:
                                                        ts = str(time.time())
                                                        logt.writelines(ts + ' '+jsonout+"\n")
                                                        logt.flush()
                                                    SendLine(jsonout)
                    
                                        else:
                                            if this.traceSend:
                                                logt.write('Undocked ou Shutdown avec Cargo vide au moment du docked\n')
                                    else:
                                        settings.logger.warning('cannot read dockedcargo from memory')
                        if this.traceSend:
                            ts = str(time.time())
                            logt.writelines(ts + ' '+lline+"\n")
                            logt.flush()
                        #settings.logger.info(lline)
                        SendLine(lline)
                                
    settings.logger.info('fin worker')
    if this.traceSend:
        logt.close()

def GetSendToServer(lline):
    global this
    #settings.logger.info("GetSendToServer " + lline )
    try:        
        paramse = {'userName': this.userName}  
        newHeaders = {'Content-type': 'application/json', 'Accept': 'application/json'}
        #newHeaders = {'Content-type': 'application/text; charset=UTF-8', 'Accept': 'application/json'}
        #settings.logger.debug("request")
        x = requests.get(this.url, params=paramse,data=lline.encode('utf-8'),headers=newHeaders, timeout=(1,3))
        #settings.logger.debug("end request")
        time.sleep(1)
        if (x is None):
            settings.logger.debug("Pas de reponse")
            x.close()
            return True, "None"
        else:
            #settings.logger.info(f"Response GET : {x.text}")
            rep = x.text
            #x.close()
            if (x.status_code != 200):
                return True, rep
            else:
                return False, rep
    except requests.ConnectionError as err:
        settings.logger.debug("Cannot connected to "+ this.url)
        return True, "None"
    except requests.Timeout as errt:
        settings.logger.debug("Timeout Error") 
        return True, "None"
    except requests.exceptions.RequestException as e:
        settings.logger.debug(f'Erreur a la transmission vers le serveur EDTFM {e.args}')
        return True, "None"
    return True, "None"

def GetWaitter(in_s):
    global this
    local_loop = 0
    settings.logger.info("GetWaitter init")
    Continue = True
    Erreur = False

    while Continue :
        settings.logger.info(f'GetWaitter waiting')
        if this.eventtfmGet.wait():
            settings.logger.info(f'GetWaitter running')  
            llinelist = []
            this.lastlockGet.acquire()
            while (len(this.dequetfmGet) > 0):
                llinelist.append(this.dequetfmGet.popleft())
            this.lastlockGet.release()
            #mis ici car parfois pas dereponse a request et donc pas de debloquage du event
            #settings.logger.debug("release get sem")
            this.eventtfmGet.clear()

            Currentlist =[]  
            #nb = 0         
            for lline in llinelist:
                #settings.logger.info(f'receive : {lline[0:80]}')
                #settings.logger.debug(len(llinelist))
                #nb = nb+1
                #settings.logger.debug(nb)
                if (lline == ""):  
                    settings.logger.debug("None")
                    erreur = False
                elif (lline=="STOP"):
                    settings.logger.info('Stop GetWaitter')
                    erreur = False
                    Continue = False
                    break
                else :
                    j = json.loads(lline)
                    if (j["PilotName_Localised"] in Currentlist):
                        #settings.logger.debug("skip "+ j["PilotName_Localised"]+ "already in list")
                        pass
                    else:
                        Currentlist.append(j["PilotName_Localised"])
                        erreur, answere = GetSendToServer(lline)
                        if erreur: 
                            settings.logger.info("error GetSendToServer")
                            # this.lastlockGet.acquire()
                            # this.ComStatus = 2
                            # this.lastlockGet.release()                        
                        else:
                            #settings.logger.debug(answere)
                            toGo = False
                            if (answere == "Wanted"):
                                #settings.logger.info(j["PilotName_Localised"] + " Wanted")
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
                                #settings.logger.info("GetWaitter send to IHM "+ answere)
            #settings.logger.debug("fin du traitement lline")
           
            #in_s.clear() 
            # if (Continue):                                                        
    settings.logger.info('fin GetWaitter') 

def get_diff(dockedCargo, undockedCargo):
     table = []
     bingo = False
        
     # for each item in dockedCargo at docking :
     for item in dockedCargo['Inventory']:
        name = item['Name']
        #settings.logger.info(name)
        # is present in cargo at undocking ?
        for itemout in undockedCargo['Inventory']:
            #settings.logger.info(itemout['Name'])
            if name == itemout['Name']:
                bingo = True
                # combien en reste il ?
                countout = item['Count'] - itemout['Count'] 
                if countout > 0 :
                    #on met ca en caisse
                    transactions = {}
                    transactions['name'] = name
                    transactions['sell'] = countout
                    table.append(transactions)
        if (bingo == False):
            transactions = {}
            transactions['name'] = name
            transactions['sell'] = item["Count"]
            table.append(transactions)
        bingo = False
     return table




