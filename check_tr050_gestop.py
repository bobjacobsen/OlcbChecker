#!/usr/bin/env python3.10
'''
Check global emergency stop

Usage:
python3.10 check_tr050_gestop.py

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

    try :  # to be sure to set speed to zero
        # send a "Set speed and direction to 0.2 scale m/s reverse"
        speed1 = 0x3e
        speed2 = 0x4c
        speed1R = speed1 | 0x80
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, [0x00, speed1R, speed2])
        olcbchecker.sendMessage(message)
        # no reply expected to this
        
        # send a "Query speed and direction"
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, [0x10])
        olcbchecker.sendMessage(message)
    
        # expect a reply    
        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)
            
        if len(reply.data) < 8:
            logger.warning ("Failure: reply 1 was too short: {}; byte[1] = 0x{:02X}".format(len(reply.data), reply.data[1]))
            return (3)
        
        # check that the set speed was echoed back
        if reply.data[1] != speed1R or reply.data[2] != speed2:
            logger.warning ("Warning - set speed 1 did not read back properly")      
    
    
        # produce global Emergency Stop event
        message = Message(MTI.Producer_Consumer_Event_Report, NodeID(olcbchecker.ownnodeid()), destination, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFD])
        olcbchecker.sendMessage(message)
        # no reply expected to this
        
    
        # send a "Query speed and direction"
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, [0x10])
        olcbchecker.sendMessage(message)
    
        # expect a reply with 0.2 reverse 
        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)
            
        if len(reply.data) < 8:
            logger.warning ("Failure: reply 2 was too short: {}; byte[1] = 0x{:02X}".format(len(reply.data), reply.data[1]))
            return (3)
        
        # check that the set speed was echoed back
        if reply.data[1] != speed1R or reply.data[2] != speed2:
            logger.warning ("Warning - global estop changed speed")      
    
    
        # send a "Set speed and direction to 0.2 scale m/s forward"
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, [0x00, speed1, speed2])
        olcbchecker.sendMessage(message)
        # no reply expected to this
        
        # send a "Query speed and direction"
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, [0x10])
        olcbchecker.sendMessage(message)
    
        # expect a reply    
        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)
            
        if len(reply.data) < 8:
            logger.warning ("Failure: reply 3 was too short: {}; byte[1] = 0x{:02X}".format(len(reply.data), reply.data[1]))
            return (3)
        
        # check that the set speed was echoed back
        if reply.data[1] != speed1 or reply.data[2] != speed2:
            logger.warning ("Warning - set speed 3 did not read back properly")      
    
        # produce global clear Emergency Stop event
        message = Message(MTI.Producer_Consumer_Event_Report, NodeID(olcbchecker.ownnodeid()), destination, [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF, 0xFC])
        olcbchecker.sendMessage(message)
        # no reply expected to this

    finally:
        # send a "Set speed and direction to 0.0 scale m/s forward"
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination, [0x00, 0x00, 0x00])
        olcbchecker.sendMessage(message)         

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
