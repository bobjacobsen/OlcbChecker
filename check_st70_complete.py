#!/usr/bin/env python3.10
'''
This checks that a stream can be cleanly closed and reopened.

Opens a stream, sends some data (less than MaxBufSize), sends Stream
Data Complete, verifies no errors, then opens a new stream to confirm
the node freed its resources.

Per StreamTransportS section 7.4, Stream Data Complete transitions the
stream to Closed state.

Usage:
python3.10 check_st70_complete.py

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

    # Open first stream
    sid1 = 0x70
    buf_size, did1 = _open_stream(logger, destination, 256, sid1)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "check completion")
        return 0

    # Send a small amount of data (less than MaxBufSize)
    small_size = min(buf_size - 1, 10) if buf_size > 1 else 1
    payload = list(range(small_size))
    data = [did1] + payload
    message = Message(MTI.Stream_Data_Send,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    # Send Stream Data Complete
    total_bytes = small_size
    complete_data = [sid1, did1]
    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      complete_data)
    olcbchecker.sendMessage(message)

    # Brief pause then check for errors
    time.sleep(0.5)

    # Check for any error messages
    while True :
        try :
            received = olcbchecker.getMessage(0.5)
            if destination != received.source :
                continue
            if received.mti == MTI.Terminate_Due_To_Error :
                logger.warning("Failure - node sent Terminate Due To "
                               "Error after Stream Data Complete")
                return(3)
            if received.mti == MTI.Initialization_Complete or \
                    received.mti == MTI.Initialization_Complete_Simple :
                logger.warning("Failure - node rebooted after stream "
                               "completion")
                return(3)
        except Empty:
            break

    # Open a second stream to verify resources were freed
    sid2 = 0x71
    buf_size2, did2 = _open_stream(logger, destination, 256, sid2)

    if buf_size2 is None :
        logger.warning("Failure - could not reopen stream after "
                       "closing first stream")
        return(3)

    # Close the second stream
    complete = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid2, did2])
    olcbchecker.sendMessage(complete)
    time.sleep(0.3)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
