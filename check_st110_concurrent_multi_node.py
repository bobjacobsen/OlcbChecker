#!/usr/bin/env python3.10
'''
This checks that the DUT can handle concurrent streams from two
different source nodes.

The checker claims a second CAN alias to act as a spoofed source node,
then opens one stream from its real identity and one from the spoofed
alias.  Verifies the DUT tracks them independently by source node.

Per StreamTransportTN section 2.3.1, a stream is uniquely identified by
(Source Node ID, Destination Node ID, Source Stream ID).  SID by itself
need not be unique -- the same SID from two different source nodes
identifies two distinct streams.

A DUT that rejects either stream is spec-legal -- this test passes with
info in that case.

Usage:
python3.10 check_st110_concurrent_multi_node.py

The -h option will display a full list of options.
'''

import sys
import logging
import time

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP
from openlcb.canbus.canframe import CanFrame
from openlcb.canbus.controlframe import ControlFrame

from queue import Empty


# Spoofed node identity -- fabricated, must not collide with real nodes
_SPOOFED_NODE_ID = "06.02.00.00.01.99"
_SPOOFED_ALIAS = 0x299


# =========================================================================
# Helpers for the real checker node (message-level API)
# =========================================================================

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


def _send_buffer(destination, did, buf_size, offset=0):
    '''Send exactly buf_size bytes of stream data.'''
    import olcbchecker
    bytes_sent = 0
    while bytes_sent < buf_size :
        chunk_size = min(buf_size - bytes_sent, 64)
        payload = [((offset + bytes_sent + i) & 0xFF)
                   for i in range(chunk_size)]
        data = [did] + payload
        message = Message(MTI.Stream_Data_Send,
                          NodeID(olcbchecker.ownnodeid()), destination, data)
        olcbchecker.sendMessage(message)
        bytes_sent += chunk_size


def _wait_for_proceed(logger, destination, sid, did, label):
    '''Wait for a Stream Data Proceed. Returns True on success.'''
    import olcbchecker
    while True :
        try :
            received = olcbchecker.getMessage(3.0)
            if destination != received.source :
                continue
            if received.mti == MTI.Stream_Data_Proceed :
                if len(received.data) < 2 :
                    logger.warning("Failure - Proceed too short ({})"
                                   .format(label))
                    return False
                if received.data[0] != sid :
                    logger.warning("Failure - Proceed SID mismatch ({}): "
                                   "expected 0x{:02X} got 0x{:02X}"
                                   .format(label, sid, received.data[0]))
                    return False
                if received.data[1] != did :
                    logger.warning("Failure - Proceed DID mismatch ({}): "
                                   "expected 0x{:02X} got 0x{:02X}"
                                   .format(label, did, received.data[1]))
                    return False
                return True
            if received.mti == MTI.Terminate_Due_To_Error :
                logger.warning("Failure - Terminate Due To Error ({})"
                               .format(label))
                return False
            continue
        except Empty:
            logger.warning("Failure - no Proceed ({})"
                           .format(label))
            return False


def _close_stream(destination, sid, did):
    '''Send Stream Data Complete to close a stream.'''
    import olcbchecker
    message = Message(MTI.Stream_Data_Complete,
                      NodeID(olcbchecker.ownnodeid()), destination,
                      [sid, did])
    olcbchecker.sendMessage(message)
    time.sleep(0.3)


# =========================================================================
# Helpers for the spoofed node (raw CAN frame API)
# =========================================================================

def _claim_spoofed_alias(logger):
    '''Claim a CAN alias for the spoofed node via CID/RID/AMD.'''
    import olcbchecker
    node_id = NodeID(_SPOOFED_NODE_ID)

    # Send CID 7, 6, 5, 4
    for n in [7, 6, 5, 4] :
        frame = CanFrame(n, node_id, _SPOOFED_ALIAS)
        olcbchecker.setup.sendCanFrame(frame)

    # Wait for any RID collision response (200ms per CAN spec)
    time.sleep(0.2)

    # Send RID to reserve the alias
    frame = CanFrame(ControlFrame.RID.value, _SPOOFED_ALIAS, [])
    olcbchecker.setup.sendCanFrame(frame)

    # Send AMD to announce the alias mapping
    frame = CanFrame(ControlFrame.AMD.value, _SPOOFED_ALIAS,
                     node_id.toArray())
    olcbchecker.setup.sendCanFrame(frame)

    time.sleep(0.1)
    return True


