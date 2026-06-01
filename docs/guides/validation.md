# Validation

Validate muDM and plain GeoJSON documents with Pydantic, read the errors you get back when something is malformed, and round-trip data to and from JSON. Every example runs top-to-bottom against the current `mudm` using the real public API.

If you are new to the data model, start with the [Getting Started](../getting-started.md) quickstart and the [Specification](../specification.md). For the model classes behind these calls, see the [Core data-model API](../reference/models.md).

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

## The two root validators

muDM gives you two root models, both imported straight from the package:

```python
from mudm import MuDM, GeoJSON
```

| Model     | Accepts                                                       | Use it for                                 |
| --------- | ------------------------------------------------------------- | ------------------------------------------ |
| `MuDM`    | `MuDMFeature`, `MuDMFeatureCollection`, or any geometry type  | Documents using muDM extensions (3D, refs) |
| `GeoJSON` | `Feature`, `FeatureCollection`, or any geometry type          | Plain GeoJSON you want to check is valid   |

Both are Pydantic `RootModel`s, so the entry point is always `model_validate(...)` for Python objects (`dict`/`list`) and `model_validate_json(...)` for raw JSON text.

!!! note "Backwards compatibility, both ways"
    Any valid GeoJSON document is also a valid muDM document, and any muDM document is valid GeoJSON. `MuDM` simply adds optional fields (like `parentId` and `featureClass`) and extra geometry types (`TIN`, `PolyhedralSurface`) on top of the GeoJSON spec. See the [Specification](../specification.md) for the full list.

## Validating a muDM document

A muDM document can arrive as a parsed Python object or as raw JSON text. Use `model_validate` for the former and `model_validate_json` for the latter.

=== "Python"

    ```python
    from mudm import MuDM

    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [10.0, 20.0]},
                "properties": {"name": "nucleus-1"},
                "featureClass": "nucleus",
                "parentId": "cell-7",
            }
        ],
    }

    m = MuDM.model_validate(doc)

    print(type(m.root).__name__)              # MuDMFeatureCollection
    print(m.root.features[0].featureClass)    # nucleus
    print(m.root.features[0].parentId)        # cell-7
    ```

    `MuDM` is a root model, so the parsed object lives on `m.root`. Pydantic picks the right member of the union for you: because the document has `"type": "FeatureCollection"` and the features carry muDM fields, it resolves to a `MuDMFeatureCollection`.

=== "JSON"

    When your data arrives as text (a file, an HTTP body, a message queue), skip the manual `json.loads` and let Pydantic parse and validate in one step:

    ```python
    import json
    from mudm import MuDM

    raw = json.dumps({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [10.0, 20.0]},
                "properties": {"name": "nucleus-1"},
                "featureClass": "nucleus",
                "parentId": "cell-7",
            }
        ],
    })

    m = MuDM.model_validate_json(raw)
    print(type(m.root).__name__)  # MuDMFeatureCollection
    ```

!!! tip
    `model_validate_json` is both faster and stricter than `json.loads` followed by `model_validate`, because Pydantic parses directly into the model. Prefer it whenever you already hold JSON text.

## Validating plain GeoJSON

If you only want to confirm that a document is well-formed GeoJSON, use `GeoJSON`. It accepts a bare geometry, a `Feature`, or a `FeatureCollection`:

```python
from mudm import GeoJSON

# A bare geometry is valid GeoJSON (and valid muDM)
g = GeoJSON.model_validate({"type": "Point", "coordinates": [1.0, 2.0, 3.0]})
print(type(g.root).__name__)  # Point

# A full FeatureCollection
fc = GeoJSON.model_validate({
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            "properties": {},
        }
    ],
})
print(type(fc.root).__name__)  # FeatureCollection
```

Because every GeoJSON document is also valid muDM, the same input passes `MuDM.model_validate` too. The difference is what you get back: `GeoJSON` yields a plain `Feature`/`FeatureCollection`, while `MuDM` yields the extended `MuDMFeature`/`MuDMFeatureCollection` that can also hold muDM-only fields.

## Validating individual pieces

You don't have to go through a root model. Every building block is its own importable, validatable model. This is handy in tests and when you build documents incrementally.

```python
from mudm import (
    MuDMFeature,
    MuDMFeatureCollection,
    TIN,
    PolyhedralSurface,
)
```

### A single feature

