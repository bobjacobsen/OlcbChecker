'''
based on LinkLayer.swift

Created by Bob Jacobsen on 6/1/22.

Handles link-layer formatting and unformatting for a particular kind of
communications link.

Nodes are handled in one of two ways:
- "Own Node" - this is a node resident within the program
- "Remote Node" - this is a node outside the program

This is a class, not a struct, because an instance corresponds to an external
object (the actual link implementation), so there's no semantic meaning to
making multiple copies of a single object.
'''


class LinkLayer:

    def __init__(self, localNodeID):
        self.localNodeID = localNodeID

    def sendMessage(self, msg):
        '''This is the basic abstract interface
        '''

    def registerMessageReceivedListener(self, listener):
        self.listeners.append(listener)

    listeners = []  # local list of listener callbacks

    def fireListeners(self, msg):
        for listener in self.listeners:
            listener(msg)
