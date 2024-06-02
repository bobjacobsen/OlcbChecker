#!/usr/bin/env python3.10

'''
Simple runner for SNIP suite
'''

import olcbchecker.setup

import check_sn10_snip

def prompt() :
    print("\nSNIP Standard checking")
    print(" a Run all in sequence")
    print(" 1 SNIP reply checking")
    print("  ")
    print(" q go back")

def checkAll() :
    result = 0
 
    print("\nSNIP reply checking")
    result += check_sn10_snip.check()

    if result == 0 :
        print("\nSuccess - all SNIP checks passed")
    else:
        print("\nAt least one SNIP check failed")
        
    return result
        
def main() :
    if olcbchecker.setup.configure.runimmediate :
        checkAll()
        return

    '''
    loop to check against SNIP Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nSNIP reply checking")
                check_sn10_snip.check()
           
            case  "a" :
                checkAll()
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    main()
