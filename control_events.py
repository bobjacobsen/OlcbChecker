#!/usr/bin/env python3.10

'''
Simple runner for message network checks
'''

import check_ev10_ida
import check_ev20_idg
import check_ev30_ip
import check_ev40_ic

def prompt() :
    print("\nEvent Exchange Standard checking")
    print(" a Run all in sequence")
    print(" 1 Identify Event Addressed checking")
    print(" 2 Identify Event Global checking")
    print(" 3 Identify Producer checking")
    print(" 4 Identify Consumer checking")
    print("  ")
    print(" q go back")

def checkAll() :
    result = 0
 
    print("\nIdentify Event Addressed checking")
    result += check_ev10_ida.check()

    print("\nIdentify Event Global checking")
    result += check_ev20_idg.check()

    print("\nIdentify Producer checking")
    result += check_ev30_ip.check()

    print("\nIdentify Consumer checking")
    result += check_ev40_ic.check()

    if result == 0 :
        print("\nSuccess - all event checks passed")
    else:
        print("\nAt least one event check failed")

    return result
    
def main() :
    '''
    loop to check against Event Transport Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nIdentify Event Addressed checking")
                check_ev10_ida.check()
            case "2" :
                print("\nIdentify Event Global checking")
                check_ev20_idg.check()
            case "3" : 
                print("\nIdentify Producer checking")
                check_ev30_ip.check()
            case "4" :
                print("\nIdentify Consumer checking")
                check_ev40_ic.check()
           
            case  "a" :
                checkAll()
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    main()
