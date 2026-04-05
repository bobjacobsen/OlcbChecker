#!/usr/bin/env python3.10
'''
This checks that the negotiated buffer size in Stream Initiate Reply
never exceeds what was proposed in the Stream Initiate Request.

Per StreamTransportS section 7.1, the Max Buffer Size in the reply must
be less than or equal to what was proposed in the request.

Usage:
python3.10 check_st30_buffer_negotiation.py

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


def _send_initiate_and_check(logger, destination, proposed_size, sid):
    '''Send a Stream Initiate Request and validate the reply buffer size.

    Returns (result_code, did) where did is the assigned DID if accepted.
    '''
    import olcbchecker
    data = [
        (proposed_size >> 8) & 0xFF, proposed_size & 0xFF,
        0x00, 0x00,
        sid
    ]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(2.0)

            if destination != received.source :
                continue

            if received.mti == MTI.Optional_Interaction_Rejected :
                logger.info("  Node rejected with OIR for size {}"
                            .format(proposed_size))
                return (0, None)

            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) < 6 :
                    logger.warning("Failure - reply too short")
                    return (3, None)

                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                did = received.data[5]

                if flags == 0x0000 or flags == 0x8000 :
                    # accepted
                    if buf_size > proposed_size :
                        logger.warning("Failure - reply buffer size {} "
                                       "exceeds proposed {}"
                                       .format(buf_size, proposed_size))
                        return (3, did)
                    if buf_size == 0 :
                        logger.warning("Failure - accepted with zero "
                                       "buffer size")
                        return (3, did)
                    return (0, did)
                elif (flags & 0xF000) == 0x1000 or \
                        (flags & 0xF000) == 0x2000 :
                    # rejected
                    logger.info("  Node rejected for size {} with "
                                "error 0x{:04X}"
                                .format(proposed_size, flags))
                    return (0, None)
                else :
                    logger.warning("Failure - invalid flags 0x{:04X}"
                                   .format(flags))
                    return (3, None)

            continue

        except Empty:
            logger.warning("Failure - no reply for proposed size {}"
                           .format(proposed_size))
            return (3, None)


def _close_stream(destination, sid, did):
    import olcbchecker
    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid, did])
    olcbchecker.sendMessage(message)
    time.sleep(0.3)


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

    # Test with buffer size 64
    sid = 0x10
    result, did = _send_initiate_and_check(logger, destination, 64, sid)
    if result != 0 :
        return result
    if did is not None :
        _close_stream(destination, sid, did)

    olcbchecker.purgeMessages()

    # Test with buffer size 1024
    sid = 0x11
    result, did = _send_initiate_and_check(logger, destination, 1024, sid)
    if result != 0 :
        return result
    if did is not None :
        _close_stream(destination, sid, did)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
