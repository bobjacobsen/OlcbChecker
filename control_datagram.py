#!/usr/bin/env python3.10

'''
Simple runner for Datagram suite
'''
import sys
import logging

import olcbchecker.setup

import check_da30_dr

def prompt() :
    print("\nDatagram Transport Standard checking")
    print(" a Run all in sequence")
    print(" 1 Datagram Reception checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("DATAGRAM")) :
    result = 0
 
    logger.info("Datagram Reception checking")
    result += check_da30_dr.check()

    if result == 0 :
        logger.info("Success - all datagram checks passed")
    else:
        logger.warn("At least one datagram check failed")
        
    return result
    
def main() :
    logger = logging.getLogger("DATAGRAM")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Datagram Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nDatagram Reception checking")
                check_da30_dr.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
