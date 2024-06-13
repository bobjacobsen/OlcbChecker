#!/usr/bin/env python3.10
'''
This uses a CAN link layer to check response to an CID frame alias collision

Usage:
python3.10 check_fr30_collide.py

The -h option will display a full list of options.
'''

import sys
import logging

from openlcb.nodeid import NodeID
from openlcb.canbus.canframe import CanFrame
from openlcb.canbus.controlframe import ControlFrame
from queue import Empty

import olcbchecker.setup

def check():
    # set up the infrastructure

    logger = logging.getLogger("FRAME")

    timeout = 0.3
    
    olcbchecker.purgeFrames()

    localAlias = olcbchecker.setup.canLink.localAlias # just to be shorter
    
    ###############################
    # checking sequence starts here
    ###############################

    # send the AME frame to start the exchange
    ame = CanFrame(ControlFrame.AME.value, localAlias)
    olcbchecker.setup.sendCanFrame(ame)
    
    try :
        # check for AMD frame from expected node (might be more than one AMD frame)
        while True: 
            waitFor = "waiting for AMD frame in first part"
            reply1 = olcbchecker.getFrame()
            if (reply1.header & 0xFF_FFF_000) != 0x10_701_000 :
                logger.warning ("Failure - frame was not AMD frame in first part")
                return 3
        
            # check it carries a node ID
            if len(reply1.data) < 6 :
                logger.warning ("Failure - first AMD frame did not carry node ID")
                return 3
        
            # and it's the right node ID
            targetnodeid = olcbchecker.setup.configure.targetnodeid
            if targetnodeid == None :
                # take first one we get 
                targetnodeid = str(NodeID(reply1.data))
                originalAlias = reply1.header&0xFFF
                break  
            if NodeID(targetnodeid) != NodeID(reply1.data) :
                # but this wasn't the right one, get another
                continue
                
            # got the right one, so now have it's orignal alias
            originalAlias = reply1.header&0xFFF
            break
 
        olcbchecker.purgeFrames()
        
        # Send a CID using that alias
        cid = CanFrame(ControlFrame.CID.value, originalAlias, [])
        olcbchecker.setup.sendCanFrame(cid)

        # check for RID frame in response
        waitFor = "waiting for RID in response to CID frame"
        reply = olcbchecker.getFrame()
        if (reply.header & 0xFF_FFF_000) != 0x10_700_000 :
            logger.warning ("Failure - frame was not RID frame in second part")
            return 3

        # collision in CID properly responded to, lets try an AMD alias collision
        amd = CanFrame(ControlFrame.AMD.value, originalAlias, NodeID(olcbchecker.setup.configure.ownnodeid).toArray())
        olcbchecker.setup.sendCanFrame(amd)

        # check for AMR frame
        waitFor = "waiting for AMR in response to AMD frame"
        reply = olcbchecker.getFrame()
        if (reply.header & 0xFF_FFF_000) != 0x10_703_000 :
            logger.warning ("Failure - frame was not AMR frame in second part")
            return 3
                
        # loop for _optional_ CID 7 frame and eventual AMD with different alias
        newAlias = 0  # zero indicates invalid, not allocated
        amdReceived = False
        first = True  # controls check for CID 7 in first pass
        try :
            while True: 
                reply2 = olcbchecker.getFrame()

                if first :
                    first = False
                    
                    # is this start of a CID sequence
                    if (reply2.header & 0xFF_000_000) == 0x17_000_000 :
                        # check for _different_ alias
                        if (reply2.header & 0x00_000_FFF) == originalAlias :
                            logger.warning ("Failure - did not receive different alias on CID 7 in second part")
                            return 3
                        # OK, remember this alias
                        newAlias = reply2.header & 0x00_000_FFF
                        continue
       
                # check for AMD frame from expected node (might be more AMD frames from others)
                if (reply2.header & 0xFF_FFF_000) != 0x10_701_000 :
                    # wasn't AMD
                    continue
        
                # check it carries a node ID
                if len(reply2.data) < 6 :
                    logger.warning ("Failure - additional AMD frame did not carry node ID")
                    return 3
        
                # and it's the right node ID
                if not NodeID(targetnodeid) == NodeID(reply2.data) :
                    # but this wasn't the right one, get another
                    continue
                
                # and it's the right alias
                # this means different from prior alias
                # and, if another was allocated via CID above, matches that
                thisAlias = reply2.header & 0x00_000_FFF
                if thisAlias == originalAlias :
                    logger.warning("Failure - found original alias in second AMD")
                    return 3
                if newAlias != 0 and (newAlias != thisAlias) :
                    logger.warning("Failure - AMD alias did not match newly allocated one")
                    return 3

                # got the right one, so now have seen an AMD
                amdReceived = True
                break
        except Empty : 
            # this is an OK case too - no AMD received
            pass
        
        # wait for traffic to subside
        olcbchecker.purgeFrames()

        # finally, send an AME and check results against above
        ame = CanFrame(ControlFrame.AME.value, localAlias)
        olcbchecker.setup.sendCanFrame(ame)
        
        countAMDs = 0
        try :
            # check for AMD frame from expected node (might be more AMD frames from others)
            while True: 
                reply3 = olcbchecker.getFrame()
                if (reply3.header & 0xFF_FFF_000) != 0x10_701_000 :
                    # wasn't AMD, skip
                    continue
        
                # check it carries a node ID - is this really an error?
                if len(reply3.data) < 6 :
                    continue
        
                # and it's the right node ID
                if NodeID(targetnodeid) != NodeID(reply3.data) :
                    # but this wasn't the right one, get another
                    continue
        
                # remember that we got one
                countAMDs += 1
                
                
        except Empty : 
            # have run out of replies to that AME
            # check for right number of AMD replies
            
            if amdReceived and countAMDs != 1 :
                logger.warning ("Failure - expected 1 AMD in third part and received "+str(countAMDs))
                return 3
            elif not amdReceived and countAMDs != 0 :
                logger.warning ("Failure - expected 0 AMDs in third part and received "+str(countAMDs))
                return 3
        
    except Empty:
        logger.warning ("Failure - did not receive expected frame while "+waitFor)
        return 3

    logger.info("Passed")
    return 0
 
if __name__ == "__main__":
    sys.exit(check())
    
