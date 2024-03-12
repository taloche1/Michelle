from typing import Dict
import load
from pathlib import Path
import unicodedata

def runn():  

    my_var2 = "CMD ВкуСняШка_808"
    #my_var2 = "CMD Laurent Yess"
    my_var3 = unicodedata.normalize('NFKD', my_var2).encode('ascii', 'ignore').decode('ascii')
    print (my_var3)
    return




    load.plugin_start3(Path().absolute())
    boucle = True
    entry = {'event':'StartUp'}
    print ("Test local")
    #open log file :
    #load.journal_entry('Laurent Yess', False, 'truc', 'machin',entry, None)
    entry['event'] = 'FSDJump'
    while boucle == True:
        nb = input("push key (0 pour sortir)")
        if nb == "0" :
            boucle = False
        else:
            load.journal_entry('Laurent Yess', False, 'truc', 'machin',entry, None)
    load.plugin_stop()


runn()