#!/usr/bin/env python3.10
'''
This uses the CAN link layer to generate
messages for stimulating timing measurements.

Usage e.g.:
python3.10 signal_generator.py -d /dev/cu.usbmodemCC570001B1

The -h option will display a full list of options.
'''

import sys

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI

from queue import Empty

def check():
    # set up the infrastructure

    import olcbchecker.setup
    trace = olcbchecker.trace() # just to be shorter

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    # predefine messages
    snip = Message(MTI.Simple_Node_Ident_Info_Request, NodeID(olcbchecker.ownnodeid()), destination)
    pip = Message(MTI.Protocol_Support_Inquiry, NodeID(olcbchecker.ownnodeid()), destination)
    
    import time
    while True :
    
    	olcbchecker.sendMessage(snip)
    	olcbchecker.sendMessage(snip)
    	#time.sleep(0.018)
    	#olcbchecker.sendMessage(pip)
    	time.sleep(3.000)
		
if __name__ == "__main__":
    sys.exit(check())
    
