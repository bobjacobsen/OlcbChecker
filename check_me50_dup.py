#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check for the reaction to a duplicate node ID

Usage:
python3.10 check_me50_dup.py

The -h option will display a full list of options.
'''

import sys

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.eventid import EventID

from queue import Empty

def check() :
    # set up the infrastructure

    import olcbchecker.setup
    trace = olcbchecker.trace() # just to be shorter

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    if olcbchecker.setup.configure.global_config.skip_interactive :
        print ("Interactive test skipped")
        return 0  
    
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
                print ("Failure - Unexpected notification EventID: {} {}".format(received, EventID(received.data)))
                return(3)
                
            break
        except Empty:
            print ("Did not receive well-known event: Check for indication on node")
            # this is a partial pass
            return(0)

    if trace >= 10 : print("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(check())
