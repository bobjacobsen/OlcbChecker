#!/usr/bin/env python3.10
'''
This checks that the node remains stable after stream operations with
a 30-second stability soak.

Opens and closes a stream (or handles rejection), then monitors the
node for 30 seconds, periodically pinging to verify responsiveness.

Usage:
python3.10 check_st85_stability.py

The -h option will display a full list of options.
'''

import sys
import logging
import time

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty


def check():
    import olcbchecker.setup
    logger = logging.getLogger("STREAM")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning("Failed in setup, no PIP information received")
            return (2)
        if not PIP.STREAM_PROTOCOL in pipSet :
            logger.info("Passed - due to Stream protocol not in PIP")
            return(0)

    # Attempt to open and close a stream
    sid = 0x85
    data = [0x01, 0x00, 0x00, 0x00, sid]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(2.0)
            if destination != received.source :
                continue

            if received.mti == MTI.Optional_Interaction_Rejected :
                break  # no stream to close

            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) >= 6 :
                    flags = (received.data[2] << 8) | received.data[3]
                    buf_size = (received.data[0] << 8) | received.data[1]
                    did = received.data[5]
                    if (flags == 0x0000 or flags == 0x8000) \
                            and buf_size > 0 :
                        # accepted - close it
                        complete = Message(MTI.Stream_Data_Complete,
                                          NodeID(olcbchecker.ownnodeid()),
                                          destination, [sid, did])
                        olcbchecker.sendMessage(complete)
                        time.sleep(0.3)
                break

        except Empty:
            break

    # Stability soak: 30 seconds, pinging every 10s
    timeout = 30
    ping_interval = 10
    last_ping = 0
    logger.info("Stability soak: monitoring node for {} seconds".format(
        timeout))
    start = time.time()

    while time.time() - start < timeout :
        try :
            received = olcbchecker.getMessage(1)

            if destination != received.source :
                continue

            if received.mti == MTI.Initialization_Complete or \
                    received.mti == MTI.Initialization_Complete_Simple :
                logger.warning("Failure - node rebooted during stability "
                               "soak after stream operations")
                return(3)

        except Empty:
            pass

        if time.time() - last_ping >= ping_interval :
            elapsed = int(time.time() - start)
            logger.info("  soak {}/{}s - pinging node...".format(
                elapsed, timeout))
            olcbchecker.purgeMessages()
            message = Message(MTI.Verify_NodeID_Number_Addressed,
                              NodeID(olcbchecker.ownnodeid()), destination)
            olcbchecker.sendMessage(message)

            alive = False
            while True :
                try :
                    received = olcbchecker.getMessage()
                    if received.mti != MTI.Verified_NodeID and \
                            received.mti != MTI.Verified_NodeID_Simple :
                        continue
                    if destination != received.source :
                        continue
                    alive = True
                    break
                except Empty:
                    break

            if not alive :
                logger.warning("Failure - node stopped responding during "
                               "stability soak")
                return(3)

            last_ping = time.time()

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
