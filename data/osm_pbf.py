"""Read OpenStreetMap PBF files with the standard library.

Enough of the format (github.com/openstreetmap/OSM-binary) to cut the ways of one kind
in a box out of a country extract: the file framing, the protobuf wire format, zlib
blobs, the header, dense nodes and ways. Relations and the metadata of each object
(versions, users, timestamps) are skipped.

    answer = extract(path, bbox="39.92,49.37,40.66,50.39",
                     keep=lambda tags: "highway" in tags and tags.get("area") != "yes")

gives a dict in the shape of an Overpass API answer ("elements" of ways with their tags
and node ids, then nodes with coordinates), so code written for Overpass answers can read
it. A way is kept when the tags pass `keep` and at least one of its nodes is in the
box; its nodes are kept out to a margin beyond the box, so a way that runs far outside
the box has node ids without a node, and readers must break the way there."""

import re
import struct
import zlib
from array import array
from datetime import datetime, timezone
from itertools import accumulate

_VARINT = re.compile(rb"[\x80-\xff]*[\x00-\x7f]")


def _uvarint(b):
    """The unsigned value of one varint's bytes."""
    v = 0
    for i, c in enumerate(b):
        v |= (c & 0x7F) << (7 * i)
    return v


def _unsigned(buf):
    """Every unsigned varint packed in buf."""
    return [_uvarint(m) for m in _VARINT.findall(buf)]


def _signed(buf):
    """Every zigzag-coded signed varint packed in buf."""
    return [(v >> 1) ^ -(v & 1) for v in _unsigned(buf)]


def fields(buf):
    """(field number, wire type, value) for each field of a protobuf message: an int for
    varints, the bytes of the value otherwise."""
    i, n = 0, len(buf)
    while i < n:
        shift = key = 0
        while True:
            c = buf[i]
            i += 1
            key |= (c & 0x7F) << shift
            if c < 0x80:
                break
            shift += 7
        number, wire = key >> 3, key & 7
        if wire == 0:
            shift = v = 0
            while True:
                c = buf[i]
                i += 1
                v |= (c & 0x7F) << shift
                if c < 0x80:
                    break
                shift += 7
        elif wire == 2:
            shift = ln = 0
            while True:
                c = buf[i]
                i += 1
                ln |= (c & 0x7F) << shift
                if c < 0x80:
                    break
                shift += 7
            v = buf[i:i + ln]
            i += ln
        elif wire == 1:
            v = buf[i:i + 8]
            i += 8
        elif wire == 5:
            v = buf[i:i + 4]
            i += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        yield number, wire, v


def _packed(values, wire, into, signed=False):
    """Append a repeated varint field to `into`, whether it came packed or one by one."""
    if wire == 2:
        into.extend(_signed(values) if signed else _unsigned(values))
    else:
        into.append(((values >> 1) ^ -(values & 1)) if signed else values)


def blobs(path):
    """(type, decompressed bytes) for every blob in the file: 'OSMHeader' then 'OSMData'."""
    with open(path, "rb") as f:
        while True:
            head = f.read(4)
            if len(head) < 4:
                return
            header = f.read(struct.unpack(">I", head)[0])
            kind, size = None, None
            for number, _, v in fields(header):
                if number == 1:
                    kind = v.decode()
                elif number == 3:
                    size = v
            blob = f.read(size)
            data = None
            for number, _, v in fields(blob):
                if number == 1:
                    data = v
                elif number == 3:
                    data = zlib.decompress(v)
                elif number in (4, 5, 6, 7):
                    raise ValueError("the file uses a compression other than zlib")
            yield kind, data


