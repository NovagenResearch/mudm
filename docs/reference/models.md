# Core Data Model

The `mudm.model` module gives you [Pydantic v2](https://docs.pydantic.dev/) models for parsing, validating, and serializing both plain GeoJSON and muDM documents. They are built on [geojson-pydantic](https://developmentseed.org/geojson-pydantic/), so muDM inherits a battle-tested GeoJSON implementation and extends it with 3D surface meshes, tiling references, provenance, and ontology vocabularies.

!!! note "Backwards compatibility"
    Any valid GeoJSON document is a valid muDM document, and any muDM document is valid GeoJSON. The muDM root and feature models are strict supersets of their GeoJSON counterparts, so existing GeoJSON tooling keeps working unchanged.

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

## What you can do here

- Parse untrusted GeoJSON or muDM JSON into typed, validated objects.
- Build 3D surface meshes (`PolyhedralSurface`, `TIN`) that GeoJSON cannot express.
- Defer large meshes to external tiles via `TiledGeometry`.
- Attach metadata, parent/child relationships, and ontology vocabularies to features.
- Round-trip documents to JSON with `model_dump_json()`.

## Importing

The public surface is exported from the top-level package. Prefer importing from `mudm` directly:

```python
from mudm import (
    GeoJSON,
    MuDM,
    MuDMFeature,
    MuDMFeatureCollection,
    TiledGeometry,
    PolyhedralSurface,
    TIN,
    OntologyTerm,
    Vocabulary,
)
```

GeoJSON geometry primitives come from `geojson_pydantic`:

```python
from geojson_pydantic import (
    Point, MultiPoint, LineString, MultiLineString,
    Polygon, MultiPolygon, GeometryCollection,
)
```

This page documents the data model only. The other core modules have their own pages: [Coordinate Transforms](../guides/transforms.md), [Tile Metadata](../guides/tiles.md), and [Provenance](../guides/provenance.md). For tiling pipelines, format converters, and Rust-accelerated processing, see the [mudm-tools documentation](https://novagenresearch.github.io/mudm-tools/) and its [Python API reference](https://novagenresearch.github.io/mudm-tools/reference/python-api/).

## GeoJSON geometry types

The standard 2D/3D GeoJSON geometries are re-used directly from geojson-pydantic. muDM does not redefine them — it imports `Point`, `MultiPoint`, `LineString`, `MultiLineString`, `Polygon`, `MultiPolygon`, and `GeometryCollection` and accepts them anywhere a geometry is expected.

| Type | Coordinates shape |
| --- | --- |
| `Point` | a single position `[x, y]` or `[x, y, z]` |
| `MultiPoint` | a list of positions |
| `LineString` | a list of two or more positions |
| `MultiLineString` | a list of LineString coordinate arrays |
| `Polygon` | a list of linear rings (first is the exterior, rest are holes) |
| `MultiPolygon` | a list of Polygon coordinate arrays |
| `GeometryCollection` | a list of geometry objects |

These follow [RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946). For their fields, validation rules, and helper methods, see the [geojson-pydantic documentation](https://developmentseed.org/geojson-pydantic/).

```python
from geojson_pydantic import Point, Polygon

pt = Point(type="Point", coordinates=(12.5, 41.9))
poly = Polygon(type="Polygon", coordinates=[[(0, 0), (1, 0), (1, 1), (0, 0)]])
print(pt.model_dump_json())
print(poly.model_dump_json())
```

!!! tip "Positions may be 3D"
    GeoJSON positions allow an optional third (Z) element, so `Point(type="Point", coordinates=(x, y, z))` is valid. For surface meshes that are not expressible as GeoJSON, use the muDM 3D geometry types below.

## muDM 3D geometry

muDM adds two ISO 19107 surface-mesh geometry types plus a shared base that lets large meshes reference external tiles instead of inlining coordinates.

### `TiledGeometry`

::: mudm.model.TiledGeometry
    options:
      show_root_heading: true
      show_source: false

`TiledGeometry` is the base for geometries whose coordinate data may live in external [tiles](../guides/tiles.md). When `tiles` is set, `coordinates` can be empty; the actual mesh data is fetched from the named tiles.

### `PolyhedralSurface`

::: mudm.model.PolyhedralSurface
    options:
      show_root_heading: true
      show_source: false

A closed surface mesh of polygonal faces. Each face has the same structure as a `Polygon` (a list of linear rings of 3D positions). A `PolyhedralSurface` must carry either `coordinates` or `tiles`.

```python
from mudm import PolyhedralSurface

surface = PolyhedralSurface(
    type="PolyhedralSurface",
    coordinates=[[[(0, 0, 0), (1, 0, 0), (1, 1, 1), (0, 0, 0)]]],
)
print(surface.bbox3d())      # (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
print(surface.centroid3d())  # centroid of unique vertices
```

### `TIN`

::: mudm.model.TIN
    options:
      show_root_heading: true
      show_source: false

A Triangulated Irregular Network: a triangle mesh where every face is a single closed ring of exactly four positions (three vertices plus a repeat of the first). Like `PolyhedralSurface`, it requires either `coordinates` or `tiles`.

```python
from mudm import TIN

tin = TIN(
    type="TIN",
    coordinates=[[[(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 0)]]],
)
print(tin.bbox3d())      # (0.0, 0.0, 0.0, 1.0, 1.0, 0.0)
print(tin.centroid3d())  # (0.333..., 0.333..., 0.0)

# A tiled TIN defers its coordinates to external tiles:
tiled = TIN(type="TIN", tiles=["tile-0", "tile-1"])
print(tiled.coordinates)  # []
```

!!! warning "TIN faces must be closed triangles"
    Each `TIN` face must have exactly one ring of exactly four positions. A three-position (unclosed) ring raises a validation error:

    ```python
    from mudm import TIN

    try:
        TIN(type="TIN", coordinates=[[[(0, 0, 0), (1, 0, 0), (0, 1, 0)]]])
    except Exception as exc:
        print("rejected:", exc)
    ```

The `bbox3d()` and `centroid3d()` helpers return `None` when a geometry has no inline coordinates (i.e. when it is tiled). To turn meshes into tiles in the first place, use the tiling engines in [mudm-tools](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/).

## Vocabulary models

muDM properties can be linked to formal ontology terms so that, for example, a `featureClass` of `"pyramidal"` resolves to a Cell Ontology term.

The two models involved are `OntologyTerm` (a single term: `uri`, optional `label`, optional `description`) and `Vocabulary` (an optional `namespace`, optional `description`, and a `terms` mapping from property value to `OntologyTerm`).

!!! note "Single source of truth"
    The full field-level API reference for `OntologyTerm` and `Vocabulary` lives on the [Ontology Vocabularies](../guides/vocabularies.md#api-reference) guide, which owns their autodoc. Only a quick example is shown here.

```python
from mudm import OntologyTerm, Vocabulary

vocab = Vocabulary(
    namespace="http://purl.obolibrary.org/obo/CL_",
    description="Cell types observed in this dataset",
    terms={
        "pyramidal": OntologyTerm(
            uri="http://purl.obolibrary.org/obo/CL_0000598",
            label="pyramidal neuron",
        ),
    },
)
print(vocab.model_dump_json(exclude_none=True))
```

A `Vocabulary` can be attached to a [`MuDMFeature`](#mudmfeature) or [`MuDMFeatureCollection`](#mudmfeaturecollection) via their `vocabularies` field, which accepts a mapping of name to `Vocabulary`, or a string reference to an external vocabulary document.

## Root and extended models

These are the entry points for parsing and producing whole documents.

### `GeoJSON`

::: mudm.model.GeoJSON
    options:
      show_root_heading: true
      show_source: false

The root wrapper for a plain GeoJSON document. Its `root` field accepts a `Feature`, a `FeatureCollection`, or any single geometry. Use `model_validate` to parse untrusted input:

```python
from mudm import GeoJSON

# A bare geometry is a valid GeoJSON root
g = GeoJSON.model_validate({"type": "Point", "coordinates": [0.0, 0.0]})
print(type(g.root).__name__)  # Point
```

### `MuDMFeature`

::: mudm.model.MuDMFeature
    options:
      show_root_heading: true
      show_source: false

A GeoJSON `Feature` extended with muDM metadata. The `geometry` field additionally accepts the muDM 3D types (`PolyhedralSurface`, `TIN`). All extra fields are optional, so a plain GeoJSON feature validates unchanged.

| Field | Wire name | Type | Description |
| --- | --- | --- | --- |
| `geometry` | `geometry` | any GeoJSON geometry, `PolyhedralSurface`, `TIN`, or `null` | The feature geometry. |
| `ref` | `ref` | `str` or `int`, optional | A reference to an external resource holding the feature's data (e.g. a store/file URI). Distinct from `parentId`. |
| `parentId` | `parentId` | `str` or `int`, optional | Identifier of the parent feature (e.g. a soma's neuron). |
| `featureClass` | `featureClass` | `str`, optional | Classification label for the feature. |
| `vocabularies` | `vocabularies` | mapping of name to `Vocabulary`, or `str`, optional | Inline vocabularies or a reference to an external one. |

!!! note "camelCase on the wire"
    Fields such as `parentId`, `featureClass`, and `vocabularies` are written in camelCase in JSON, matching the field names on the model.

=== "Python"

    ```python
    from mudm import MuDMFeature
    from geojson_pydantic import Point

    feat = MuDMFeature(
        type="Feature",
        geometry=Point(type="Point", coordinates=(1.0, 2.0)),
        properties={"name": "soma"},
        parentId="neuron-1",
        featureClass="soma",
    )
    print(feat.model_dump_json(exclude_none=True))
    ```

=== "JSON"

    ```json
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
      "properties": {"name": "soma"},
      "parentId": "neuron-1",
      "featureClass": "soma"
    }
    ```

### `MuDMFeatureCollection`

::: mudm.model.MuDMFeatureCollection
    options:
      show_root_heading: true
      show_source: false

A GeoJSON `FeatureCollection` whose `features` are `MuDMFeature` objects. It adds a `provenance` field (see [Provenance](../guides/provenance.md)) and a collection-level `vocabularies` field.

| Field | Wire name | Type | Description |
| --- | --- | --- | --- |
| `features` | `features` | list of `MuDMFeature` | The collection's features. |
| `properties` | `properties` | object, optional | Collection-level properties. |
| `id` | `id` | `str` or `int`, optional | Identifier of the collection. |
| `provenance` | `provenance` | `Workflow`, `WorkflowCollection`, `Artifact`, or `ArtifactCollection`, optional | How the collection was produced. |
| `vocabularies` | `vocabularies` | mapping of name to `Vocabulary`, or `str`, optional | Collection-level vocabularies. |

```python
from mudm import MuDMFeatureCollection, MuDMFeature
from geojson_pydantic import Point

fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(
            type="Feature",
            geometry=Point(type="Point", coordinates=(0.0, 0.0)),
            properties=None,
            featureClass="soma",
        ),
    ],
)
print(len(fc.features))  # 1
```

### `MuDM`

::: mudm.model.MuDM
    options:
      show_root_heading: true
      show_source: false

The root wrapper for a muDM document. Its `root` accepts a `MuDMFeature`, a `MuDMFeatureCollection`, or any single geometry. Because muDM is a superset of GeoJSON, plain GeoJSON parses cleanly into `MuDM`:

=== "Python"

    ```python
    from mudm import MuDM

    geojson = {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
        "properties": {"name": "soma"},
    }
    doc = MuDM.model_validate(geojson)
    print(type(doc.root).__name__)  # MuDMFeature
    ```

=== "JSON"

    ```json
    {
      "type": "Feature",
      "geometry": {"type": "Point", "coordinates": [1.0, 2.0]},
      "properties": {"name": "soma"}
    }
    ```

## Where to next

- [Coordinate Transforms](../guides/transforms.md) — affine transforms and voxel/physical coordinate conversion.
- [Tile Metadata](../guides/tiles.md) — the tile model referenced by `TiledGeometry`.
- [Provenance & Traceability](../guides/provenance.md) — the workflow and artifact models used in `provenance`.
- [Ontology Vocabularies](../guides/vocabularies.md) — attaching ontology terms to features (owns the `OntologyTerm` / `Vocabulary` reference).
- [Metadata & Properties](../guides/metadata.md) — modeling feature attributes.
- [Validation](../guides/validation.md) — validating documents against the model.
- [Worked Examples](../guides/examples.md) — end-to-end examples using these models.
- [muDM Specification](../specification.md) — the formal data-model specification.
- [mudm-tools](https://novagenresearch.github.io/mudm-tools/) — tiling pipelines, format converters, and Rust-accelerated processing for muDM data.
