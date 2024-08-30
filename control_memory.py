#!/usr/bin/env python3.10

'''
Simple runner for Memory Configuration suite
'''
import sys
import logging

import olcbchecker.setup

import check_mc10_co
import check_mc20_ckasi
import check_mc30_read
import check_mc40_lock
import check_mc50_restart

def prompt() :
    print("\nMemory Configuration Standard checking")
    print(" a Run all in sequence")
    print(" 1 Configuration Options checking")
    print(" 2 Address Space Information checking")
    print(" 3 Read checking")
    print(" 4 Lock/Reserve checking")
    print(" 5 Restart checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("MEMORY")) :
    result = 0
 
    logger.info("Configuration Options checking")
    result += check_mc10_co.check()

    logger.info("Address Space Information checking")
    result += check_mc20_ckasi.check()

    logger.info("Read checking")
    result += check_mc30_read.check()

    logger.info("Lock/Reserve checking")
    result += check_mc40_lock.check()

    logger.info("Restart checking")
    result += check_mc50_restart.check()

    if result == 0 :
        logger.info("Success - all memory checks passed")
    else:
        logger.warning("At least one memory check failed")
        
    return result
    
def main() :
    logger = logging.getLogger("MEMORY")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Memory Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nConfiguration Options checking")
                check_mc10_co.check()

            case "2" : 
                print("\nAddress Space Information checking")
                check_mc20_ckasi.check()
           
            case "3" : 
                print("\nRead checking")
                check_mc30_read.check()
           
            case "4" : 
                print("\nLock/Reserve checking")
                check_mc40_lock.check()
           
            case "5" : 
                print("\nRestart checking")
                check_mc50_restart.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
