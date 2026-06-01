# Coordinate Transforms

`mudm.transforms` gives you the 3D coordinate machinery for microscopy data: a
4x4 affine transform, a helper that applies it to any geometry (GeoJSON *and*
muDM 3D types), and a voxel-to-physical coordinate system for moving between
pixel-space and real-world units like micrometers.

Everything on this page is part of the public API, so you can import it straight
from the package:

```python
from mudm import (
    AffineTransform,
    VoxelCoordinateSystem,
    apply_transform,
    translate_geometry,
    voxel_to_physical,
    physical_to_voxel,
)
```

## When to reach for this

| Goal | Tool |
| --- | --- |
| Convert geometry from **voxel/pixel** coordinates to **physical** units (or back) | [`VoxelCoordinateSystem`](#voxelcoordinatesystem) + [`voxel_to_physical` / `physical_to_voxel`](#converting-between-voxel-and-physical-coordinates) |
| **Move, scale, or rotate** geometry in 3D | [`AffineTransform`](#affinetransform) + [`apply_transform`](#applying-a-transform) |
| Shift something by a fixed offset | [`translate_geometry`](#translating-by-an-offset) |

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

## AffineTransform

`AffineTransform` is a 4x4 affine matrix stored in **row-major** order. The top
3x3 block holds rotation and scale; the rightmost column holds the translation:

```text
[[r00, r01, r02, tx],
 [r10, r11, r12, ty],
 [r20, r21, r22, tz],
 [0,   0,   0,   1 ]]
```

A new point `(x, y, z)` is computed as:

```text
nx = r00*x + r01*y + r02*z + tx
ny = r10*x + r11*y + r12*z + ty
nz = r20*x + r21*y + r22*z + tz
```

The matrix must be exactly 4 rows by 4 columns, and its bottom row must be
`[0, 0, 0, 1]` — validation rejects anything else.

### Identity, translation, and scale

```python
from mudm import AffineTransform

# Identity — leaves coordinates unchanged.
identity = AffineTransform(
    type="affine",
    matrix=[
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ],
)

# Translation by (10, 20, 30) — the offsets live in the last column.
translation = AffineTransform(
    type="affine",
    matrix=[
        [1, 0, 0, 10],
        [0, 1, 0, 20],
        [0, 0, 1, 30],
        [0, 0, 0, 1],
    ],
)

# Scale by (2, 3, 4) — the factors live on the diagonal.
scale = AffineTransform(
    type="affine",
    matrix=[
        [2, 0, 0, 0],
        [0, 3, 0, 0],
        [0, 0, 4, 0],
        [0, 0, 0, 1],
    ],
)

assert translation.matrix[0][3] == 10.0
assert scale.matrix[2][2] == 4.0
```

### Validation: must be 4x4 with a `[0, 0, 0, 1]` bottom row

A matrix with the wrong shape is rejected:

```python
from pydantic import ValidationError
from mudm import AffineTransform

try:
    AffineTransform(type="affine", matrix=[[1, 0], [0, 1]])
except ValidationError as exc:
    print("rejected:", exc.errors()[0]["msg"])
    # rejected: Value error, Affine matrix must have 4 rows, got 2
```

So is a 4x4 matrix whose bottom row is not `[0, 0, 0, 1]`. `apply_transform`
only reads the top three rows, so a non-identity bottom row (e.g. a projective
`w`-row) would be silently ignored and produce geometrically wrong results —
validation rejects it up front:

```python
from pydantic import ValidationError
from mudm import AffineTransform

try:
    AffineTransform(
        type="affine",
        matrix=[
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [1, 2, 3, 4],
        ],
    )
except ValidationError as exc:
    print("rejected:", exc.errors()[0]["msg"])
    # rejected: Value error, Affine matrix bottom row must be [0, 0, 0, 1], got [1.0, 2.0, 3.0, 4.0]
```

!!! note "Why 4x4 and not 3x4?"
    Carrying the full homogeneous 4x4 form (including the trailing
    `[0, 0, 0, 1]` row) keeps transforms **composable**: you can multiply two
    matrices to get a single combined transform, and the round-trip through JSON
    is unambiguous. Because the bottom row is always `[0, 0, 0, 1]`, the
    transform stays a true affine (not a projective) map.

### Round-trips through JSON

Because `AffineTransform` is a Pydantic model, it serializes cleanly to the wire
format and back:

=== "Python"

    ```python
    from mudm import AffineTransform

    t = AffineTransform(
        type="affine",
        matrix=[
            [1, 0, 0, 5],
            [0, 1, 0, 10],
            [0, 0, 1, 15],
            [0, 0, 0, 1],
        ],
    )
    data = t.model_dump()
    t2 = AffineTransform.model_validate(data)
    assert t2.matrix[2][3] == 15.0
    ```

=== "JSON"

    ```json
    {
      "type": "affine",
      "matrix": [
        [1.0, 0.0, 0.0, 5.0],
        [0.0, 1.0, 0.0, 10.0],
        [0.0, 0.0, 1.0, 15.0],
        [0.0, 0.0, 0.0, 1.0]
      ]
    }
    ```

## Applying a transform

`apply_transform(geometry, transform)` returns a **new** geometry of the same
type with every coordinate transformed. It works on all GeoJSON geometry types
(`Point`, `MultiPoint`, `LineString`, `MultiLineString`, `Polygon`,
`MultiPolygon`) and on the muDM 3D types `TIN` and `PolyhedralSurface`.

!!! tip "Non-destructive"
    The input geometry is never mutated — you always get a fresh object back, so
    it is safe to keep the original around.

### Transforming a Point

```python
from mudm import AffineTransform, apply_transform
from geojson_pydantic import Point

p = Point(type="Point", coordinates=(10.0, 20.0, 30.0))
t = AffineTransform(
    type="affine",
    matrix=[
        [1, 0, 0, 5],
        [0, 1, 0, 10],
        [0, 0, 1, 15],
        [0, 0, 0, 1],
    ],
)
moved = apply_transform(p, t)
assert moved.coordinates[0] == 15.0   # 10 + 5
assert moved.coordinates[1] == 30.0   # 20 + 10
assert moved.coordinates[2] == 45.0   # 30 + 15
```

A scale transform multiplies each axis:

```python
from mudm import AffineTransform, apply_transform
from geojson_pydantic import Point

p = Point(type="Point", coordinates=(10.0, 20.0, 30.0))
scale = AffineTransform(
    type="affine",
    matrix=[
        [2, 0, 0, 0],
        [0, 3, 0, 0],
        [0, 0, 4, 0],
        [0, 0, 0, 1],
    ],
)
scaled = apply_transform(p, scale)
assert tuple(scaled.coordinates) == (20.0, 60.0, 120.0)
```

### Transforming a LineString

The same call walks the nested coordinate arrays for you:

```python
from mudm import AffineTransform, apply_transform
from geojson_pydantic import LineString

ls = LineString(type="LineString", coordinates=[(0, 0, 0), (10, 10, 10)])
t = AffineTransform(
    type="affine",
    matrix=[
        [1, 0, 0, 100],
        [0, 1, 0, 200],
        [0, 0, 1, 300],
        [0, 0, 0, 1],
    ],
)
result = apply_transform(ls, t)
assert result.coordinates[0][0] == 100.0   # first vertex, x
assert result.coordinates[1][2] == 310.0   # second vertex, z
```

### Transforming a TIN (or PolyhedralSurface)

muDM's 3D surface types nest one level deeper than GeoJSON polygons, but
`apply_transform` handles them identically and returns the same type:

```python
from mudm import AffineTransform, apply_transform, TIN

tin = TIN(
    type="TIN",
    coordinates=[
        [[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 0)]],
    ],
)
t = AffineTransform(
    type="affine",
    matrix=[
        [1, 0, 0, 10],
        [0, 1, 0, 20],
        [0, 0, 1, 30],
        [0, 0, 0, 1],
    ],
)
result = apply_transform(tin, t)
assert isinstance(result, TIN)
# First vertex of the first triangle, now translated.
assert tuple(result.coordinates[0][0][0]) == (10.0, 20.0, 30.0)
```

`PolyhedralSurface` works exactly the same way — pass one in, get one back. See
the [Specification](../specification.md) for how `TIN` and `PolyhedralSurface`
coordinates are structured.

## Translating by an offset

`translate_geometry(geometry, dx, dy, dz)` is a convenience wrapper: it builds a
translation `AffineTransform` for you and calls `apply_transform`. Reach for it
when all you need is a fixed shift.

```python
from mudm import translate_geometry
from geojson_pydantic import Point

p = Point(type="Point", coordinates=(1.0, 2.0, 3.0))
moved = translate_geometry(p, 10, 20, 30)
assert tuple(moved.coordinates) == (11.0, 22.0, 33.0)

# A zero translation is the identity.
same = translate_geometry(p, 0, 0, 0)
assert tuple(same.coordinates) == (1.0, 2.0, 3.0)
```

It works on 3D types too:

```python
from mudm import translate_geometry, TIN

tin = TIN(
    type="TIN",
    coordinates=[
        [[(0, 0, 0), (1, 0, 0), (0.5, 1, 0), (0, 0, 0)]],
    ],
)
result = translate_geometry(tin, 100, 200, 300)
assert tuple(result.coordinates[0][0][0]) == (100.0, 200.0, 300.0)
```

## VoxelCoordinateSystem

Microscopy data starts life in **voxel** (pixel) coordinates, but analysis and
visualization usually need **physical** coordinates in real units. A
`VoxelCoordinateSystem` records the mapping between the two.

The conversion is a per-axis affine relation:

```text
physical = voxel * resolution + origin
```

### Fields

| Field        | Type          | Description                                                   |
|--------------|---------------|---------------------------------------------------------------|
| `axes`       | `list[str]`   | Axis names, e.g. `["x", "y", "z"]`.                          |
| `units`      | `list[str]`   | Physical unit per axis, e.g. `["micrometer", ...]`.          |
| `resolution` | `list[float]` | Physical size of one voxel along each axis.                   |
| `origin`     | `list[float]` | Physical coordinate of the voxel-space origin. Defaults to `[0.0, 0.0, 0.0]`. |

```python
from mudm import VoxelCoordinateSystem

vcs = VoxelCoordinateSystem(
    axes=["x", "y", "z"],
    units=["micrometer", "micrometer", "micrometer"],
    resolution=[0.4, 0.4, 0.05],
    origin=[10.0, 20.0, 30.0],
)
assert vcs.resolution == [0.4, 0.4, 0.05]

# origin is optional and defaults to the world origin.
default_origin = VoxelCoordinateSystem(
    axes=["x", "y", "z"],
    units=["micrometer", "micrometer", "micrometer"],
    resolution=[1.0, 1.0, 1.0],
)
assert default_origin.origin == [0.0, 0.0, 0.0]
```

!!! note "Anisotropic voxels are normal"
    The example above uses `0.4 µm` laterally and `0.05 µm` axially — typical for
    confocal stacks. Per-axis `resolution` is exactly what you need to handle
    this anisotropy correctly.

### Converting between voxel and physical coordinates

`voxel_to_physical(coords, vcs)` and `physical_to_voxel(coords, vcs)` apply the
relation above and its inverse. Both take and return an `(x, y, z)` tuple.

```python
from mudm import VoxelCoordinateSystem, voxel_to_physical, physical_to_voxel

vcs = VoxelCoordinateSystem(
    axes=["x", "y", "z"],
    units=["micrometer", "micrometer", "micrometer"],
    resolution=[0.4, 0.4, 0.05],
    origin=[10.0, 20.0, 30.0],
)

# voxel -> physical: voxel * resolution + origin
phys = voxel_to_physical((100.0, 200.0, 300.0), vcs)
assert phys == (100.0 * 0.4 + 10.0, 200.0 * 0.4 + 20.0, 300.0 * 0.05 + 30.0)
# -> (50.0, 100.0, 45.0)

# physical -> voxel: (physical - origin) / resolution
vox = physical_to_voxel((50.0, 100.0, 45.0), vcs)
assert vox == ((50.0 - 10.0) / 0.4, (100.0 - 20.0) / 0.4, (45.0 - 30.0) / 0.05)
# -> (100.0, 200.0, 300.0)
```

### Round-trip

The two functions are exact inverses (modulo floating-point precision):

```python
from mudm import VoxelCoordinateSystem, voxel_to_physical, physical_to_voxel

vcs = VoxelCoordinateSystem(
    axes=["x", "y", "z"],
    units=["micrometer", "micrometer", "micrometer"],
    resolution=[0.4, 0.4, 0.05],
    origin=[10.0, 20.0, 30.0],
)

original = (100.0, 200.0, 300.0)
back = physical_to_voxel(voxel_to_physical(original, vcs), vcs)
assert back == original
```

## How this fits the multiscale model

`AffineTransform` is not a standalone class — it subclasses
`CoordinateTransformation`, the OME-harmonized base type defined in
`mudm.tilemodel`. That makes it a drop-in alongside the other transform types
that live there:

| Type              | `type` value    | Payload                | Use                                  |
|-------------------|-----------------|------------------------|--------------------------------------|
| `Identity`        | `"identity"`    | (none)                 | No-op transform.                     |
| `Translation`     | `"translation"` | `translation: list`    | Per-axis offset vector.              |
| `Scale`           | `"scale"`       | `scale: list`          | Per-axis scale vector.               |
| `AffineTransform` | `"affine"`      | `matrix: 4x4`          | Full rotation + scale + translation. |

A `Multiscale` object records the mapping from each resolution level to
physical space. Its serialized `coordinateTransformations` list is the OME
wire form, which accepts **`identity`, `translation`, and `scale`** — these
round-trip losslessly through `model_dump()` / `model_validate()`:

```python
from mudm.tilemodel import Multiscale, Axis, Scale

ms = Multiscale(
    axes=[
        Axis(name="x", type="space", unit="micrometer"),
        Axis(name="y", type="space", unit="micrometer"),
        Axis(name="z", type="space", unit="micrometer"),
    ],
    coordinateTransformations=[Scale(scale=[0.4, 0.4, 0.05])],
)
reloaded = Multiscale.model_validate(ms.model_dump())
assert reloaded.coordinateTransformations[0].type == "scale"
assert reloaded.coordinateTransformations[0].scale == [0.4, 0.4, 0.05]
```

`AffineTransform` shares the `CoordinateTransformation` base but is **not** a
member of the serialized `coordinateTransformations` list (the TileJSON wire
form admits only the three types above). Use it to *apply* a full affine to
geometry via [`apply_transform`](#applying-a-transform); to record a single
affine in multiscale metadata, use `Multiscale.transformationMatrix`.

```python
from mudm import AffineTransform
from mudm.tilemodel import CoordinateTransformation

affine = AffineTransform(matrix=[
    [0.4, 0, 0, 0],
    [0, 0.4, 0, 0],
    [0, 0, 0.05, 0],
    [0, 0, 0, 1],
])
assert isinstance(affine, CoordinateTransformation)
```

For how this multiscale metadata is carried in tiled pyramids, see
[Tile Metadata](tiles.md). To build the pyramids themselves — running the
tiling engines and writing OME-NGFF — use the **mudm-tools** pipelines:
the [2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/),
[3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/), and
[OME-NGFF](https://novagenresearch.github.io/mudm-tools/guides/ome-ngff/) guides
cover the coordinate-system and multiscale concepts muDM shares with OME-NGFF.

!!! tip "Backwards compatibility"
    A `VoxelCoordinateSystem` and an `AffineTransform` only ever read or produce
    plain coordinate arrays, so the geometries they operate on stay valid
    GeoJSON. Any GeoJSON document is valid muDM, and any muDM document is valid
    GeoJSON — transforms never break that guarantee.

## API reference

::: mudm.transforms.AffineTransform

::: mudm.transforms.VoxelCoordinateSystem

::: mudm.transforms.apply_transform

::: mudm.transforms.translate_geometry

::: mudm.transforms.voxel_to_physical

::: mudm.transforms.physical_to_voxel

## Where to next

- [Tile Metadata](tiles.md) — how multiscale transforms ride along with tiled pyramids.
- [Spatial Layout](layout.md) — bounds and placement helpers that pair with transforms.
- [Specification](../specification.md) — the formal schema for geometry and transform types.
- [Core data-model API](../reference/models.md) — the full Pydantic model reference.
- [mudm-tools docs](https://novagenresearch.github.io/mudm-tools/) — pipelines, tiling engines, and format converters that turn transforms into pyramids and OME-NGFF output.
