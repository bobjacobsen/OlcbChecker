#!/usr/bin/env python3.10
'''
This checks that a node which does NOT advertise Stream Protocol in PIP
properly rejects a Stream Initiate Request with either OIR or a Stream
Initiate Reply with a permanent/temporary error.

Usage:
python3.10 check_st20_reject_unsupported.py

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
    import olcbchecker.setup
    logger = logging.getLogger("STREAM")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # This check is specifically for nodes that do NOT support streams
    pipSet = olcbchecker.gatherPIP(destination, always=True)
    if pipSet is None:
        logger.warning("Failed in setup, no PIP information received")
        return (2)
    if PIP.STREAM_PROTOCOL in pipSet :
        logger.info("Passed - Stream protocol is in PIP, this check "
                     "is for unsupported nodes only")
        return(0)

    # Send Stream Initiate Request
    data = [0x01, 0x00, 0x00, 0x00, 0x01]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(2.0)

            if destination != received.source :
                continue

            if received.mti == MTI.Optional_Interaction_Rejected :
                logger.info("Passed - node correctly rejected with OIR")
                return 0

            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue

                if len(received.data) < 6 :
                    logger.warning("Failure - Stream Initiate Reply too "
                                   "short: {} bytes".format(
                                       len(received.data)))
                    return(3)

                flags = (received.data[2] << 8) | received.data[3]
                buf_size = (received.data[0] << 8) | received.data[1]

                # Should be rejected
                if flags == 0x0000 or flags == 0x8000 :
                    if buf_size > 0 :
                        logger.warning("Failure - node accepted stream "
                                       "but does not advertise Stream "
                                       "Protocol in PIP")
                        return(3)

                # Valid rejection
                if (flags & 0xF000) == 0x1000 or \
                        (flags & 0xF000) == 0x2000 :
                    if buf_size != 0 :
                        logger.warning("Failure - rejected but buffer "
                                       "size non-zero: {}".format(buf_size))
                        return(3)
                    logger.info("Passed - node correctly rejected with "
                                "Stream Initiate Reply error 0x{:04X}"
                                .format(flags))
                    return 0

                logger.warning("Failure - unexpected flags 0x{:04X}"
                               .format(flags))
                return(3)

            continue

        except Empty:
            logger.warning("Failure - no reply to Stream Initiate Request "
                           "from node that does not support streams")
            return(3)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
