#!/usr/bin/env python3.10
'''
This checks that the PIP Simple Protocol subset bit is consistent with
the Verified Node ID MTI used by the node.

Per MessageNetworkS section 4.1.4, nodes shall use:
  - Init Complete 0x0101 and Verified Node ID 0x0171 if Simple
  - Init Complete 0x0100 and Verified Node ID 0x0170 if Full

Usage:
python3.10 check_me60_pip_simple.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty

def check():
    # set up the infrastructure

    import olcbchecker.setup
    logger = logging.getLogger("MESSAGE")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # Step 1: Gather PIP and check Simple Protocol subset bit
    pipSet = olcbchecker.gatherPIP(destination, always=True)
    if pipSet is None:
        logger.warning("Failure - no PIP information received")
        return (2)

    simple_in_pip = PIP.SIMPLE_PROTOCOL in pipSet

    # Step 2: Send Verify Node ID Addressed to target
    olcbchecker.purgeMessages()
    message = Message(MTI.Verify_NodeID_Number_Addressed, NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    # Step 3: Wait for Verified Node ID reply
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # accept either Verified_NodeID or Verified_NodeID_Simple
            if received.mti != MTI.Verified_NodeID and received.mti != MTI.Verified_NodeID_Simple :
                continue # wait for next

            if destination != received.source : # check source in message header
                continue  # allow other nodes

            break
        except Empty:
            logger.warning ("Failure - no Verified Node ID reply received")
            return(3)

    # Step 4: Check consistency
    if simple_in_pip :
        if received.mti != MTI.Verified_NodeID_Simple :
            logger.warning ("Failure - PIP has Simple Protocol bit set but node replied with "
                           "Verified_NodeID (0x{:04X}) instead of Verified_NodeID_Simple (0x{:04X})"
                           .format(received.mti.value, MTI.Verified_NodeID_Simple.value))
            return(3)
    else :
        if received.mti != MTI.Verified_NodeID :
            logger.warning ("Failure - PIP does not have Simple Protocol bit but node replied with "
                           "Verified_NodeID_Simple (0x{:04X}) instead of Verified_NodeID (0x{:04X})"
                           .format(received.mti.value, MTI.Verified_NodeID.value))
            return(3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
