import winsound

def beep():
    global this
    if (this.dobeep):
        frequency = 1250  # Set Frequency in Hertz
        duration = 150  # Set Duration in ms
        winsound.Beep(frequency, duration)  


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
