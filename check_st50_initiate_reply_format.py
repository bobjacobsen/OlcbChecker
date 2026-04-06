#!/usr/bin/env python3.10
'''
This validates every field in the Stream Initiate Reply message.

Per StreamTransportS section 5.2, the reply must contain:
- Bytes 0-1: Max Buffer Size (final value, or 0 if rejected)
- Bytes 2-3: Flags and Error Codes
- Byte 4: Source Stream ID (must echo the request)
- Byte 5: Destination Stream ID (0x00-0xFE, 0xFF reserved)

Usage:
python3.10 check_st50_initiate_reply_format.py

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

    # Send Stream Initiate Request with distinctive SID 0x42
    sid = 0x42
    proposed_size = 512
    data = [(proposed_size >> 8) & 0xFF, proposed_size & 0xFF,
            0x00, 0x00, sid]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage(2.0)

            if destination != received.source :
                continue

            if received.mti == MTI.Optional_Interaction_Rejected :
                logger.info("Passed - node responded with OIR")
                return 0

            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue

                # Validate length
                if len(received.data) < 6 :
                    logger.warning("Failure - Stream Initiate Reply must "
                                   "be at least 6 bytes, got {}"
                                   .format(len(received.data)))
                    return(3)

                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                reply_sid = received.data[4]
                did = received.data[5]

                # Validate SID echoed exactly
                if reply_sid != sid :
                    logger.warning("Failure - Source Stream ID not echoed "
                                   "correctly: sent 0x{:02X}, got "
                                   "0x{:02X}".format(sid, reply_sid))
                    return(3)

                # Validate DID not reserved
                if did == 0xFF :
                    logger.warning("Failure - Destination Stream ID uses "
                                   "reserved value 0xFF")
                    return(3)

                # Validate flags/buffer consistency
                if flags == 0x0000 or flags == 0x8000 :
                    # accepted
                    if buf_size == 0 :
                        logger.warning("Failure - accepted (flags "
                                       "0x{:04X}) but buffer size is 0"
                                       .format(flags))
                        return(3)
                    if buf_size > proposed_size :
                        logger.warning("Failure - reply buffer {} exceeds "
                                       "proposed {}".format(buf_size,
                                                            proposed_size))
                        return(3)
                    # close the stream
                    complete = Message(MTI.Stream_Data_Complete,
                                      NodeID(olcbchecker.ownnodeid()),
                                      destination, [sid, did])
                    olcbchecker.sendMessage(complete)
                    time.sleep(0.3)

                elif (flags & 0xF000) == 0x1000 :
                    # permanent error
                    if buf_size != 0 :
                        logger.warning("Failure - permanent error but "
                                       "buffer size non-zero: {}"
                                       .format(buf_size))
                        return(3)
                    # validate specific error codes
                    valid_codes = [0x1000, 0x1010, 0x1020, 0x1040]
                    if flags not in valid_codes :
                        logger.warning("Failure - unknown permanent error "
                                       "code 0x{:04X}".format(flags))
                        return(3)

                elif (flags & 0xF000) == 0x2000 :
                    # temporary error
                    if buf_size != 0 :
                        logger.warning("Failure - temporary error but "
                                       "buffer size non-zero: {}"
                                       .format(buf_size))
                        return(3)
                    valid_codes = [0x2000, 0x2020, 0x2040]
                    if flags not in valid_codes :
                        logger.warning("Failure - unknown temporary error "
                                       "code 0x{:04X}".format(flags))
                        return(3)

                else :
                    logger.warning("Failure - invalid flags pattern "
                                   "0x{:04X}".format(flags))
                    return(3)

                break

            continue

        except Empty:
            logger.warning("Failure - no reply to Stream Initiate Request")
            return(3)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
