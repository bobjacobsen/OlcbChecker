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
import check_mc60_out_of_range
import check_mc70_write_under_mask
import check_mc80_write

def prompt() :
    force = olcbchecker.setup.configure.force_writes
    print("\nMemory Configuration Standard checking")
    print(" a Run all in sequence")
    print(" 1 Configuration Options checking")
    print(" 2 Address Space Information checking")
    print(" 3 Read checking")
    print(" 4 Lock/Reserve checking")
    print(" 5 Restart checking")
    print(" 6 Out-of-Range Read checking")
    if force :
        print(" 7 Write Under Mask checking")
        print(" 8 Config Memory Write checking")
    else :
        print(" 7 Write Under Mask checking (requires -w)")
        print(" 8 Config Memory Write checking (requires -w)")
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

    logger.info("Out-of-Range Read checking")
    result += check_mc60_out_of_range.check()

    logger.info("Write Under Mask checking")
    result += check_mc70_write_under_mask.check()

    logger.info("Config Memory Write checking")
    result += check_mc80_write.check()

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

            case "6" :
                print("\nOut-of-Range Read checking")
                check_mc60_out_of_range.check()

            case "7" :
                print("\nWrite Under Mask checking")
                check_mc70_write_under_mask.check()

            case "8" :
                print("\nConfig Memory Write checking")
                check_mc80_write.check()

            case  "a" :
                checkAll(logger)

            case "q" | "quit" : return

            case _ : continue

    return
if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
