# muDM Specification

This is the formal, normative specification of the muDM (micro Data Model) wire format. It tells you exactly what a valid muDM document looks like, which members are required, and which are optional. If you want a gentle tour with worked examples, start with the [Example walkthrough](guides/examples.md); if you want the field-by-field Python API, the source models in `mudm.model` and `mudm.tilemodel` are the source of truth (see the [Models reference](reference/models.md)).

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, MAY, and OPTIONAL in this document are to be interpreted as described in RFC 2119.

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models. This specification describes the *format* those models implement.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

    This page specifies the *data* only. The *processing and tiling* of muDM data — generating tiled pyramids, running converters, building viewers — is documented at the [mudm-tools docs site](https://novagenresearch.github.io/mudm-tools/).

## Introduction

muDM is a data model and format, inspired by [GeoJSON](https://geojson.org), for encoding a variety of data structures related to microscopy images, including reference points, regions of interest, meshes, and other annotations. It is represented in JSON.

muDM is fully backwards compatible with [GeoJSON RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946):

- Any GeoJSON document is accepted as a valid muDM document.
- Because GeoJSON permits foreign top-level members, every muDM document is also valid GeoJSON. Consumers that only understand GeoJSON will ignore the muDM-specific members.

!!! note "Coordinate order"
    The single largest practical difference from GeoJSON is coordinate order. GeoJSON positions are `[longitude, latitude, altitude]`. muDM positions are `[X, Y, optional Z]` in the order of the document's [multiscale axes](#multiscale-and-coordinate-systems). The default coordinate system is image coordinates in pixels: origin at the top-left, X increasing right, Y increasing down, Z increasing into the image.

The Python public API mirrors this specification. Import the models you need from the top-level package:

```python
from mudm import (
    MuDM,
    MuDMFeature,
    MuDMFeatureCollection,
    TIN,
    PolyhedralSurface,
    Vocabulary,
    OntologyTerm,
)
from mudm.tilemodel import Multiscale, Axis, AxisType, Unit
```

## Objects

### muDM Object

A muDM object is a JSON object whose `type` member is one of `"Feature"`, `"FeatureCollection"`, or any of the Geometry Object types listed below. This is identical to the set of GeoJSON object types, extended with the muDM 3D geometry types.

- A muDM object MAY have a `"bbox"` member: an array of length 4 (2D: `[minX, minY, maxX, maxY]`) or length 6 (3D: `[minX, minY, minZ, maxX, maxY, maxZ]`).
- A muDM object MAY have additional foreign members. Foreign members MUST be ignored by consumers that do not understand them; this is what preserves GeoJSON compatibility.

The Python type `MuDM` (a Pydantic `RootModel`) accepts a `MuDMFeature`, a `MuDMFeatureCollection`, or any geometry as its root.

### Geometry Object

A Geometry Object represents a region of space. Its `type` member is one of:

| `type` | Description |
| --- | --- |
| `Point` | A single position. |
| `MultiPoint` | An array of positions. |
| `LineString` | Two or more positions forming a connected line. |
| `MultiLineString` | An array of LineString coordinate arrays. |
| `Polygon` | An array of linear rings (first ring is the outer boundary, the rest are holes). |
| `MultiPolygon` | An array of Polygon coordinate arrays. |
| `PolyhedralSurface` | A closed surface mesh of polygonal faces (muDM 3D extension). |
| `TIN` | A triangulated irregular network — a triangle mesh (muDM 3D extension). |
| `GeometryCollection` | A collection of geometries. |

Every geometry except `GeometryCollection` MUST have a `"coordinates"` member (the 3D types MAY instead reference external `"tiles"`; see [3D Geometry Types](#3d-geometry-types-iso-19107)).

A **position** is the fundamental coordinate primitive: an array of 2 or 3 numbers, `[X, Y]` or `[X, Y, Z]`, in [multiscale axes order](#multiscale-and-coordinate-systems).

- `Point` — a single position. To describe a circular object, store a `radius` (in pixels) in the feature's `properties`.
- `MultiPoint` — an array of positions.
- `LineString` — an array of two or more positions. A line's thickness (e.g. a tube/path radius) is likewise stored in `properties`.
- `MultiLineString` — an array of LineString coordinate arrays.
- `Polygon` — an array of linear rings. The first ring is the outer boundary; subsequent rings are interior holes. A linear ring is a closed LineString of four or more positions where the first and last positions are identical.
- `MultiPolygon` — an array of Polygon coordinate arrays.

!!! note "Where `radius` lives"
    muDM reuses the standard [geojson-pydantic](https://developmentseed.org/geojson-pydantic/) `Point`/`LineString` geometries, which have **no** geometry-level `radius` field — a `radius` placed inside the `geometry` object is silently dropped on validation. Store it in the feature's `properties` so it round-trips, as shown below and in the [Examples](guides/examples.md) gallery.

```python
from mudm import MuDMFeature

point = MuDMFeature(
    type="Feature",
    geometry={"type": "Point", "coordinates": [10, 20]},
    properties={"radius": 5, "cellType": "pyramidal"},
)
print(point.geometry.type)        # "Point"
print(point.properties["radius"])  # 5
```

#### 3D Geometry Types (ISO 19107)

muDM adds two surface-mesh geometry types modelled on ISO 19107. Both are implemented in Python by classes that inherit from `TiledGeometry`, which contributes an OPTIONAL `"tiles"` member.

| `type` | `coordinates` shape | Per-face rule |
| --- | --- | --- |
| `PolyhedralSurface` | array of Polygon coordinate arrays | Each face is a Polygon (one or more linear rings of 3D positions). At least 1 face when coordinates are inline; a tiled mesh (`tiles` set, `coordinates` empty) may have 0 faces. |
| `TIN` | array of Polygon coordinate arrays | Each face MUST have exactly one ring of exactly 4 positions (3 triangle vertices plus the repeated first vertex). At least 1 face when coordinates are inline; a tiled mesh may have 0 faces. |

Common rules for both 3D types:

- A `PolyhedralSurface` or `TIN` object MUST provide either a non-empty `"coordinates"` array **or** a `"tiles"` array. It is a validation error to supply neither.
- When data is materialised externally (for example in a tiled pyramid), `"coordinates"` MAY be empty or omitted and `"tiles"` lists the spatial tile identifiers that hold the mesh. See [Tile Metadata](guides/tiles.md).
- The `"tiles"` member, when present, is an array of strings.

`TIN` is the primary type for tiled 3D mesh data. The strict 4-position-per-face rule lets a triangle be reconstructed unambiguously and validated cheaply.

```python
from mudm import TIN, PolyhedralSurface

# Inline triangle mesh: each face is one closed ring of 4 positions.
mesh = TIN(
    type="TIN",
    coordinates=[
        [[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]],
        [[[1, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]]],
    ],
)
print(mesh.bbox3d())     # (0.0, 0.0, 0.0, 1.0, 1.0, 0.0)
print(mesh.centroid3d())

# Tiled surface: no inline coordinates, data lives in external tiles.
surface = PolyhedralSurface(type="PolyhedralSurface", tiles=["0/0/0", "0/0/1"])
print(surface.tiles)
```

!!! warning "TIN face shape"
    A `TIN` face that does not have exactly one ring of exactly four positions is rejected at validation time. Open triangles (3 positions) are not accepted — repeat the first vertex to close the ring.

The `bbox3d()` and `centroid3d()` helper methods return `None` when a 3D geometry carries only `"tiles"` and no inline coordinates.

!!! tip "Generating the tiles themselves"
    This specification defines how a 3D geometry *references* external tiles; it does not describe how to *produce* a tiled pyramid. For 3D tiling engines and the streaming generators that emit these tile identifiers, see the [mudm-tools 3D tiling guide](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/).

### GeometryCollection

A `GeometryCollection` has a `"geometries"` member: an array of Geometry Objects. The array MAY be empty. A `GeometryCollection` MUST NOT contain another `GeometryCollection` nested arbitrarily where a simpler representation would do, but empty and homogeneous collections are valid.

### Feature Object

A Feature binds a geometry to a set of properties.

| Member | Required | Description |
| --- | --- | --- |
| `type` | MUST | The string `"Feature"`. |
| `geometry` | MUST | A Geometry Object, or `null`. |
| `properties` | OPTIONAL | A JSON object of key/value pairs, or `null`. |
| `id` | OPTIONAL | A feature identifier (string or integer). |
| `ref` | OPTIONAL | A reference to an external resource holding the feature's data (string or integer), e.g. a Zarr store URI. |
| `parentId` | OPTIONAL | The `id` of a parent feature, expressing containment or hierarchy (string or integer). |
| `featureClass` | OPTIONAL | A string naming the kind of object, e.g. `"cell"`, `"nucleus"`. |
| `vocabularies` | OPTIONAL | Ontology vocabularies for this feature's properties; see [Ontology Vocabularies](#ontology-vocabularies). |

The members `ref`, `parentId`, `featureClass`, and `vocabularies` are muDM extensions (the Python class is `MuDMFeature`). They are foreign members from a pure-GeoJSON perspective and are safely ignored by GeoJSON-only consumers.

```python
from mudm import MuDMFeature

cell = MuDMFeature(
    type="Feature",
    geometry={"type": "Point", "coordinates": [10, 20]},
    properties={"cellType": "pyramidal"},
    id="cell-42",
    parentId="tissue-1",
    featureClass="cell",
    ref="s3://bucket/store.zarr",
)
print(cell.featureClass, cell.parentId, cell.ref)
```

#### Special Feature Objects

- **Image** — A Feature whose `properties.type` is `"Image"` and which carries a string `properties.URI`. Its `geometry` MUST be a Polygon (a rectangular outer ring) giving the image's pixel extent. It MAY carry `properties.correction`, a relative `[x, y]` correction offset.

### FeatureCollection Object

A FeatureCollection groups features and document-level metadata.

| Member | Required | Description |
| --- | --- | --- |
| `type` | MUST | The string `"FeatureCollection"`. |
| `features` | MUST | An array of Feature Objects (MAY be empty). |
| `properties` | OPTIONAL | A JSON object applying to the whole collection. |
| `id` | OPTIONAL | A collection identifier (string or integer). |
| `provenance` | OPTIONAL | A provenance object; see [Provenance](#provenance). |
| `vocabularies` | OPTIONAL | Collection-level ontology vocabularies; see [Ontology Vocabularies](#ontology-vocabularies). |

The Python class is `MuDMFeatureCollection`. Its `features` are `MuDMFeature` objects, so they support both the 3D geometry types and the muDM feature members.

```python
from mudm import MuDMFeature, MuDMFeatureCollection

fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(
            type="Feature",
            geometry={"type": "Point", "coordinates": [10, 20]},
            properties={"cellType": "pyramidal"},
            featureClass="cell",
        )
    ],
    properties={"experiment": "exp-001"},
)
print(len(fc.features), fc.properties["experiment"])
```

#### Special FeatureCollection Objects

- **StitchingVector** — A FeatureCollection whose `properties.type` is `"StitchingVector"`. Every member of `features` MUST be an Image feature. This represents the placement of image tiles within a larger mosaic.

## Multiscale and Coordinate Systems

muDM positions are bare numbers; the **multiscale object** gives them physical meaning. It defines the named axes, their order, units, and the transformations from stored coordinates to physical space. The Python model is `mudm.tilemodel.Multiscale`, and it appears on tile metadata (`TileModel.multiscale`).

A multiscale object has the following members:

| Member | Required | Description |
| --- | --- | --- |
| `axes` | MUST | An ordered array of Axis objects. The order of `axes` defines the order of numbers in every position in the document. |
| `coordinateTransformations` | OPTIONAL | An ordered list of coordinate transformations (harmonised with the OME model). |
| `transformationMatrix` | OPTIONAL | An explicit transformation matrix as an array of rows of numbers. |

Each **Axis** object has:

| Member | Required | Description |
| --- | --- | --- |
| `name` | MUST | The axis name, e.g. `"x"`, `"y"`, `"z"`, `"t"`, `"c"`. |
| `type` | OPTIONAL | One of `"space"`, `"time"`, `"channel"` (`AxisType`). |
| `unit` | OPTIONAL | A unit from the `Unit` enumeration, e.g. `"micrometer"`, `"nanometer"`, `"pixel"`, `"degree"`. |
| `description` | OPTIONAL | A human-readable description. |

The available coordinate transformation types are `identity`, `translation` (with a `translation` vector), and `scale` (with a `scale` vector), each distinguished by its `type` member. For the helper functions that apply these transformations to geometries, see [Coordinate Transforms](guides/transforms.md).

!!! note "Default image coordinate system"
    When no multiscale object is supplied, positions are interpreted in the default image coordinate system: the unit is the pixel, the origin is the top-left corner, X increases to the right, Y increases downward, and Z increases into the image. Coordinate order always follows the `axes` order when a multiscale object is present.

```python
from mudm.tilemodel import Multiscale, Axis, AxisType, Unit, Scale

ms = Multiscale(
    axes=[
        Axis(name="x", type=AxisType.SPACE, unit=Unit.MICROMETER),
        Axis(name="y", type=AxisType.SPACE, unit=Unit.MICROMETER),
        Axis(name="z", type=AxisType.SPACE, unit=Unit.MICROMETER),
    ],
    coordinateTransformations=[Scale(scale=[0.65, 0.65, 2.0])],
)
print([a.name for a in ms.axes])  # ['x', 'y', 'z']
```

## Ontology Vocabularies

Properties on features are free-form, but muDM lets you bind property values to formal ontology terms with a `vocabularies` member. This member may appear on a Feature and on a FeatureCollection.

The `vocabularies` member is either:

1. A **mapping** from a property name to a `Vocabulary` object, or
2. A **string URI** pointing to an externally hosted vocabulary definition.

A `Vocabulary` object has:

| Member | Required | Description |
| --- | --- | --- |
| `namespace` | OPTIONAL | A common URI prefix for the ontology, e.g. `"http://purl.obolibrary.org/obo/CL_"`. |
| `description` | OPTIONAL | A description of the vocabulary. |
| `terms` | MUST | A mapping from a property value to an `OntologyTerm`. |

Each `OntologyTerm` has:

| Member | Required | Description |
| --- | --- | --- |
| `uri` | MUST | The full URI of the ontology term. |
| `label` | OPTIONAL | A human-readable label. |
| `description` | OPTIONAL | A longer description. |

!!! tip "Feature overrides collection"
    When both a Feature and its enclosing FeatureCollection define `vocabularies`, the feature-level vocabularies override the collection-level ones for that feature.

```python
from mudm import MuDMFeature, MuDMFeatureCollection, Vocabulary, OntologyTerm

cell_types = Vocabulary(
    namespace="http://purl.obolibrary.org/obo/CL_",
    terms={
        "pyramidal": OntologyTerm(
            uri="http://purl.obolibrary.org/obo/CL_0000598",
            label="pyramidal neuron",
        )
    },
)

fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(
            type="Feature",
            geometry={"type": "Point", "coordinates": [10, 20]},
            properties={"cellType": "pyramidal"},
            featureClass="cell",
        )
    ],
    vocabularies={"cellType": cell_types},
)
print(fc.vocabularies["cellType"].terms["pyramidal"].label)
```

See [Ontology Vocabularies](guides/vocabularies.md) for the full guide.

## Provenance

A FeatureCollection MAY carry a `provenance` member recording how its features were produced — for example the workflow that ran, its sub-workflows, and the input and output artifacts. The value is one of the provenance models (`Workflow`, `WorkflowCollection`, `Artifact`, or `ArtifactCollection`).

This specification only notes the presence of the member; the full provenance data model, including the `subWorkflows`, `workflowProvenance`, `outputArtifacts`, `mudmLinks`, `mudmId`, and `mudmField` members, is documented in [Provenance & Traceability](guides/provenance.md).

## Validating a document

Because every model is a Pydantic v2 model, validation is a single call. Parse and validate against the muDM root type:

```python
from mudm import MuDM

doc = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [10, 20]},
            "properties": {"cellType": "pyramidal"},
            "featureClass": "cell",
        }
    ],
}

mudm = MuDM.model_validate(doc)        # raises ValidationError if invalid
print(mudm.root.features[0].featureClass)  # "cell"
```

For validation patterns, error handling, and round-tripping with GeoJSON, see the [Validation guide](guides/validation.md).

## Where to next

- [Example walkthrough](guides/examples.md) — a guided, runnable tour of building muDM documents.
- [Coordinate Transforms](guides/transforms.md) — applying scale, translation, and affine transforms to geometries.
- [Tile Metadata](guides/tiles.md) — the tiled pyramid format and the `tiles` member on 3D geometries.
- [Ontology Vocabularies](guides/vocabularies.md) — binding properties to ontology terms.
- [Provenance & Traceability](guides/provenance.md) — the full provenance data model.
- [Models reference](reference/models.md) — the field-by-field Pydantic API for every type named above.
- [mudm-tools docs site](https://novagenresearch.github.io/mudm-tools/) — tiling pipelines ([2D](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/) / [3D](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/)), [format converters](https://novagenresearch.github.io/mudm-tools/guides/converters/), and Rust-accelerated processing for muDM data.
