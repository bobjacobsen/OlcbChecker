#!/usr/bin/env python3.10

'''
Simple runner for CDI suite
'''

import check_cd10_read

def prompt() :
    print("\nCDI Standard checking")
    print(" a Run all in sequence")
    print(" 1 Validation checking")
    print("  ")
    print(" q go back")

def checkAll() :
    result = 0
 
    print("\nValidation checking")
    result += check_cd10_read.check()

    if result == 0 :
        print("\nSuccess - all CDI checks passed")
    else:
        print("\nAt least one CDI check failed")
        
    return result
    
def main() :
    '''
    loop to check against Frame Transport Standard
    '''
    while True :
        prompt()
        selection = input(">> ").lower()
        match selection :
            case "1" : 
                print("\nValidation checking")
                check_cd10_read.check()
                           
            case  "a" :
                checkAll()
            
            case "q" | "quit" : return
            
            case _ : continue
                   
    return
if __name__ == "__main__":
    main()
