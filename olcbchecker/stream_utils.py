"""
Stream transport utilities for OlcbChecker memory configuration tests.

Provides helpers for both stream source (checker sends data) and stream
destination (checker receives data) roles, plus memory configuration
stream command builders.

Read Stream flow (checker is destination):
    Checker sends Read Stream Command datagram -> node ACKs ->
    node sends Stream Initiate Request -> checker replies accept ->
    node sends Read Stream Reply datagram -> checker ACKs ->
    node streams data -> checker sends Proceed at window boundaries ->
    node sends Stream Data Complete

Write Stream flow (checker is source):
    Checker sends Write Stream Command datagram -> node ACKs ->
    checker sends Stream Initiate Request -> node replies accept ->
    checker streams data -> node sends Proceed at window boundaries ->
    checker sends Stream Data Complete ->
    node sends Write Stream Reply datagram -> checker ACKs
"""

import logging
import time

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI

from queue import Empty

import olcbchecker

# Module-level cache for stream support query results
_stream_support_cache = {}

# Checker's next destination stream ID counter (for when checker is
# the stream destination and must assign a DID)
_next_checker_did = 0x01


def _get_next_checker_did():
    """Allocate a destination stream ID for the checker."""
    global _next_checker_did
    did = _next_checker_did
    _next_checker_did += 1
    if _next_checker_did >= 0xFF:
        _next_checker_did = 0x01
    return did


# ---------------------------------------------------------------------------
# Config Options query
# ---------------------------------------------------------------------------

def query_stream_support(destination):
    """Query Config Options to check if stream read/write is supported.

    Sends a Get Configuration Options command (0x20, 0x80), parses the
    reply, and returns True if the stream bit (0x01 in the write-lengths
    byte) is set. Results are cached per destination.

    Returns True/False, or None if the query failed.
    """
    cache_key = str(destination)
    if cache_key in _stream_support_cache:
        return _stream_support_cache[cache_key]

    olcbchecker.purgeMessages()

    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()),
                      destination, [0x20, 0x80])
    olcbchecker.sendMessage(message)

    try:
        reply = _get_reply_datagram(destination)
    except Exception:
        _stream_support_cache[cache_key] = None
        return None

    if len(reply.data) < 5:
        _stream_support_cache[cache_key] = False
        return False

    # Byte 4 is the write-lengths byte; bit 0 = stream support
    stream_supported = bool(reply.data[4] & 0x01)
    _stream_support_cache[cache_key] = stream_supported
    return stream_supported


# ---------------------------------------------------------------------------
# Datagram helpers (shared by stream command flows)
# ---------------------------------------------------------------------------

def _get_reply_datagram(destination):
    """Wait for Datagram Received OK then the reply datagram.

    Sends Datagram Received OK for the reply. Returns the reply message.
    Raises Exception on timeout or rejection.
    """
    # Wait for Datagram Received OK or Rejected
    while True:
        try:
            received = olcbchecker.getMessage()
            if received.mti not in (MTI.Datagram_Received_OK,
                                    MTI.Datagram_Rejected):
                continue
            if destination != received.source:
                continue
            if NodeID(olcbchecker.ownnodeid()) != received.destination:
                continue
            if received.mti == MTI.Datagram_Received_OK:
                break
            else:
                raise Exception("Datagram rejected")
        except Empty:
            raise Exception("No reply to datagram")

    # Wait for the reply datagram
    while True:
        try:
            received = olcbchecker.getMessage()
            if received.mti != MTI.Datagram:
                continue
            if destination != received.source:
                continue
            if NodeID(olcbchecker.ownnodeid()) != received.destination:
                continue

            ack = Message(MTI.Datagram_Received_OK,
                          NodeID(olcbchecker.ownnodeid()), destination, [0])
            olcbchecker.sendMessage(ack)
            return received
        except Empty:
            raise Exception("No reply datagram received")


