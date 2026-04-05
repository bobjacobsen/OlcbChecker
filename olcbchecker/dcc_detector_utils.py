'''
Utility functions for DCC Detector Event ID encoding and decoding.

Mirrors the C implementation in openlcb_dcc_detector.h/.c.
Each Event ID packs a 6-byte detector unique ID, 2 direction/occupancy bits,
and a 14-bit DCC address into a standard 8-byte Event ID.
'''

# Direction / occupancy status (upper 2 bits of the 16-bit tail)
DCC_DETECTOR_UNOCCUPIED       = 0x00
DCC_DETECTOR_OCCUPIED_FORWARD = 0x01
DCC_DETECTOR_OCCUPIED_REVERSE = 0x02
DCC_DETECTOR_OCCUPIED_UNKNOWN = 0x03

# DCC address type prefixes (upper byte of the 14-bit address field)
DCC_DETECTOR_SHORT_ADDRESS_PREFIX   = 0x38
DCC_DETECTOR_CONSIST_ADDRESS_PREFIX = 0x39

# Special sentinel
DCC_DETECTOR_TRACK_EMPTY = 0x3800

# Bit-field geometry
DCC_DETECTOR_ADDRESS_BITS    = 14
DCC_DETECTOR_ADDRESS_MASK    = 0x3FFF
DCC_DETECTOR_DIRECTION_MASK  = 0xC000
DCC_DETECTOR_DIRECTION_SHIFT = 14

# Reserved prefix range (0x3A-0x3F in the upper byte of the 14-bit field)
_RESERVED_PREFIX_MIN = 0x3A
_RESERVED_PREFIX_MAX = 0x3F

# Valid direction values
VALID_DIRECTIONS = {
    DCC_DETECTOR_UNOCCUPIED,
    DCC_DETECTOR_OCCUPIED_FORWARD,
    DCC_DETECTOR_OCCUPIED_REVERSE,
    DCC_DETECTOR_OCCUPIED_UNKNOWN,
}

DIRECTION_NAMES = {
    DCC_DETECTOR_UNOCCUPIED:       "unoccupied (exit)",
    DCC_DETECTOR_OCCUPIED_FORWARD: "occupied forward (entry)",
    DCC_DETECTOR_OCCUPIED_REVERSE: "occupied reverse (entry)",
    DCC_DETECTOR_OCCUPIED_UNKNOWN: "occupied direction unknown (entry)",
}

ADDRESS_TYPE_LONG        = "long"
ADDRESS_TYPE_SHORT       = "short"
ADDRESS_TYPE_CONSIST     = "consist"
ADDRESS_TYPE_TRACK_EMPTY = "track_empty"


def extract_detector_id(event_id_int):
    '''Extract the upper 6 bytes (48-bit detector node ID) from an Event ID.'''
    return (event_id_int >> 16) & 0xFFFFFFFFFFFF


def extract_direction(event_id_int):
    '''Extract the 2-bit direction/occupancy field.'''
    tail = event_id_int & 0xFFFF
    return (tail & DCC_DETECTOR_DIRECTION_MASK) >> DCC_DETECTOR_DIRECTION_SHIFT


def extract_raw_address(event_id_int):
    '''Extract the raw 14-bit DCC address field.'''
    return event_id_int & DCC_DETECTOR_ADDRESS_MASK


def extract_address_type(event_id_int):
    '''Classify the DCC address as long, short, consist, or track_empty.'''
    raw = extract_raw_address(event_id_int)

    if raw == DCC_DETECTOR_TRACK_EMPTY:
        return ADDRESS_TYPE_TRACK_EMPTY

    high_byte = (raw >> 8) & 0x3F
    if high_byte == DCC_DETECTOR_SHORT_ADDRESS_PREFIX:
        return ADDRESS_TYPE_SHORT
    if high_byte == DCC_DETECTOR_CONSIST_ADDRESS_PREFIX:
        return ADDRESS_TYPE_CONSIST

    return ADDRESS_TYPE_LONG


def extract_dcc_address(event_id_int):
    '''Extract the usable DCC address (strips prefix for short/consist).'''
    raw = extract_raw_address(event_id_int)
    addr_type = extract_address_type(event_id_int)

    if addr_type == ADDRESS_TYPE_TRACK_EMPTY:
        return 0
    if addr_type in (ADDRESS_TYPE_SHORT, ADDRESS_TYPE_CONSIST):
        return raw & 0x00FF
    return raw  # long address


def is_track_empty(event_id_int):
    '''Test whether an Event ID represents the track-empty sentinel.'''
    return extract_raw_address(event_id_int) == DCC_DETECTOR_TRACK_EMPTY


def has_reserved_prefix(event_id_int):
    '''Check if the address prefix is in the reserved 0x3A-0x3F range.'''
    raw = extract_raw_address(event_id_int)
    high_byte = (raw >> 8) & 0x3F
    return _RESERVED_PREFIX_MIN <= high_byte <= _RESERVED_PREFIX_MAX


def is_valid_event_id(event_id_int):
    '''Validate that direction bits and address prefix are legal.

    Returns (ok, reason) tuple.
    '''
    direction = extract_direction(event_id_int)
    if direction not in VALID_DIRECTIONS:
        return (False, "invalid direction bits: 0x{:02X}".format(direction))

    if has_reserved_prefix(event_id_int):
        raw = extract_raw_address(event_id_int)
        high_byte = (raw >> 8) & 0x3F
        return (False, "reserved address prefix: 0x{:02X}".format(high_byte))

    addr_type = extract_address_type(event_id_int)
    if addr_type in (ADDRESS_TYPE_SHORT, ADDRESS_TYPE_CONSIST):
        addr = extract_dcc_address(event_id_int)
        if addr > 127:
            return (False, "{} address out of range: {}".format(addr_type, addr))

    return (True, None)


def is_detector_event(event_id_int, node_id_int):
    '''Check if the upper 6 bytes of the Event ID match the given node ID.'''
    return extract_detector_id(event_id_int) == (node_id_int & 0xFFFFFFFFFFFF)


def describe_event(event_id_int):
    '''Return a human-readable description of a detector Event ID.'''
    detector = extract_detector_id(event_id_int)
    direction = extract_direction(event_id_int)
    addr_type = extract_address_type(event_id_int)
    dcc_addr = extract_dcc_address(event_id_int)
    raw = extract_raw_address(event_id_int)

    dir_name = DIRECTION_NAMES.get(direction, "unknown(0x{:02X})".format(direction))

    if addr_type == ADDRESS_TYPE_TRACK_EMPTY:
        addr_desc = "track empty"
    elif addr_type == ADDRESS_TYPE_SHORT:
        addr_desc = "short addr {}".format(dcc_addr)
    elif addr_type == ADDRESS_TYPE_CONSIST:
        addr_desc = "consist addr {}".format(dcc_addr)
    else:
        addr_desc = "long addr {}".format(dcc_addr)

    return "detector {:012X}, {}, {} (raw 0x{:04X})".format(
        detector, dir_name, addr_desc, raw)
