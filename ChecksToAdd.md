The following items should be added to check plans:

 - Add multi-PIP and multi-SNIP to message capacity check
 - Check datagram error and overlap handling
    - Overlapping datagrams from two sources are properly handled or errored
    - Datagrams with incorrect first-middle-last are properly errored and can be followed with valid ones
 - Check errors and error handling in section 4.3 of the Memory Configuration Standard
   - Invoking error messages by sending datagram reads with parameters outside the range
   - Send a datagram with the first byte a protocol number that does not exist (not 0x20) and checking the returned error
 - Check the Memory Configuration write under mask functionally if it is flagged as present 
 - ACDI should check that the user space is writable, goes to SNIP, reads back
   - Also can be used for general memory write checks

The following items should be added to the check scripts:

 - Implement the Firmware Update check plan
 - Implement the Broadcast Time check plan
 - Section 3 Frame Level of the Message Level plan not implemented
 - Is the Message Level duplicate test really checking the right thing?
 - CDI section 2.4 not implemented
