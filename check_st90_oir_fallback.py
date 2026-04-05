#!/usr/bin/env python3.10
'''
This verifies that when a node has STREAM_PROTOCOL in PIP, it responds
to a Stream Initiate Request with either a Stream Initiate Reply or
an Optional Interaction Rejected (OIR) message.

Both responses are valid per StreamTransportS section 7.1. OIR is a
spec-legal fallback. Failure is if neither is received.

Usage:
python3.10 check_st90_oir_fallback.py

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

    # This check requires STREAM_PROTOCOL in PIP
    pipSet = olcbchecker.gatherPIP(destination, always=True)
    if pipSet is None:
        logger.warning("Failed in setup, no PIP information received")
        return (2)
    if not PIP.STREAM_PROTOCOL in pipSet :
        logger.info("Passed - Stream protocol not in PIP, this check "
                     "is for stream-capable nodes only")
        return(0)

    # Send Stream Initiate Request
    sid = 0x90
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
                logger.info("Passed - node responded with OIR "
                            "(spec-legal fallback)")
                return 0

            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) < 6 :
                    logger.warning("Failure - reply too short: {} bytes"
                                   .format(len(received.data)))
                    return(3)

                flags = (received.data[2] << 8) | received.data[3]
                buf_size = (received.data[0] << 8) | received.data[1]
                did = received.data[5]

                if flags == 0x0000 or flags == 0x8000 :
                    # accepted - close it
                    if buf_size > 0 :
                        complete = Message(MTI.Stream_Data_Complete,
                                          NodeID(olcbchecker.ownnodeid()),
                                          destination, [sid, did])
                        olcbchecker.sendMessage(complete)
                        time.sleep(0.3)

                logger.info("Passed - node responded with Stream "
                            "Initiate Reply")
                return 0

            continue

        except Empty:
            logger.warning("Failure - node with STREAM_PROTOCOL in PIP "
                           "did not respond to Stream Initiate Request "
                           "with either Reply or OIR")
            return(3)


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
