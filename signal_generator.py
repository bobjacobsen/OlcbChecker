#!/usr/bin/env python3.10
'''
This uses the CAN link layer to generate
messages for stimulating timing measurements.

You should edit the `while` loop at the bottom
to send the particular messages you'd like to exercise.
There are some commented-out examples.

Usage e.g.:
python3.10 signal_generator.py -d /dev/cu.usbmodemCC570001B1

The -h option will display a full list of options.
'''

import sys
import time

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI

def check():
    # set up the infrastructure

    import olcbchecker.setup
    trace = olcbchecker.trace() # just to be shorter

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    # predefine some messages
    snip = Message(MTI.Simple_Node_Ident_Info_Request, NodeID(olcbchecker.ownnodeid()), destination)
    pip = Message(MTI.Protocol_Support_Inquiry, NodeID(olcbchecker.ownnodeid()), destination)
    datagramNull = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [00, 00])
    datagramRead = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x43, 0, 0, 0, 0, 2])
    datagramAck  = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination)
    
    # wait for alias allocation to complete
    time.sleep(2.000)
    
    while True :
    
        # SNIP and pip
        olcbchecker.sendMessage(snip)
        olcbchecker.sendMessage(snip)
        #time.sleep(0.008)
        #olcbchecker.sendMessage(snip)
        olcbchecker.sendMessage(pip)
        
        # Exercise datagrams 
        # The delays before the responses are manually tuned for a specific node type
        #olcbchecker.sendMessage(datagramRead)
        #olcbchecker.sendMessage(datagramRead)
        #olcbchecker.sendMessage(datagramRead)
        #time.sleep(0.150)
        #olcbchecker.sendMessage(datagramAck)
        #time.sleep(0.100)
        #olcbchecker.sendMessage(datagramAck)
        #time.sleep(0.100)
        #olcbchecker.sendMessage(datagramAck)
        
        # repeat periodically forever
        time.sleep(3.000)

if __name__ == "__main__":
    sys.exit(check())
    
