#!/usr/bin/env python3.10

'''
Top level of checking suite
'''
import sys
import logging

# We only import each specific option as it's 
# invoked to reduce startup time and propagation of errors
# during development

def prompt() :
    print("\nOpenLCB checking program")
    print(" s Setup")
    print("")
    print(" 0 Frame Transport checking")
    print(" 1 Message Network checking")
    print(" 2 SNIP checking")
    print(" 3 Event Transport checking")
    print(" 4 Datagram Transport checking")
    print(" 5 Memory Configuration checking")
    print(" 6 Configuration Definition Information (CDI) checking")
    print(" 7 Train Control checking")
    print(" 8 Train Search checking")
    print(" 9 Function Definition Information (FDI) checking")
    print("  ")
    print(" a Run all in sequence without three train protocols")
    print(" t Run all in sequence including three train protocols")
    print("  ")
    print(" q  Quit")
    
def checkAll() :
    total = 0
    import control_frame
    total += min(control_frame.checkAll(),1)
    import control_message
    total += min(control_message.checkAll(),1)
    import control_snip
    total += min(control_snip.checkAll(),1)
    import control_events
    total += min(control_events.checkAll(),1)
    import control_datagram
    total += min(control_datagram.checkAll(),1)
    import control_memory
    total += min(control_memory.checkAll(),1)
    import control_cdi
    total += min(control_cdi.checkAll(),1)
    import control_traincontrol
    total += min(control_traincontrol.checkAll(),1)
    import control_trainsearch
    total += min(control_trainsearch.checkAll(),1)
    import control_fdi
    total += min(control_fdi.checkAll(),1)
    
    logger = logging.getLogger("OLCBCHECKER")
    if total > 0 :
        logger.info("{} sections had failures".format(total))
    else :
        logger.info("All sections passed")
    return total;
   
def checkAllNoTrains() :
    total = 0
    import control_frame
    total += min(control_frame.checkAll(),1)
    import control_message
    total += min(control_message.checkAll(),1)
    import control_snip
    total += min(control_snip.checkAll(),1)
    import control_events
    total += min(control_events.checkAll(),1)
    import control_datagram
    total += min(control_datagram.checkAll(),1)
    import control_memory
    total += min(control_memory.checkAll(),1)
    import control_cdi
    total += min(control_cdi.checkAll(),1)
    
    logger = logging.getLogger("OLCBCHECKER")
    if total > 0 :
        logger.info("{} sections had failures".format(total))
    else :
        logger.info("All sections passed")
    return total;
 
def main() :

    # if immediate running has been requested, do that
    if olcbchecker.setup.configure.runimmediate :
        return (checkAll())
        
    # Otherwise, show the menu and process input
    '''
    loop to check against individual standards
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "s" : 
                import control_setup
                control_setup.main()

            case "0" : 
                import control_frame
                control_frame.main()

            case "1" : 
                import control_message
                control_message.main()
           
            case "2" : 
                import control_snip
                control_snip.main()
                       
            case "3" : 
                import control_events
                control_events.main()
                       
            case "4" : 
                import control_datagram
                control_datagram.main()
                       
            case "5" : 
                import control_memory
                control_memory.main()
                       
            case "6" : 
                import control_cdi
                control_cdi.main()
                       
            case "7" : 
                import control_traincontrol
                control_traincontrol.main()
                       
            case "8" : 
                import control_trainsearch
                control_trainsearch.main()
                       
            case "9" : 
                import control_fdi
                control_fdi.main()
                       
            case "a" : 
                checkAllNoTrains()    
                                  
            case "t" : 
                checkAll()     
                                  
            case "q" | "quit" : return
                   
            case _ : continue
            
    return
if __name__ == "__main__":
    # check options to see if a connection is specified
    import builtins
    builtins.olcbchecker_bypass_a_or_d_check = True
    import configure
    
    print("in _main_")
    print(configure.devicename)
    print(configure.hostname)
    print(configure.targetnodeid)
    
    if configure.devicename is None and configure.hostname is None :
        print ("With neither an address nor device specified, you can")
        print ("only set the options, so we'll take you directly to")
        print ("that menu.  You can restart with the -a or -d option")
        print ("(or -h for additional help), or configure using the")
        print ("following menu.")
        print ("")
        import control_setup
        control_setup.main()
        # can't continue without reset
        sys.exit(0)
        
    if not configure.targetnodeid :
        print ("Without a target node defined, you can")
        print ("only set the options, so we'll take you directly to")
        print ("that menu.  You can restart with the -t option")
        print ("(or -h for additional help), or configure using the")
        print ("following menu.")
        print ("")
        import control_setup
        control_setup.main()
        # can't continue without reset
        sys.exit(0)

    # do the setup, including argument parsing
    import olcbchecker.setup
        
    # run the checks or show the menu
    import olcbchecker
    result = main()
    olcbchecker.setup.interface.close()
    sys.exit(result)
