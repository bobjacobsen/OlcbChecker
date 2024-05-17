#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check PIP message exchange.

Usage:
python3.10 check_me30_pip.py

The -h option will display a full list of options.
'''

import sys

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty

import configure


def check():
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
    
    # send an PIP message to provoke response
    ownid = configure.global_config.ownnodeid
    message = Message(MTI.Protocol_Support_Inquiry, NodeID(ownid), destination)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a pip reply?
            if not received.mti == MTI.Protocol_Support_Reply : continue # wait for next
        
            if destination != received.source : # check source in message header
                print ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)
        
            if NodeID(ownid) != received.destination : # check destination in message header
                print ("Failure - Unexpected destination of reply message: {} {}".format(received, received.destination))
                return(3)
        
            result = received.data[0] << 24 | \
                        received.data[1] << 16 | \
                        received.data[2] <<8|  \
                        received.data[3]
            if trace >= 10 :
                print("PIP reports:")
                list = PIP.contentsNamesFromInt(result)
                for e in list :
                    print (" ",e)
            if received.data[3] != 0 :
                print ("Failure - Unexpected contents in 4th byte; 0x{:02X}".format(received.data[3]))
                return(3)
            break
        except Empty:
            print ("Failure - no reply to PIP request")
            return(3)

    # send a pip message to another node (our node) and expect no reply
    message = Message(MTI.Protocol_Support_Inquiry, NodeID(ownid), NodeID(ownid))
    olcbchecker.sendMessage(message)
    try :
            received = olcbchecker.getMessage() # timeout if no entries
            # error, we received a reply
            print ("Failure - Unexpected reply to PIP request addressed to a different node")
            return(3)
    except:
        # this is normal, success
        pass
                    
    if trace >= 10 : print("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(check())
