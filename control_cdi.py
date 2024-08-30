#!/usr/bin/env python3.10

'''
Simple runner for CDI suite
'''
import sys
import logging

import olcbchecker.setup

import check_cd10_valid
import check_cd20_read
import check_cd30_acdi

def prompt() :
    print("\nCDI Standard checking")
    print(" a Run all in sequence")
    print(" 1 CDI Memory Present checking")
    print(" 2 Validation checking")
    print(" 3 ACDI checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("CDI")) :
    result = 0
 
    logger.info("CDI Memory Present checking")
    result += check_cd10_valid.check()

    logger.info("Validation checking")
    result += check_cd20_read.check()

    logger.info("ACDI checking")
    result += check_cd30_acdi.check()

    if result == 0 :
        logger.info("Success - all CDI checks passed")
    else:
        logger.warning("At least one CDI check failed")
        
    return result
    
def main() :
    logger = logging.getLogger("CDI")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Frame Transport Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nCDI Memory Present checking")
                check_cd10_valid.check()
                           
            case "2" : 
                print("\nValidation checking")
                check_cd20_read.check()
                           
            case "3" : 
                print("\nACDI checking")
                check_cd30_acdi.check()
                           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