def _release_spoofed_alias():
    '''Release the spoofed alias via AMR.'''
    import olcbchecker
    node_id = NodeID(_SPOOFED_NODE_ID)
    frame = CanFrame(ControlFrame.AMR.value, _SPOOFED_ALIAS,
                     node_id.toArray())
    olcbchecker.setup.sendCanFrame(frame)
    time.sleep(0.1)


def _get_dest_alias(destination):
    '''Look up the CAN alias for the destination node.'''
    import olcbchecker
    alias = olcbchecker.setup.canLink.nodeIdToAlias.get(destination)
    return alias


def _spoofed_open_stream(logger, dest_alias, proposed_size, sid):
    '''Open a stream from the spoofed node via raw CAN frames.

    Returns (buf_size, did) or (None, None).
    '''
    import olcbchecker

    # Build Stream Initiate Request as addressed CAN frame
    # Header: Frame Type 1, MTI 0x0CC8 -> field 0xCC8, source = spoofed alias
    header = 0x19_CC8_000 | (_SPOOFED_ALIAS & 0xFFF)

    # Data: [dest_alias_hi, dest_alias_lo, buf_hi, buf_lo, 0x00, 0x00, sid]
    dest_hi = (dest_alias >> 8) & 0x0F
    dest_lo = dest_alias & 0xFF
    data = [dest_hi, dest_lo,
            (proposed_size >> 8) & 0xFF, proposed_size & 0xFF,
            0x00, 0x00, sid]

    frame = CanFrame(header, data)
    olcbchecker.setup.sendCanFrame(frame)

    # Read reply from frame queue (not message queue)
    while True :
        try :
            reply = olcbchecker.getFrame(2.0)

            # Extract MTI field from header bits [23:12]
            mti_field = (reply.header >> 12) & 0xFFF

            # Stream Initiate Reply: MTI 0x0868 -> field 0x868
            if mti_field == 0x868 :
                if len(reply.data) < 2 :
                    continue
                # Check destination alias matches spoofed node
                frame_dest = ((reply.data[0] & 0x0F) << 8) | reply.data[1]
                if frame_dest != _SPOOFED_ALIAS :
                    continue
                # Payload starts at data[2]
                payload = reply.data[2:]
                if len(payload) < 6 :
                    return (None, None)
                buf_size = (payload[0] << 8) | payload[1]
                flags = (payload[2] << 8) | payload[3]
                did = payload[5]
                if (flags == 0x0000 or flags == 0x8000) and buf_size > 0 :
                    return (buf_size, did)
                else :
                    return (None, None)

            # Optional Interaction Rejected: MTI 0x0068 -> field 0x068
            if mti_field == 0x068 :
                if len(reply.data) >= 2 :
                    frame_dest = ((reply.data[0] & 0x0F) << 8) | reply.data[1]
                    if frame_dest == _SPOOFED_ALIAS :
                        return (None, None)

            continue

        except Empty:
            return (None, None)


def _spoofed_send_buffer(dest_alias, did, buf_size, offset=0):
    '''Send stream data from the spoofed node via raw CAN Frame Type 7.'''
    import olcbchecker

    # Frame Type 7: header 0x1F_DDD_SSS
    header = 0x1F_000_000 | ((dest_alias & 0xFFF) << 12) | \
             (_SPOOFED_ALIAS & 0xFFF)

    bytes_sent = 0
    while bytes_sent < buf_size :
        chunk_size = min(buf_size - bytes_sent, 7)
        payload = [((offset + bytes_sent + i) & 0xFF)
                   for i in range(chunk_size)]
        data = [did] + payload
        frame = CanFrame(header, data)
        olcbchecker.setup.sendCanFrame(frame)
        bytes_sent += chunk_size