def _wait_datagram_ok(destination):
    """Wait for Datagram Received OK. Returns the flags byte.

    Raises Exception on rejection or timeout.
    """
    while True:
        try:
            received = olcbchecker.getMessage(2.0)
            if received.mti not in (MTI.Datagram_Received_OK,
                                    MTI.Datagram_Rejected):
                continue
            if destination != received.source:
                continue
            if NodeID(olcbchecker.ownnodeid()) != received.destination:
                continue
            if received.mti == MTI.Datagram_Rejected:
                raise Exception("Datagram rejected")
            flags = received.data[0] if received.data else 0
            return flags
        except Empty:
            raise Exception("No Datagram Received OK")


# ---------------------------------------------------------------------------
# Memory config stream command builders
# ---------------------------------------------------------------------------

def build_read_stream_command(space, offset, length, dest_stream_id):
    """Build datagram payload for a Read Stream Command.

    Args:
        space: Address space number (0xFF, 0xFE, 0xFD, or explicit)
        offset: 32-bit starting address
        length: 32-bit read count (0 = read to end of space)
        dest_stream_id: Suggested destination stream ID (0xFF if none)

    Returns:
        List of bytes for the datagram payload.

    Format per MemoryConfigurationS section 4.6:
        Byte 0: 0x20 (config mem prefix)
        Byte 1: 0x60-0x63 (command with space encoding)
        Bytes 2-5: Starting address (big-endian)
        Byte 6: Address space (if not encoded in byte 1)
        Byte 7/6: 0xFF (reserved, ignore on receipt)
        Byte 8/7: Destination Stream ID
        Bytes 9-12/8-11: Read count (big-endian, 4 bytes)
    """
    ad = [(offset >> 24) & 0xFF, (offset >> 16) & 0xFF,
          (offset >> 8) & 0xFF, offset & 0xFF]

    if space == 0xFF:
        cmd = 0x63
        payload = [0x20, cmd] + ad
    elif space == 0xFE:
        cmd = 0x62
        payload = [0x20, cmd] + ad
    elif space == 0xFD:
        cmd = 0x61
        payload = [0x20, cmd] + ad
    else:
        cmd = 0x60
        payload = [0x20, cmd] + ad + [space]

    payload.append(0xFF)  # reserved byte
    payload.append(dest_stream_id)
    payload.extend([(length >> 24) & 0xFF, (length >> 16) & 0xFF,
                    (length >> 8) & 0xFF, length & 0xFF])
    return payload


def build_write_stream_command(space, offset, source_stream_id):
    """Build datagram payload for a Write Stream Command.

    Args:
        space: Address space number
        offset: 32-bit starting address
        source_stream_id: Source stream ID assigned by the checker

    Returns:
        List of bytes for the datagram payload.

    Format per MemoryConfigurationS section 4.11:
        Byte 0: 0x20 (config mem prefix)
        Byte 1: 0x20-0x23 (command with space encoding)
        Bytes 2-5: Starting address (big-endian)
        Byte 6: Address space (if not encoded in byte 1)
        Byte 7/6: Source Stream ID
    """
    ad = [(offset >> 24) & 0xFF, (offset >> 16) & 0xFF,
          (offset >> 8) & 0xFF, offset & 0xFF]

    if space == 0xFF:
        cmd = 0x23
        payload = [0x20, cmd] + ad
    elif space == 0xFE:
        cmd = 0x22
        payload = [0x20, cmd] + ad
    elif space == 0xFD:
        cmd = 0x21
        payload = [0x20, cmd] + ad
    else:
        cmd = 0x20
        payload = [0x20, cmd] + ad + [space]

    payload.append(source_stream_id)
    return payload


# ---------------------------------------------------------------------------
# Stream destination functions (checker receives data from node)
# ---------------------------------------------------------------------------

