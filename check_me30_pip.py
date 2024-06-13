#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check PIP message exchange.

Usage:
python3.10 check_me30_pip.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty

def check():
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
    
    # send an PIP message to provoke response
    message = Message(MTI.Protocol_Support_Inquiry, NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a pip reply?
            if not received.mti == MTI.Protocol_Support_Reply : continue # wait for next
        
            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)
        
            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                logger.warning ("Failure - Unexpected destination of reply message: {} {}".format(received, received.destination))
                return(3)
        
            result = received.data[0] << 24 | \
                        received.data[1] << 16 | \
                        received.data[2] <<8|  \
                        received.data[3]
            
            logger.info("PIP reports:")
            list = PIP.contentsNamesFromInt(result)
            for e in list :
                logger.info ("  "+str(e))
            if received.data[3] != 0 :
                logger.warning ("Failure - Unexpected contents in 4th byte; 0x{:02X}".format(received.data[3]))
                return(3)
            break
        except Empty:
            logger.warning ("Failure - no reply to PIP request")
            return(3)

    # send a pip message to another node (our node) and expect no reply
    message = Message(MTI.Protocol_Support_Inquiry, NodeID(olcbchecker.ownnodeid()), NodeID(olcbchecker.ownnodeid()))
    olcbchecker.sendMessage(message)
    try :
            received = olcbchecker.getMessage() # timeout if no entries
            # error, we received a reply
            logger.warning ("Failure - Unexpected reply to PIP request addressed to a different node")
            return(3)
    except:
        # this is normal, success
        pass
                    
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(check())
