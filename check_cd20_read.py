#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check CDI contents against schema

Usage:
python3.10 check_cd20_read.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

import xmlschema

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
                raise Exception("Failure - Original Datagram rejected")

        except Empty:
            raise Exception("Failure - no reply to request datagram")
    
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
    
    


def check():
    # set up the infrastructure

    logger = logging.getLogger("CDI")

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
            logger.warning("Failed in setup, no PIP information received")
            return (2)
        if not PIP.CONFIGURATION_DESCRIPTION_INFORMATION in pipSet :
            logger.info("Passed - due to CDI protocol not in PIP")
            return(0)

    address = 0
    LENGTH = 64
    content = []

    retval = 0
    
    while not 0x00 in content : 
    
        ad1 = (address >> 24) & 0xFF
        ad2 = (address >> 16) & 0xFF
        ad3 = (address >> 8) & 0xFF
        ad4 = address & 0xFF
        
        # send an read datagran
        request = [0x20, 0x43, ad1,ad2,ad3,ad4, LENGTH]
        message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, request)
        olcbchecker.sendMessage(message)

        try :
            reply = getReplyDatagram(destination)

            # if read failed, the check failed - no 0 read?
            if reply.data[1] == 0x58 :
                logger.warning("Failure - CDI read operation failed.  Perhaps no terminating zero byte?")
                retval = retval+1
                break

        except Exception as e:
            logger.warning(e)
            # this returns immediately because we can't continue
            return (3)
        
        content.extend(reply.data[6:]) 
        address = address+LENGTH
         
    # here have CDI, perhaps plus a few zeros.
    # convert to string
    result = ""
    for one in content:  
        if one == 0 : break
        result = result+chr(one)

    # check length against memory space definition.
    # first, get definition - a previous check made sure it's there
    olcbchecker.sendMessage(Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x84, 0xFF]))
    reply = getReplyDatagram(destination)
    if reply.data[1] == 0x87 :
        length = reply.data[3]*2568256*256+reply.data[4]*256*256+reply.data[5]*256+reply.data[6]+1 # datagram is highest address, doesn't include location 0 
    else :
        logger.warning("Failure - address space 0xFF did not verify")
        retval = retval+1
    if len(content) != length :
        logger.warning("Failure - length of data read {} does not match address space length {}".format(len(content), length))
        retval = retval+1
        
    # check starting line
    # although the Standard is more specific, we accept
    #    both ' and "
    #    optional attributes, like encoding, after the initial version attribute
    if not result.translate(str.maketrans("'",'"')).startswith('<?xml version="1.0"') :
        firstLine = result[0: result.find("\n")]
        logger.warning("Failure - First line not correct: \""+firstLine+"\"")
        retval = retval+1
        
    # retrieve schema name and check
    key = "xsi:noNamespaceSchemaLocation="
    start = result.find(key)
    quote = result[start+len(key)]  # could be ', could be "
    end = result.find(quote, start+len(key)+1)
    schemaLocation = result[start+len(key)+1:end]
    if not schemaLocation.startswith("http://openlcb.org/schema/cdi/1") :
        logger.error("Failure - unexpected schema URL: "+schemaLocation)
        retval = retval+1
    
    # tempory write to file; this needs to be changed to in-memory
    temp = open("tempCDI.xml", "w")
    temp.write(result)
    temp.close()
    
    try :
        xmlschema.validate('tempCDI.xml', schemaLocation)
    except Exception as e:
        logger.warning("Failure - CDI XML "+str(e))
        return 3
    
    if retval == 0 :
        logger.info("Passed")
    else :
        logger.info("Failed {} checks, see above".format(str(retval)))
    return retval

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
