#!/usr/bin/env python3.10
'''
This checks the Train Control Reserve/Release management commands.

Per TrainControlS section 4.3, Management commands include:
  - Reserve (0x40, 0x01): First reserve accepted; subsequent from same
    source also accepted.
  - Release (0x40, 0x02): Releases the reservation.

Usage:
python3.10 check_tr100_reserve.py

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

# Management protocol byte definitions
MGMT_CMD       = 0x40
MGMT_RESERVE   = 0x01
MGMT_RELEASE   = 0x02

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

    try :
        # =====================================================
        # Step 1: Reserve the train
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [MGMT_CMD, MGMT_RESERVE])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 1 reserve reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[0] != MGMT_CMD or reply.data[1] != MGMT_RESERVE:
            logger.warning ("Failure: step 1 reply header incorrect: [0x{:02X}, 0x{:02X}]"
                           .format(reply.data[0], reply.data[1]))
            return (3)

        # Result byte: 0x00 = accepted
        if reply.data[2] != 0x00:
            logger.warning ("Failure: step 1 reserve rejected, result=0x{:02X}".format(reply.data[2]))
            return (3)


        # =====================================================
        # Step 2: Reserve again from same source — should still be accepted
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [MGMT_CMD, MGMT_RESERVE])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 2 reserve reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[2] != 0x00:
            logger.warning ("Failure: step 2 second reserve from same source rejected, result=0x{:02X}"
                           .format(reply.data[2]))
            return (3)


        # =====================================================
        # Step 3: Release the train
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [MGMT_CMD, MGMT_RELEASE])
        olcbchecker.sendMessage(message)

        # Release may or may not have a reply; drain any reply
        try :
            reply = getTrainControlReply(destination)
        except Exception :
            pass  # no reply is acceptable for release


        # =====================================================
        # Step 4: Reserve again after release — should be accepted
        # =====================================================
        olcbchecker.purgeMessages()

        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [MGMT_CMD, MGMT_RESERVE])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 4 reserve reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[2] != 0x00:
            logger.warning ("Failure: step 4 reserve after release rejected, result=0x{:02X}"
                           .format(reply.data[2]))
            return (3)

    finally :
        # Cleanup: always release
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [MGMT_CMD, MGMT_RELEASE])
        olcbchecker.sendMessage(message)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
