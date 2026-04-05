#!/usr/bin/env python3.10
'''
This checks behavior when requesting the largest possible buffer size (65535).

Per StreamTransportS, the reply Max Buffer Size must be less than or equal
to the proposed value. The node should negotiate down to its capability.

Usage:
python3.10 check_st37_max_buffer.py

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

    # Send Stream Initiate Request with buffer size = 0xFFFF
    sid = 0x30
    data = [0xFF, 0xFF, 0x00, 0x00, sid]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(2.0)

            if destination != received.source :
                continue

            if received.mti == MTI.Optional_Interaction_Rejected :
                logger.info("Passed - node rejected with OIR")
                return 0

            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) < 6 :
                    logger.warning("Failure - reply too short: {} bytes"
                                   .format(len(received.data)))
                    return(3)

                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                did = received.data[5]

                if flags == 0x0000 or flags == 0x8000 :
                    # accepted
                    if buf_size > 0xFFFF :
                        logger.warning("Failure - reply buffer size {} "
                                       "exceeds proposed 65535"
                                       .format(buf_size))
                        return(3)
                    if buf_size == 0 :
                        logger.warning("Failure - accepted with zero "
                                       "buffer size")
                        return(3)
                    logger.info("  Node negotiated buffer to {}"
                                .format(buf_size))
                    # close the stream
                    complete = Message(MTI.Stream_Data_Complete,
                                      NodeID(olcbchecker.ownnodeid()),
                                      destination, [sid, did])
                    olcbchecker.sendMessage(complete)
                    time.sleep(0.3)
                    logger.info("Passed")
                    return 0

                elif (flags & 0xF000) == 0x1000 or \
                        (flags & 0xF000) == 0x2000 :
                    logger.info("Passed - node rejected with error "
                                "0x{:04X}".format(flags))
                    return 0

                else :
                    logger.warning("Failure - invalid flags 0x{:04X}"
                                   .format(flags))
                    return(3)

            continue

        except Empty:
            logger.warning("Failure - no reply to Stream Initiate Request")
            return(3)


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
