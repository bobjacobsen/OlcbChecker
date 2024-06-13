#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check for an OIR reply to an unknown MTI

Usage:
python3.10 check_me40_oir.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI

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
    
    # send a global message which should get no response
    
    message = Message(MTI.Link_Layer_Down, NodeID(olcbchecker.ownnodeid()), destination) # MTI selected to be global
    olcbchecker.sendMessage(message)

    try :
        received = olcbchecker.getMessage() # timeout if no replies
        logger.warning ("Failure - Unexpected reply to global unknown MTU: {} {}".format(received, received.source))
        return(3)
    except:
        # this is normal
        pass
        
    # send an addressed message to own node which should get no response
    message = Message(MTI.New_Node_Seen, NodeID(olcbchecker.ownnodeid()),  NodeID(olcbchecker.ownnodeid()) ) # MTI selected to be addressed
    olcbchecker.sendMessage(message)

    try :
        received = olcbchecker.getMessage() # timeout if no replies
        logger.warning ("Failure - Unexpected reply to global unknown MTU: {} {}".format(received, received.source))
        return(3)
    except:
        # this is normal
        pass
        
            
    # send a message to DBC to provoke response
    message = Message(MTI.New_Node_Seen, NodeID(olcbchecker.ownnodeid()), destination) # MTI selected to be addressed
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a reply from that node?
            if not received.mti == MTI.Optional_Interaction_Rejected : continue # wait for next
            # this is a OIR message, success

            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)
        
            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                logger.warning ("Failure - Unexpected destination of reply message: {} {}".format(received, received.destination))
                return(3)
            if len(received.data) < 4:
                logger.warning ("Failure - Unexpected length of reply message: {} {}".format(received, received.data))
                return(3)

            try :            
                seenMTI = MTI(0x2000|received.data[2]<<8 | received.data[3])
            except ValueError :
                seenMTI = None
            if seenMTI != MTI.New_Node_Seen :
                logger.warning ("Failure - MTI not carried in data: {} {}".format(received, received.data, seenMTI))
                try :
                    earlyMTI = MTI(0x2000|received.data[0]<<8 | received.data[1])
                except ValueError:
                    earlyMTI = None
                if earlyMTI == MTI.New_Node_Seen :
                    logger.warning("    Hint: MTI incorrectly found in first two bytes of OIR reply")
                return(3)
            
            break
        except Empty:
            logger.warning ("Failure - Did not receive Optional Interaction Rejected reply")
            return(3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(check())