def header(data):
    """What the header block says: the data's date (osmosis_replication_timestamp, as an
    ISO string), the writing program and source, and the file's own bounding box."""
    out = {}
    for number, _, v in fields(data):
        if number == 1:
            box = {n: (x >> 1) ^ -(x & 1) for n, _, x in fields(v)}
            out["bbox"] = {k: box[n] * 1e-9 for k, n in (("left", 1), ("right", 2), ("top", 3), ("bottom", 4)) if n in box}
        elif number == 16:
            out["writingprogram"] = v.decode()
        elif number == 17:
            out["source"] = v.decode()
        elif number == 32:
            out["timestamp"] = datetime.fromtimestamp(v, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return out


def _block(data):
    """(strings, granularity, lat_offset, lon_offset, [group bytes]) of a primitive block."""
    strings, groups, granularity, lat0, lon0 = [], [], 100, 0, 0
    for number, _, v in fields(data):
        if number == 1:
            strings = [s for n, _, s in fields(v) if n == 1]
        elif number == 2:
            groups.append(v)
        elif number == 17:
            granularity = v
        elif number == 19:
            lat0 = v                                          # int64, not zigzag coded
        elif number == 20:
            lon0 = v
    return strings, granularity, lat0, lon0, groups


def ways(data, keep):
    """(id, tags, node ids) for each way in a data block whose tags pass keep."""
    strings, _, _, _, groups = _block(data)
    text = {}

    def s(k):
        t = text.get(k)
        if t is None:
            t = text[k] = strings[k].decode("utf-8", "replace")
        return t

    for group in groups:
        for number, _, way in fields(group):
            if number != 3:
                continue
            wid, keys, vals, refs = None, [], [], []
            for n, wire, v in fields(way):
                if n == 1:
                    wid = v
                elif n == 2:
                    _packed(v, wire, keys)
                elif n == 3:
                    _packed(v, wire, vals)
                elif n == 8:
                    _packed(v, wire, refs, signed=True)
            tags = {s(k): s(v) for k, v in zip(keys, vals)}
            if keep(tags):
                yield wid, tags, list(accumulate(refs))


def nodes(data):
    """(id, latitude, longitude) for each node in a data block, dense or not."""
    _, granularity, lat0, lon0, groups = _block(data)
    for group in groups:
        for number, _, v in fields(group):
            if number == 2:                                       # dense nodes, delta coded
                ids, lats, lons = [], [], []
                for n, wire, x in fields(v):
                    if n == 1:
                        _packed(x, wire, ids, signed=True)
                    elif n == 8:
                        _packed(x, wire, lats, signed=True)
                    elif n == 9:
                        _packed(x, wire, lons, signed=True)
                for i, lat, lon in zip(accumulate(ids), accumulate(lats), accumulate(lons)):
                    yield i, (lat0 + granularity * lat) * 1e-9, (lon0 + granularity * lon) * 1e-9
            elif number == 1:                                     # a plain node
                nid = lat = lon = None
                for n, _, x in fields(v):
                    if n == 1:
                        nid = (x >> 1) ^ -(x & 1)
                    elif n == 8:
                        lat = (x >> 1) ^ -(x & 1)
                    elif n == 9:
                        lon = (x >> 1) ^ -(x & 1)
                yield nid, (lat0 + granularity * lat) * 1e-9, (lon0 + granularity * lon) * 1e-9


def extract(path, bbox, keep, margin_deg=0.05, say=print):
    """The ways whose tags pass keep with at least one node in bbox ("s,w,n,e"), and the
    nodes of those ways out to margin_deg beyond it, as an Overpass-shaped dict."""
    south, west, north, east = (float(v) for v in bbox.split(","))
    info, kept, needed = {}, [], set()
    for kind, data in blobs(path):                                 # first the ways
        if kind == "OSMHeader":
            info = header(data)
        elif kind == "OSMData":
            for wid, tags, refs in ways(data, keep):
                kept.append((wid, tags, array("q", refs)))
                needed.update(refs)
    say(f"  {len(kept):,} ways pass the filter in the whole file, with {len(needed):,} nodes")
    coords = {}
    s, w, n, e = south - margin_deg, west - margin_deg, north + margin_deg, east + margin_deg
    for kind, data in blobs(path):                                 # then their nodes near the box
        if kind == "OSMData":
            for nid, lat, lon in nodes(data):
                if nid in needed and s <= lat <= n and w <= lon <= e:
                    coords[nid] = (round(lat, 7), round(lon, 7))
    elements, used = [], set()
    for wid, tags, refs in sorted(kept, key=lambda t: t[0]):
        inside = False
        for r in refs:
            c = coords.get(r)
            if c and south <= c[0] <= north and west <= c[1] <= east:
                inside = True
                break
        if inside:
            elements.append({"type": "way", "id": wid, "nodes": refs.tolist(), "tags": tags})
            used.update(r for r in refs if r in coords)
    for nid in sorted(used):
        lat, lon = coords[nid]
        elements.append({"type": "node", "id": nid, "lat": lat, "lon": lon})
    say(f"  {len(elements) - len(used):,} ways touch the box, with {len(used):,} nodes")
    return {
        "version": 0.6,
        "generator": f"data/osm_pbf.py from {info.get('source') or path}",
        "osm3s": {"timestamp_osm_base": info.get("timestamp"), "bbox": bbox,
                  "copyright": "The data included in this document is from www.openstreetmap.org. "
                               "The data is made available under ODbL."},
        "elements": elements,
    }
