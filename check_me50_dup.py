#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check for the reaction to a duplicate node ID

Usage:
python3.10 check_me50_dup.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.eventid import EventID

from queue import Empty

def check() :
    # set up the infrastructure

    import olcbchecker.setup
    logger = logging.getLogger("MESSAGE")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################
    
    # send a message with our alias but target's NodeID to see if it provokes a response
    message = Message(MTI.Verified_NodeID, NodeID(olcbchecker.ownnodeid()), None, destination.toArray()) # send from destination node
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply from that node?
            if not received.mti == MTI.Producer_Consumer_Event_Report : continue # wait for next
            # this is a PCER message, success

            if EventID("01.01.00.00.00.00.02.01") != EventID(received.data) :
                logger.warning ("Failure - Unexpected notification EventID: {} {}".format(received, EventID(received.data)))
                return(3)
                
            break
        except Empty:
            if olcbchecker.setup.configure.skip_interactive :
                logger.warning ("Did not receive well-known event.")
                logger.warning("    Interactive checks skipped, so not checking for indication on node.")
                # fall through to pass result
                break
            else :
                logger.warning ("Did not receive well-known event.")
                logger.warning ("      Check for indication on node using some other form of indication. ")
                logger.warning ("      Enter 'y' if present and 'n' if not.")
                entry = input("  >> ").lower()
                if entry == 'n' :
                    # this is a failure
                    logger.warning("Failure - no indication of duplicate Node ID")
                    return (3)
                # otherwise, fall though to a pass result
                break

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
