#!/usr/bin/env python3.10
'''
This checks that a node responds to a Stream Initiate Request with
either a valid Stream Initiate Reply or Optional Interaction Rejected.

Per StreamTransportS section 7.1, the destination node is required to
send a Stream Initiate Reply, or the general error message Optional
Interaction Rejected.

Usage:
python3.10 check_st10_initiate.py

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

    # check if PIP says this is present
    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning("Failed in setup, no PIP information received")
            return (2)
        if not PIP.STREAM_PROTOCOL in pipSet :
            logger.info("Passed - due to Stream protocol not in PIP")
            return(0)

    # Send Stream Initiate Request
    # Bytes 0-1: Max Buffer Size = 256 (0x0100)
    # Bytes 2-3: Flags = 0x0000
    # Byte 4: Source Stream ID = 0x01
    data = [0x01, 0x00, 0x00, 0x00, 0x01]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    sid = 0x01
    did = None
    stream_accepted = False

    while True :
        try :
            received = olcbchecker.getMessage(2.0)

            if received.mti == MTI.Optional_Interaction_Rejected :
                if destination != received.source :
                    continue
                logger.info("Passed - node responded with Optional "
                            "Interaction Rejected")
                return 0

            if received.mti == MTI.Stream_Initiate_Reply :
                if destination != received.source :
                    continue

                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    logger.warning("Failure - Unexpected destination of "
                                   "reply: {}".format(received.destination))
                    return(3)

                if len(received.data) < 6 :
                    logger.warning("Failure - Stream Initiate Reply too "
                                   "short: {} bytes".format(
                                       len(received.data)))
                    return(3)

                # Check SID echoed back
                if received.data[4] != sid :
                    logger.warning("Failure - Source Stream ID not echoed: "
                                   "sent 0x{:02X}, got 0x{:02X}".format(
                                       sid, received.data[4]))
                    return(3)

                # Check DID not reserved
                did = received.data[5]
                if did == 0xFF :
                    logger.warning("Failure - Destination Stream ID is "
                                   "reserved value 0xFF")
                    return(3)

                # Check flags
                flags = (received.data[2] << 8) | received.data[3]
                buf_size = (received.data[0] << 8) | received.data[1]

                if flags == 0x0000 or flags == 0x8000 :
                    # accepted
                    if buf_size == 0 :
                        logger.warning("Failure - accepted but buffer "
                                       "size is 0")
                        return(3)
                    if buf_size > 256 :
                        logger.warning("Failure - reply buffer size {} "
                                       "exceeds requested 256".format(
                                           buf_size))
                        return(3)
                    stream_accepted = True
                elif (flags & 0xF000) == 0x1000 or \
                        (flags & 0xF000) == 0x2000 :
                    # rejected with valid error code
                    if buf_size != 0 :
                        logger.warning("Failure - rejected but buffer "
                                       "size is non-zero: {}".format(
                                           buf_size))
                        return(3)
                else :
                    logger.warning("Failure - invalid flags in reply: "
                                   "0x{:04X}".format(flags))
                    return(3)

                break

            # ignore other messages
            continue

        except Empty:
            logger.warning("Failure - no reply to Stream Initiate Request")
            return(3)

    # If stream was accepted, close it cleanly
    if stream_accepted :
        complete_data = [sid, did]
        message = Message(MTI.Stream_Data_Complete,
                          NodeID(olcbchecker.ownnodeid()), destination,
                          complete_data)
        olcbchecker.sendMessage(message)
        time.sleep(0.5)

    # Stability soak
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
                logger.warning("Failure - node rebooted after stream "
                               "initiation")
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
                logger.warning("Failure - node stopped responding after "
                               "stream initiation")
                return(3)

            last_ping = time.time()

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
