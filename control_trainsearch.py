#!/usr/bin/env python3.10

'''
Simple runner for Train Search suite
'''
import sys
import logging

import olcbchecker.setup

import check_ts10_create
import check_ts20_partial
import check_ts30_reserved2
import check_ts40_reserved4

def prompt() :
    print("\nTrain Search Standard checking")
    print(" a Run all in sequence")
    print(" 1 Create Train checking")
    print(" 2 Partial Values checking")
    print(" 3 Reserved Address Section 2 checking")
    print(" 4 Reserved Address Section 4 checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("TRAIN_SEARCH")) :
    result = 0
 
    logger.info("Create Train checking")
    result += check_ts10_create.check()

    logger.info("Partial Values checking")
    result += check_ts20_partial.check()

    logger.info("Reserved Address Section 2 checking")
    result += check_ts30_reserved2.check()

    logger.info("Reserved Address Section 4 checking")
    result += check_ts40_reserved4.check()

    if result == 0 :
        logger.info("Success - all Train Search checks passed")
    else:
        logger.warning("At least one Train Search check failed")
        
    return result
        
def main() :
    logger = logging.getLogger("TRAIN_SEARCH")
    
    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Train Search Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nTrain Search checking")
                check_ts10_create.check()
           
            case "2" : 
                print("\nPartial Values checking")
                check_ts20_partial.check()
           
            case "3" : 
                print("\nReserved Address Section 2 checking")
                check_ts30_reserved2.check()
           
            case "4" : 
                print("\nReserved Address Section 4 checking")
                check_ts40_reserved4.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
