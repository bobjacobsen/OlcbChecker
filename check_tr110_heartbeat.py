#!/usr/bin/env python3.10
'''
This checks the Train Control Heartbeat / Keep-alive mechanism.

Per TrainControlS section 6.6:
  - A Train Node may send a Heartbeat Request (0x40, 0x03, timeout) to the
    Controller to verify it is still alive.
  - The Controller may reply with any command/query or a No-op (0x40, 0x03)
    to clear the heartbeat.
  - If no reply is received within the deadline, the Train Node shall
    interpret that as a Set Speed 0 command (emergency stop).
  - Trains shall not initiate a Heartbeat Request if the last Set Speed
    is zero.

Usage:
python3.10 check_tr110_heartbeat.py

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

import olcbchecker.setup

# Protocol byte definitions
SPEED_SET      = 0x00
EMERGENCY_STOP = 0x02
SPEED_QUERY    = 0x10
CTRL_CMD       = 0x20
CTRL_ASSIGN    = 0x01
CTRL_RELEASE   = 0x02
MGMT_CMD       = 0x40
MGMT_NOOP      = 0x03


def getTrainControlReply(destination, timeout=0.8) :
    '''Wait for a Traction Control Reply from the destination node.
    Raises Exception if no reply received within timeout.'''
    while True :
        try :
            received = olcbchecker.getMessage(timeout) # timeout if no entries
            if not (received.mti == MTI.Traction_Control_Reply) :
                continue

            if destination != received.source :
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination :
                continue

            return received

        except Empty:
            raise Exception("Failure - no Traction Control Reply received")


def waitForHeartbeatRequest(destination, timeout=5.0) :
    '''Wait for a Heartbeat Request (Management Reply [0x40, 0x03, ...])
    from the destination node. Returns the reply message.
    Raises Exception if no heartbeat request received within timeout.'''
    deadline = time.time() + timeout
    while True :
        remaining = deadline - time.time()
        if remaining <= 0:
            raise Exception("Failure - no Heartbeat Request received within {} seconds".format(timeout))
        try :
            wait_time = min(remaining, 0.8)
            received = olcbchecker.getMessage(wait_time)
            if not (received.mti == MTI.Traction_Control_Reply) :
                continue

            if destination != received.source :
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination :
                continue

            # Check for Heartbeat Request: [0x40, 0x03, timeout...]
            if len(received.data) >= 2 and received.data[0] == MGMT_CMD and received.data[1] == MGMT_NOOP:
                return received

            # Other replies are ignored while waiting for heartbeat
            continue

        except Empty:
            continue  # Keep waiting until deadline


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

    own_id_bytes = NodeID(olcbchecker.ownnodeid()).toArray()

    # Non-zero speed: 0.2 m/s forward (float16: 0x3E4C)
    speed_hi = 0x3E
    speed_lo = 0x4C

    try :
        # =====================================================
        # Step 1: Assign controller
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_ASSIGN, 0x00] + own_id_bytes)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3 or reply.data[2] != 0x00:
            logger.warning ("Failure: step 1 controller assign rejected")
            return (3)


        # =====================================================
        # Step 2: Set speed to non-zero value
        # Per spec: "Trains shall not initiate a Heartbeat Request
        # if the last Set Speed is zero"
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [SPEED_SET, speed_hi, speed_lo])
        olcbchecker.sendMessage(message)
        # No reply expected for Set Speed


        # =====================================================
        # Step 3: Wait for Heartbeat Request from train node
        # The library sends this at the halfway point of the
        # heartbeat timeout.
        # Per TrainControlS 6.6: "The Heartbeat Request may be sent
        # by a Train Node" — heartbeat is optional, so if the node
        # never sends one we pass with an info message.
        # =====================================================
        try :
            hb_reply = waitForHeartbeatRequest(destination, timeout=10.0)
        except Exception :
            # Heartbeat not implemented — this is valid per spec
            logger.info("Passed - train node does not send Heartbeat Requests (optional per spec)")
            return (0)

        # Extract timeout value from reply (bytes 2+ are the timeout in seconds)
        if len(hb_reply.data) >= 3:
            # Could be 1 or 3 bytes for timeout depending on implementation
            if len(hb_reply.data) >= 5:
                hb_timeout = (hb_reply.data[2] << 16) | (hb_reply.data[3] << 8) | hb_reply.data[4]
            else:
                hb_timeout = hb_reply.data[2]
        else:
            hb_timeout = 0

        if hb_timeout == 0:
            logger.warning ("Failure: step 3 heartbeat timeout value is 0")
            return (3)


        # =====================================================
        # Step 4: Keepalive test — send NOOP before deadline,
        # then verify speed is still non-zero
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [MGMT_CMD, MGMT_NOOP])
        olcbchecker.sendMessage(message)

        # Query speed to verify it's still set
        olcbchecker.purgeMessages()
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [SPEED_QUERY])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning("Failure: step 4 no speed query reply after keepalive - " + str(e))
            return (3)

        if len(reply.data) < 4:
            logger.warning ("Failure: step 4 speed query reply too short: {}".format(len(reply.data)))
            return (3)

        # Check speed is still non-zero (strip direction bit for comparison)
        reply_speed_hi = reply.data[1] & 0x7F  # mask off direction bit
        reply_speed_lo = reply.data[2]
        if reply_speed_hi == 0x00 and reply_speed_lo == 0x00:
            logger.warning ("Failure: step 4 speed unexpectedly zero after keepalive")
            return (3)


        # =====================================================
        # Step 5: Wait for second Heartbeat Request after
        # keepalive reset the counter
        # =====================================================
        try :
            hb_reply2 = waitForHeartbeatRequest(destination, timeout=10.0)
        except Exception as e:
            logger.warning("Failure: step 5 no second heartbeat request - " + str(e))
            return (3)


        # =====================================================
        # Step 6: Timeout test — do NOT send keepalive.
        # Wait for the full heartbeat timeout to expire.
        # =====================================================
        time.sleep(hb_timeout + 1)


        # =====================================================
        # Step 7: Query speed — should be 0 (emergency stopped)
        # =====================================================
        olcbchecker.purgeMessages()
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [SPEED_QUERY])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning("Failure: step 7 no speed query reply after timeout - " + str(e))
            return (3)

        if len(reply.data) < 4:
            logger.warning ("Failure: step 7 speed query reply too short: {}".format(len(reply.data)))
            return (3)

        # Speed magnitude should be zero (direction bit may be preserved)
        reply_speed_hi = reply.data[1] & 0x7F  # mask off direction bit
        reply_speed_lo = reply.data[2]
        if reply_speed_hi != 0x00 or reply_speed_lo != 0x00:
            logger.warning ("Failure: step 7 speed not zero after heartbeat timeout: "
                           "0x{:02X}{:02X}".format(reply.data[1], reply.data[2]))
            return (3)

        # Optionally check E-Stop status bit (bit 0 of status byte at data[3])
        if len(reply.data) >= 4:
            status = reply.data[3]
            if (status & 0x01) == 0:
                logger.warning ("Warning: step 7 E-Stop status bit not set (status=0x{:02X})"
                               .format(status))
                # This is a warning, not a failure — spec says "Set Speed 0" not necessarily E-Stop bit


        # =====================================================
        # Step 8: No heartbeat when speed is zero
        # Per TrainControlS 6.6: "Trains shall not initiate a
        # Heartbeat Request if the last Set Speed is zero"
        # Speed is already zero from step 7 timeout. Verify no
        # heartbeat request is sent.
        # =====================================================
        olcbchecker.purgeMessages()
        # Wait long enough that a heartbeat would have been sent if active
        try :
            unexpected_hb = waitForHeartbeatRequest(destination, timeout=float(hb_timeout + 1))
            logger.warning ("Failure: step 8 heartbeat request received when speed is zero")
            return (3)
        except Exception :
            pass  # Expected — no heartbeat when speed is zero


        # =====================================================
        # Step 9: No heartbeat after Emergency Stop
        # Set speed non-zero, wait for heartbeat to confirm it
        # is active, then send E-Stop and verify no heartbeat.
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [SPEED_SET, speed_hi, speed_lo])
        olcbchecker.sendMessage(message)

        try :
            waitForHeartbeatRequest(destination, timeout=10.0)
        except Exception as e:
            logger.warning("Failure: step 9 no heartbeat after re-setting speed - " + str(e))
            return (3)

        # Send Emergency Stop
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [EMERGENCY_STOP])
        olcbchecker.sendMessage(message)

        # Verify no heartbeat after E-Stop
        olcbchecker.purgeMessages()
        try :
            unexpected_hb = waitForHeartbeatRequest(destination, timeout=float(hb_timeout + 1))
            logger.warning ("Failure: step 9 heartbeat request received after E-Stop")
            return (3)
        except Exception :
            pass  # Expected — no heartbeat in E-Stop state


        # =====================================================
        # Step 10: Speed query after controller release
        # Per TrainControlS 6.6: "In case there is no assigned
        # Controller node, the Train Node shall continue
        # operating as last commanded."
        # Set speed, release controller, verify speed unchanged.
        # =====================================================
        # Clear E-Stop by setting speed
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [SPEED_SET, speed_hi, speed_lo])
        olcbchecker.sendMessage(message)

        # Release controller
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_RELEASE, 0x00] + own_id_bytes)
        olcbchecker.sendMessage(message)

        # Wait longer than the heartbeat timeout
        time.sleep(hb_timeout + 1)

        # Re-assign controller so we can query
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [CTRL_CMD, CTRL_ASSIGN, 0x00] + own_id_bytes)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning("Failure: step 10 no assign reply - " + str(e))
            return (3)

        # Query speed — should still be non-zero (not e-stopped)
        olcbchecker.purgeMessages()
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [SPEED_QUERY])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning("Failure: step 10 no speed query reply - " + str(e))
            return (3)

        if len(reply.data) < 4:
            logger.warning ("Failure: step 10 speed query reply too short: {}".format(len(reply.data)))
            return (3)

        reply_speed_hi = reply.data[1] & 0x7F
        reply_speed_lo = reply.data[2]
        if reply_speed_hi == 0x00 and reply_speed_lo == 0x00:
            logger.warning ("Failure: step 10 speed is zero after controller release — "
                           "train should continue operating as last commanded")
            return (3)


    finally :
        # Cleanup: set speed to 0 and release controller
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [SPEED_SET, 0x00, 0x00])
        olcbchecker.sendMessage(message)

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