def accept_incoming_stream(logger, destination, timeout=3.0):
    """Wait for a Stream Initiate Request from the node and accept it.

    The node is the stream source; the checker is the stream destination.
    This is used after sending a Read Stream Command datagram.

    Returns:
        (sid, did, buf_size) on success -- sid is the node's source stream
        ID, did is the checker's assigned destination stream ID, buf_size
        is the negotiated buffer size.

    Raises Exception on timeout or if the node sends an error.
    """
    while True:
        try:
            received = olcbchecker.getMessage(timeout)
            if destination != received.source:
                continue
            if NodeID(olcbchecker.ownnodeid()) != received.destination:
                continue

            if received.mti == MTI.Stream_Initiate_Request:
                if len(received.data) < 5:
                    raise Exception("Stream Initiate Request too short")

                proposed_size = (received.data[0] << 8) | received.data[1]
                sid = received.data[4]

                # Accept with proposed size (or cap to our buffer)
                buf_size = min(proposed_size, 256)
                did = _get_next_checker_did()

                reply_data = [
                    (buf_size >> 8) & 0xFF, buf_size & 0xFF,
                    0x80, 0x00,  # flags: accept (0x8000)
                    sid,
                    did
                ]
                reply = Message(MTI.Stream_Initiate_Reply,
                                NodeID(olcbchecker.ownnodeid()),
                                destination, reply_data)
                olcbchecker.sendMessage(reply)
                return (sid, did, buf_size)

            if received.mti == MTI.Terminate_Due_To_Error:
                raise Exception("Node sent Terminate Due To Error "
                                "instead of Stream Initiate Request")

            continue

        except Empty:
            raise Exception("No Stream Initiate Request received")


def receive_stream_data(logger, destination, sid, did, buf_size,
                        timeout=3.0):
    """Receive stream data from the node, sending Proceed as needed.

    Accumulates all payload bytes until Stream Data Complete is received.

    Args:
        sid: Node's source stream ID
        did: Checker's destination stream ID
        buf_size: Negotiated buffer size (window for Proceed)
        timeout: Seconds to wait for each message

    Returns:
        List of received payload bytes.

    Raises Exception on timeout or protocol error.
    """
    collected = []
    bytes_since_proceed = 0

    while True:
        try:
            received = olcbchecker.getMessage(timeout)
            if destination != received.source:
                continue

            if received.mti == MTI.Stream_Data_Send:
                if len(received.data) < 1:
                    continue
                # Byte 0 is DID, rest is payload
                payload = received.data[1:]
                collected.extend(payload)
                bytes_since_proceed += len(payload)

                # Send Proceed when we have received buf_size bytes
                if bytes_since_proceed >= buf_size:
                    proceed = Message(
                        MTI.Stream_Data_Proceed,
                        NodeID(olcbchecker.ownnodeid()),
                        destination, [sid, did])
                    olcbchecker.sendMessage(proceed)
                    bytes_since_proceed = 0

                continue

            if received.mti == MTI.Stream_Data_Complete:
                return collected

            if received.mti == MTI.Terminate_Due_To_Error:
                raise Exception("Node sent Terminate Due To Error "
                                "during stream data transfer")

            continue

        except Empty:
            raise Exception(
                "Timeout waiting for stream data ({} bytes received "
                "so far)".format(len(collected)))


# ---------------------------------------------------------------------------
# Stream source functions (checker sends data to node)
# ---------------------------------------------------------------------------

