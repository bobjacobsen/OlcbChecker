#!/usr/bin/env python3.10

'''
Simple runner for message network checks
'''
import sys
import logging

import olcbchecker.setup

import check_ev10_ida
import check_ev20_idg
import check_ev30_ip
import check_ev40_ic

def prompt() :
    print("\nEvent Exchange Standard checking")
    print(" a Run all in sequence")
    print(" 1 Identify Event Addressed checking")
    print(" 2 Identify Event Global checking")
    print(" 3 Identify Producer checking")
    print(" 4 Identify Consumer checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("EVENTS")) :
    result = 0
 
    logger.info("Identify Event Addressed checking")
    result += check_ev10_ida.check()

    logger.info("Identify Event Global checking")
    result += check_ev20_idg.check()

    logger.info("Identify Producer checking")
    result += check_ev30_ip.check()

    logger.info("Identify Consumer checking")
    result += check_ev40_ic.check()

    if result == 0 :
        logger.info("Success - all event checks passed")
    else:
        logger.warning("At least one event check failed")

    return result
    
def main() :
    logger = logging.getLogger("EVENT")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Event Transport Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nIdentify Event Addressed checking")
                check_ev10_ida.check()
            case "2" :
                print("\nIdentify Event Global checking")
                check_ev20_idg.check()
            case "3" : 
                print("\nIdentify Producer checking")
                check_ev30_ip.check()
            case "4" :
                print("\nIdentify Consumer checking")
                check_ev40_ic.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    sys.exit(main())
