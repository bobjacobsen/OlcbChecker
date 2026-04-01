#!/usr/bin/env python3.10
'''
This checks that a datagram with an unknown protocol byte is properly rejected.

Per DatagramTransportS section 6, the receiving node shall reply with
Datagram Received OK or Datagram Rejected.  A datagram whose first byte
is not a recognised protocol identifier should be rejected with a
permanent error (error code in the 0x1xxx range).

Usage:
python3.10 check_da40_unknown_protocol.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty

def check() :
    # set up the infrastructure

    import olcbchecker.setup
    logger = logging.getLogger("DATAGRAM")

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
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.DATAGRAM_PROTOCOL in pipSet :
            logger.info("Passed - due to Datagram protocol not in PIP")
            return(0)

    # send a datagram with an unknown protocol byte (0x99)
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x99])
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a datagram reply, OK or not?
            if not (received.mti == MTI.Datagram_Received_OK or received.mti == MTI.Datagram_Rejected) :
                continue # wait for next

            if destination != received.source : # check source in message header
                logger.warning ("Failure - Unexpected source of reply message: {} {}".format(received, received.source))
                return(3)

            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                logger.warning ("Failure - Unexpected destination of reply message: {} {}".format(received, received.destination))
                return(3)

            if received.mti == MTI.Datagram_Received_OK :
                logger.warning ("Failure - Datagram with unknown protocol byte was accepted instead of rejected")
                return(3)

            # must be Datagram_Rejected
            if len(received.data) < 2 :
                logger.warning ("Failure - Datagram Rejected reply too short: {} bytes".format(len(received.data)))
                return(3)

            # check for permanent error (upper nibble of first byte should be 0x1x)
            if (received.data[0] & 0xF0) != 0x10 :
                logger.warning ("Failure - Expected permanent error (0x1x), got 0x{:02X}".format(received.data[0]))
                return(3)

            break
        except Empty:
            logger.warning ("Failure - no reply to sent Datagram with unknown protocol byte")
            return(3)

    # Stability soak: wait 30 seconds watching for unexpected reinitialization
    # while periodically verifying the node is still responsive
    import time
    timeout = 30
    ping_interval = 10  # seconds between liveness checks
    last_ping = 0  # force an immediate first ping
    logger.info("Stability soak: monitoring node for {} seconds (pinging every {}s to verify responsiveness)".format(timeout, ping_interval))
    start = time.time()

    while time.time() - start < timeout :
        try :
            received = olcbchecker.getMessage(1) # 1-second poll

            if destination != received.source :
                continue  # ignore messages from other nodes

            if received.mti == MTI.Initialization_Complete or received.mti == MTI.Initialization_Complete_Simple :
                logger.warning("Failure - node rebooted after unknown protocol datagram")
                return (3)

        except Empty:
            pass  # no messages -- expected during quiet periods

        # Periodic liveness ping via Verify Node ID Addressed
        if time.time() - last_ping >= ping_interval :
            olcbchecker.purgeMessages()
            message = Message(MTI.Verify_NodeID_Number_Addressed, NodeID(olcbchecker.ownnodeid()), destination)
            olcbchecker.sendMessage(message)

            alive = False
            while True :
                try :
                    received = olcbchecker.getMessage()
                    if received.mti != MTI.Verified_NodeID and received.mti != MTI.Verified_NodeID_Simple :
                        continue
                    if destination != received.source :
                        continue
                    alive = True
                    break
                except Empty:
                    break

            if not alive :
                logger.warning ("Failure - node stopped responding after unknown protocol datagram")
                return(3)

            last_ping = time.time()

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
