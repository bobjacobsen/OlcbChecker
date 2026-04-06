#!/usr/bin/env python3.10
'''
This checks the Memory Configuration Write Under Mask functionality.

Per MemoryConfigurationS section 4.10, Write Under Mask uses alternating
(mask, data) byte pairs.  Bits where mask=1 are written from the data byte;
bits where mask=0 are preserved from the current value.

This check is only run if Config Options indicates write-under-mask support.

Usage:
python3.10 check_mc70_write_under_mask.py

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

    # Step 1: Get Config Options to check write-under-mask support
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x80])
    olcbchecker.sendMessage(message)

    try :
        reply = getReplyDatagram(destination)
    except Exception as e:
        logger.warning(str(e))
        return (3)

    if len(reply.data) < 5 :
        logger.warning ("Failure - Config Options reply too short")
        return (3)

    # Check write-under-mask support bit (bit 0x8000 of available commands)
    # Available commands are in bytes 2-3 of the reply
    if not (reply.data[2] & 0x80) :
        logger.info("Passed - write under mask not supported by this node")
        return 0

    # Step 2: Read current value at space 0xFD address 0
    try :
        original = readByte(destination, 0, 0xFD)
    except Exception as e:
        logger.warning(str(e))
        return (3)

    try :
        # Step 3: Write Under Mask — set low nibble to 0x0F
        # Short form write-under-mask to 0xFD: command byte 0x09
        # Format: [0x20, 0x09, addr(4), mask, data, ...]
        sendWriteDatagram(destination,
            [0x20, 0x09, 0, 0, 0, 0, 0x0F, 0x0F])

        # Step 4: Read back and verify low nibble
        value = readByte(destination, 0, 0xFD)
        expected = (original & 0xF0) | 0x0F
        if value != expected :
            logger.warning ("Failure - after low nibble mask write: expected 0x{:02X}, got 0x{:02X}".format(expected, value))
            return (3)

        # Step 5: Write Under Mask — set high nibble to 0xA0
        sendWriteDatagram(destination,
            [0x20, 0x09, 0, 0, 0, 0, 0xF0, 0xA0])

        # Step 6: Read back and verify both nibbles
        value = readByte(destination, 0, 0xFD)
        expected = 0xAF  # high nibble 0xA0 from step 5, low nibble 0x0F from step 3
        if value != expected :
            logger.warning ("Failure - after high nibble mask write: expected 0x{:02X}, got 0x{:02X}".format(expected, value))
            return (3)

    except Exception as e:
        logger.warning(str(e))
        return (3)

    finally :
        # Step 7: Restore original value
        try :
            sendWriteDatagram(destination, [0x20, 0x01, 0, 0, 0, 0, original])
        except Exception :
            pass  # best effort restore

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
