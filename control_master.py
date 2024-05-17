#!/usr/bin/env python3

'''
Top level of checking suite
'''

# We only import each specific option as it's 
# invoked to reduce startup time and propagation of errors
# during development
import argparse
import sys
import configparser
import configure


def parse_args():
    parser = argparse.ArgumentParser(description='Validate an OpenLCB implementation/node')
    parser.add_argument('--hostname', action='store', help='Hostname or IP address of a node to check')
    parser.add_argument('--port', action='store', help='Port to connect to when using an IP connection')
    parser.add_argument('--device', action='store', help='A serial device to connect to in order to talk to a node')
    parser.add_argument('--target-node-id', action='store', help='The target node ID to validate')
    parser.add_argument('--add-test', action='append', help='A test to run.  May be specified multiple times')
    parser.add_argument('--run-all', action='store_true', help='Shorthand to run all tests', default=None)
    parser.add_argument('--config-file', action='store', help='The configuration file to use to specify options.  '
                                                              'Command-line args will override any settings from the config file')
    parser.add_argument('--skip-interactive', action='store_true', help='Skip interactive tests', default=None)
    parser.add_argument('--check-pip', action='store_true', help='Check PIP bits', default=None)

    return parser.parse_args()


def parse_config_file(config_file):
    if config_file is None:
        return None

    config = configparser.ConfigParser()

    from pathlib import Path
    file = Path(config_file)
    if not file.is_file():
        return None

    # Okay, we have a file, let's load it!
    print(f"Loading config file: {config_file}")
    config.read(config_file)
    return config

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


def all_tests():
    """
    Return a list of all tests that we can run
    """
    import control_frame
    import control_message
    import control_snip
    import control_events
    import control_datagram
    import control_memory
    import control_cdi

    return [control_frame,
            control_message,
            control_snip,
            control_events,
            control_datagram,
            control_memory,
            control_cdi]

def string_to_test(name : str):
    import control_frame
    import control_message
    import control_snip
    import control_events
    import control_datagram
    import control_memory
    import control_cdi

    if name == 'control_frame':
        return control_frame
    if name == 'control_message':
        return control_message
    if name == 'control_snip':
        return control_snip
    if name == 'control_events':
        return control_events
    if name == 'control_datagram':
        return control_datagram
    if name == 'control_memory':
        return control_memory
    if name == 'control_cdi':
        return control_cdi

    return None

def main() :
    args = parse_args()
    config = parse_config_file(args.config_file)
    tests_to_run = []

    if config is None and not any(vars(args).values()):
        # No arguments provided, go into our prompt
        run_prompt()
        return

    if config is not None:
        # Set our settings according to the config file
        configure.global_config.set_config(config['OlcbChecker'])

        for test_name in configure.global_config.tests:
            test_obj = string_to_test(test_name)
            if test_obj is None:
                print(f"Test {test_name} is invalid, not running")
                continue
            tests_to_run.append(test_obj)

    # Command-line args take precedence over anything set by the config file
    if args.hostname is not None:
        configure.global_config.hostname = args.hostname
    if args.port is not None:
        configure.global_config.portnumber = args.port
    if args.device is not None:
        configure.global_config.devicename = args.device
    if args.target_node_id is not None:
        configure.global_config.targetnodeid = args.target_node_id
    if args.skip_interactive is not None:
        configure.global_config.skip_interactive = args.skip_interactive
    if args.check_pip is not None:
        configure.global_config.checkpip = args.check_pip
    if args.add_test is not None:
        for test_name in args.add_test:
            test_obj = string_to_test(test_name)
            if test_obj is None:
                print(f"Test {test_name} is invalid, not running")
                continue
            tests_to_run.append(test_obj)

    # Now let's do some logic tests to make sure that our configuration looks sane
    if configure.global_config.hostname is None and configure.global_config.devicename is None:
        print("ERROR: Neither hostname nor devicename is set, can't run tests!")
        sys.exit(1)

    if args.run_all is not None:
        tests_to_run = all_tests()

    print(f"About to run {len(tests_to_run)} tests")
    total = 0
    for test in tests_to_run:
        total += min(test.checkAll(), 1)

    if total > 0:
        print("\n{} sections had failures".format(total))
        sys.exit(2)
    else:
        print("\nAll sections passed")

    return


def run_prompt():
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
                       
            case "q" | "quit" : return
                   
            case _ : continue
            
    return
if __name__ == "__main__":
    main()
