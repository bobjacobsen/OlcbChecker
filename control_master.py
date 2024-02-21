#!/usr/bin/env python3.10

'''
Top level of checking suite
'''

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
    
def main() :
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
                total = 0
                import control_frame
                total += control_frame.checkAll()
                import control_message
                total += control_message.checkAll()
                import control_snip
                total += control_snip.checkAll()
                import control_events
                total += control_events.checkAll()
                import control_datagram
                total += control_datagram.checkAll()
                import control_memory
                total += control_memory.checkAll()
                import control_cdi
                total += control_cdi.checkAll()
                import control_cdi
                total += control_cdi.checkAll()
                
                if total > 0 :
                    print ("{} sections had failures".format(total))
                else
                    print ("All sections passed")
                       
            case "q" | "quit" : return
                   
            case _ : continue
            
    return
if __name__ == "__main__":
    main()
