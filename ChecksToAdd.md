The following items should be added to check plans, then check scripts:

 - Add multi-PIP and multi-SNIP cases to message capacity check
 
 - Check PIP simple bit against Verify Node ID -> Verified Node ID's Simple bit
 
 - Check datagram error and overlap handling
    - Overlapping datagrams from two sources are properly handled or errored
    - Datagrams with incorrect first-middle-last are properly errored and can be followed with valid ones 
    - Check for proper operation if the node doesn't PIP declare Datagram protocol
    - Send a datagram with the first byte a protocol number that does not exist (not 0x20) and checking the returned error
    
 - Check errors and error handling in section 4.3 of the Memory Configuration Standard
    - Invoking error messages by sending datagram reads with parameters outside the range
    - Check the Memory Configuration write under mask functionally if it is flagged as present 
    
 - ACDI should check that the user space is writable, goes to SNIP, reads back
    - Also can be used as a general memory write checks
    - But isn't SNIP supposed to be constant between reboots?
 
 - Train Control checks subsection 11 needs a detailed plan

 - Memory Configuration check now only checks that servers do the right thing. A section should be added for checking client implementations using a dummy (OlcbChecker-provided) server.
    - This includes splitting the checking document and control_memory.py file to separately do client and server checking.  Not quite sure how to include that in "run all" though.
    - This came up in a discusion of checking for proper handling of the returned "extended timout" field and related operation. See https://groups.io/g/openlcb/message/16746 for a good discussion of what can be checked.

- From discussion of a node that reserves multiple aliases
    - Check that the AMD responses for those have different node IDs
    - In Frame section 3, check for collisions on both aliases
    - check for _non_-permitted state just drops reservation by using an AME to that node

- The FDI space might say it's read-only in the address-space reply. Or it might not. What does that mean for FDI checking?
    
----------------------

The following items should be added to the check scripts:

 - Implement the Firmware Update check plan
 - Implement the Broadcast Time check plan
 - The three-PIP message part of the PIP section in the Message Level plan is not implemented.
 - The three-SNIP message part of the SNIP check is not implemented.
 - Section 3 Frame Level of the Message Level plan is not implemented
 - check_me10_init.py is not checking against Simple bit in PIP
 - Is the Message Level duplicate check really checking the right thing?
 - CDI section 2.4 not implemented
 - Code the Train Control checks for subsection 8, 9, 10, 11
 
----------------------

To be considered:
 - should we be checking that the flags for memory write, etc datagram reply are correct?
