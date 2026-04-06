#!/usr/bin/env python3.10

'''
Simple runner for Stream Transport suite
'''
import sys
import logging

import olcbchecker.setup

import check_st10_initiate
import check_st20_reject_unsupported
import check_st30_buffer_negotiation
import check_st35_min_buffer
import check_st37_max_buffer
import check_st40_unknown_content_uid
import check_st50_initiate_reply_format
import check_st60_data_send
import check_st65_data_proceed_flow
import check_st70_complete
import check_st80_terminate_error
import check_st85_stability
import check_st90_oir_fallback
import check_st100_concurrent_same_node
import check_st110_concurrent_multi_node
import check_st120_sustained_transfer
import check_st130_min_chunk_send
import check_st140_concurrent_sustained
import check_st150_asymmetric_buffers
import check_st155_negotiation_enforcement
import check_st170_zero_payload_flush
import check_st180_interleaved_data_send
import check_st190_suggested_did
import check_st200_complete_with_byte_count
import check_st210_reject_then_retry

def prompt() :
    print("\nStream Transport Standard checking")
    print(" a Run all in sequence")
    print(" 1 Stream Initiate Request/Reply checking")
    print(" 2 Reject when unsupported checking")
    print(" 3 Buffer negotiation checking")
    print(" 4 Minimum buffer size checking")
    print(" 5 Maximum buffer size checking")
    print(" 6 Unknown Content UID checking")
    print(" 7 Initiate Reply format checking")
    print(" 8 Data send and Proceed checking")
    print(" 9 Data Proceed flow control checking")
    print("10 Stream completion checking")
    print("11 Terminate Due To Error checking")
    print("12 Post-stream stability checking")
    print("13 OIR fallback checking")
    print("14 Concurrent streams (same node) checking")
    print("15 Concurrent streams (multi node) checking")
    print("16 Sustained transfer checking")
    print("17 Minimum chunk send checking")
    print("18 Concurrent sustained checking")
    print("19 Asymmetric buffers checking")
    print("20 Negotiation enforcement checking")
    print("21 Zero-payload flush checking")
    print("22 Interleaved data send checking")
    print("23 Suggested DID checking")
    print("24 Complete with byte count checking")
    print("25 Reject then retry checking")
    print("  ")
    print(" q go back")

def checkAll(logger=logging.getLogger("STREAM")) :
    result = 0

    logger.info("Stream Initiate Request/Reply checking")
    result += check_st10_initiate.check()

    logger.info("Reject when unsupported checking")
    result += check_st20_reject_unsupported.check()

    logger.info("Buffer negotiation checking")
    result += check_st30_buffer_negotiation.check()

    logger.info("Minimum buffer size checking")
    result += check_st35_min_buffer.check()

    logger.info("Maximum buffer size checking")
    result += check_st37_max_buffer.check()

    logger.info("Unknown Content UID checking")
    result += check_st40_unknown_content_uid.check()

    logger.info("Initiate Reply format checking")
    result += check_st50_initiate_reply_format.check()

    logger.info("Data send and Proceed checking")
    result += check_st60_data_send.check()

    logger.info("Data Proceed flow control checking")
    result += check_st65_data_proceed_flow.check()

    logger.info("Stream completion checking")
    result += check_st70_complete.check()

    logger.info("Terminate Due To Error checking")
    result += check_st80_terminate_error.check()

    logger.info("Post-stream stability checking")
    result += check_st85_stability.check()

    logger.info("OIR fallback checking")
    result += check_st90_oir_fallback.check()

    logger.info("Concurrent streams (same node) checking")
    result += check_st100_concurrent_same_node.check()

    logger.info("Concurrent streams (multi node) checking")
    result += check_st110_concurrent_multi_node.check()

    logger.info("Sustained transfer checking")
    result += check_st120_sustained_transfer.check()

    logger.info("Minimum chunk send checking")
    result += check_st130_min_chunk_send.check()

    logger.info("Concurrent sustained checking")
    result += check_st140_concurrent_sustained.check()

    logger.info("Asymmetric buffers checking")
    result += check_st150_asymmetric_buffers.check()

    logger.info("Negotiation enforcement checking")
    result += check_st155_negotiation_enforcement.check()

    logger.info("Zero-payload flush checking")
    result += check_st170_zero_payload_flush.check()

    logger.info("Interleaved data send checking")
    result += check_st180_interleaved_data_send.check()

    logger.info("Suggested DID checking")
    result += check_st190_suggested_did.check()

    logger.info("Complete with byte count checking")
    result += check_st200_complete_with_byte_count.check()

    logger.info("Reject then retry checking")
    result += check_st210_reject_then_retry.check()

    if result == 0 :
        logger.info("Success - all stream checks passed")
    else:
        logger.warning("At least one stream check failed")

    return result

def main() :
    logger = logging.getLogger("STREAM")

    if olcbchecker.setup.configure.runimmediate :
        return (checkAll(logger))

    '''
    loop to check against Stream Transport Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" :
                print("\nStream Initiate Request/Reply checking")
                check_st10_initiate.check()

            case "2" :
                print("\nReject when unsupported checking")
                check_st20_reject_unsupported.check()

            case "3" :
                print("\nBuffer negotiation checking")
                check_st30_buffer_negotiation.check()

            case "4" :
                print("\nMinimum buffer size checking")
                check_st35_min_buffer.check()

            case "5" :
                print("\nMaximum buffer size checking")
                check_st37_max_buffer.check()

            case "6" :
                print("\nUnknown Content UID checking")
                check_st40_unknown_content_uid.check()

            case "7" :
                print("\nInitiate Reply format checking")
                check_st50_initiate_reply_format.check()

            case "8" :
                print("\nData send and Proceed checking")
                check_st60_data_send.check()

            case "9" :
                print("\nData Proceed flow control checking")
                check_st65_data_proceed_flow.check()

            case "10" :
                print("\nStream completion checking")
                check_st70_complete.check()

            case "11" :
                print("\nTerminate Due To Error checking")
                check_st80_terminate_error.check()

            case "12" :
                print("\nPost-stream stability checking")
                check_st85_stability.check()

            case "13" :
                print("\nOIR fallback checking")
                check_st90_oir_fallback.check()

            case "14" :
                print("\nConcurrent streams (same node) checking")
                check_st100_concurrent_same_node.check()

            case "15" :
                print("\nConcurrent streams (multi node) checking")
                check_st110_concurrent_multi_node.check()

            case "16" :
                print("\nSustained transfer checking")
                check_st120_sustained_transfer.check()

            case "17" :
                print("\nMinimum chunk send checking")
                check_st130_min_chunk_send.check()

            case "18" :
                print("\nConcurrent sustained checking")
                check_st140_concurrent_sustained.check()

            case "19" :
                print("\nAsymmetric buffers checking")
                check_st150_asymmetric_buffers.check()

            case "20" :
                print("\nNegotiation enforcement checking")
                check_st155_negotiation_enforcement.check()

            case "21" :
                print("\nZero-payload flush checking")
                check_st170_zero_payload_flush.check()

            case "22" :
                print("\nInterleaved data send checking")
                check_st180_interleaved_data_send.check()

            case "23" :
                print("\nSuggested DID checking")
                check_st190_suggested_did.check()

            case "24" :
                print("\nComplete with byte count checking")
                check_st200_complete_with_byte_count.check()

            case "25" :
                print("\nReject then retry checking")
                check_st210_reject_then_retry.check()

            case  "a" :
                checkAll(logger)

            case "q" | "quit" : return

            case _ : continue

    return

if __name__ == "__main__":
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
