#!/usr/bin/env python3.10

'''
Runner for DCC Detector Protocol checks
'''
import sys
import logging

import olcbchecker.setup

import check_dd10_identify
import check_dd20_event_format
import check_dd30_identify_producer
import check_dd40_track_empty

def prompt() :
    print("\nDCC Detector Protocol checking")
    print(" a Run all in sequence")
    print(" 1 Identify detector events")
    print(" 2 Event ID format validation")
    print(" 3 Identify Producer replies")
    print(" 4 Track-empty sentinel (info only)")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("DCC_DETECTOR")) :
    result = 0

    logger.info("Identify detector events")
    result += check_dd10_identify.check()

    logger.info("Event ID format validation")
    result += check_dd20_event_format.check()

    logger.info("Identify Producer replies")
    result += check_dd30_identify_producer.check()

    logger.info("Track-empty sentinel (info only)")
    result += check_dd40_track_empty.check()

    if result == 0 :
        logger.info("Success - all DCC Detector checks passed")
    else:
        logger.warning("At least one DCC Detector check failed")

    return result

def main() :
    logger = logging.getLogger("DCC_DETECTOR")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against DCC Detector Protocol Working Note
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" :
                print("\nIdentify detector events")
                check_dd10_identify.check()
            case "2" :
                print("\nEvent ID format validation")
                check_dd20_event_format.check()
            case "3" :
                print("\nIdentify Producer replies")
                check_dd30_identify_producer.check()
            case "4" :
                print("\nTrack-empty sentinel (info only)")
                check_dd40_track_empty.check()

            case  "a" :
                checkAll(logger)

            case "q" | "quit" : return

            case _ : continue

    return
if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
