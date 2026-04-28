import pytest
from pathlib import Path
from tests.conftest import build_3mf_bytes
from app.parser.threemf import parse_3mf, ParsedBody


def test_parse_3mf_returns_unit_and_bodies(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    assert result.unit == "millimeter"
    assert len(result.bodies) == 1


def test_parsed_body_has_name(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    assert result.bodies[0].name == "TestBox"


def test_parsed_body_has_vertices(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    body = result.bodies[0]
    assert body.vertices.shape == (8, 3)


def test_parsed_body_vertices_in_mm(simple_box_3mf):
    result = parse_3mf(simple_box_3mf)
    body = result.bodies[0]
    # Box is 100x50x19mm; max coords should match
    assert body.vertices[:, 0].max() == pytest.approx(100.0)
    assert body.vertices[:, 1].max() == pytest.approx(50.0)
    assert body.vertices[:, 2].max() == pytest.approx(19.0)


def test_parse_inch_units(tmp_path):
    # 4" x 2" x 0.75" box in inches
    objects = [
        {
            "id": "1",
            "name": "InchBox",
            "vertices": [
                (0, 0, 0), (4, 0, 0), (4, 2, 0), (0, 2, 0),
                (0, 0, 0.75), (4, 0, 0.75), (4, 2, 0.75), (0, 2, 0.75),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        }
    ]
    path = tmp_path / "inch.3mf"
    path.write_bytes(build_3mf_bytes(unit="inch", objects=objects))
    result = parse_3mf(path)
    body = result.bodies[0]
    # Should be converted to mm: 4" = 101.6mm
    assert body.vertices[:, 0].max() == pytest.approx(101.6)
    assert body.vertices[:, 2].max() == pytest.approx(19.05)


def test_parse_multi_part(multi_part_3mf):
    result = parse_3mf(multi_part_3mf)
    assert len(result.bodies) == 2
    names = {b.name for b in result.bodies}
    assert names == {"Side Panel", "Rail"}


def test_parse_unnamed_object(tmp_path):
    objects = [
        {
            "id": "1",
            "vertices": [
                (0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0),
                (0, 0, 10), (10, 0, 10), (10, 10, 10), (0, 10, 10),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        }
    ]
    path = tmp_path / "unnamed.3mf"
    path.write_bytes(build_3mf_bytes(objects=objects))
    result = parse_3mf(path)
    assert result.bodies[0].name == "Part 1"


def test_parse_with_transform(tmp_path):
    # Transform that translates the box by (200, 0, 0)
    # 3MF transform: "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32"
    # Identity rotation + translation (200, 0, 0):
    objects = [
        {
            "id": "1",
            "name": "Translated",
            "vertices": [
                (0, 0, 0), (100, 0, 0), (100, 50, 0), (0, 50, 0),
                (0, 0, 19), (100, 0, 19), (100, 50, 19), (0, 50, 19),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
            "transform": "1 0 0 0 1 0 0 0 1 200 0 0",
        }
    ]
    path = tmp_path / "transformed.3mf"
    path.write_bytes(build_3mf_bytes(objects=objects))
    result = parse_3mf(path)
    body = result.bodies[0]
    # Box should now span x: 200 to 300
    assert body.vertices[:, 0].min() == pytest.approx(200.0)
    assert body.vertices[:, 0].max() == pytest.approx(300.0)


def test_parse_invalid_file_raises(tmp_path):
    path = tmp_path / "bad.3mf"
    path.write_text("not a zip file")
    with pytest.raises(ValueError, match="Invalid 3MF"):
        parse_3mf(path)
