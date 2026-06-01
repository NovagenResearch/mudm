# Spatial Layout

`mudm.layout` arranges the features of a collection so they sit side-by-side without overlapping — perfect for previewing or exporting many objects (cells, neurons, regions) together instead of stacking them on top of each other at their original coordinates.

Layout never changes the *shape* of a feature. It only translates geometries in X/Y/Z. Because muDM geometries are GeoJSON-compatible, a laid-out collection is still valid GeoJSON and still valid muDM — backwards compatibility holds end to end.

## When to use this

Microscopy features are usually stored at their acquired coordinates, so many of them overlap when rendered together (every cell segmented from one field of view shares the same origin region, for example). Layout spreads them apart in a row or on a grid so you can:

- preview a whole collection in a viewer without objects colliding,
- export an arranged scene to glTF, Neuroglancer, or Arrow/Parquet,
- build figure-ready "contact sheets" of many spatial objects.

The two building blocks are:

- [`compute_collection_offsets`](#mudm.layout.compute_collection_offsets) — figures out the `(dx, dy, dz)` translation for each feature *without* touching geometry.
- [`apply_layout`](#mudm.layout.apply_layout) — runs the same computation and returns a **new** collection with the geometries actually translated. The original is left untouched.

Both rely on [`geometry_bounds`](#mudm.layout.geometry_bounds) to measure each feature.

!!! note "Layout vs. tiling"
    Layout is a lightweight, in-memory rearrangement for *viewing* moderate collections. For multi-resolution tile pyramids over large datasets — and for turning a laid-out scene into glTF, Neuroglancer, or Parquet — use the processing pipelines in the separate `mudm-tools` package. See [3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/) and [GeoParquet & glTF](https://novagenresearch.github.io/mudm-tools/guides/geoparquet-gltf/).

## The public surface

| Symbol | Import | Returns |
| --- | --- | --- |
| [`geometry_bounds`](#mudm.layout.geometry_bounds) | `from mudm import geometry_bounds` | 3D bounding box, or `None` |
| [`apply_layout`](#mudm.layout.apply_layout) | `from mudm import apply_layout` | a new `MuDMFeatureCollection` |
| [`compute_collection_offsets`](#mudm.layout.compute_collection_offsets) | `from mudm.layout import compute_collection_offsets` | `list[(dx, dy, dz)]` |

!!! note "`compute_collection_offsets` lives in the submodule"
    `geometry_bounds` and `apply_layout` are part of the top-level public API (`from mudm import ...`). `compute_collection_offsets` is imported from the submodule: `from mudm.layout import compute_collection_offsets`.

## Measuring a feature: `geometry_bounds`

`geometry_bounds(geom)` returns a 3D bounding box in OGC/GeoJSON ordering:

```text
(xmin, ymin, zmin, xmax, ymax, zmax)
```

It returns `None` for `None` or empty geometry. For muDM 3D surface types (`TIN`, `PolyhedralSurface`) it uses their `bbox3d()` method; for ordinary GeoJSON geometries it recursively walks the nested coordinate arrays. Missing Y or Z components default to `0.0`.

```python
from geojson_pydantic import Point, Polygon
from mudm import TIN, geometry_bounds

# A 3D point — min == max on every axis
geometry_bounds(Point(type="Point", coordinates=(1.0, 2.0, 3.0)))
# -> (1.0, 2.0, 3.0, 1.0, 2.0, 3.0)

# A 2D polygon — Z defaults to 0.0
geometry_bounds(
    Polygon(type="Polygon", coordinates=[[(0, 0), (10, 0), (10, 5), (0, 5), (0, 0)]])
)
# -> (0.0, 0.0, 0.0, 10.0, 5.0, 0.0)

# A 3D TIN — real Z extent
tin = TIN(type="TIN", coordinates=[[[(0, 0, 0), (10, 0, 0), (5, 10, 5), (0, 0, 0)]]])
geometry_bounds(tin)
# -> (0.0, 0.0, 0.0, 10.0, 10.0, 5.0)

geometry_bounds(None)  # -> None
```

## Computing offsets: `compute_collection_offsets`

`compute_collection_offsets(features, spacing=None, grid_max_x=None, grid_max_y=None, grid_max_z=None)` returns a list of `(dx, dy, dz)` tuples, one per feature, in source coordinates. It modifies nothing — it just tells you where each feature *would* move.

Two invariants always hold:

- **The first feature stays put.** Its offset is always `(0.0, 0.0, 0.0)`; every other feature is placed relative to it.
- **No arguments means no movement.** With `spacing=None` and no grid parameters, every offset is zero — coordinates are kept exactly as-is.

```python
from mudm import TIN
from mudm.model import MuDMFeature
from mudm.layout import compute_collection_offsets


def tin_at(x_start, x_end):
    """A small TIN spanning x_start..x_end along X."""
    mid = (x_start + x_end) / 2
    return TIN(
        type="TIN",
        coordinates=[[[(x_start, 0, 0), (x_end, 0, 0), (mid, 10, 5), (x_start, 0, 0)]]],
    )


features = [
    MuDMFeature(type="Feature", geometry=tin_at(0, 100), properties=None),
    MuDMFeature(type="Feature", geometry=tin_at(0, 80), properties=None),
]

# Default: no layout requested -> everything stays where it is
compute_collection_offsets(features)
# -> [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]
```

### The `spacing` argument

`spacing` controls the gap between features:

| `spacing` value | Behavior |
| --- | --- |
| `None` (default) | No layout — all offsets zero (unless a grid is requested). |
| `0.0` | Auto gap: 20% of the largest feature extent. |
| `> 0` | Fixed gap (row) or fixed center-to-center cell size (grid). |

## Row layout (side-by-side along X)

When you pass `spacing` (and no `grid_max_*`), features are laid out in a single row along the X axis. Each feature is shifted so its `xmin` lands at the running cursor plus the gap; the cursor then advances to that feature's new `xmax`.

With `spacing=0.0`, the gap is auto-computed as 20% of the widest feature:

```python
# spacing=0.0 -> auto gap; second feature is pushed past the first's xmax (100)
offsets = compute_collection_offsets(features, spacing=0.0)
# -> [(0.0, 0.0, 0.0), (120.0, 0.0, 0.0)]
# offsets[1][0] > 100.0   (only X moves; dy == dz == 0)
```

With a positive `spacing`, the gap is exact. Here the second feature's `xmin` (originally `0`) is placed at the first feature's `xmax` (`100`) plus the gap (`50`):

```python
offsets = compute_collection_offsets(features, spacing=50.0)
# -> [(0.0, 0.0, 0.0), (150.0, 0.0, 0.0)]
```

## Grid layout (wraps X → Y → Z)

Pass any of `grid_max_x`, `grid_max_y`, `grid_max_z` to switch to grid layout. These are **cell counts per axis**, not sizes. Features fill the grid in order, wrapping from columns (X) to rows (Y) to layers (Z):

- `col = i % grid_max_x`
- `row = (i // grid_max_x) % grid_max_y`
- `layer = i // (grid_max_x * grid_max_y)`

Axes you leave as `None` are unconstrained: rows and layers expand as needed to hold every feature, so a grid with only `grid_max_x` set can never overflow.

Features are placed by **center**: each feature's bounding-box center is moved to the target cell center, relative to feature 0's center.

### Cell size

| `spacing` | Cell size (center-to-center) |
| --- | --- |
| `> 0` | Fixed: `spacing` on every axis, regardless of feature extent. |
| `<= 0` (e.g. `0.0`) | Auto: per-axis `max extent + 20% gap` of the largest feature. |

```python
from mudm.model import MuDMFeature
from mudm.layout import compute_collection_offsets

# Four identical TINs, 2 columns -> wraps into 2 rows
feats = [MuDMFeature(type="Feature", geometry=tin_at(0, 100), properties=None)
         for _ in range(4)]

compute_collection_offsets(feats, spacing=10.0, grid_max_x=2)
# -> [(0.0, 0.0, 0.0),    # feature 0: reference, no move
#     (10.0, 0.0, 0.0),   # feature 1: col 1, same row  -> +X
#     (0.0, 10.0, 0.0),   # feature 2: col 0, row 1      -> +Y
#     (10.0, 10.0, 0.0)]  # feature 3: col 1, row 1      -> +X, +Y
```

Add `grid_max_y` to cap rows and force wrapping into Z layers:

```python
# 5 features in a 2x2 grid -> the 5th wraps to layer 1 (col 0, row 0, +Z)
feats = [MuDMFeature(type="Feature", geometry=tin_at(0, 100), properties=None)
         for _ in range(5)]
offsets = compute_collection_offsets(feats, spacing=10.0, grid_max_x=2, grid_max_y=2)
# offsets[4] -> (0.0, 0.0, 10.0)   (dx == 0, dy == 0, dz > 0)
```

### Grid capacity

When every axis is constrained, the grid has a fixed capacity of `grid_max_x * grid_max_y * grid_max_z` cells. Exceeding it raises `ValueError`:

```python
feats = [MuDMFeature(type="Feature", geometry=tin_at(0, 100), properties=None)
         for _ in range(10)]

compute_collection_offsets(
    feats, spacing=10.0, grid_max_x=2, grid_max_y=2, grid_max_z=2,
)
# ValueError: Cannot fit 10 features in grid (2 cols x 2 rows x 2 layers = 8 cells)...
```

!!! tip "Avoiding overflow"
    Leave at least one axis unconstrained (typically `grid_max_z=None`) and the layout can always grow to hold every feature. Constrain all three only when you deliberately want a hard cap.

## Applying the layout: `apply_layout`

`apply_layout(collection, spacing=None, grid_max_x=None, grid_max_y=None, grid_max_z=None)` runs `compute_collection_offsets` and returns a **new** `MuDMFeatureCollection` with each geometry translated by its offset. The input collection is never mutated.

```python
from mudm import MuDMFeatureCollection, apply_layout
from mudm.model import MuDMFeature

coll = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(type="Feature", geometry=tin_at(0, 100), properties={"id": "a"}),
        MuDMFeature(type="Feature", geometry=tin_at(0, 80), properties={"id": "b"}),
    ],
)

result = apply_layout(coll, spacing=50.0)

# First feature unchanged; second feature's xmin vertex shifted to 100 + 50 = 150
result.features[0].geometry.coordinates[0][0][0][0]  # -> 0.0
result.features[1].geometry.coordinates[0][0][0][0]  # -> 150.0

# The original is untouched
coll.features[1].geometry.coordinates[0][0][0][0]    # -> 0.0

# Properties are carried through unchanged
result.features[0].properties  # -> {"id": "a"}
```

The same call works for grid layout — only the arguments change:

```python
coll = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[MuDMFeature(type="Feature", geometry=tin_at(0, 100), properties=None)
              for _ in range(4)],
)
result = apply_layout(coll, spacing=10.0, grid_max_x=2)

result.features[0].geometry.coordinates[0][0][0][0]  # -> 0.0 (reference)
# Feature 2 lands in col 0, row 1: X unchanged, Y shifted up
result.features[2].geometry.coordinates[0][0][0][1]  # -> 10.0  (> 0)
```

### Behavior worth knowing

- **Zero offsets skip copying.** A feature whose offset is effectively zero (within `1e-12`) is passed through to the new collection unchanged.
- **Null geometries are preserved.** A feature with `geometry=None` is kept as-is and never raises.
- **Any geometry type works.** Layout uses [`translate_geometry`](transforms.md) under the hood, so `Point`, `Polygon`, `TIN`, `PolyhedralSurface`, and other GeoJSON types all translate correctly.

```python
from geojson_pydantic import Point
from mudm import MuDMFeatureCollection, apply_layout
from mudm.model import MuDMFeature

coll = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(type="Feature", geometry=Point(type="Point", coordinates=(0, 0, 0)), properties=None),
        MuDMFeature(type="Feature", geometry=Point(type="Point", coordinates=(0, 0, 0)), properties=None),
    ],
)
result = apply_layout(coll, spacing=10.0)
result.features[1].geometry.coordinates[0]  # -> 10.0  (second point shifted along X)
```

## Layout for visualization

A laid-out `MuDMFeatureCollection` is the natural input to the `mudm-tools` exporters. Run layout first to spread your features apart, then hand the result to a converter or tiling engine:

- **glTF / GeoParquet** — see [GeoParquet & glTF](https://novagenresearch.github.io/mudm-tools/guides/geoparquet-gltf/).
- **Neuroglancer precomputed meshes** — see [Neuroglancer](https://novagenresearch.github.io/mudm-tools/guides/neuroglancer/).
- **3D tile pyramids** — see [3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/).

Because the laid-out collection is still valid muDM (and valid GeoJSON), nothing downstream needs to know layout happened — the coordinates are simply translated.

## Where to next

- [Coordinate Transforms](transforms.md) — `translate_geometry`, `AffineTransform`, and voxel↔physical conversion. Layout is built on `translate_geometry`.
- [Tile Metadata](tiles.md) — the TileJSON/TileModel surface for referencing tiled geometry.
- [Worked examples](examples.md) — end-to-end recipes that combine layout with the rest of the model.
- [Core data-model API](../reference/models.md) — `MuDMFeature`, `MuDMFeatureCollection`, `TIN`, and `PolyhedralSurface`.
- [mudm-tools docs](https://novagenresearch.github.io/mudm-tools/) — pipelines, tiling engines, and format converters that consume a laid-out collection.

## API reference

::: mudm.layout.geometry_bounds

::: mudm.layout.compute_collection_offsets

::: mudm.layout.apply_layout
