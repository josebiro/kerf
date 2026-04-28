import io
import zipfile
import pytest
from pathlib import Path


def build_3mf_xml(
    unit: str = "millimeter",
    objects: list[dict] | None = None,
) -> str:
    """Build a minimal 3D/3dmodel.model XML string.

    Each object dict has:
        - id: str
        - name: str (optional)
        - vertices: list of (x, y, z) tuples
        - triangles: list of (v1, v2, v3) tuples
        - transform: str (optional, for build item)
    """
    if objects is None:
        # Default: single 100x50x19 mm box (roughly 4"x2"x3/4")
        objects = [
            {
                "id": "1",
                "name": "TestBox",
                "vertices": [
                    (0, 0, 0), (100, 0, 0), (100, 50, 0), (0, 50, 0),
                    (0, 0, 19), (100, 0, 19), (100, 50, 19), (0, 50, 19),
                ],
                "triangles": [
                    (0, 1, 2), (0, 2, 3),  # bottom
                    (4, 6, 5), (4, 7, 6),  # top
                    (0, 4, 5), (0, 5, 1),  # front
                    (2, 6, 7), (2, 7, 3),  # back
                    (0, 3, 7), (0, 7, 4),  # left
                    (1, 5, 6), (1, 6, 2),  # right
                ],
            }
        ]

    resource_xml = ""
    build_xml = ""
    for obj in objects:
        verts = "\n".join(
            f'          <vertex x="{x}" y="{y}" z="{z}" />'
            for x, y, z in obj["vertices"]
        )
        tris = "\n".join(
            f'          <triangle v1="{v1}" v2="{v2}" v3="{v3}" />'
            for v1, v2, v3 in obj["triangles"]
        )
        name_attr = f' name="{obj["name"]}"' if "name" in obj else ""
        resource_xml += f"""
    <object id="{obj['id']}"{name_attr} type="model">
      <mesh>
        <vertices>
{verts}
        </vertices>
        <triangles>
{tris}
        </triangles>
      </mesh>
    </object>"""

        transform_attr = ""
        if "transform" in obj:
            transform_attr = f' transform="{obj["transform"]}"'
        build_xml += f'    <item objectid="{obj["id"]}"{transform_attr} />\n'

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<model unit="{unit}" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
  <resources>{resource_xml}
  </resources>
  <build>
{build_xml}  </build>
</model>"""


def build_3mf_bytes(
    unit: str = "millimeter",
    objects: list[dict] | None = None,
) -> bytes:
    """Build a complete 3MF file (ZIP) as bytes."""
    xml_content = build_3mf_xml(unit=unit, objects=objects)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("3D/3dmodel.model", xml_content)
        zf.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml" />'
            "</Types>",
        )
    return buf.getvalue()


@pytest.fixture
def simple_box_3mf(tmp_path) -> Path:
    """A 3MF file containing a single 100x50x19mm box."""
    path = tmp_path / "box.3mf"
    path.write_bytes(build_3mf_bytes())
    return path


@pytest.fixture
def multi_part_3mf(tmp_path) -> Path:
    """A 3MF file with two different parts: a wide panel and a narrow rail."""
    objects = [
        {
            "id": "1",
            "name": "Side Panel",
            "vertices": [
                (0, 0, 0), (600, 0, 0), (600, 400, 0), (0, 400, 0),
                (0, 0, 19), (600, 0, 19), (600, 400, 19), (0, 400, 19),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        },
        {
            "id": "2",
            "name": "Rail",
            "vertices": [
                (0, 0, 0), (500, 0, 0), (500, 60, 0), (0, 60, 0),
                (0, 0, 19), (500, 0, 19), (500, 60, 19), (0, 60, 19),
            ],
            "triangles": [
                (0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6),
                (0, 4, 5), (0, 5, 1), (2, 6, 7), (2, 7, 3),
                (0, 3, 7), (0, 7, 4), (1, 5, 6), (1, 6, 2),
            ],
        },
    ]
    path = tmp_path / "multi.3mf"
    path.write_bytes(build_3mf_bytes(objects=objects))
    return path
