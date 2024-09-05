#!/usr/bin/env python3.10
'''
Check set and query Train functions

Usage:
python3.10 check_tr030_func.py

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

def getTrainControlReply(destination) :
    '''
    Invoked after a train control message gets
    sent, this waits for a train control reply
    and returns it.
    Raises Exception if something went wrong.
    '''

    # wait for the reply datagram
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a train control reply, OK or not?
            if not (received.mti == MTI.Traction_Control_Reply) : 
                continue # wait for next
    
            if destination != received.source : # check source in message header
                continue
    
            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                continue

            # here we've received the reply datagram
            return received
            
        except Empty:
            raise Exception("Failure - no reply datagram received")
    


def check():
    # set up the infrastructure

    logger = logging.getLogger("TRAIN_CONTROL")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################
    
    # check if PIP says this is present
    pipSet = olcbchecker.gatherPIP(destination)  # needed for CDI check later
    if olcbchecker.isCheckPip() : 
        if pipSet is None:
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.TRAIN_CONTROL_PROTOCOL in pipSet :
            logger.info("Passed - due to Train Control protocol not in PIP")
            return(0)

    try :   # to be sure to set Function off 
        # set F0 on
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, 
                    [0x01, 0x00, 0x00, 0x00,  0x00, 0x01])
        olcbchecker.sendMessage(message)
        # no reply expected to this
        
        # send a "Query Function" for F0
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, 
                    [0x11, 0x00, 0x00, 0x00])
        olcbchecker.sendMessage(message)
    
        # expect a reply    
        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)
            
        if len(reply.data) < 6:
            logger.warning ("Failure: reply 1 was too short: {}; byte[1] = 0x{:02X}".format(len(reply.data), reply.data[1]))
            return (3)
        
        # check that the function was echoed back
        if reply.data[4] != 0x00 or reply.data[5] != 0x01:
            logger.warning ("Warning - function 0 did not read back properly")      
    

        # set F0 off
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, 
                    [0x01, 0x00, 0x00, 0x00,  0x00, 0x00])
        olcbchecker.sendMessage(message)
        # no reply expected to this
        
        # send a "Query Function" for F0
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, 
                    [0x11, 0x00, 0x00, 0x00])
        olcbchecker.sendMessage(message)
    
        # expect a reply    
        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)
            
        if len(reply.data) < 6:
            logger.warning ("Failure: reply 1 was too short: {}; byte[1] = 0x{:02X}".format(len(reply.data), reply.data[1]))
            return (3)
        
        # check that the function was echoed back
        if reply.data[4] != 0x00 or reply.data[5] != 0x00:
            logger.warning ("Warning - function 0 did not read back properly")      
    
    
    
    
          
    
    finally:
        # send a "SetF0 off 
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, 
                    [0x01, 0x00, 0x00, 0x00,  0x00, 0x00])
        olcbchecker.sendMessage(message)         

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    olcbchecker.setup.interface.close()
    sys.exit(result)