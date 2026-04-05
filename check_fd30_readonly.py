#!/usr/bin/env python3.10
'''
This checks that the FDI address space (0xFA) is flagged as read-only
in the Address Space Information reply.

Per TrainControlS section 7.2, the FDI space provides read-only XML
metadata describing the functions supported by the train node.

Usage:
python3.10 check_fd30_readonly.py

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


def check():
    logger = logging.getLogger("FDI")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # check if PIP says Train Control is present
    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.TRAIN_CONTROL_PROTOCOL in pipSet :
            logger.info("Passed - due to Train Control protocol not in PIP")
            return(0)

    # Send Get Address Space Information for space 0xFA (FDI)
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x84, 0xFA])
    olcbchecker.sendMessage(message)

    try :
        reply = getReplyDatagram(destination)
    except Exception as e:
        logger.warning(str(e))
        return (3)

    if len(reply.data) < 8 :
        logger.warning ("Failure - Address Space Info reply too short: {}".format(len(reply.data)))
        return (3)

    # Check that space is present
    if reply.data[1] != 0x87 :
        logger.warning ("Failure - FDI space 0xFA not present (reply byte = 0x{:02X})".format(reply.data[1]))
        return (3)

    if reply.data[2] != 0xFA :
        logger.warning ("Failure - reply space number mismatch: expected 0xFA, got 0x{:02X}".format(reply.data[2]))
        return (3)

    # Check read-only flag in byte 7
    # Bit 0 of flags byte: 1 = read-only
    if not (reply.data[7] & 0x01) :
        logger.warning ("Failure - FDI space 0xFA is not flagged as read-only (flags = 0x{:02X})".format(reply.data[7]))
        return (3)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