```python
from mudm import MuDMFeature

f = MuDMFeature.model_validate({
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [5.0, 6.0]},
    "properties": {"intensity": 0.8},
    "ref": "annotation-3",
    "featureClass": "punctum",
})
print(f.ref)           # annotation-3
print(f.featureClass)  # punctum
```

A feature with no geometry is valid (`geometry` may be `None`):

```python
empty = MuDMFeature.model_validate({
    "type": "Feature",
    "geometry": None,
    "properties": None,
})
print(empty.geometry)  # None
```

### A feature collection

```python
from mudm import MuDMFeatureCollection

fc = MuDMFeatureCollection.model_validate({
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {},
            "featureClass": "cell",
        }
    ],
    "id": "field-of-view-1",
})
print(fc.id)             # field-of-view-1
print(len(fc.features))  # 1
```

### Geometry types, including 3D

The standard GeoJSON geometries (`Point`, `MultiPoint`, `LineString`, `MultiLineString`, `Polygon`, `MultiPolygon`, `GeometryCollection`) are supported, plus two muDM 3D mesh types from ISO 19107: `TIN` and `PolyhedralSurface`.

A **TIN** (Triangulated Irregular Network) is a triangle mesh. Each face is a single closed ring of exactly 4 positions (3 corners plus the repeated first corner):

```python
from mudm import TIN

tin = TIN.model_validate({
    "type": "TIN",
    "coordinates": [
        [[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]],   # one triangle
        [[[1, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]]],   # another triangle
    ],
})
print(tin.bbox3d())      # (0.0, 0.0, 0.0, 1.0, 1.0, 0.0)
print(tin.centroid3d())  # (0.5, 0.5, 0.0) — centroid of unique vertices
```

A **PolyhedralSurface** is a mesh of arbitrary polygonal faces; each face has the same shape as a `Polygon` (a list of linear rings):

```python
from mudm import PolyhedralSurface

surf = PolyhedralSurface.model_validate({
    "type": "PolyhedralSurface",
    "coordinates": [
        [[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]]],  # one quad face
    ],
})
print(surf.bbox3d())  # (0.0, 0.0, 0.0, 1.0, 1.0, 0.0)
```

!!! note "Tiled geometry"
    Both `TIN` and `PolyhedralSurface` may carry empty `coordinates` if they instead reference external tiles via the `tiles` field. A mesh must have *either* `coordinates` or `tiles`. For building and consuming tiled meshes, see the [Tile Metadata](tiles.md) guide and the [3D tiling guide](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/) in the mudm-tools docs.

## Handling validation failures

When input does not match the model, Pydantic raises `pydantic.ValidationError`. Catch it and inspect `.errors()` to find out exactly what went wrong.

```python
from pydantic import ValidationError
```

### A malformed TIN face

Each TIN face must be a single ring of exactly 4 positions. Here a face has 5:

```python
from mudm import TIN
from pydantic import ValidationError

try:
    TIN.model_validate({
        "type": "TIN",
        "coordinates": [
            [[[0, 0, 0], [1, 0, 0], [0, 1, 0], [2, 2, 2], [0, 0, 0]]]
        ],
    })
except ValidationError as exc:
    for err in exc.errors():
        print(err["type"], "->", err["msg"])
# value_error -> Value error, TIN face 0 ring must have exactly 4 positions (closed triangle), got 5
```

A TIN with neither `coordinates` nor `tiles` fails the model-level check:

```python
try:
    TIN.model_validate({"type": "TIN"})
except ValidationError as exc:
    print(exc.errors()[0]["msg"])
# Value error, TIN requires either coordinates or tiles
```

### A non-4x4 affine matrix

The [coordinate transforms](transforms.md) carry an `AffineTransform` whose `matrix` must be exactly 4 rows of 4 columns:

```python
from mudm import AffineTransform
from pydantic import ValidationError

try:
    AffineTransform(matrix=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])  # 3 rows
except ValidationError as exc:
    print(exc.errors()[0]["msg"])
# Value error, Affine matrix must have 4 rows, got 3
```

### Reading `exc.errors()`

`ValidationError.errors()` returns a list of dicts. The fields you will use most are:

| Key     | Meaning                                                     |
| ------- | ----------------------------------------------------------- |
| `loc`   | Tuple path to the offending value inside the document       |
| `msg`   | Human-readable explanation                                  |
| `type`  | Machine-readable error code (e.g. `too_short`, `int_type`)  |
| `input` | The value that failed                                       |