def _spoofed_wait_for_proceed(logger, sid, did, label):
    '''Wait for Stream Data Proceed addressed to spoofed node.

    Reads from frame queue. Returns True on success.
    '''
    import olcbchecker

    while True :
        try :
            reply = olcbchecker.getFrame(3.0)

            mti_field = (reply.header >> 12) & 0xFFF

            # Stream Data Proceed: MTI 0x0888 -> field 0x888
            if mti_field == 0x888 :
                if len(reply.data) < 4 :
                    continue
                frame_dest = ((reply.data[0] & 0x0F) << 8) | reply.data[1]
                if frame_dest != _SPOOFED_ALIAS :
                    continue
                # Payload: data[2] = SID, data[3] = DID
                if reply.data[2] != sid :
                    logger.warning("Failure - spoofed Proceed SID mismatch "
                                   "({}): expected 0x{:02X} got 0x{:02X}"
                                   .format(label, sid, reply.data[2]))
                    return False
                if reply.data[3] != did :
                    logger.warning("Failure - spoofed Proceed DID mismatch "
                                   "({}): expected 0x{:02X} got 0x{:02X}"
                                   .format(label, did, reply.data[3]))
                    return False
                return True

            # Terminate Due To Error: MTI 0x00A8 -> field 0x0A8
            if mti_field == 0x0A8 :
                if len(reply.data) >= 2 :
                    frame_dest = ((reply.data[0] & 0x0F) << 8) | reply.data[1]
                    if frame_dest == _SPOOFED_ALIAS :
                        logger.warning("Failure - Terminate on spoofed "
                                       "stream ({})".format(label))
                        return False

            continue

        except Empty:
            logger.warning("Failure - no spoofed Proceed ({})"
                           .format(label))
            return False


def _spoofed_close_stream(dest_alias, sid, did):
    '''Close a stream from the spoofed node via raw CAN frame.'''
    import olcbchecker

    # Stream Data Complete: MTI 0x08A8 -> field 0x8A8
    header = 0x19_8A8_000 | (_SPOOFED_ALIAS & 0xFFF)
    dest_hi = (dest_alias >> 8) & 0x0F
    dest_lo = dest_alias & 0xFF
    data = [dest_hi, dest_lo, sid, did]
    frame = CanFrame(header, data)
    olcbchecker.setup.sendCanFrame(frame)
    time.sleep(0.3)


# =========================================================================
# Main check
# =========================================================================

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

    # Get destination alias for raw frame construction
    dest_alias = _get_dest_alias(destination)
    if dest_alias is None :
        logger.warning("Failed in setup, could not resolve destination alias")
        return (2)

    # Open stream A from real checker node
    sid_a = 0x6E
    buf_a, did_a = _open_stream(logger, destination, 256, sid_a)

    if buf_a is None :
        logger.info("Passed - node does not accept streams, cannot "
                     "test multi-node concurrent streams")
        return 0

    # Claim spoofed alias
    _claim_spoofed_alias(logger)

    # Purge frames generated by alias claiming
    olcbchecker.purgeFrames()
    olcbchecker.purgeMessages()

    # Open stream B from spoofed node (same SID is legal -- different source)
    sid_b = 0x01
    buf_b, did_b = _spoofed_open_stream(logger, dest_alias, 256, sid_b)

    if buf_b is None :
        _close_stream(destination, sid_a, did_a)
        _release_spoofed_alias()
        logger.info("Passed - node rejected stream from second source, "
                     "spec-legal")
        return 0

    # One round of interleaved transfer

    # Stream A (real node, message-level)
    _send_buffer(destination, did_a, buf_a, offset=0)
    if not _wait_for_proceed(logger, destination, sid_a, did_a,
                             "real node") :
        _close_stream(destination, sid_a, did_a)
        _spoofed_close_stream(dest_alias, sid_b, did_b)
        _release_spoofed_alias()
        return(3)

    # Stream B (spoofed node, raw CAN frames)
    _spoofed_send_buffer(dest_alias, did_b, buf_b, offset=0)
    if not _spoofed_wait_for_proceed(logger, sid_b, did_b,
                                     "spoofed node") :
        _close_stream(destination, sid_a, did_a)
        _spoofed_close_stream(dest_alias, sid_b, did_b)
        _release_spoofed_alias()
        return(3)

    # Close both streams
    _close_stream(destination, sid_a, did_a)
    _spoofed_close_stream(dest_alias, sid_b, did_b)

    # Release spoofed alias
    _release_spoofed_alias()

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
