#!/usr/bin/env python3.10

'''
Simple runner for broadcast time protocol checks.

The node under test must be either a Clock Producer (generator) or a
Clock Consumer (display).  The tester selects which role is being
tested and only the applicable checks are run.
'''
import sys
import logging

import olcbchecker.setup

import check_bt10_query
import check_bt20_set
import check_bt30_immediate
import check_bt40_multiset
import check_bt50_freq
import check_bt60_requested
import check_bt70_rollover
import check_bt80_startup
import check_bt100_consumer_startup
import check_bt110_consumer_sync
import check_bt120_consumer_startstop
import check_bt130_consumer_rate

def promptNodeType() :
    print("\nBroadcast Time Protocol - Select node type under test")
    print(" p Clock Producer (generator)")
    print(" c Clock Consumer (display)")
    print(" q go back")

def checkAllProducer(logger=logging.getLogger("BCAST_TIME")) :
    result = 0

    logger.info("Clock Query checking")
    result += check_bt10_query.check()

    logger.info("Clock Set checking")
    result += check_bt20_set.check()

    logger.info("Clock Set Immediate Report checking")
    result += check_bt30_immediate.check()

    logger.info("Multiple Set Commands checking")
    result += check_bt40_multiset.check()

    logger.info("Clock Report Frequency checking")
    result += check_bt50_freq.check()

    logger.info("Requested Time checking")
    result += check_bt60_requested.check()

    logger.info("Date Rollover checking")
    result += check_bt70_rollover.check()

    logger.info("Startup Sequence checking")
    result += check_bt80_startup.check()

    if result == 0 :
        logger.info("Success - all broadcast time producer checks passed")
    else:
        logger.warning("At least one broadcast time producer check failed")

    return result

def checkAllConsumer(logger=logging.getLogger("BCAST_TIME")) :
    result = 0

    logger.info("Consumer Startup checking")
    result += check_bt100_consumer_startup.check()

    logger.info("Consumer Synchronization checking")
    result += check_bt110_consumer_sync.check()

    logger.info("Consumer Stop/Start checking")
    result += check_bt120_consumer_startstop.check()

    logger.info("Consumer Rate Change checking")
    result += check_bt130_consumer_rate.check()

    if result == 0 :
        logger.info("Success - all broadcast time consumer checks passed")
    else:
        logger.warning("At least one broadcast time consumer check failed")

    return result

def checkAll(logger=logging.getLogger("BCAST_TIME")) :
    '''Ask the tester which node type is under test and run the
    applicable checks.  Returns the accumulated result.'''

    while True :
        promptNodeType()
        selection = input(">> ").lower()
        match selection :
            case "p" :
                return checkAllProducer(logger)

            case "c" :
                return checkAllConsumer(logger)

            case "q" | "quit" :
                return 0

            case _ : continue

def main() :
    logger = logging.getLogger("BCAST_TIME")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Broadcast Time Protocol Standard
    '''

    # First, select the node type under test
    node_type = None
    while node_type is None :
        promptNodeType()
        selection = input(">> ").lower()
        match selection :
            case "p" :
                node_type = "producer"

            case "c" :
                node_type = "consumer"

            case "q" | "quit" : return

            case _ : continue

    while True :
        if node_type == "producer" :
            print("\nBroadcast Time Protocol - Clock Producer checking")
            print(" a Run all producer checks in sequence")
            print("")
            print(" 1 Clock Query checking")
            print(" 2 Clock Set checking")
            print(" 3 Clock Set Immediate Report checking")
            print(" 4 Multiple Set Commands checking")
            print(" 5 Clock Report Frequency checking")
            print(" 6 Requested Time checking")
            print(" 7 Date Rollover checking")
            print(" 8 Startup Sequence checking")
            print("  ")
            print(" q go back")
        else :
            print("\nBroadcast Time Protocol - Clock Consumer checking")
            print(" a Run all consumer checks in sequence")
            print("")
            print(" 1 Consumer Startup checking")
            print(" 2 Consumer Synchronization checking")
            print(" 3 Consumer Stop/Start checking")
            print(" 4 Consumer Rate Change checking")
            print("  ")
            print(" q go back")

        selection = input(">> ").lower()

        if node_type == "producer" :
            match selection :
                case "1" :
                    print("\nClock Query checking")
                    check_bt10_query.check()
                case "2" :
                    print("\nClock Set checking")
                    check_bt20_set.check()
                case "3" :
                    print("\nClock Set Immediate Report checking")
                    check_bt30_immediate.check()
                case "4" :
                    print("\nMultiple Set Commands checking")
                    check_bt40_multiset.check()
                case "5" :
                    print("\nClock Report Frequency checking")
                    check_bt50_freq.check()
                case "6" :
                    print("\nRequested Time checking")
                    check_bt60_requested.check()
                case "7" :
                    print("\nDate Rollover checking")
                    check_bt70_rollover.check()
                case "8" :
                    print("\nStartup Sequence checking")
                    check_bt80_startup.check()

                case "a" :
                    checkAllProducer(logger)

                case "q" | "quit" : return

                case _ : continue

        else :
            match selection :
                case "1" :
                    print("\nConsumer Startup checking")
                    check_bt100_consumer_startup.check()
                case "2" :
                    print("\nConsumer Synchronization checking")
                    check_bt110_consumer_sync.check()
                case "3" :
                    print("\nConsumer Stop/Start checking")
                    check_bt120_consumer_startstop.check()
                case "4" :
                    print("\nConsumer Rate Change checking")
                    check_bt130_consumer_rate.check()

                case "a" :
                    checkAllConsumer(logger)

                case "q" | "quit" : return

                case _ : continue

    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
