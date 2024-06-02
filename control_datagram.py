#!/usr/bin/env python3.10

'''
Simple runner for Datagram suite
'''

import olcbchecker.setup

import check_da30_dr

def prompt() :
    print("\nDatagram Transport Standard checking")
    print(" a Run all in sequence")
    print(" 1 Datagram Reception checking")
    print("  ")
    print(" q go back")

def checkAll() :
    result = 0
 
    print("\nDatagram Reception checking")
    result += check_da30_dr.check()

    if result == 0 :
        print("\nSuccess - all datagram checks passed")
    else:
        print("\nAt least one datagram check failed")
        
    return result
    
def main() :
    if olcbchecker.setup.configure.runimmediate :
        checkAll()
        return

    '''
    loop to check against Datagram Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nDatagram Reception checking")
                check_da30_dr.check()
           
            case  "a" :
                checkAll()
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    main()
