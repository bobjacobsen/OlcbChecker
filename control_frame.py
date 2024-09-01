#!/usr/bin/env python3.10

'''
Simple runner for frame transport suite
'''
import sys
import logging

import olcbchecker.setup

import check_fr10_init
import check_fr20_ame
import check_fr30_collide
import check_fr40_highbit

import subprocess

def prompt() :
    print("\nFrame Transport Standard checking")
    print(" a Run all in sequence")
    print(" 1 Initialization checking")
    print(" 2 AME checking")
    print(" 3 Collision checking")
    print(" 4 Reserved bit checking")
    print(" 5 Capacity checking")
    print(" 6 Standard frame checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("FRAME")) :
    result = 0
 
    logger.info("Initialization checking")
    result += check_fr10_init.check()

    logger.info("AME checking")
    result += check_fr20_ame.check()

    logger.info("Collision checking")
    result += check_fr30_collide.check()

    logger.info("Reserved bit checking")
    result += check_fr40_highbit.check()

    logger.info("Capacity checking")
    result += check_fr50_capacity.check()

    logger.info("Standard frame checking")
    result += check_fr60_standard.check()

    if result == 0 :
        logger.info("Success - all frame checks passed")
    else:
        logger.warning("At least one frame check failed")
        
    return result
    
def main() :
    logger = logging.getLogger("FRAME")

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
                print("\nInitialization checking")
                check_fr10_init.check()

            case "2" : 
                print("\nAME checking")
                check_fr20_ame.check()
           
            case "3" : 
                print("\nCollision checking")
                check_fr30_collide.check()
           
            case "4" : 
                print("\nReserved bit checking")
                check_fr40_highbit.check()
           
            case "5" : 
                print("\nCapacity checking")
                check_fr50_capacity.check()
           
            case "6" : 
                print("\nStandard frame checking")
                check_fr60_standard.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
