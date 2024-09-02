#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check memmory configuration read command

Usage:
python3.10 check_mc30_read.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty

import olcbchecker.setup

def getReplyDatagram(destination) :
    '''
    Invoked after a datagram has been sent, this waits
    for first the datagram reply message, then a 
    datagram message that contains a reply.  It 
    replies with a datagram OK, then returns the reply datagram message.
    Raises Exception if something went wrong.
    '''
    # first, wait for the reply
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a datagram reply, OK or not?
            if not (received.mti == MTI.Datagram_Received_OK or received.mti == MTI.Datagram_Rejected) : 
                continue # wait for next
    
            if destination != received.source : # check source in message header
                continue
    
            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                continue
    
            if received.mti == MTI.Datagram_Received_OK :
                # OK, proceed to check reply Pending bit
                if not received.data :
                    raise Exception("Failure - no flags in Datagram Received OK")
                if received.data[0] & 0x80 != 0x80 :
                    raise Exception("Failure - Reply Pending not set in Datagram Received OK")
                # at this point, all OK
                break
            else : # must be datagram rejected
                # can't proceed
                raise Exception("Failure - Original Datagram rejected")

        except Empty:
            raise Exception("Failure - no reply to original request")
    
    # now wait for the reply datagram
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a datagram reply, OK or not?
            if not (received.mti == MTI.Datagram) : 
                continue # wait for next
    
            if destination != received.source : # check source in message header
                continue
    
            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                continue

            # here we've received the reply datagram
            # send the reply
            message = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination, [0])
            olcbchecker.sendMessage(message)

            return received
            
        except Empty:
            raise Exception("Failure - no reply datagram received")
    
    
def sendAndCheckResponse(destination, request, length) :
        # returns non-zero if fail
        # send a read datagram
        message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, request)
        olcbchecker.sendMessage(message)

        try :
            reply = getReplyDatagram(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)
        
        # check length of returned datagram
        if len(reply.data) != len(request) -1 + length :
            logger.warning("Failure - length was {}, expected {}".format(len(reply.data), len(request) -1 + length) )
            return 3
        
        expectedReply = request
        expectedReply[1] = expectedReply[1] | 0x10
        
        checkLen = len(request)-1
        if expectedReply[:checkLen] != reply.data[:checkLen] :
            logger.warning("Failure - header was {}, expected {}".format(reply.data[:checkLen]), expectedReply[:checkLen])
            return 3
            
        return 0

def check():
    # set up the infrastructure

    logger = logging.getLogger("MEMORY")

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
        if not PIP.MEMORY_CONFIGURATION_PROTOCOL in pipSet :
            logger.info("Passed - due to Memory Configuration protocol not in PIP")
            return(0)

    reply = sendAndCheckResponse(destination, [0x20, 0x41, 0,0,0,0, 2], 2)
    if reply != 0 : 
        logger.warning("   in read of 2 bytes from short-form read")
        return reply

    reply = sendAndCheckResponse(destination, [0x20, 0x41, 0,0,0,0, 10], 10)
    if reply != 0 : 
        logger.warning("   in read of 10 bytes from short-form read")
        return reply

    reply = sendAndCheckResponse(destination, [0x20, 0x41, 0,0,0,0, 64], 64)
    if reply != 0 : 
        logger.warning("   in read of 64 bytes from short-form read")
        return reply
        
    reply = sendAndCheckResponse(destination, [0x20, 0x40, 0,0,0,0, 0xFD, 2], 2)
    if reply != 0 : 
        logger.warning("   in read of 2 bytes from long-form read")
        return reply

    reply = sendAndCheckResponse(destination, [0x20, 0x40, 0,0,0,0, 0xFD, 10], 10)
    if reply != 0 : 
        logger.warning("   in read of 10 bytes from long-form read")
        return reply

    reply = sendAndCheckResponse(destination, [0x20, 0x40, 0,0,0,0, 0xFD, 64], 64)
    if reply != 0 : 
        logger.warning("   in read of 64 bytes from long-form read")
        return reply
        
            
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)
