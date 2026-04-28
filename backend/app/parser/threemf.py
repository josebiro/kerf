import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.units import convert_from_3mf_unit

_NS = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}


@dataclass
class ParsedBody:
    name: str
    vertices: np.ndarray  # shape (N, 3), in millimeters
    triangle_count: int


@dataclass
class ParseResult:
    unit: str
    bodies: list[ParsedBody]


def _parse_transform(transform_str: str) -> np.ndarray:
    """Parse a 3MF transform string into a 4x4 matrix.

    3MF format: "m00 m01 m02 m10 m11 m12 m20 m21 m22 m30 m31 m32"
    This is a row-major 3x4 affine matrix (rotation columns + translation row).
    """
    vals = [float(v) for v in transform_str.strip().split()]
    if len(vals) != 12:
        raise ValueError(f"Transform must have 12 values, got {len(vals)}")
    mat = np.eye(4)
    mat[0, 0], mat[0, 1], mat[0, 2] = vals[0], vals[1], vals[2]
    mat[1, 0], mat[1, 1], mat[1, 2] = vals[3], vals[4], vals[5]
    mat[2, 0], mat[2, 1], mat[2, 2] = vals[6], vals[7], vals[8]
    mat[3, 0], mat[3, 1], mat[3, 2] = vals[9], vals[10], vals[11]
    return mat


def parse_3mf(file_path: Path) -> ParseResult:
    """Parse a 3MF file and return extracted bodies with vertices in mm."""
    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            model_xml = zf.read("3D/3dmodel.model")
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError(f"Invalid 3MF file: {e}") from e

    root = ET.fromstring(model_xml)
    unit = root.get("unit", "millimeter")

    # Build object lookup: id -> (name, vertices, triangle_count)
    objects: dict[str, tuple[str | None, np.ndarray, int]] = {}
    unnamed_counter = 0

    for obj in root.findall(".//m:object", _NS):
        obj_id = obj.get("id")
        obj_name = obj.get("name")
        mesh = obj.find("m:mesh", _NS)
        if mesh is None:
            continue

        verts_elem = mesh.find("m:vertices", _NS)
        if verts_elem is None:
            continue

        vertices = []
        for v in verts_elem.findall("m:vertex", _NS):
            vertices.append((float(v.get("x")), float(v.get("y")), float(v.get("z"))))

        tri_elem = mesh.find("m:triangles", _NS)
        tri_count = len(tri_elem.findall("m:triangle", _NS)) if tri_elem is not None else 0

        vert_array = np.array(vertices, dtype=np.float64)
        objects[obj_id] = (obj_name, vert_array, tri_count)

    # Process build items (apply transforms)
    bodies: list[ParsedBody] = []
    build = root.find("m:build", _NS)
    items = build.findall("m:item", _NS) if build is not None else []

    for item in items:
        obj_id = item.get("objectid")
        if obj_id not in objects:
            continue

        obj_name, vert_array, tri_count = objects[obj_id]
        verts = vert_array.copy()

        # Apply transform if present
        transform_str = item.get("transform")
        if transform_str:
            mat = _parse_transform(transform_str)
            ones = np.ones((verts.shape[0], 1))
            homogeneous = np.hstack([verts, ones])
            transformed = homogeneous @ mat
            verts = transformed[:, :3]

        # Convert to mm
        if unit != "millimeter":
            verts = verts * convert_from_3mf_unit(1.0, unit)

        # Assign name
        if obj_name is None:
            unnamed_counter += 1
            obj_name = f"Part {unnamed_counter}"

        bodies.append(ParsedBody(name=obj_name, vertices=verts, triangle_count=tri_count))

    return ParseResult(unit=unit, bodies=bodies)
