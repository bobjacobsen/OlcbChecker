#!/usr/bin/env python3.10

'''
Simple runner for Train Control suite
'''
import sys
import logging

import olcbchecker.setup

import check_tr010_events
import check_tr020_speed
import check_tr030_func
import check_tr040_estop
import check_tr050_gestop
import check_tr060_geoff
import check_tr070_memspaces

def prompt() :
    print("\nTrain Control Standard checking")
    print(" a Run all in sequence")
    print(" 1 Events checking")
    print(" 2 Speed checking")
    print(" 3 Function checking")
    print(" 4 Emergency stop checking")
    print(" 5 Global emergency stop checking")
    print(" 6 Global emergency off checking")
    print(" 7 Memory space checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("TRAIN_CONTROL")) :
    result = 0
 
    logger.info("Events checking")
    result += check_tr010_events.check()

    logger.info("Speed checking")
    result += check_tr020_speed.check()

    logger.info("Function checking")
    result += check_tr030_func.check()

    logger.info("Emergency stop checking")
    result += check_tr040_estop.check()

    logger.info("Global emergency stop checking")
    result += check_tr050_gestop.check()

    logger.info("Global emergency off checking")
    result += check_tr060_geoff.check()

    logger.info("Memory space checking")
    result += check_tr070_memspaces.check()

    if result == 0 :
        logger.info("Success - all Train Control checks passed")
    else:
        logger.warning("At least one Train Control check failed")
        
    return result
        
def main() :
    logger = logging.getLogger("TRAIN_CONTROL")
    
    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Train Control Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nEvents checking")
                check_tr010_events.check()
           
            case "2" : 
                print("\nSpeed checking")
                check_tr020_speed.check()
           
            case "3" : 
                print("\nFunction checking")
                check_tr030_func.check()
           
            case "4" : 
                print("\nEmergency stop checking")
                check_tr040_estop.check()
           
            case "5" : 
                print("\nGlobal emergency stop checking")
                check_tr050_gestop.check()
           
            case "6" : 
                print("\nGlobal emergency off checking")
                check_tr060_geoff.check()
           
            case "7" : 
                print("\nMemory space checking")
                check_tr070_memspaces.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
