#!/usr/bin/env python3.10
'''
This checks ACDI space consistency and writeback.

Per the CDI Standard section 5.1.2, ACDI address spaces:
  Space 252 (0xFC) - Manufacturer info (read-only):
    Address 0:   Version (1 byte)
    Address 1:   Manufacturer name (41 bytes)
    Address 42:  Model name (41 bytes)
    Address 83:  Hardware version (21 bytes)
    Address 104: Software version (21 bytes)

  Space 251 (0xFB) - User info (read/write):
    Address 0:   Version (1 byte)
    Address 1:   User-supplied name (63 bytes)
    Address 64:  User-supplied description (64 bytes)

The check:
  1) Verifies the ACDI-related Configuration Options flags are consistent
     with PIP and address space presence
  2) For each ACDI space flagged as readable, reads all fields and
     compares against SNIP
  3) If ACDI User Write is flagged, performs a write-then-read roundtrip
     on the user name field (saving and restoring original data)

Usage:
python3.10 check_cd40_acdi_writeback.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.message import Message
from openlcb.mti import MTI
from openlcb.pip import PIP
from openlcb.snip import SNIP

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
                        ack = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination, [0])
                        olcbchecker.sendMessage(ack)
                        break
                    except Empty:
                        raise Exception("Failure - no write reply datagram after Reply Pending")
            return

        except Empty:
            raise Exception("Failure - no reply to write request")


def readMemoryString(destination, address, length, space) :
    '''Read a null-terminated string from a memory space.'''
    ad1 = (address >> 24) & 0xFF
    ad2 = (address >> 16) & 0xFF
    ad3 = (address >> 8) & 0xFF
    ad4 = address & 0xFF

    # 0x40 = read command with explicit space byte
    request = [0x20, 0x40, ad1, ad2, ad3, ad4, space, length]
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, request)
    olcbchecker.sendMessage(message)
    reply = getReplyDatagram(destination)
    raw = reply.data[7:]
    result = ""
    for b in raw :
        if b == 0 :
            break
        result += chr(b)
    return result


def readMemoryByte(destination, address, space) :
    '''Read a single byte from a memory space.  Returns int.'''
    ad1 = (address >> 24) & 0xFF
    ad2 = (address >> 16) & 0xFF
    ad3 = (address >> 8) & 0xFF
    ad4 = address & 0xFF

    request = [0x20, 0x40, ad1, ad2, ad3, ad4, space, 1]
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, request)
    olcbchecker.sendMessage(message)
    reply = getReplyDatagram(destination)
    return reply.data[7]


def writeMemorySpace(destination, address, space, data) :
    '''Write data to a memory space using explicit space byte (command 0x00).'''
    ad1 = (address >> 24) & 0xFF
    ad2 = (address >> 16) & 0xFF
    ad3 = (address >> 8) & 0xFF
    ad4 = address & 0xFF

    # 0x00 = write command with explicit space byte in byte 6
    sendWriteDatagram(destination,
        [0x20, 0x00, ad1, ad2, ad3, ad4, space] + data)


def getSnip(destination) :
    '''Request SNIP and return a populated SNIP object.'''
    message = Message(MTI.Simple_Node_Ident_Info_Request, NodeID(olcbchecker.ownnodeid()), destination)
    olcbchecker.sendMessage(message)

    results = []
    while True :
        try :
            received = olcbchecker.getMessage()
            if received.mti != MTI.Simple_Node_Ident_Info_Reply :
                continue
            if destination != received.source :
                continue
            if NodeID(olcbchecker.ownnodeid()) != received.destination :
                continue
            results.extend(received.data)
        except Empty:
            break

    snip = SNIP()
    snip.addData(results)
    return snip


def checkAddressSpaceInfo(destination, space, expect_readonly, expect_high, expect_low, logger) :
    '''Query Address Space Information and verify present, read-only, and address bounds.
    Returns True on success, False on failure (after logging).'''
    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x84, space])
    olcbchecker.sendMessage(message)
    try :
        reply = getReplyDatagram(destination)
    except Exception as e :
        logger.warning("Failure - could not query address space info for 0x{:02X}: {}".format(space, str(e)))
        return False

    if len(reply.data) < 8 :
        logger.warning("Failure - address space info reply too short for 0x{:02X}".format(space))
        return False

    # Check present
    if reply.data[1] != 0x87 :
        logger.warning("Failure - space 0x{:02X} not present (reply byte 0x{:02X})".format(space, reply.data[1]))
        return False

    # Check space number echoed back
    if reply.data[2] != space :
        logger.warning("Failure - space 0x{:02X} reply echoed space 0x{:02X}".format(space, reply.data[2]))
        return False

    # Extract highest address (bytes 3-6, big-endian)
    high_addr = (reply.data[3] << 24) | (reply.data[4] << 16) | (reply.data[5] << 8) | reply.data[6]

    if high_addr != expect_high :
        logger.warning("Failure - space 0x{:02X} highest address {} != expected {}".format(space, high_addr, expect_high))
        return False

    # Check flags byte
    flags = reply.data[7]
    is_readonly = bool(flags & 0x01)

    if is_readonly != expect_readonly :
        if expect_readonly :
            logger.warning("Failure - space 0x{:02X} should be read-only but is not".format(space))
        else :
            logger.warning("Failure - space 0x{:02X} should be writable but is read-only".format(space))
        return False

    # Check low address if present
    has_low_addr = bool(flags & 0x02)
    if has_low_addr :
        if len(reply.data) < 12 :
            logger.warning("Failure - space 0x{:02X} flags say low address present but reply too short".format(space))
            return False
        low_addr = (reply.data[8] << 24) | (reply.data[9] << 16) | (reply.data[10] << 8) | reply.data[11]
        if low_addr != expect_low :
            logger.warning("Failure - space 0x{:02X} low address {} != expected {}".format(space, low_addr, expect_low))
            return False

    return True


def check():
    logger = logging.getLogger("CDI")

    olcbchecker.purgeMessages()

    destination = olcbchecker.getTargetID()

    ###############################
    # checking sequence starts here
    ###############################

    # check PIP for ACDI and Memory Configuration support
    pipSet = olcbchecker.gatherPIP(destination, always=True)

    if pipSet is None :
        logger.warning("Failure - no PIP information received")
        return (2)

    if not PIP.ADCDI_PROTOCOL in pipSet :
        logger.info("Passed - ACDI not in PIP")
        return 0

    if not PIP.MEMORY_CONFIGURATION_PROTOCOL in pipSet :
        logger.info("Passed - Memory Configuration not in PIP (needed for ACDI)")
        return 0

    # -------------------------------------------------------
    # Step 1: Get Configuration Options and check ACDI flags
    # -------------------------------------------------------

    message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, [0x20, 0x80])
    olcbchecker.sendMessage(message)

    try :
        options_reply = getReplyDatagram(destination)
    except Exception as e:
        logger.warning("Failure - could not get Configuration Options: " + str(e))
        return (3)

    if len(options_reply.data) < 5 :
        logger.warning("Failure - Configuration Options reply too short")
        return (3)

    # Extract command flags word (bytes 2-3, big-endian)
    cmd_flags = (options_reply.data[2] << 8) | options_reply.data[3]

    acdi_mfg_read  = bool(cmd_flags & 0x0800)
    acdi_user_read = bool(cmd_flags & 0x0400)
    acdi_user_write = bool(cmd_flags & 0x0200)

    # ACDI is in PIP, so all three flags should be consistent:
    # - Manufacturer read should be set
    # - User read should be set
    # - If user write is set, user read must also be set

    if not acdi_mfg_read :
        logger.warning("Failure - ACDI in PIP but ACDI Manufacturer Read flag not set in Options")
        return (3)

    if not acdi_user_read :
        logger.warning("Failure - ACDI in PIP but ACDI User Read flag not set in Options")
        return (3)

    if acdi_user_write and not acdi_user_read :
        logger.warning("Failure - ACDI User Write set but ACDI User Read not set in Options")
        return (3)

    # Check that ACDI spaces fall within the highest/lowest address space range
    if len(options_reply.data) >= 6 :
        highest_space = options_reply.data[5]
        lowest_space = options_reply.data[6] if len(options_reply.data) >= 7 else 0

        if acdi_mfg_read and (0xFC > highest_space or 0xFC < lowest_space) :
            logger.warning("Failure - space 0xFC outside supported range 0x{:02X}-0x{:02X}".format(lowest_space, highest_space))
            return (3)

        if acdi_user_read and (0xFB > highest_space or 0xFB < lowest_space) :
            logger.warning("Failure - space 0xFB outside supported range 0x{:02X}-0x{:02X}".format(lowest_space, highest_space))
            return (3)

    # Verify address spaces report correct presence, read-only, and bounds
    # 0xFC: 1 + 41 + 41 + 21 + 21 = 125 bytes, addresses 0-124, always read-only
    # 0xFB: 1 + 63 + 64 = 128 bytes, addresses 0-127, read-only only if no User Write
    if acdi_mfg_read :
        if not checkAddressSpaceInfo(destination, 0xFC, True, 124, 0, logger) :
            return (3)

    if acdi_user_read :
        expect_readonly = not acdi_user_write
        if not checkAddressSpaceInfo(destination, 0xFB, expect_readonly, 127, 0, logger) :
            return (3)

    # -------------------------------------------------------
    # Step 2: Get SNIP for comparison
    # -------------------------------------------------------

    snip = None
    if PIP.SIMPLE_NODE_IDENTIFICATION_PROTOCOL in pipSet :
        snip = getSnip(destination)

    # -------------------------------------------------------
    # Step 3: If Manufacturer Read, read 0xFC and compare to SNIP
    # -------------------------------------------------------

    if acdi_mfg_read :

        mfg_version = readMemoryByte(destination, 0, 0xFC)
        if mfg_version != 0 and mfg_version != 4 :
            logger.warning("Failure - Space 0xFC version {} not valid (expected 0 or 4)".format(mfg_version))
            return (3)

        mfg_name = readMemoryString(destination, 1, 41, 0xFC)
        mfg_model = readMemoryString(destination, 42, 41, 0xFC)
        mfg_hw_ver = readMemoryString(destination, 83, 21, 0xFC)
        mfg_sw_ver = readMemoryString(destination, 104, 21, 0xFC)

        if snip is not None :
            # Compare version bytes
            snip_mfg_version = snip.data[0]
            if mfg_version != snip_mfg_version :
                logger.warning("Failure - ACDI 0xFC version {} != SNIP manufacturer version {}".format(mfg_version, snip_mfg_version))
                return (3)

            if mfg_name != snip.manufacturerName :
                logger.warning("Failure - ACDI manufacturer '{}' != SNIP '{}'".format(mfg_name, snip.manufacturerName))
                return (3)
            if mfg_model != snip.modelName :
                logger.warning("Failure - ACDI model '{}' != SNIP '{}'".format(mfg_model, snip.modelName))
                return (3)
            if mfg_hw_ver != snip.hardwareVersion :
                logger.warning("Failure - ACDI hardware version '{}' != SNIP '{}'".format(mfg_hw_ver, snip.hardwareVersion))
                return (3)
            if mfg_sw_ver != snip.softwareVersion :
                logger.warning("Failure - ACDI software version '{}' != SNIP '{}'".format(mfg_sw_ver, snip.softwareVersion))
                return (3)

    # -------------------------------------------------------
    # Step 4: If User Read, read 0xFB and compare to SNIP
    # -------------------------------------------------------

    if acdi_user_read :

        user_version = readMemoryByte(destination, 0, 0xFB)
        if user_version != 0 and user_version != 2 :
            logger.warning("Failure - Space 0xFB version {} not valid (expected 0 or 2)".format(user_version))
            return (3)

        user_name = readMemoryString(destination, 1, 63, 0xFB)
        user_desc = readMemoryString(destination, 64, 64, 0xFB)

        if snip is not None :
            # Compare version bytes — user version is just before string 4
            user_ver_index = snip.findString(4) - 1
            if user_ver_index >= 0 :
                snip_user_version = snip.data[user_ver_index]
                if user_version != snip_user_version :
                    logger.warning("Failure - ACDI 0xFB version {} != SNIP user version {}".format(user_version, snip_user_version))
                    return (3)

            if user_name != snip.userProvidedNodeName :
                logger.warning("Failure - ACDI user name '{}' != SNIP '{}'".format(user_name, snip.userProvidedNodeName))
                return (3)
            if user_desc != snip.userProvidedDescription :
                logger.warning("Failure - ACDI user description '{}' != SNIP '{}'".format(user_desc, snip.userProvidedDescription))
                return (3)

    # -------------------------------------------------------
    # Step 5: If User Write, write-then-read roundtrip on user name
    # -------------------------------------------------------

    if acdi_user_write :

        ACDI_USER_NAME_ADDR = 1
        ACDI_USER_NAME_LEN = 63

        # Save original user name
        original_name = readMemoryString(destination, ACDI_USER_NAME_ADDR, ACDI_USER_NAME_LEN, 0xFB)

        # Write check data pattern
        check_name = "OLCB_TST"
        check_data = [ord(c) for c in check_name] + [0x00]

        try :
            writeMemorySpace(destination, ACDI_USER_NAME_ADDR, 0xFB, check_data)
        except Exception as e:
            logger.warning("Failure writing check name to ACDI space: " + str(e))
            return (3)

        # Read back and verify
        try :
            readback = readMemoryString(destination, ACDI_USER_NAME_ADDR, ACDI_USER_NAME_LEN, 0xFB)
        except Exception as e:
            logger.warning("Failure reading back from ACDI space: " + str(e))
            # try to restore
            restore_data = [ord(c) for c in original_name] + [0x00]
            try :
                writeMemorySpace(destination, ACDI_USER_NAME_ADDR, 0xFB, restore_data)
            except Exception :
                pass
            return (3)

        if readback != check_name :
            logger.warning("Failure - wrote '{}' to ACDI 0xFB but read back '{}'".format(check_name, readback))
            # restore
            restore_data = [ord(c) for c in original_name] + [0x00]
            try :
                writeMemorySpace(destination, ACDI_USER_NAME_ADDR, 0xFB, restore_data)
            except Exception :
                pass
            return (3)

        # Restore original user name
        restore_data = [ord(c) for c in original_name] + [0x00]
        try :
            writeMemorySpace(destination, ACDI_USER_NAME_ADDR, 0xFB, restore_data)
        except Exception :
            pass  # best effort restore

    # -------------------------------------------------------
    # Step 6: Verify write to read-only 0xFC is rejected
    # -------------------------------------------------------

    if acdi_mfg_read :

        try :
            # Attempt to write to read-only manufacturer space
            ad1, ad2, ad3, ad4 = 0, 0, 0, 1  # address 1 (manufacturer name)
            write_data = [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFC, 0x41]
            message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, write_data)
            olcbchecker.sendMessage(message)

            # Should get Datagram Rejected or a Write Reply with Fail
            while True :
                try :
                    received = olcbchecker.getMessage()
                    if destination != received.source :
                        continue
                    if NodeID(olcbchecker.ownnodeid()) != received.destination :
                        continue

                    if received.mti == MTI.Datagram_Rejected :
                        # Good — rejected at datagram level
                        break

                    if received.mti == MTI.Datagram_Received_OK :
                        # Node accepted the datagram, wait for Write Reply with Fail
                        while True :
                            try :
                                reply = olcbchecker.getMessage()
                                if reply.mti != MTI.Datagram :
                                    continue
                                if destination != reply.source :
                                    continue
                                # ACK the reply datagram
                                ack = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination, [0])
                                olcbchecker.sendMessage(ack)
                                # Check for Fail bit (0x08 in byte 1)
                                if len(reply.data) >= 2 and (reply.data[1] & 0x08) :
                                    break  # Good — write failed as expected
                                else :
                                    logger.warning("Failure - write to read-only 0xFC succeeded (should have been rejected)")
                                    return (3)
                            except Empty :
                                logger.warning("Failure - no Write Reply after writing to read-only 0xFC")
                                return (3)
                        break

                except Empty :
                    logger.warning("Failure - no response to write attempt on read-only 0xFC")
                    return (3)

        except Exception as e :
            logger.warning("Failure - unexpected error writing to 0xFC: " + str(e))
            return (3)

    # -------------------------------------------------------
    # Step 7: Verify write to 0xFB version byte (address 0) is rejected
    # -------------------------------------------------------

    if acdi_user_write :

        try :
            # Attempt to write to the version byte at address 0
            ad1, ad2, ad3, ad4 = 0, 0, 0, 0
            write_data = [0x20, 0x00, ad1, ad2, ad3, ad4, 0xFB, 0x02]
            message = Message(MTI.Datagram, NodeID(olcbchecker.ownnodeid()), destination, write_data)
            olcbchecker.sendMessage(message)

            while True :
                try :
                    received = olcbchecker.getMessage()
                    if destination != received.source :
                        continue
                    if NodeID(olcbchecker.ownnodeid()) != received.destination :
                        continue

                    if received.mti == MTI.Datagram_Rejected :
                        break  # Good

                    if received.mti == MTI.Datagram_Received_OK :
                        while True :
                            try :
                                reply = olcbchecker.getMessage()
                                if reply.mti != MTI.Datagram :
                                    continue
                                if destination != reply.source :
                                    continue
                                ack = Message(MTI.Datagram_Received_OK, NodeID(olcbchecker.ownnodeid()), destination, [0])
                                olcbchecker.sendMessage(ack)
                                if len(reply.data) >= 2 and (reply.data[1] & 0x08) :
                                    break  # Good — write to version byte failed
                                else :
                                    logger.warning("Failure - write to 0xFB version byte (address 0) succeeded (should have been rejected)")
                                    return (3)
                            except Empty :
                                logger.warning("Failure - no Write Reply after writing to 0xFB version byte")
                                return (3)
                        break

                except Empty :
                    logger.warning("Failure - no response to write attempt on 0xFB address 0")
                    return (3)

        except Exception as e :
            logger.warning("Failure - unexpected error writing to 0xFB address 0: " + str(e))
            return (3)

    logger.info("Passed")
    return 0


if __name__ == "__main__":
    result = check()
    import olcbchecker
    olcbchecker.setup.interface.close()
    sys.exit(result)
