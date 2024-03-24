#!/usr/bin/env python3.10
'''
This uses the CAN link layer to generate
a continuous stream of low-priority messages
to provide a background of frames trying to arbitrate

Usage e.g.:
python3.10 background_generator.py -d /dev/cu.usbmodemCC570001B1

The -h option will display a full list of options.

To get the lowest possible CAN priority, this sends
a datagram to the 0xFFF alias.  
'''

import sys
import time

from openlcb.nodeid import NodeID

def check():

    # get and process options
    import configure
        
    trace = configure.trace # just to be shorter
    
    # configure the physical link
    if configure.hostname is not None : 
        from openlcb.canbus.tcpsocket import TcpSocket
        s = TcpSocket()
        s.connect(configure.hostname, configure.portnumber)
    else :
        from openlcb.canbus.seriallink import SerialLink
        s = SerialLink()
        s.connect(configure.devicename)
        
    if trace >= 20 :
        print("RM, SM are message level receive and send; RL, SL are link (frame) interface; RR, SR are raw socket interface")
    
    def sendToSocket(string) :
        if trace >= 40 : print("      SR: "+string.strip())
        s.send(string)


    # Predefined frames
    amdFrameOwn   = ":X10701FFEN03000000FEED;"
    amdFrameODest = ":X10701FFFN03000000BEEF;"
    
    dataFrame   = ":X1AFFFFFEN00;" # from FFF to FFE
    
    # establish aliases for our traffic
    sendToSocket(amdFrameOwn)
    sendToSocket(amdFrameODest)
    
    while True :
    
    	sendToSocket(dataFrame)
		
if __name__ == "__main__":
    sys.exit(check())
    
