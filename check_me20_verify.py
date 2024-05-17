#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check Verify message exchange

Usage:
python3.10 check_me20_verify.py

The -h option will display a full list of options.
'''

import sys

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty
import configure

def check():
    # set up the infrastructure

    import olcbchecker.setup
    trace = olcbchecker.trace() # just to be shorter

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    # Will we be checking PIP?
    pipSet = olcbchecker.gatherPIP(destination)

    ###############################
    # checking sequence starts here
    ###############################

    # send a Verify Nodes Global message
    message = Message(MTI.Verify_NodeID_Number_Global, NodeID(configure.global_config.ownnodeid), None)
    olcbchecker.sendMessage(message)

    # pull the received frames and get the source ID from first as remote NodeID
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries

            if received.mti != MTI.Verified_NodeID :
                continue # ignore other messages

            if destination != received.source : # check source in message header
                continue # allow other nodes to reply to this global request
        
            if len(received.data) != 6 :
                print ("Failure - Unexpected length of reply message: {}".format(received))
                return(3)
            
            if destination != NodeID(received.data) :
                print ("Failure - Unexpected contents of reply message: {}".format(received))
                return(3)
            
            # check against PIP
            if pipSet is not None :
                simple = PIP.SIMPLE_PROTOCOL in pipSet
                if simple and received.mti == MTI.Verified_NodeID :
                    print ("Failure - PIP says Simple Node but didn't receive correct MTI")
                    return(3) 
                elif (not simple) and received.mti == MTI.Verified_NodeID_Simple :
                    print ("Failure - PIP says not Simple Node but didn't receive correct MTI")
                    return(3) 

            break
        except Empty:
            print ("Failure - did not get response to global")
            return(3)

    olcbchecker.purgeMessages()

    # send an addressed verify to this node and check for answer
    message = Message(MTI.Verify_NodeID_Number_Addressed, NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a valid reply?
            if received.mti != MTI.Verified_NodeID and received.mti != MTI.Verified_NodeID_Simple: continue # wait for next
        
            if destination != received.source : # check source in message header
                print ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)
        
            if len(received.data) != 6 :
                print ("Failure - Unexpected length of reply message: {}".format(received))
                return(3)
            
            if destination != NodeID(received.data) :
                print ("Failure - Unexpected contents of reply message: {}".format(received))
                return(3)
            
            # check against PIP
            if pipSet is not None :
                simple = PIP.SIMPLE_PROTOCOL in pipSet
                if simple and received.mti == MTI.Verified_NodeID :
                    print ("Failure - PIP says Simple Node but didn't receive correct MTI")
                    return(3) 
                elif (not simple) and received.mti == MTI.Verified_NodeID_Simple :
                    print ("Failure - PIP says not Simple Node but didn't receive correct MTI")
                    return(3) 
            break
        except Empty:
            print ("Failure - no reply to Verify Node Addressed request")
            return(3) 

    # pull any early received messages
    olcbchecker.purgeMessages()

    # send an addressed verify to a different node (the origin node) and check for lack of answer
    message = Message(MTI.Verify_NodeID_Number_Addressed, NodeID(olcbchecker.ownnodeid()), NodeID(olcbchecker.ownnodeid()))
    olcbchecker.sendMessage(message)

    try :
        received = olcbchecker.getMessage() # timeout if no entries
        # is this a pip reply?
        if received.mti == MTI.Verified_NodeID: # wait for next
            print ("Failure - Should not have gotten a reply {}".format(received))
            return(3) 
        print ("Failure - Unexpected message {}".format(received))
        return(3)  
    except Empty:
        # this is success
        pass

    if trace >= 10 : print("Passed")
    return 0

if __name__ == "__main__":
    sys.exit(check())
