#!/usr/bin/env python3.10

'''
Simple runner for SNIP suite
'''
import sys
import logging

import olcbchecker.setup

import check_sn10_snip

def prompt() :
    print("\nSNIP Standard checking")
    print(" a Run all in sequence")
    print(" 1 SNIP reply checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("SNIP")) :
    result = 0
 
    logger.info("SNIP reply checking")
    result += check_sn10_snip.check()

    if result == 0 :
        logger.info("Success - all SNIP checks passed")
    else:
        logger.warning("At least one SNIP check failed")
        
    return result
        
def main() :
    logger = logging.getLogger("SNIP")
    
    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against SNIP Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nSNIP reply checking")
                check_sn10_snip.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    sys.exit(main())
