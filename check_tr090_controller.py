#!/usr/bin/env python3.10
'''
This checks the Train Control Controller Assign/Release/Query lifecycle.

Per TrainControlS section 6.1:
  - A Throttle Node assigns itself as Controller via Assign Controller (0x20, 0x01).
  - Query Controller (0x20, 0x03) returns flags and active controller Node ID.
  - Release Controller (0x20, 0x02) clears the assignment.
  - The Train Node shall reply to Assign Controller within 3 seconds.

Usage:
python3.10 check_tr090_controller.py

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

# Controller Configuration protocol byte definitions
CTRL_CMD       = 0x20
CTRL_ASSIGN    = 0x01
CTRL_RELEASE   = 0x02
CTRL_QUERY     = 0x03


def getTrainControlReply(destination) :
    '''Wait for a Traction Control Reply from the destination node.
    Raises Exception if no reply received.'''
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            if not (received.mti == MTI.Traction_Control_Reply) :
                continue

            if destination != received.source :
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination :
                continue

            return received

        except Empty:
            raise Exception("Failure - no Traction Control Reply received")


def check():
    logger = logging.getLogger("TRAIN_CONTROL")

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

    # Build our 6-byte node ID for controller commands
    own_id_bytes = NodeID(olcbchecker.ownnodeid()).toArray()

    try :
        # =====================================================
        # Step 1: Query with no controller assigned
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_QUERY])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 1 query reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[0] != CTRL_CMD or reply.data[1] != CTRL_QUERY:
            logger.warning ("Failure: step 1 reply header incorrect: [0x{:02X}, 0x{:02X}]"
                           .format(reply.data[0], reply.data[1]))
            return (3)

        # Flags should be 0x00 (no controller assigned)
        if reply.data[2] != 0x00:
            logger.warning ("Failure: step 1 query flags not 0x00 (no controller), got 0x{:02X}"
                           .format(reply.data[2]))
            return (3)


        # =====================================================
        # Step 2: Assign our node as controller
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_ASSIGN, 0x00] + own_id_bytes)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 2 assign reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[0] != CTRL_CMD or reply.data[1] != CTRL_ASSIGN:
            logger.warning ("Failure: step 2 reply header incorrect: [0x{:02X}, 0x{:02X}]"
                           .format(reply.data[0], reply.data[1]))
            return (3)

        # Result byte: 0x00 = accepted
        if reply.data[2] != 0x00:
            logger.warning ("Failure: step 2 assign rejected, result=0x{:02X}".format(reply.data[2]))
            return (3)


        # =====================================================
        # Step 3: Query with controller assigned — should show our node ID
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_QUERY])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 9:
            logger.warning ("Failure: step 3 query reply too short: {} (expected 9: cmd+sub+flags+6-byte NodeID)"
                           .format(len(reply.data)))
            return (3)

        if reply.data[0] != CTRL_CMD or reply.data[1] != CTRL_QUERY:
            logger.warning ("Failure: step 3 reply header incorrect: [0x{:02X}, 0x{:02X}]"
                           .format(reply.data[0], reply.data[1]))
            return (3)

        # Flags should have bit 0 set (controller assigned)
        if (reply.data[2] & 0x01) == 0:
            logger.warning ("Failure: step 3 query flags bit 0 not set, got 0x{:02X}"
                           .format(reply.data[2]))
            return (3)

        # Verify the returned controller node ID matches ours
        returned_id = reply.data[3:9]
        if returned_id != own_id_bytes:
            logger.warning ("Failure: step 3 controller node ID mismatch: got {} expected {}"
                           .format([hex(b) for b in returned_id], [hex(b) for b in own_id_bytes]))
            return (3)


        # =====================================================
        # Step 4: Release controller
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_RELEASE, 0x00] + own_id_bytes)
        olcbchecker.sendMessage(message)

        # Release may or may not have a reply; drain any reply
        try :
            reply = getTrainControlReply(destination)
        except Exception :
            pass  # no reply is acceptable for release


        # =====================================================
        # Step 5: Query after release — should show no controller
        # =====================================================
        olcbchecker.purgeMessages()

        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_QUERY])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 5 query reply too short: {}".format(len(reply.data)))
            return (3)

        # Flags should be 0x00 (no controller assigned)
        if reply.data[2] != 0x00:
            logger.warning ("Failure: step 5 query flags not 0x00 after release, got 0x{:02X}"
                           .format(reply.data[2]))
            return (3)

    finally :
        # Cleanup: always release
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_RELEASE, 0x00] + own_id_bytes)
        olcbchecker.sendMessage(message)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
