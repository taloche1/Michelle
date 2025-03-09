import json




def workerCargo():
  
   
  
    
             
  filej = open('Cargoplein.json', 'r') 
  dockedCargo = json.load(filej)                

  filej.close()
                   
  cc = dockedCargo["Count"]
  print(f' Count {cc}')
  if (cc > 0):
    filej = open('Cargopvide.json', 'r') 
    undockedCargo = json.load(filej)
    filej.close()
    transactions = []
    transactions = get_diff(dockedCargo, undockedCargo)
    jsonout = json.dumps(transactions)
    jsonoutstrip = jsonout.replace('"','')
    print(jsonoutstrip)

  
  
                                

def get_diff(dockedCargo, undockedCargo):
     table = []
     bingo = False
   

     print(f'dock json : {dockedCargo}')
     print(f'undock json : {undockedCargo}')

     # for each item in dockedCargo at docking :
     for item in dockedCargo['Inventory']:

        name = item['Name']
        print(f'Recheche  {name}')
        # is present in cargo at undocking ?
        for itemout in undockedCargo['Inventory']:
            print(itemout['Name'])
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

workerCargo()
