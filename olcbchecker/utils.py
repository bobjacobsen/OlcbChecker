# utility routines to assist with checking various conditions

# Event ID handling

from openlcb.eventid import EventID

# get the upper-bits mask from a range eventID
# for example, a range event of 0x0102030405060700 will get return a mask of 0xFFFFFFFFFFFFFF00
def rangemask(event) :
    eventrange = event.eventId   # get the event ID as a number
    
    lowbit = eventrange & 0x1
    mask = 0xFFFFFFFFFFFFFFFF  # the part that will be 1's in the result
    
    while eventrange != 0 :  # end is just a safety value
        if (eventrange & 1) == lowbit :
            # still part of the range bits
            mask = (mask << 1)
            eventrange = eventrange >> 1
        else :
            break
    return EventID(mask & 0xFFFFFFFFFFFFFFFF)
            
if not rangemask(EventID(0x0102030405060700)) == EventID(0xFFFFFFFFFFFFFF00) : print ("rM fail 1")

# given a collection of individual Event IDs,
#       a collection of range Event IDs,
#       and a single target Event ID
#   return True if the target is covered by one of the lists, add false otherwise
def checkAgainstIdList(individuals, ranges, event) :
    if event in individuals : return True
    
    for r in ranges :
        mask = rangemask(r).eventId
        compare = r.eventId
        eid = event.eventId
        if (compare&mask) == (eid&mask) : return True
    return False
    
if not checkAgainstIdList([EventID("1.2.3.4.5.6.7.8")], [], EventID("1.2.3.4.5.6.7.8") ) : print ("cAIL failed 1")
if not checkAgainstIdList([], [EventID("1.2.3.4.5.6.7.0")], EventID("1.2.3.4.5.6.7.8") ) : print ("cAIL failed 2")
if checkAgainstIdList([], [EventID("1.2.3.4.5.6.7.0")], EventID("1.2.3.4.5.6.8.8") ) : print ("cAIL failed 3")
