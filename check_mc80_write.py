#!/usr/bin/env python3.10
'''
This checks basic Config Memory (0xFD) write functionality.

Performs a read-write-verify-restore cycle on a single byte in the 0xFD
address space, respecting the published Address Space Information for
boundaries and writability.

This check is gated behind the --force-writes (-w) flag because it
physically writes to configuration memory.

Usage:
python3.10 check_mc80_write.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP

from queue import Empty

import olcbchecker.setup


def getReplyDatagram(destination) :
    '''
    Invoked after a datagram has been sent, this waits
    for first the datagram reply message, then a
    datagram message that contains a reply.  It
    replies with a datagram OK, then returns the reply datagram message.
    Raises Exception if something went wrong.
    '''
    # first, wait for the reply
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            if not (received.mti == MTI.Datagram_Received_OK or received.mti == MTI.Datagram_Rejected) :
                continue

            if destination != received.source :
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination :
                continue

            if received.mti == MTI.Datagram_Received_OK :
                break
            else :
                raise Exception("Failure - Original Datagram rejected")

        except Empty:
            raise Exception("Failure - no reply to request")

    # now wait for the reply datagram
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            if not (received.mti == MTI.Datagram) :
                continue

            if destination != received.source :
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination :
                continue

            message = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination, [0])
            olcbchecker.sendMessage(message)

            return received

        except Empty:
            raise Exception("Failure - no reply datagram received")


def sendWriteDatagram(destination, data) :
    '''Send a write datagram and wait for acknowledgment.
    Handles optional Reply Pending + reply datagram.
    Raises Exception on failure.'''
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, data)
    olcbchecker.sendMessage(message)

    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            if not (received.mti == MTI.Datagram_Received_OK or received.mti == MTI.Datagram_Rejected) :
                continue

            if destination != received.source :
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination :
                continue

            if received.mti == MTI.Datagram_Rejected :
                raise Exception("Failure - Write Datagram rejected")

            # Check Reply Pending bit
            if received.data and (received.data[0] & 0x80) :
                # wait for reply datagram
                while True :
                    try :
                        received = olcbchecker.getMessage()
                        if received.mti != MTI.Datagram :
                            continue
                        if destination != received.source :
                            continue
                        # acknowledge the reply
                        ack = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination, [0])
                        olcbchecker.sendMessage(ack)
                        break
                    except Empty:
                        raise Exception("Failure - no write reply datagram after Reply Pending")
            return

        except Empty:
            raise Exception("Failure - no reply to write request")


def readByte(destination, address, space) :
    '''Read a single byte from memory.  Returns the byte value.'''
    ad1 = (address >> 24) & 0xFF
    ad2 = (address >> 16) & 0xFF
    ad3 = (address >> 8) & 0xFF
    ad4 = address & 0xFF

    request = [0x20, 0x40, ad1, ad2, ad3, ad4, space, 1]
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, request)
    olcbchecker.sendMessage(message)
    reply = getReplyDatagram(destination)
    if len(reply.data) < 8 :
        raise Exception("Failure - read reply too short")
    return reply.data[7]


def check():
    logger = logging.getLogger("MEMORY")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # check if PIP says Memory Configuration is present
    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.MEMORY_CONFIGURATION_PROTOCOL in pipSet :
            logger.info("Passed - due to Memory Configuration protocol not in PIP")
            return(0)

    # Guard: skip unless --force-writes (-w) is enabled
    if not olcbchecker.setup.configure.force_writes :
        logger.info("Passed - skipped (use --force-writes to enable write checks)")
        return 0

    # Step 1: Query Address Space Information for 0xFD
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x84, 0xFD])
    olcbchecker.sendMessage(message)

    try :
        reply = getReplyDatagram(destination)
    except Exception as e:
        logger.warning(str(e))
        return (3)

    if len(reply.data) < 8 :
        logger.warning ("Failure - Address Space Info reply too short for 0xFD")
        return (3)

    # Verify space is present (byte 1 == 0x87)
    if reply.data[1] != 0x87 :
        logger.warning ("Failure - 0xFD space not present (byte 1 = 0x{:02X}, expected 0x87)".format(reply.data[1]))
        return (3)

    # Verify space number matches
    if reply.data[2] != 0xFD :
        logger.warning ("Failure - space number mismatch (got 0x{:02X}, expected 0xFD)".format(reply.data[2]))
        return (3)

    # Extract highest address from bytes 3-6
    highest_address = (reply.data[3] << 24) | (reply.data[4] << 16) | (reply.data[5] << 8) | reply.data[6]

    # Check flags byte 7
    flags = reply.data[7]

    # Bit 0 = read-only; if set, we cannot write
    if flags & 0x01 :
        logger.info("Passed - 0xFD space is read-only, cannot check writes")
        return 0

    # Bit 1 = low address valid
    low_address = 0
    if flags & 0x02 :
        if len(reply.data) >= 12 :
            low_address = (reply.data[8] << 24) | (reply.data[9] << 16) | (reply.data[10] << 8) | reply.data[11]
        else :
            logger.warning ("Failure - low address flag set but not enough bytes in reply")
            return (3)

    # Validate we have a writable range
    if low_address > highest_address :
        logger.warning ("Failure - low address (0x{:X}) > highest address (0x{:X})".format(low_address, highest_address))
        return (3)

    # Step 2: Pick check address — use low_address
    check_address = low_address

    # Step 3: Read original value
    try :
        original = readByte(destination, check_address, 0xFD)
    except Exception as e:
        logger.warning(str(e))
        return (3)

    # Compute new pattern: bitwise complement of original
    check_value = (~original) & 0xFF

    try :
        # Step 4: Write check pattern
        ad1 = (check_address >> 24) & 0xFF
        ad2 = (check_address >> 16) & 0xFF
        ad3 = (check_address >> 8) & 0xFF
        ad4 = check_address & 0xFF

        sendWriteDatagram(destination,
            [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFD, check_value])

        # Step 5: Read back and verify write
        value = readByte(destination, check_address, 0xFD)
        if value != check_value :
            logger.warning ("Failure - write verify: wrote 0x{:02X}, read back 0x{:02X}".format(check_value, value))
            return (3)

        # Step 6: Restore original value
        sendWriteDatagram(destination,
            [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFD, original])

        # Step 7: Read back and verify restore
        value = readByte(destination, check_address, 0xFD)
        if value != original :
            logger.warning ("Failure - restore verify: wrote 0x{:02X}, read back 0x{:02X}".format(original, value))
            return (3)

    except Exception as e:
        # Best-effort restore on failure
        try :
            ad1 = (check_address >> 24) & 0xFF
            ad2 = (check_address >> 16) & 0xFF
            ad3 = (check_address >> 8) & 0xFF
            ad4 = check_address & 0xFF
            sendWriteDatagram(destination, [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFD, original])
        except Exception :
            pass
        logger.warning(str(e))
        return (3)

    logger.info("Passed (datagram)")

    # --- Stream write pass ---
    from olcbchecker.stream_utils import query_stream_support, write_via_stream
    from openlcb.pip import PIP as PIP_enum

    stream_ok = query_stream_support(destination)
    if not stream_ok :
        logger.info("Skipped (stream) - Config Options stream bit not set")
        return 0

    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is not None and PIP_enum.STREAM_PROTOCOL not in pipSet :
            logger.info("Skipped (stream) - Stream protocol not in PIP")
            return 0

    try :
        # Read original value (for restore)
        stream_original = readByte(destination, check_address, 0xFD)

        # Compute check pattern
        stream_check_value = (~stream_original) & 0xFF

        # Write via stream
        write_via_stream(logger, destination, 0xFD, check_address,
                         [stream_check_value])

        # Read back via datagram to verify
        value = readByte(destination, check_address, 0xFD)
        if value != stream_check_value :
            logger.warning("Failure (stream) - write verify: wrote "
                           "0x{:02X}, read back 0x{:02X}"
                           .format(stream_check_value, value))
            # Restore before failing
            sendWriteDatagram(destination,
                [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFD, stream_original])
            return 3

        # Restore original value via datagram
        sendWriteDatagram(destination,
            [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFD, stream_original])

        # Verify restore
        value = readByte(destination, check_address, 0xFD)
        if value != stream_original :
            logger.warning("Failure (stream) - restore verify: wrote "
                           "0x{:02X}, read back 0x{:02X}"
                           .format(stream_original, value))
            return 3

        logger.info("Passed (stream)")

    except Exception as e :
        # Best-effort restore
        try :
            sendWriteDatagram(destination,
                [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFD, original])
        except Exception :
            pass
        logger.warning("Failure (stream) - {}".format(str(e)))
        return 3

    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
