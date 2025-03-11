from load import this
import os
import time
import json
import unicodedata
import requests
from requests.exceptions import ConnectTimeout
import settings
#from settings import This

this = settings.this


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

def workerCargo(in_s):
    global this
    
    settings.logger.info("workerCargo init")
    Continue = True
    Erreur = False
    fname = os.path.join(this.LogDir,'Cargo.json')
    table = []
    while Continue :
        settings.logger.info(f'worker Cargo waiting')
        if this.eventtfmCargo.wait():
            eventr = this.event
            this.event = ""
            marketr = this.Market_ID
            settings.logger.info(f'workerCargo running receive {eventr} for Market {marketr}')             
            if eventr == "Docked":
                #if docked take marketid and cargo.json
                try:
                    filej = open(fname, 'r') 
                    dockedCargo = json.load(filej)
                    filej.close()
                except:
                    settings.logger.info('worker Cargo Erreur loading Cargo.json')   
            elif eventr == "Undocked":
                #if undocked compare old json with new one
                # si pas vide au depart
                readok = True
                try:
                    cc = dockedCargo["Count"]
                except:
                    settings.logger.info('cannot read dockedcargo from memory')
                    readok = False
                if readok:
                    if (cc > 0):
                        try:
                            filej = open(fname, 'r') 
                            undockedCargo = json.load(filej)
                            filej.close()
                        except:
                            settings.logger.info('worker Cargo Erreur loading Cargo.json')
                        #settings.logger.info(dockedCargo)
                        #settings.logger.info(undockedCargo)
                        tete = {}
                        tete['timestamp'] = undockedCargo['timestamp']
                        tete['event'] = 'Deposit'
                        tete['marketId'] = marketr
                        table.append(tete)
                        transactions = []
                        transactions = get_diff(dockedCargo, undockedCargo)
                        #settings.logger.info(transactions)
                        tete['commodities'] = transactions  
                        jsonout = json.dumps(tete)
                        #jsonoutstrip = jsonout.replace('"','')
                        settings.logger.info(jsonout)
                        # send to SM
                        erreur = SendToServer(jsonout)
                        if (erreur):
                            settings.logger.info(f'cannot send Cargo to serveur')
                    
            elif eventr == "STOP":
                Continue = False
                break 
            else:
                settings.logger.info('receive nawak')
                settings.logger.info(eventr)
            this.eventtfmCargo.clear()     
                                  
    settings.logger.info('fin workerCargo')

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
                countout = item["Count"] - itemout['Count'] 
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




