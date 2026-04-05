#!/usr/bin/env python3.10
'''
This checks basic stream data transfer and flow control.

Opens a stream, sends exactly MaxBufSize bytes of data, and verifies
that the destination sends a Stream Data Proceed message.

Per StreamTransportS section 7.3, after sending MaxBufSize bytes the
source pauses, and the destination sends a Stream Data Proceed when
ready for more.

Usage:
python3.10 check_st60_data_send.py

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


def _open_stream(logger, destination, proposed_size, sid):
    '''Attempt to open a stream. Returns (buf_size, did) or (None, None).'''
    import olcbchecker

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
                return (None, None)

            if received.mti == MTI.Stream_Initiate_Reply :
                if NodeID(olcbchecker.ownnodeid()) != received.destination :
                    continue
                if len(received.data) < 6 :
                    return (None, None)

                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                did = received.data[5]

                if (flags == 0x0000 or flags == 0x8000) and buf_size > 0 :
                    return (buf_size, did)
                else :
                    return (None, None)

            continue

        except Empty:
            return (None, None)


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

    sid = 0x60
    buf_size, did = _open_stream(logger, destination, 256, sid)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "test data transfer")
        return 0

    # Send exactly MaxBufSize bytes of payload
    # Stream Data Send: byte 0 = DID, bytes 1+ = payload
    bytes_sent = 0
    while bytes_sent < buf_size :
        chunk_size = min(buf_size - bytes_sent, 64)
        payload = [(bytes_sent + i) & 0xFF for i in range(chunk_size)]
        data = [did] + payload
        message = Message(MTI.Stream_Data_Send,
                          NodeID(olcbchecker.ownnodeid()), destination, data)
        olcbchecker.sendMessage(message)
        bytes_sent += chunk_size

    # Wait for Stream Data Proceed
    while True :
        try :
            received = olcbchecker.getMessage(3.0)

            if destination != received.source :
                continue

            if received.mti == MTI.Stream_Data_Proceed :
                if len(received.data) < 2 :
                    logger.warning("Failure - Stream Data Proceed too "
                                   "short: {} bytes"
                                   .format(len(received.data)))
                    # still close the stream
                    break

                if received.data[0] != sid :
                    logger.warning("Failure - Proceed SID mismatch: "
                                   "expected 0x{:02X}, got 0x{:02X}"
                                   .format(sid, received.data[0]))
                    break

                if received.data[1] != did :
                    logger.warning("Failure - Proceed DID mismatch: "
                                   "expected 0x{:02X}, got 0x{:02X}"
                                   .format(did, received.data[1]))
                    break

                # Success - got valid Proceed
                complete = Message(MTI.Stream_Data_Complete,
                                  NodeID(olcbchecker.ownnodeid()),
                                  destination, [sid, did])
                olcbchecker.sendMessage(complete)
                time.sleep(0.3)
                logger.info("Passed")
                return 0

            if received.mti == MTI.Terminate_Due_To_Error :
                logger.warning("Failure - node sent Terminate Due To "
                               "Error during data transfer")
                return(3)

            continue

        except Empty:
            logger.warning("Failure - no Stream Data Proceed received "
                           "after sending {} bytes".format(bytes_sent))
            # close the stream
            complete = Message(MTI.Stream_Data_Complete,
                              NodeID(olcbchecker.ownnodeid()),
                              destination, [sid, did])
            olcbchecker.sendMessage(complete)
            time.sleep(0.3)
            return(3)

    # If we broke out with an error, close and fail
    complete = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid, did])
    olcbchecker.sendMessage(complete)
    time.sleep(0.3)
    return(3)


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
