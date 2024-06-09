#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check ACDI consistency

Usage:
python3.10 check_mc10_co.py

The -h option will display a full list of options.
'''

import sys

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP
from openlcb.snip import SNIP

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
    
# get a string from a certain place in memory
def read_memory(destination, address, length, space) :  
    ad1 = (address >> 24) & 0xFF
    ad2 = (address >> 16) & 0xFF
    ad3 = (address >> 8) & 0xFF
    ad4 = address & 0xFF

    memory_read_command = [0x20, 0x40, ad1, ad2, ad3, ad4, space, length] 
    datagram = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, memory_read_command)
    olcbchecker.sendMessage(datagram)
    content = getReplyDatagram(destination).data[7:]
    # if we just asked for one byte, return that as an int
    if length == 1 : return content[0]
    # convert to string for convenience
    result = ""
    for one in content:  
        if one == 0 : break
        result = result+chr(one)
    return result        

def check():
    # set up the infrastructure

    trace = olcbchecker.trace() # just to be shorter

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################
    
    pipSet = olcbchecker.gatherPIP(destination, always = True)

    memory_config_present = (pipSet is None) or (PIP.MEMORY_CONFIGURATION_PROTOCOL in pipSet)
    snip_in_pip = (pipSet is None) or (PIP.SIMPLE_NODE_IDENTIFICATION_PROTOCOL in pipSet)
    acdi_in_pip = (pipSet is None) or (PIP.ADCDI_PROTOCOL  in pipSet)

    #####
    # ACDI bit set and Memory Configuration bit not set
    #####

    if acdi_in_pip and not memory_config_present :  
        print ("Failure - ACDI is in PIP but Memory Configuration is not")
        return 3
        
    #####
    # ACDI bit and Memory Configuration bit set
    #####
    
    manufacturerName = ""
    modelName = ""
    hardwareVersion = ""
    softwareVersion = ""
    userProvidedNodeName = ""
    userProvidedDescription = ""

    if acdi_in_pip and memory_config_present :
    
        # check 251 and 252 spaces show present
        memory_address_space_cmd = [0x20, 0x84, 251] 
        datagram = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, memory_address_space_cmd)
        olcbchecker.sendMessage(datagram)
        try :
            content = getReplyDatagram(destination).data
            if content[1] != 0x87 :
                print ("Failure - space 251 marked as not present")
                return 3
        except Exception as e :
            print (e)
            return (3)

        memory_address_space_cmd = [0x20, 0x84, 252] 
        datagram = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, memory_address_space_cmd)
        olcbchecker.sendMessage(datagram)
        try :
            content = getReplyDatagram(destination).data
            if content[1] != 0x87 :
                print ("Failure - space 252 marked as not present")
                return 3
            
            # check version numbers in 251 and 252 spaces
            v2 = read_memory(destination, 0, 1, 252)
            if v2 != 0 and v2 != 4 :
                print("Failure - Space 252 version number not match")
                return (3)
            v1 = read_memory(destination, 0, 1, 251)
            if v1 != 0 and v1 != 2 :
                print("Failure - Space 251 version number not match")
                return (3)
            
            # load the six strings
            manufacturerName =  read_memory(destination, 1, 41, 252)
            modelName =         read_memory(destination, 42, 41, 252)
            hardwareVersion =   read_memory(destination, 83, 21, 252)
            softwareVersion =   read_memory(destination, 104, 21, 252)
            userProvidedNodeName = read_memory(destination, 1, 64, 251)
            userProvidedDescription = read_memory(destination, 64, 64, 251)
        except Exception as e :
            print (e)
            return (3)
            
    
    #####
    # SNIP bit, ACDI bit and Memory Configuration bit set
    #####

    if snip_in_pip and acdi_in_pip and memory_config_present :
    
        # send an SNIP request message to provoke response
        message = Message(MTI.Simple_Node_Ident_Info_Request, NodeID(olcbchecker.ownnodeid()), destination)
        olcbchecker.sendMessage(message)

        results = []
        while True :
            try :
                received = olcbchecker.getMessage() # timeout if no entries
                # is this a snip reply?
                if not received.mti == MTI.Simple_Node_Ident_Info_Reply : continue # wait for next
        
                if destination != received.source : # check source in message header
                    print ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                    return(3)
        
                if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                    print ("Failure - Unexpected destination of reply message: {} {}".format(received, received.destination))
                    return(3)
        
                # accumulate the data
                results.extend(received.data)
            except Empty:
                break  # finished receiving the reply

        # load into SNIP for convenient retrieval
        snip = SNIP()
        snip.addData(results)

        # now check the results against previously acquired data
        if not manufacturerName == snip.manufacturerName :
            print("Failure - SNIP and ACDI manufacturer name did not match")
            return (3)
        if not modelName == snip.modelName :
            print("Failure - SNIP and ACDI model name did not match")
            return (3)
        if not hardwareVersion == snip.hardwareVersion :
            print("Failure - SNIP and ACDI hardware Version did not match")
            return (3)
        if not softwareVersion == snip.softwareVersion :
            print("Failure - SNIP and ACDI software version did not match")
            return (3)
        if not userProvidedNodeName == snip.userProvidedNodeName :
            print("Failure - SNIP and ACDI user provided node name did not match")
            return (3)
        if not manufacturerName == snip.manufacturerName :
            print("Failure - SNIP and ACDI user provided description did not match")
            return (3)
    

    #####
    #  Memory Configuration bit and CDI bit set
    #####

    if memory_config_present and acdi_in_pip :
    
        # read CDI to check for ACDI
    
        address = 0
        LENGTH = 64
        content = []
    
        while not 0x00 in content and address < 820 : 
    
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
            except Exception as e:
                print (e)
                return (3)
        
            content.extend(reply.data[6:]) 
            address = address+LENGTH
         
        # here have front of CDI
        # convert to string for convenience
        result = ""
        for one in content:  
            if one == 0 : break
            result = result+chr(one)
        acdi_in_cdi = "<acdi" in result # could be <acdi/> or <acdi></acdi>

        if acdi_in_cdi and not acdi_in_pip :
            print ("Failure - ACDI in CDI but not in PIP")
            return 3

        if not acdi_in_cdi and acdi_in_pip :
            print ("Failure - ACDI in PIP but not in CDI")
            return 3

    
    
    if trace >= 10 : print("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(check())
