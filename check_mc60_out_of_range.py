#!/usr/bin/env python3.10
'''
This checks that a memory configuration read to an address beyond the
highest address in the space returns a proper error.

Per MemoryConfigurationS section 4.5, if no bytes can be read the Read
Reply shall have the Fail bit set with an error code.
Section 4.3 defines error code 0x1082 (permanent: invalid argument,
out of bounds).

Usage:
python3.10 check_mc60_out_of_range.py

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
            # is this a datagram reply, OK or not?
            if not (received.mti == MTI.Datagram_Received_OK or received.mti == MTI.Datagram_Rejected) :
                continue # wait for next

            if destination != received.source : # check source in message header
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                continue

            if received.mti == MTI.Datagram_Received_OK :
                # OK, proceed
                break
            else : # must be datagram rejected
                # can't proceed
                raise Exception("Failure - Original Datagram rejected")

        except Empty:
            raise Exception("Failure - no reply to request")

    # now wait for the reply datagram
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a datagram reply, OK or not?
            if not (received.mti == MTI.Datagram) :
                continue # wait for next

            if destination != received.source : # check source in message header
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                continue

            # here we've received the reply datagram
            # send the reply
            message = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination, [0])
            olcbchecker.sendMessage(message)

            return received

        except Empty:
            raise Exception("Failure - no reply datagram received")


def getReadReplyOrRejection(destination) :
    '''
    Invoked after a read datagram has been sent, this waits for either:
    (a) Datagram Received OK (with Reply Pending) followed by a Read Reply
        datagram — the standard-preferred flow, OR
    (b) Datagram Rejected — some implementations reject out-of-range reads
        at the datagram level rather than accepting and sending a Read Reply
        with the Fail bit.

    Returns a tuple (reply_datagram, rejected_error_code).
    - On path (a): reply_datagram is the Read Reply, rejected_error_code is None
    - On path (b): reply_datagram is None, rejected_error_code is the error code
    Raises Exception only for unexpected protocol failures.
    '''
    # first, wait for Datagram Received OK or Datagram Rejected
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
                # Path (b): node rejected at datagram level
                error_code = 0
                if received.data and len(received.data) >= 2 :
                    error_code = (received.data[0] << 8) | received.data[1]
                return (None, error_code)

            if received.mti == MTI.Datagram_Received_OK :
                break

        except Empty:
            raise Exception("Failure - no reply to read request")

    # Path (a): got Datagram Received OK, now wait for the reply datagram
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

            return (received, None)

        except Empty:
            raise Exception("Failure - no reply datagram received")


def check():
    # set up the infrastructure

    logger = logging.getLogger("MEMORY")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # check if PIP says this is present
    if olcbchecker.isCheckPip() :
        pipSet = olcbchecker.gatherPIP(destination)
        if pipSet is None:
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.MEMORY_CONFIGURATION_PROTOCOL in pipSet :
            logger.info("Passed - due to Memory Configuration protocol not in PIP")
            return(0)

    # Step 1: Get Address Space Information for space 0xFD to find highest address
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x84, 0xFD])
    olcbchecker.sendMessage(message)

    try :
        reply = getReplyDatagram(destination)
    except Exception as e:
        logger.warning(str(e))
        return (3)

    if len(reply.data) < 8 :
        logger.warning ("Failure - Address Space Info reply too short: {}".format(len(reply.data)))
        return (3)

    if reply.data[1] != 0x87 :
        logger.warning ("Failure - Space 0xFD not present (reply byte = 0x{:02X})".format(reply.data[1]))
        return (3)

    # extract highest address from bytes 3-6 (big-endian)
    highest_address = (reply.data[3] << 24) | (reply.data[4] << 16) | (reply.data[5] << 8) | reply.data[6]

    # Step 2: Read from well beyond highest address
    out_of_range = highest_address + 0x100
    ad1 = (out_of_range >> 24) & 0xFF
    ad2 = (out_of_range >> 16) & 0xFF
    ad3 = (out_of_range >> 8) & 0xFF
    ad4 = out_of_range & 0xFF

    # long-form read: [0x20, 0x40, addr(4), space, count]
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination,
                      [0x20, 0x40, ad1, ad2, ad3, ad4, 0xFD, 64])
    olcbchecker.sendMessage(message)

    try :
        (reply, rejected_error) = getReadReplyOrRejection(destination)
    except Exception as e:
        logger.warning(str(e))
        return (3)

    if reply is None :
        # Path (b): Datagram Rejected at protocol level
        # This is an acceptable way to indicate out-of-range, though the
        # standard prefers a Read Reply with Fail bit.
        logger.info("Note - node rejected datagram (error 0x{:04X}) instead of "
                     "Read Reply with Fail bit".format(rejected_error))
    else :
        # Path (a): Got a Read Reply datagram — verify the Fail bit is set
        if len(reply.data) < 2 :
            logger.warning ("Failure - Read Reply too short: {}".format(len(reply.data)))
            return (3)

        reply_cmd = reply.data[1]
        if (reply_cmd & 0x08) == 0 :
            logger.warning ("Failure - Read Reply from out-of-range address did not have Fail bit set"
                            " (command byte = 0x{:02X})".format(reply_cmd))
            return (3)

        # Optionally verify error code contains 0x1082
        if len(reply.data) >= 9 :
            error_high = reply.data[7]
            error_low = reply.data[8]
            error_code = (error_high << 8) | error_low
            if error_code != 0x1082 :
                logger.info("Note - error code was 0x{:04X}, expected 0x1082".format(error_code))

    # Stability soak: wait 30 seconds watching for unexpected reinitialization
    # while periodically verifying the node is still responsive
    import time
    timeout = 30
    ping_interval = 10  # seconds between liveness checks
    last_ping = 0  # force an immediate first ping
    logger.info("Stability soak: monitoring node for {} seconds (pinging every {}s to verify responsiveness)".format(timeout, ping_interval))
    start = time.time()

    while time.time() - start < timeout :
        try :
            received = olcbchecker.getMessage(1) # 1-second poll

            if destination != received.source :
                continue  # ignore messages from other nodes

            if received.mti == MTI.Initialization_Complete or received.mti == MTI.Initialization_Complete_Simple :
                logger.warning("Failure - node rebooted after out-of-range read")
                return (3)

        except Empty:
            pass  # no messages -- expected during quiet periods

        # Periodic liveness ping via Verify Node ID Addressed
        if time.time() - last_ping >= ping_interval :
            olcbchecker.purgeMessages()
            message = Message(MTI.Verify_NodeID_Number_Addressed, NodeID(olcbchecker.ownnodeid()), destination)
            olcbchecker.sendMessage(message)

            alive = False
            while True :
                try :
                    received = olcbchecker.getMessage()
                    if received.mti != MTI.Verified_NodeID and received.mti != MTI.Verified_NodeID_Simple :
                        continue
                    if destination != received.source :
                        continue
                    alive = True
                    break
                except Empty:
                    break

            if not alive :
                logger.warning ("Failure - node stopped responding after out-of-range read")
                return(3)

            last_ping = time.time()

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
