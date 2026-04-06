#!/usr/bin/env python3.10
'''
This checks that the DUT handles a Terminate Due To Error during an
open stream gracefully.

Per StreamTransportS section 7.4, a stream is closed if the remote node
sends a Terminate Due To Error whose rejected MTI is Stream Data Send
or Stream Data Proceed.

Check A: TDE with rejected MTI = Stream Data Proceed (0x0888)
Check B: TDE with rejected MTI = Stream Data Send (0x1F88)

Both checks verify that the stream slot is freed (re-open succeeds)
and the node does not reboot.

Usage:
python3.10 check_st80_terminate_error.py

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

    sid = 0x80
    buf_size, did = _open_stream(logger, destination, 256, sid)

    if buf_size is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "check error termination")
        return 0

    # --- Check A: TDE with rejected MTI = Stream Data Proceed (0x0888) ---

    # Send Terminate Due To Error to close the stream abruptly.
    # Per Message Network Standard, TDE payload is:
    #   bytes 0-1 = error code (use 0x1000 Permanent error)
    #   bytes 2-3 = rejected MTI
    error_code = 0x1000
    rejected_mti = MTI.Stream_Data_Proceed.value
    error_data = [
        (error_code >> 8) & 0xFF, error_code & 0xFF,
        (rejected_mti >> 8) & 0xFF, rejected_mti & 0xFF
    ]
    message = Message(MTI.Terminate_Due_To_Error,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      error_data)
    olcbchecker.sendMessage(message)

    time.sleep(1.0)

    # Check that the node has not rebooted
    while True :
        try :
            received = olcbchecker.getMessage(0.5)
            if destination != received.source :
                continue
            if received.mti == MTI.Initialization_Complete or \
                    received.mti == MTI.Initialization_Complete_Simple :
                logger.warning("Failure - node rebooted after Terminate "
                               "Due To Error (Stream Data Proceed)")
                return(3)
        except Empty:
            break

    # Verify node is still alive
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
        logger.warning("Failure - node not responding after Terminate "
                       "Due To Error (Stream Data Proceed)")
        return(3)

    # Stream slot must be freed -- require re-open to succeed
    sid2 = 0x81
    buf_size2, did2 = _open_stream(logger, destination, 256, sid2)

    if buf_size2 is None :
        logger.warning("Failure - stream slot not freed after Terminate "
                       "Due To Error (Stream Data Proceed)")
        return(3)

    # Close the recovery stream cleanly
    complete = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid2, did2])
    olcbchecker.sendMessage(complete)
    time.sleep(0.3)

    # --- Check B: TDE with rejected MTI = Stream Data Send (0x1F88) ---

    sid3 = 0x82
    buf_size3, did3 = _open_stream(logger, destination, 256, sid3)

    if buf_size3 is None :
        logger.info("Passed - Check A passed but node declined second "
                    "stream for Check B, skipping Send variant")
        return 0

    rejected_mti_send = MTI.Stream_Data_Send.value
    error_data_send = [
        (error_code >> 8) & 0xFF, error_code & 0xFF,
        (rejected_mti_send >> 8) & 0xFF, rejected_mti_send & 0xFF
    ]
    message = Message(MTI.Terminate_Due_To_Error,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      error_data_send)
    olcbchecker.sendMessage(message)

    time.sleep(1.0)

    # Check that the node has not rebooted
    while True :
        try :
            received = olcbchecker.getMessage(0.5)
            if destination != received.source :
                continue
            if received.mti == MTI.Initialization_Complete or \
                    received.mti == MTI.Initialization_Complete_Simple :
                logger.warning("Failure - node rebooted after Terminate "
                               "Due To Error (Stream Data Send)")
                return(3)
        except Empty:
            break

    # Verify node is still alive
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
        logger.warning("Failure - node not responding after Terminate "
                       "Due To Error (Stream Data Send)")
        return(3)

    # Stream slot must be freed -- require re-open to succeed
    sid4 = 0x83
    buf_size4, did4 = _open_stream(logger, destination, 256, sid4)

    if buf_size4 is None :
        logger.warning("Failure - stream slot not freed after Terminate "
                       "Due To Error (Stream Data Send)")
        return(3)

    # Close the recovery stream cleanly
    complete = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid4, did4])
    olcbchecker.sendMessage(complete)
    time.sleep(0.3)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
