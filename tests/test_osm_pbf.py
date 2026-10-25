"""The PBF reader in data/osm_pbf.py, on a file written here with a small protobuf
encoder: a header, a block of dense nodes and a block of ways."""

import importlib.util
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("osm_pbf", ROOT / "data" / "osm_pbf.py")
osm_pbf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(osm_pbf)


# ------------------------------------------------------------- a protobuf encoder

def varint(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def zigzag(v):
    return (v << 1) ^ (v >> 63) if v < 0 else v << 1


def field_varint(number, v):
    return varint(number << 3) + varint(v)


def field_bytes(number, b):
    return varint((number << 3) | 2) + varint(len(b)) + b


def packed(number, values, signed=False):
    return field_bytes(number, b"".join(varint(zigzag(v) if signed else v) for v in values))


def deltas(values):
    return [b - a for a, b in zip([0] + list(values), values)]


def blob(kind, payload):
    data = field_bytes(3, zlib.compress(payload)) + field_varint(2, len(payload))
    head = field_bytes(1, kind.encode()) + field_varint(3, len(data))
    return struct.pack(">I", len(head)) + head + data


def pbf_file(path):
    header = field_varint(32, 1_761_339_600)                     # 2025-10-24T21:00:00Z
    header += field_bytes(17, b"test extract")
    strings = [b"", b"highway", b"residential", b"motorway", b"name", b"Test street", b"area", b"yes"]
    table = field_bytes(1, b"".join(field_bytes(1, s) for s in strings))
    # Nodes 1 to 4 at 40.40 N and 49.80 to 49.83 E, 5 far away; granularity 100 nanodegrees.
    ids = [1, 2, 3, 4, 5]
    lats = [404_000_000, 404_000_000, 404_000_000, 404_000_000, 410_000_000]
    lons = [498_000_000, 498_100_000, 498_200_000, 498_300_000, 505_000_000]
    dense = packed(1, deltas(ids), signed=True) + packed(8, deltas(lats), signed=True) + packed(9, deltas(lons), signed=True)
    nodes_block = table + field_bytes(2, field_bytes(2, dense))
    # Way 10: a residential street over nodes 1-2-3; way 11: a motorway 3-4; way 12: a
    # pedestrian area (dropped by the filter); way 13: a residential street far away, 4-5.
    def way(wid, refs, tags):
        keys = [strings.index(k) for k, _ in tags]
        vals = [strings.index(v) for _, v in tags]
        return field_bytes(3, field_varint(1, wid) + packed(2, keys) + packed(3, vals) + packed(8, deltas(refs), signed=True))
    ways_block = table + field_bytes(2, way(10, [1, 2, 3], [(b"highway", b"residential"), (b"name", b"Test street")])
                                     + way(11, [3, 4], [(b"highway", b"motorway")])
                                     + way(12, [1, 2], [(b"highway", b"residential"), (b"area", b"yes")])
                                     + way(13, [5, 4], [(b"highway", b"residential")]))
    path.write_bytes(blob("OSMHeader", header) + blob("OSMData", nodes_block) + blob("OSMData", ways_block))


class PbfReader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.osm.pbf"
        pbf_file(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_header_nodes_and_ways(self):
        kinds = [kind for kind, _ in osm_pbf.blobs(self.path)]
        self.assertEqual(kinds, ["OSMHeader", "OSMData", "OSMData"])
        blobs = list(osm_pbf.blobs(self.path))
        info = osm_pbf.header(blobs[0][1])
        self.assertEqual(info["timestamp"], "2025-10-24T21:00:00Z")
        self.assertEqual(info["source"], "test extract")
        nodes = list(osm_pbf.nodes(blobs[1][1]))
        self.assertEqual([n[0] for n in nodes], [1, 2, 3, 4, 5])
        self.assertAlmostEqual(nodes[1][1], 40.4, places=7)
        self.assertAlmostEqual(nodes[1][2], 49.81, places=7)
        ways = list(osm_pbf.ways(blobs[2][1], keep=lambda tags: True))
        self.assertEqual([(w[0], w[2]) for w in ways], [(10, [1, 2, 3]), (11, [3, 4]), (12, [1, 2]), (13, [5, 4])])
        self.assertEqual(ways[0][1], {"highway": "residential", "name": "Test street"})

    def test_extract_keeps_ways_touching_the_box_and_their_nearby_nodes(self):
        answer = osm_pbf.extract(self.path, "40.39,49.79,40.41,49.85",
                                 keep=lambda tags: "highway" in tags and tags.get("area") != "yes", say=lambda *a: None)
        ways = [e for e in answer["elements"] if e["type"] == "way"]
        nodes = [e for e in answer["elements"] if e["type"] == "node"]
        self.assertEqual([w["id"] for w in ways], [10, 11, 13])            # 12 is an area; 13 touches the box at node 4
        self.assertEqual([n["id"] for n in nodes], [1, 2, 3, 4])          # node 5 is beyond the margin
        self.assertEqual(ways[2]["nodes"], [5, 4])                        # the way keeps its ids all the same
        self.assertEqual(nodes[0], {"type": "node", "id": 1, "lat": 40.4, "lon": 49.8})
        self.assertEqual(answer["osm3s"]["timestamp_osm_base"], "2025-10-24T21:00:00Z")
        self.assertEqual(answer["elements"], sorted(answer["elements"], key=lambda e: (e["type"] != "way", e["id"])))
