#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check memmory configuration lock command

Usage:
python3.10 check_mc40_lock.py

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
                # OK, proceed
                break
            else : # must be datagram rejected
                # can't proceed
                raise Exception("Failure - Request Datagram rejected")

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
    
def sendLockCommand(destination, node) :
    reply = [0x20, 0x88]
    reply.extend(node)
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, reply)

    olcbchecker.sendMessage(message)

def checkLockReply(destination, node, logger) :
    # returns non-zero if fail
    try :
        reply = getReplyDatagram(destination)
    except Exception as e:
        logger = logging.getLogger("MEMORY")
        logger.warning (str(e))
        return (3)
    # check that the reply is OK
    if len(reply.data) < 8 :
        logger = logging.getLogger("MEMORY")
        logger.warning ("Failure - reply was too short")
        return (3)
        
    if reply.data[0] != 0x20 or reply.data[1]!= 0x8A :
        logger = logging.getLogger("MEMORY")
        logger.warning ("Failure - improper command set")
        return (3)
    
    # check for expected node ID
    if reply.data[2:] != node :
        logger = logging.getLogger("MEMORY")
        logger.warning ("Failure - Unexpects node ID {}, expected {}".format(reply.data[2:], node))    
    # is OK
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

    # lock contents used by check
    nodeA = [1,2,3,4,5,6]
    nodeB = [6,5,4,3,2,1]
    zero =  [0,0,0,0,0,0]
    
    sendLockCommand(destination, zero)
    reply = checkLockReply(destination, zero, logger)
    if reply != 0 : logger.warning ("Failure - step 1 failed"); return reply    
      
    sendLockCommand(destination, nodeA)
    reply = checkLockReply(destination, nodeA, logger)
    if reply != 0 : logger.warning ("Failure - step 2 failed"); return reply     

    sendLockCommand(destination, nodeB)
    reply = checkLockReply(destination, nodeA, logger)
    if reply != 0 : logger.warning ("Failure - step 3 failed"); return reply     
        
    sendLockCommand(destination, zero)
    reply = checkLockReply(destination, zero, logger)
    if reply != 0 : logger.warning ("Failure - step 4 failed"); return reply   
        
    sendLockCommand(destination, nodeB)
    reply = checkLockReply(destination, nodeB, logger)
    if reply != 0 : logger.warning ("Failure - step 5 failed"); return reply 
        
    sendLockCommand(destination, nodeA)
    reply = checkLockReply(destination, nodeB, logger)
    if reply != 0 : logger.warning ("Failure - step 6 failed"); return reply 
        
    sendLockCommand(destination, nodeA)
    reply = checkLockReply(destination, nodeB, logger)
    if reply != 0 : logger.warning ("Failure - step 7 failed"); return reply 
        
    sendLockCommand(destination, zero)
    reply = checkLockReply(destination, zero, logger)
    if reply != 0 : logger.warning ("Failure - step 8 failed"); return reply 
        
    sendLockCommand(destination, zero)
    reply = checkLockReply(destination, zero, logger)
    if reply != 0 : logger.warning ("Failure - step 9 failed"); return reply 
        
    
    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)
