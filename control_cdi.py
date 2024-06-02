#!/usr/bin/env python3.10

'''
Simple runner for CDI suite
'''

import olcbchecker.setup

import check_cd10_valid
import check_cd20_read
import check_cd30_acdi

def prompt() :
    print("\nCDI Standard checking")
    print(" a Run all in sequence")
    print(" 1 CDI Memory Present checking")
    print(" 2 Validation checking")
    print(" 3 ACDI checking")
    print("  ")
    print(" q go back")

def checkAll() :
    result = 0
 
    print("\nCDI Memory Present checking")
    result += check_cd10_valid.check()

    print("\nValidation checking")
    result += check_cd20_read.check()

    print("\nACDI checking")
    result += check_cd30_acdi.check()

    if result == 0 :
        print("\nSuccess - all CDI checks passed")
    else:
        print("\nAt least one CDI check failed")
        
    return result
    
def main() :
    if olcbchecker.setup.configure.runimmediate :
        checkAll()
        return

    '''
    loop to check against Frame Transport Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nCDI Memory Present checking")
                check_cd10_valid.check()
                           
            case "2" : 
                print("\nValidation checking")
                check_cd20_read.check()
                           
            case "3" : 
                print("\nACDI checking")
                check_cd30_acdi.check()
                           
            case  "a" :
                checkAll()
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    main()