def open_outbound_stream(logger, destination, proposed_size, sid):
    """Initiate a stream from the checker to the node.

    The checker is the stream source; the node is the destination.
    This is used after sending a Write Stream Command datagram.

    Args:
        proposed_size: Max buffer size to propose
        sid: Source stream ID assigned by the checker

    Returns:
        (buf_size, did) on acceptance -- buf_size is negotiated size,
        did is the node's assigned destination stream ID.
        (None, None) on rejection.
    """
    data = [(proposed_size >> 8) & 0xFF, proposed_size & 0xFF,
            0x00, 0x00, sid]
    message = Message(MTI.Stream_Initiate_Request,
                      NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True:
        try:
            received = olcbchecker.getMessage(2.0)
            if destination != received.source:
                continue

            if received.mti == MTI.Optional_Interaction_Rejected:
                return (None, None)

            if received.mti == MTI.Stream_Initiate_Reply:
                if NodeID(olcbchecker.ownnodeid()) != received.destination:
                    continue
                if len(received.data) < 6:
                    return (None, None)

                buf_size = (received.data[0] << 8) | received.data[1]
                flags = (received.data[2] << 8) | received.data[3]
                did = received.data[5]

                if (flags == 0x0000 or flags == 0x8000) and buf_size > 0:
                    return (buf_size, did)
                else:
                    return (None, None)

            continue

        except Empty:
            return (None, None)


def send_stream_data(logger, destination, did, buf_size, data):
    """Send data over an open stream, respecting flow control.

    Sends data in chunks, waiting for Proceed after each buf_size
    bytes sent.

    Args:
        did: Node's destination stream ID
        buf_size: Negotiated buffer size
        data: List of bytes to send

    Raises Exception on timeout waiting for Proceed.
    """
    bytes_sent = 0
    total = len(data)

    while bytes_sent < total:
        # Send up to buf_size bytes
        window_sent = 0
        while window_sent < buf_size and bytes_sent < total:
            chunk_size = min(buf_size - window_sent, total - bytes_sent, 64)
            payload = data[bytes_sent:bytes_sent + chunk_size]
            msg_data = [did] + payload
            message = Message(MTI.Stream_Data_Send,
                              NodeID(olcbchecker.ownnodeid()),
                              destination, msg_data)
            olcbchecker.sendMessage(message)
            bytes_sent += chunk_size
            window_sent += chunk_size

        # If we have more data, wait for Proceed
        if bytes_sent < total:
            if not _wait_for_proceed(destination, buf_size):
                raise Exception(
                    "No Stream Data Proceed after sending {} bytes"
                    .format(bytes_sent))


def _wait_for_proceed(destination, buf_size, timeout=3.0):
    """Wait for a Stream Data Proceed message. Returns True on success."""
    while True:
        try:
            received = olcbchecker.getMessage(timeout)
            if destination != received.source:
                continue
            if received.mti == MTI.Stream_Data_Proceed:
                return True
            if received.mti == MTI.Terminate_Due_To_Error:
                return False
            continue
        except Empty:
            return False


def close_stream(logger, destination, sid, did):
    """Send Stream Data Complete to close an open stream.

    Args:
        sid: Source stream ID
        did: Destination stream ID
    """
    complete = Message(MTI.Stream_Data_Complete,
                       NodeID(olcbchecker.ownnodeid()),
                       destination, [sid, did])
    olcbchecker.sendMessage(complete)
    time.sleep(0.3)


# ---------------------------------------------------------------------------
# Combined memory config stream operations
# ---------------------------------------------------------------------------

def read_via_stream(logger, destination, space, offset, length):
    """Perform a complete Read Stream operation.

    Sends Read Stream Command datagram, accepts the incoming stream from
    the node (node is source, checker is destination), receives the Read
    Stream Reply datagram, collects all streamed data, and returns it.

    Args:
        space: Address space (0xFF, 0xFE, 0xFD, etc.)
        offset: Starting address
        length: Number of bytes to read (0 = read to end)

    Returns:
        List of received data bytes.

    Raises Exception on any protocol failure.
    """
    olcbchecker.purgeMessages()

    dest_stream_id = _get_next_checker_did()

    # Step 1: Send Read Stream Command datagram
    payload = build_read_stream_command(space, offset, length,
                                        dest_stream_id)
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()),
                      destination, payload)
    olcbchecker.sendMessage(message)

    # Step 2: Wait for Datagram Received OK
    flags = _wait_datagram_ok(destination)

    # Step 3: Accept incoming stream (node is source)
    sid, did, buf_size = accept_incoming_stream(logger, destination)

    # Step 4: Wait for Read Stream Reply datagram from node
    reply = _wait_for_read_stream_reply(destination)
    if reply is None:
        raise Exception("No Read Stream Reply datagram received")

    # Check for failure in the reply
    reply_cmd = reply.data[1]
    if (reply_cmd & 0x08) != 0:
        # Fail bit set
        error_msg = "Read Stream Reply indicates failure"
        if len(reply.data) >= 9:
            error_code = (reply.data[7] << 8) | reply.data[8]
            error_msg += " (error 0x{:04X})".format(error_code)
        raise Exception(error_msg)

    # Step 5: Receive stream data
    data = receive_stream_data(logger, destination, sid, did, buf_size)

    return data


