#!/usr/bin/env python3.10

'''
Top level of checking suite
'''

import olcbchecker.setup

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
    print(" 6 CDI checking")
    print("  ")
    print(" a run all in sequence")
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
    
    if total > 0 :
        print ("\n{} sections had failures".format(total))
    else :
        print ("\nAll sections passed")
    return total;
    
def main() :
    if olcbchecker.setup.configure.runimmediate :
        return (checkAll())
        
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
                       
            case "a" : 
                checkAll()     
                                  
            case "q" | "quit" : return
                   
            case _ : continue
            
    return
if __name__ == "__main__":
    main()
