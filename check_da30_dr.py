#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check Datagram exchange.

Usage:
python3.10 check_da30_dr.py

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
    logger = logging.getLogger("DATAGRAM")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################
    
    # check if PIP says this is present
    if olcbchecker.isCheckPip() : 
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.DATAGRAM_PROTOCOL in pipSet :
            logger.info("Passed - due to Datagram protocol not in PIP")
            return(0)

    sampleLengths = [ 1, 10, 72]
    
    for length in sampleLengths:

        data = list(range(0, length))

        # send an datagram to provoke response
        message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, data)
        olcbchecker.sendMessage(message)

        while True :
            try :
                received = olcbchecker.getMessage() # timeout if no entries
                # is this a datagram reply, OK or not?
                if not (received.mti == MTI.Datagram_Received_OK or received.mti == MTI.Datagram_Rejected) : 
                    continue # wait for next
        
                if destination != received.source : # check source in message header
                    logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                    return(3)
        
                if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                    logger.warning ("Failure - Unexpected destination of reply message: {} {}".format(received, received.destination))
                    return(3)
        
                if received.mti == MTI.Datagram_Received_OK :
                    # check for exactly one byte of flags
                    if len(received.data) != 1 :
                        logger.warning ("Failure - Unexpected length in OK reply: {}".format(len(received.data)))
                        return(3)
                else : # must be datagram rejected
                    # check for contains at least 2 bytes of error code 
                    if len(received.data) != 2 :
                        logger.warning ("Failure - Unexpected length in reject reply: {}".format(len(received.data)))
                        return(3)
                    # check for valid flags
                    bits = received.data[0]
                    if (bits & 0xF0 ) != 0x10 and (bits & 0xF0 ) != 0x10 :
                        logger.warning ("Failure - Unexpected contents flag upper nibble contents: 0x{:02X}".format(received.data[0]))
                        return(3)
                    if (bits & 0x0F ) != 0x00:
                        logger.warning ("Failure - Unexpected contents flag 2nd nibble contents: 0x{:02X}".format(received.data[0]))
                        return(3)
                break
            except Empty:
                logger.warning ("Failure - no reply to sent Datagram")
                return(3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