def _wait_for_read_stream_reply(destination, timeout=3.0):
    """Wait for a Read Stream Reply datagram from the node.

    The reply is a datagram with command byte 0x70-0x7B.
    Sends Datagram Received OK in response.

    Returns the reply message, or None on timeout.
    """
    while True:
        try:
            received = olcbchecker.getMessage(timeout)
            if received.mti != MTI.Datagram:
                continue
            if destination != received.source:
                continue
            if NodeID(olcbchecker.ownnodeid()) != received.destination:
                continue

            # Verify it is a Read Stream Reply (0x70-0x7B)
            if len(received.data) >= 2:
                cmd = received.data[1]
                if (cmd & 0xF0) == 0x70:
                    ack = Message(MTI.Datagram_Received_OK,
                                  NodeID(olcbchecker.ownnodeid()),
                                  destination, [0])
                    olcbchecker.sendMessage(ack)
                    return received

            continue
        except Empty:
            return None


def write_via_stream(logger, destination, space, offset, data):
    """Perform a complete Write Stream operation.

    Sends Write Stream Command datagram, opens an outbound stream to the
    node (checker is source, node is destination), sends data, closes the
    stream, and waits for the Write Stream Reply datagram.

    Args:
        space: Address space
        offset: Starting address
        data: List of bytes to write

    Raises Exception on any protocol failure.
    """
    olcbchecker.purgeMessages()

    sid = 0xA0  # checker's source stream ID for writes

    # Step 1: Send Write Stream Command datagram
    payload = build_write_stream_command(space, offset, sid)
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()),
                      destination, payload)
    olcbchecker.sendMessage(message)

    # Step 2: Wait for Datagram Received OK
    flags = _wait_datagram_ok(destination)

    # Step 3: Open outbound stream (checker is source)
    buf_size, did = open_outbound_stream(logger, destination, 256, sid)
    if buf_size is None:
        raise Exception("Node rejected stream for Write Stream operation")

    # Step 4: Send data
    send_stream_data(logger, destination, did, buf_size, data)

    # Step 5: Close stream
    close_stream(logger, destination, sid, did)

    # Step 6: Wait for Write Stream Reply datagram
    reply = _wait_for_write_stream_reply(destination)
    if reply is None:
        raise Exception("No Write Stream Reply datagram received")

    # Check for failure
    reply_cmd = reply.data[1]
    if (reply_cmd & 0x08) != 0:
        error_msg = "Write Stream Reply indicates failure"
        if len(reply.data) >= 9:
            error_code = (reply.data[7] << 8) | reply.data[8]
            error_msg += " (error 0x{:04X})".format(error_code)
        raise Exception(error_msg)


def _wait_for_write_stream_reply(destination, timeout=5.0):
    """Wait for a Write Stream Reply datagram from the node.

    The reply is a datagram with command byte 0x30-0x3B.
    Sends Datagram Received OK in response.

    Returns the reply message, or None on timeout.
    """
    while True:
        try:
            received = olcbchecker.getMessage(timeout)
            if received.mti != MTI.Datagram:
                continue
            if destination != received.source:
                continue
            if NodeID(olcbchecker.ownnodeid()) != received.destination:
                continue

            if len(received.data) >= 2:
                cmd = received.data[1]
                if (cmd & 0xF0) == 0x30:
                    ack = Message(MTI.Datagram_Received_OK,
                                  NodeID(olcbchecker.ownnodeid()),
                                  destination, [0])
                    olcbchecker.sendMessage(ack)
                    return received

            continue
        except Empty:
            return None
