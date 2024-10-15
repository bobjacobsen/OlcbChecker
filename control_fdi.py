#!/usr/bin/env python3.10

'''
Simple runner for Function Definition Information suite
'''
import sys
import logging

import olcbchecker.setup

import check_fd10_valid
import check_fd20_read

def prompt() :
    print("\nFDI Standard checking")
    print(" a Run all in sequence")
    print(" 1 FDI valid checking")
    print(" 2 FDI read checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("FDI")) :
    result = 0
 
    logger.info("FDI valid checking")
    result += check_fd10_valid.check()

    logger.info("FDI read checking")
    result += check_fd20_read.check()

    if result == 0 :
        logger.info("Success - all FDI checks passed")
    else:
        logger.warning("At least one FDI check failed")
        
    return result
        
def main() :
    logger = logging.getLogger("FDI")
    
    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Function Definition Information Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nFDI valid checking")
                check_fd10_valid.check()
           
            case "2" : 
                print("\nFDI read checking")
                check_fd20_read.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
