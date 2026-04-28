import pytest
from app.units import mm_to_inches, inches_to_mm, convert_from_3mf_unit


def test_mm_to_inches():
    assert mm_to_inches(25.4) == pytest.approx(1.0)
    assert mm_to_inches(0.0) == pytest.approx(0.0)
    assert mm_to_inches(304.8) == pytest.approx(12.0)


def test_inches_to_mm():
    assert inches_to_mm(1.0) == pytest.approx(25.4)
    assert inches_to_mm(12.0) == pytest.approx(304.8)


def test_convert_from_3mf_millimeter():
    assert convert_from_3mf_unit(100.0, "millimeter") == pytest.approx(100.0)


def test_convert_from_3mf_centimeter():
    assert convert_from_3mf_unit(10.0, "centimeter") == pytest.approx(100.0)


def test_convert_from_3mf_inch():
    assert convert_from_3mf_unit(1.0, "inch") == pytest.approx(25.4)


def test_convert_from_3mf_foot():
    assert convert_from_3mf_unit(1.0, "foot") == pytest.approx(304.8)


def test_convert_from_3mf_meter():
    assert convert_from_3mf_unit(1.0, "meter") == pytest.approx(1000.0)


def test_convert_from_3mf_micrometer():
    assert convert_from_3mf_unit(1000.0, "micrometer") == pytest.approx(1.0)


def test_convert_from_3mf_unknown_unit_raises():
    with pytest.raises(ValueError, match="Unknown 3MF unit"):
        convert_from_3mf_unit(1.0, "cubits")
