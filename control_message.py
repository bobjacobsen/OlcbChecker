#!/usr/bin/env python3.10

'''
Simple runner for message network checks
'''
import sys
import logging

import olcbchecker.setup

import check_me10_init
import check_me20_verify
import check_me30_pip
import check_me40_oir
import check_me50_dup

def prompt() :
    print("\nMessage Network Standard checking")
    print(" a Run all in sequence")
    print(" 1 Node Initialized checking")
    print(" 2 Verify Node checking")
    print(" 3 Protocol Support Inquiry checking")
    print(" 4 Optional Interaction Rejected checking")
    print(" 5 Duplicate Node ID Discovery checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("MESSAGE")) :
    result = 0
 
    logger.info("Node Initialized checking")
    result += check_me10_init.check()

    logger.info("Verify Node checking")
    result += check_me20_verify.check()

    logger.info("Protocol Support Inquiry checking")
    result += check_me30_pip.check()

    logger.info("Optional Interaction Rejected checking")
    result += check_me40_oir.check()

    logger.info("Duplicate Node ID Discovery checking")
    result += check_me50_dup.check()

    if result == 0 :
        logger.info("Success - all message checks passed")
    else:
        logger.warning("At least one message check failed")

    return result
    
def main() :
    logger = logging.getLogger("MESSAGE")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Message Network Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nNode Initialized checking")
                check_me10_init.check()
            case "2" :
                print("\nVerify Node checking")
                check_me20_verify.check()
            case "3" :
                print("\nProtocol Support Inquiry checking")
                check_me30_pip.check()
            case "4" :
                print("\nOptional Interaction Rejected checking")
                check_me40_oir.check()
            case "5" :
                print("\nDuplicate Node ID Discovery checking")
                check_me50_dup.check()
           
            case  "a" :
                checkAll(logger)
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
