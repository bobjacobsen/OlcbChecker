#!/usr/bin/env python3.10
'''
Check Listener Configuration command and response

Checks the full listener lifecycle per Train Control Standard Section 6.5:
  1. Query Listeners (index 0) -> count=0
  2. Attach Listener A with REVERSE flag -> OK
  3. Query Listeners (index 0) -> count=1, A with REVERSE
  4. Attach Listener B with LINK_F0 flag -> OK
  5. Query Listeners (index 0) -> count=2, A with REVERSE
  6. Query Listeners (index 1) -> count=2, B with LINK_F0
  7. Detach Listener A -> OK
  8. Query Listeners (index 0) -> count=1, B with LINK_F0
  9. Detach non-existent Listener A again -> fail (non-zero)
 10. Detach Listener B -> OK
 11. Query Listeners (index 0) -> count=0

Usage:
python3.10 check_tr080_listener.py

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

# Listener Configuration protocol byte definitions
LISTENER_CONFIG  = 0x30
LISTENER_ATTACH  = 0x01
LISTENER_DETACH  = 0x02
LISTENER_QUERY   = 0x03

# Listener flags
FLAG_REVERSE     = 0x02
FLAG_LINK_F0     = 0x04

def getTrainControlReply(destination) :
    '''
    Invoked after a train control message gets
    sent, this waits for a train control reply
    and returns it.
    Raises Exception if something went wrong.
    '''

    # wait for the reply datagram
    while True :
        try :
            received = olcbchecker.getMessage() # timeout if no entries
            # is this a train control reply, OK or not?
            if not (received.mti == MTI.Traction_Control_Reply) :
                continue # wait for next

            if destination != received.source : # check source in message header
                continue

            if NodeID(olcbchecker.ownnodeid()) != received.destination : # check destination in message header
                continue

            # here we've received the reply datagram
            return received

        except Empty:
            raise Exception("Failure - no reply datagram received")


def nodeIDToList(nodeIDStr) :
    '''Convert a dotted node ID string like "11.22.33.44.55.66" to a list of bytes'''
    parts = nodeIDStr.split(".")
    return [int(p, 16) for p in parts]


def check():
    # set up the infrastructure

    logger = logging.getLogger("TRAIN_CONTROL")

    # pull any early received messages
    olcbchecker.purgeMessages()

    # get configured DUT node ID - this uses Verify Global in some cases, but not all
    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # check if PIP says this is present
    pipSet = olcbchecker.gatherPIP(destination)  # needed for CDI check later
    if olcbchecker.isCheckPip() :
        if pipSet is None:
            logger.warning ("Failed in setup, no PIP information received")
            return (2)
        if not PIP.TRAIN_CONTROL_PROTOCOL in pipSet :
            logger.info("Passed - due to Train Control protocol not in PIP")
            return(0)

    # Use the checker's own node ID as Listener A
    listenerA = nodeIDToList(olcbchecker.ownnodeid())
    # Use a fabricated node ID as Listener B
    listenerB = [0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF]

    try :
        # =====================================================
        # Step 1: Query Listeners (index 0) -> count=0
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_QUERY, 0x00])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 1 query reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[0] != LISTENER_CONFIG or reply.data[1] != LISTENER_QUERY:
            logger.warning ("Failure: step 1 reply header incorrect")
            return (3)

        if reply.data[2] != 0:
            logger.warning ("Failure: step 1 expected count=0, got {}".format(reply.data[2]))
            return (3)


        # =====================================================
        # Step 2: Attach Listener A with REVERSE flag -> OK
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_ATTACH, FLAG_REVERSE] + listenerA)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 9:
            logger.warning ("Failure: step 2 attach reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[0] != LISTENER_CONFIG or reply.data[1] != LISTENER_ATTACH:
            logger.warning ("Failure: step 2 reply header incorrect")
            return (3)

        # Check echoed node ID (bytes 2-7) matches listener A
        if reply.data[2:8] != listenerA:
            logger.warning ("Failure: step 2 echoed node ID does not match listener A")
            return (3)

        # Check result = 0 (OK)
        if reply.data[8] != 0x00:
            logger.warning ("Failure: step 2 attach failed, result=0x{:02X}".format(reply.data[8]))
            return (3)


        # =====================================================
        # Step 3: Query Listeners (index 0) -> count=1, A with REVERSE
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_QUERY, 0x00])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 11:
            logger.warning ("Failure: step 3 query reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[2] != 1:
            logger.warning ("Failure: step 3 expected count=1, got {}".format(reply.data[2]))
            return (3)

        if reply.data[3] != 0:
            logger.warning ("Failure: step 3 expected index=0, got {}".format(reply.data[3]))
            return (3)

        if reply.data[4] != FLAG_REVERSE:
            logger.warning ("Failure: step 3 expected flags=0x{:02X}, got 0x{:02X}".format(FLAG_REVERSE, reply.data[4]))
            return (3)

        if reply.data[5:11] != listenerA:
            logger.warning ("Failure: step 3 returned node ID does not match listener A")
            return (3)


        # =====================================================
        # Step 4: Attach Listener B with LINK_F0 flag -> OK
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_ATTACH, FLAG_LINK_F0] + listenerB)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 9:
            logger.warning ("Failure: step 4 attach reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[8] != 0x00:
            logger.warning ("Failure: step 4 attach failed, result=0x{:02X}".format(reply.data[8]))
            return (3)


        # =====================================================
        # Step 5: Query Listeners (index 0) -> count=2, A with REVERSE
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_QUERY, 0x00])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 11:
            logger.warning ("Failure: step 5 query reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[2] != 2:
            logger.warning ("Failure: step 5 expected count=2, got {}".format(reply.data[2]))
            return (3)

        if reply.data[3] != 0:
            logger.warning ("Failure: step 5 expected index=0, got {}".format(reply.data[3]))
            return (3)

        if reply.data[4] != FLAG_REVERSE:
            logger.warning ("Failure: step 5 expected flags=0x{:02X}, got 0x{:02X}".format(FLAG_REVERSE, reply.data[4]))
            return (3)

        if reply.data[5:11] != listenerA:
            logger.warning ("Failure: step 5 returned node ID does not match listener A")
            return (3)


        # =====================================================
        # Step 6: Query Listeners (index 1) -> count=2, B with LINK_F0
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_QUERY, 0x01])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 11:
            logger.warning ("Failure: step 6 query reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[2] != 2:
            logger.warning ("Failure: step 6 expected count=2, got {}".format(reply.data[2]))
            return (3)

        if reply.data[3] != 1:
            logger.warning ("Failure: step 6 expected index=1, got {}".format(reply.data[3]))
            return (3)

        if reply.data[4] != FLAG_LINK_F0:
            logger.warning ("Failure: step 6 expected flags=0x{:02X}, got 0x{:02X}".format(FLAG_LINK_F0, reply.data[4]))
            return (3)

        if reply.data[5:11] != listenerB:
            logger.warning ("Failure: step 6 returned node ID does not match listener B")
            return (3)


        # =====================================================
        # Step 7: Detach Listener A -> OK
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_DETACH, 0x00] + listenerA)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 9:
            logger.warning ("Failure: step 7 detach reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[0] != LISTENER_CONFIG or reply.data[1] != LISTENER_DETACH:
            logger.warning ("Failure: step 7 reply header incorrect")
            return (3)

        if reply.data[2:8] != listenerA:
            logger.warning ("Failure: step 7 echoed node ID does not match listener A")
            return (3)

        if reply.data[8] != 0x00:
            logger.warning ("Failure: step 7 detach failed, result=0x{:02X}".format(reply.data[8]))
            return (3)


        # =====================================================
        # Step 8: Query Listeners (index 0) -> count=1, B with LINK_F0
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_QUERY, 0x00])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 11:
            logger.warning ("Failure: step 8 query reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[2] != 1:
            logger.warning ("Failure: step 8 expected count=1, got {}".format(reply.data[2]))
            return (3)

        if reply.data[3] != 0:
            logger.warning ("Failure: step 8 expected index=0, got {}".format(reply.data[3]))
            return (3)

        if reply.data[4] != FLAG_LINK_F0:
            logger.warning ("Failure: step 8 expected flags=0x{:02X}, got 0x{:02X}".format(FLAG_LINK_F0, reply.data[4]))
            return (3)

        if reply.data[5:11] != listenerB:
            logger.warning ("Failure: step 8 returned node ID does not match listener B")
            return (3)


        # =====================================================
        # Step 9: Detach non-existent Listener A again -> fail (non-zero)
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_DETACH, 0x00] + listenerA)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 9:
            logger.warning ("Failure: step 9 detach reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[8] == 0x00:
            logger.warning ("Failure: step 9 detach of non-existent listener should have failed")
            return (3)


        # =====================================================
        # Step 10: Detach Listener B -> OK
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_DETACH, 0x00] + listenerB)
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 9:
            logger.warning ("Failure: step 10 detach reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[8] != 0x00:
            logger.warning ("Failure: step 10 detach failed, result=0x{:02X}".format(reply.data[8]))
            return (3)


        # =====================================================
        # Step 11: Query Listeners (index 0) -> count=0
        # =====================================================
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_QUERY, 0x00])
        olcbchecker.sendMessage(message)

        try :
            reply = getTrainControlReply(destination)
        except Exception as e:
            logger.warning(str(e))
            return (3)

        if len(reply.data) < 3:
            logger.warning ("Failure: step 11 query reply too short: {}".format(len(reply.data)))
            return (3)

        if reply.data[2] != 0:
            logger.warning ("Failure: step 11 expected count=0, got {}".format(reply.data[2]))
            return (3)


    except Exception as e:
        logger.warning(str(e))
        return (3)

    finally:
        # Cleanup: detach both listeners in case check failed mid-way
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_DETACH, 0x00] + listenerA)
        olcbchecker.sendMessage(message)
        message = Message(MTI.Traction_Control_Command, NodeID(olcbchecker.ownnodeid()), destination,
                    [LISTENER_CONFIG, LISTENER_DETACH, 0x00] + listenerB)
        olcbchecker.sendMessage(message)

    logger.info("Passed")
    return 0

if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
