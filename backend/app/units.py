"""Unit conversion utilities.

Internally all dimensions are stored in millimeters. Convert from the 3MF file's
declared unit on parse, and convert to inches for lumber matching / display.
"""

_3MF_UNIT_TO_MM = {
    "millimeter": 1.0,
    "centimeter": 10.0,
    "meter": 1000.0,
    "inch": 25.4,
    "foot": 304.8,
    "micrometer": 0.001,
}


def convert_from_3mf_unit(value: float, unit: str) -> float:
    """Convert a value from a 3MF unit to millimeters."""
    factor = _3MF_UNIT_TO_MM.get(unit)
    if factor is None:
        raise ValueError(f"Unknown 3MF unit: {unit!r}")
    return value * factor


def mm_to_inches(mm: float) -> float:
    """Convert millimeters to inches."""
    return mm / 25.4


def inches_to_mm(inches: float) -> float:
    """Convert inches to millimeters."""
    return inches * 25.4