```python
from mudm import TIN
from pydantic import ValidationError

try:
    # A triangle ring with only 3 positions (a GeoJSON ring needs at least 4)
    TIN.model_validate({
        "type": "TIN",
        "coordinates": [[[[0, 0, 0], [1, 0, 0], [0, 1, 0]]]],
    })
except ValidationError as exc:
    print("count:", exc.error_count())  # 1
    err = exc.errors()[0]
    print("loc: ", err["loc"])   # ('coordinates', 0, 0)
    print("type:", err["type"])  # too_short
    print("msg: ", err["msg"])   # List should have at least 4 items after validation, not 3
```

The `loc` path `('coordinates', 0, 0)` reads as "in `coordinates`, face index 0, ring index 0" — exactly where you need to look to fix the data.

!!! tip "Validation order"
    Field-shape rules from the underlying GeoJSON types (like "a ring needs at least 4 points") fire *before* muDM's custom checks. So a 3-point ring trips GeoJSON's `too_short` rule, while a 5-point ring passes that and then trips muDM's "exactly 4 positions" rule. Read the `type` code to tell which layer rejected your input.

## Strict typing of identifiers

A few identifier fields are deliberately strict. `ref`, `parentId`, and the collection `id` accept only a real string or a real integer — Pydantic will not silently coerce a float or a numeric string into one. This is enforced with `StrictStr` / `StrictInt`.

```python
from mudm import MuDMFeature
from pydantic import ValidationError

# Integers and strings are both fine and keep their type:
f = MuDMFeature.model_validate({
    "type": "Feature", "geometry": None, "properties": None, "ref": 42,
})
print(f.ref, type(f.ref).__name__)  # 42 int

# A float for an identifier is rejected rather than truncated:
try:
    MuDMFeature.model_validate({
        "type": "Feature", "geometry": None, "properties": None, "ref": 3.5,
    })
except ValidationError as exc:
    print(exc.errors()[0]["type"])  # int_type
```

This protects identifier integrity: `7` and `"7"` stay distinct, and `3.5` can never quietly become `3`.

## Round-trip and serialization

Once you have a validated model, turn it back into a dict with `model_dump()` or into JSON text with `model_dump_json()`. muDM uses camelCase field names on the wire (`parentId`, `featureClass`, `mudmId`, ...), and these are preserved on dump.

=== "Python"

    ```python
    from mudm import MuDM

    m = MuDM.model_validate({
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
                "properties": {"name": "x"},
                "featureClass": "cell",
            }
        ],
    })

    as_dict = m.model_dump()        # nested dict
    as_json = m.model_dump_json()   # JSON string
    print(type(as_dict).__name__)   # dict
    ```

=== "JSON"

    A full round-trip should give back an equivalent document:

    ```python
    restored = MuDM.model_validate(m.model_dump())
    assert restored == m
    ```

### Trimming the output

muDM models carry many optional fields that default to `None`. By default these appear in the output as `null`. Two arguments keep your JSON lean:

| Argument             | Effect                                                     |
| -------------------- | ---------------------------------------------------------- |
| `exclude_none=True`  | Drop every key whose value is `None`                       |
| `exclude_unset=True` | Drop every key you never explicitly set (keeps it minimal) |

```python
# Keep only the fields that actually carry a value:
print(m.model_dump_json(exclude_none=True))
# {"type":"FeatureCollection","features":[{"type":"Feature",
#   "geometry":{"type":"Point","coordinates":[1.0,2.0]},
#   "properties":{"name":"x"},"featureClass":"cell"}]}
```

!!! tip "Which one should I use?"
    Use `exclude_none=True` when you want a clean wire format that drops empty metadata. Use `exclude_unset=True` when you want to echo back *only* what the caller provided, without filling in defaults. They can be combined.

## Where to next

- [Getting Started](../getting-started.md) — build your first muDM document.
- [Specification](../specification.md) — the full field reference and the GeoJSON compatibility guarantees.
- [Coordinate Transforms](transforms.md) — `AffineTransform`, voxel/physical conversions, and 3D geometry transforms.
- [Tile Metadata](tiles.md) — TileJSON and the tile model behind tiled meshes.
- [Core data-model API](../reference/models.md) — the model classes behind these validators.
- [mudm-tools documentation](https://novagenresearch.github.io/mudm-tools/) — tiling pipelines, format converters, and visualization for muDM data.
