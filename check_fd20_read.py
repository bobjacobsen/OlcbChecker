#!/usr/bin/env python3.10
'''
Check FDI contents against schema

Usage:
python3.10 check_fd20_read.py

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
            raise Exception("Failure - no reply to read request")
    
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

    logger = logging.getLogger("FDI")

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
        if not PIP.FUNCTION_DESCRIPTION_INFORMATION in pipSet :
            logger.info("Passed - due to FDI protocol not in PIP")
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
        request = [0x20, 0x40, ad1,ad2,ad3,ad4, 0xFA, LENGTH]
        message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, request)
        olcbchecker.sendMessage(message)

        try :
            reply = getReplyDatagram(destination)
            
            # if read failed, the check failed - no 0 read?
            if (reply.data[1] & 0xF8) == 0x58 :
                logger.warning("Failure - FDI read operation reply indicates read failed. Perhaps no terminating zero byte?")
                retval = retval+1
                break
                
        except Exception as e:
            logger.warning(e)
            # this returns immediately because we can't continue
            return (3)
        
        content.extend(reply.data[7:]) 
        address = address+LENGTH

    receivedContentLength = len(content)         
    # here have FDI, perhaps plus a few zeros.
    # convert to string
    result = ""
    foundNull = False
    for one in content:  
        if one == 0 : 
            foundNull = True
            break
        result = result+chr(one)
    if not foundNull :
        logger.warning("Did not find null at end of FDI")
        retval = retval+1
    
    # check length against memory space definition.
    # first, get definition - a previous check made sure it's there
    olcbchecker.sendMessage(Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x84, 0xFA]))
    reply = getReplyDatagram(destination)
    
    if reply.data[1] == 0x87 :
        length = reply.data[3]*256*256*256+reply.data[4]*256*256+reply.data[5]*256+reply.data[6]
    else :
        logger.warning("Failure - address space 0xFA did not verify")
        retval = retval+1
    
    if (result == "") :
        logger.warning("Failure - no FDI information found - ending check")
        return 1
       
    if receivedContentLength != length :  # includes null if we stripped one
        logger.warning("Failure - length of data read {} does not match address space length {}".format(receivedContentLength, length))
        retval = retval+1
 
    # check starting line
    # although the Standard is more specific, we accept
    #    both ' and "
    #    optional attributes, like encoding, after the initial version attribute
    firstLine = result[0: result.find(">")+1]
    if not result.translate(str.maketrans("'",'"')).startswith('<?xml version="1.0"') :
        logger.warning("Failure - First line not correct: \""+firstLine+"\"")
        retval = retval+1
    
    # Courtesy notification of first line
    if not result.startswith('<?xml version="1.0"?>') :
        logger.info("Note: File starts with "+firstLine+" but recommend start with '<?xml version=\"1.0\"?>'")
        
    # retrieve schema name and check
    key = "xsi:noNamespaceSchemaLocation="
    start = result.find(key)
    quote = result[start+len(key)]  # could be ', could be "
    end = result.find(quote, start+len(key)+1)
    schemaLocation = result[start+len(key)+1:end]
    # accept http or https, because we control that server
    if not schemaLocation.startswith("https://openlcb.org/schema/fdi/1") and not schemaLocation.startswith("http://openlcb.org/schema/fdi/1") :
        logger.error("Failure - unexpected schema URL: "+schemaLocation)
        retval = retval+1
    
 
    # tempory write to file; this needs to be changed to in-memory
    temp = open("tempFDI.xml", "w")
    temp.write(result)
    temp.close()
    
    try :
        xmlschema.validate('tempFDI.xml', schemaLocation)
    except Exception as e:
        logger.warning("Failure - FDI XML "+str(e))
        retval = retval+1
    
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
