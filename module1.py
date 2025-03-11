from load import logger
import os

def workerCargo(in_s):
    global this
    local_loop = 0
    logger.info("workerCargo init")
    Continue = True
    Erreur = False
    fname = os.path.join(this.LogDir,'Cargo.json')
    table = []
    while Continue :
        logger.info(f'worker Cargo waiting')
        if this.eventtfmCargo.wait():
            eventr = this.event
            this.event = ""
            marketr = this.Market_ID
            logger.info(f'workerCargo running receive {eventr} for Market {marketr}')             
            if eventr == "Docked":
                #if docked take marketid and cargo.json
                try:
                    filej = open(fname, 'r') 
                    dockedCargo = json.load(filej)
                    filej.close()
                except:
                    logger.info('worker Cargo Erreur loading Cargo.json')   
            elif eventr == "Undocked":
                #if undocked compare old json with new one
                # si pas vide au depart
                readok = True
                try:
                    cc = dockedCargo["Count"]
                except:
                    logger.info('cannot read dockedcargo from memory')
                    readok = False
                if readok:
                    if (cc > 0):
                        try:
                            filej = open(fname, 'r') 
                            undockedCargo = json.load(filej)
                            filej.close()
                        except:
                            logger.info('worker Cargo Erreur loading Cargo.json')
                        #logger.info(dockedCargo)
                        #logger.info(undockedCargo)
                        tete = {}
                        tete['timestamp'] = undockedCargo['timestamp']
                        tete['event'] = 'Deposit'
                        tete['marketId'] = marketr
                        table.append(tete)
                        transactions = []
                        transactions = get_diff(dockedCargo, undockedCargo)
                        #logger.info(transactions)
                        tete['commodities'] = transactions  
                        jsonout = json.dumps(tete)
                        #jsonoutstrip = jsonout.replace('"','')
                        logger.info(jsonout)
                        # send to SM
                        erreur = SendToServer(jsonout)
                        if (erreur):
                            logger.info(f'cannot send Cargo to serveur')
                    
            elif eventr == "STOP":
                Continue = False
                break 
            else:
                logger.info('receive nawak')
                logger.info(eventr)
            this.eventtfmCargo.clear()     
                                  
    logger.info('fin workerCargo')




