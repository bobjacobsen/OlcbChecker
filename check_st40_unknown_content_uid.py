#!/usr/bin/env python3.10
'''
This checks behavior when sending a Stream Initiate Request without prior
announcement and with an unknown Stream Content UID.

Per StreamTransportS section 7.2, if the Stream Content UID is unknown to
the destination node, it should use the Permanent Error, Unimplemented
error code (0x1040) in the rejection message. Acceptance is also valid.

Usage:
python3.10 check_st40_unknown_content_uid.py

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

    # Send 12-byte Stream Initiate Request with unknown Content UID
    # Bytes 0-1: Max Buffer Size = 256
    # Bytes 2-3: Flags = 0x0000
    # Byte 4: Source Stream ID = 0x40
    # Byte 5: Proposed Destination Stream ID = 0x00
    # Bytes 6-11: Fabricated Stream Content UID
    sid = 0x40
    data = [0x01, 0x00, 0x00, 0x00, sid, 0x00,
            0xFE, 0xFE, 0xFE, 0xFE, 0xFE, 0xFE]
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
                    # accepted - this is valid per spec
                    logger.info("  Node accepted unknown Content UID "
                                "(valid per spec)")
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
                    # rejected - expected, especially 0x1040
                    if buf_size != 0 :
                        logger.warning("Failure - rejected but buffer "
                                       "size non-zero: {}".format(buf_size))
                        return(3)
                    logger.info("Passed - node rejected unknown UID with "
                                "error 0x{:04X}".format(flags))
                    return 0

                else :
                    logger.warning("Failure - invalid flags 0x{:04X}"
                                   .format(flags))
                    return(3)

            continue

        except Empty:
            logger.warning("Failure - no reply to Stream Initiate Request "
                           "with unknown Content UID")
            return(3)


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
