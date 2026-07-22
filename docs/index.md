# muDM

**muDM** (micro Data Model) is a GeoJSON-inspired data model for microscopy spatial data — annotations, regions of interest, coordinate systems, and 3D mesh surfaces. It extends GeoJSON with microscopy-specific features while keeping full backwards compatibility: **any GeoJSON document is valid muDM, and any muDM document is valid GeoJSON.** This is the **core data model package**: [Pydantic v2](https://docs.pydantic.dev/) models for validating and serializing muDM documents, built on [geojson-pydantic](https://developmentseed.org/geojson-pydantic/), pure Python with no compiled component.

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

## Capabilities

| Capability | Entry point | Guide |
|------------|-------------|-------|
| Validate & serialize muDM / GeoJSON documents | `mudm.MuDM`, `mudm.GeoJSON` | [Getting Started](getting-started.md) · [Validation](guides/validation.md) |
| Geometry, incl. 3D `TIN` / `PolyhedralSurface` | `mudm.model` (`TIN`, `PolyhedralSurface`, `TiledGeometry`) | [Examples](guides/examples.md) · [Specification](specification.md) |
| Metadata & properties on features | `mudm.model.MuDMFeature` (`featureClass`, `properties`, `ref`) | [Metadata & Properties](guides/metadata.md) |
| Ontology vocabularies | `mudm.model.Vocabulary`, `mudm.model.OntologyTerm` | [Ontology Vocabularies](guides/vocabularies.md) |
| Coordinate transforms (affine, voxel↔physical) | `mudm.transforms` (`AffineTransform`, `VoxelCoordinateSystem`) | [Coordinate Transforms](guides/transforms.md) |
| Spatial layout (bounds, arranging features) | `mudm.layout` (`geometry_bounds`, `apply_layout`) | [Spatial Layout](guides/layout.md) |
| Tile & pyramid metadata | `mudm.tilemodel` (`TileJSON`, `TileModel`, `Asset`, `PyramidJSON`) | [Tile Metadata](guides/tiles.md) |
| Provenance & data lineage | `mudm.provenance` (`Workflow`, `Artifact`, `MuDMLink`) | [Provenance & Traceability](guides/provenance.md) |

!!! tip "Where processing happens"
    Core `mudm` defines and validates the *shape* of the data. To build tile pyramids, convert from Xenium/OBJ/GeoJSON, or export GeoParquet / glTF, reach for the separate **`mudm-tools`** package — see its [documentation site](https://novagenresearch.github.io/mudm-tools/).

## Install

=== "pip (end users)"

    ```bash
    pip install mudm
    ```

=== "uv (projects)"

    ```bash
    uv add mudm
    ```

`mudm` is pure Python with minimal dependencies and no Rust or compiled component. See [Installation](installation.md) for supported Python versions and details.

## 30-second example

Build a small feature collection, validate it against the muDM root model, and serialize it back to JSON:

```python
from mudm import MuDM, MuDMFeature, MuDMFeatureCollection

# A single annotation: a point labelled "nucleus", classified as a cell.
feature = MuDMFeature(
    type="Feature",
    geometry={"type": "Point", "coordinates": [120.5, 88.0]},
    properties={"label": "nucleus"},
    featureClass="cell",
)

# Group features into a collection.
collection = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[feature],
)

# Validate the whole document against the muDM root model.
doc = MuDM.model_validate(collection.model_dump())

# Serialize back to the wire format (camelCase fields like featureClass).
print(doc.model_dump_json(exclude_none=True, indent=2))
```

This prints a document that is, by construction, also a valid GeoJSON `FeatureCollection` — the only addition here is the optional `featureClass` field.

!!! tip "Validating data you already have"
    If you have a dict or JSON loaded from disk, validate it directly with `MuDM.model_validate(data)` (or `MuDMFeatureCollection.model_validate(data)`). See [Validation](guides/validation.md) for error handling and strictness.

## Where to next

- **New here?** Start with [Installation](installation.md), then [Getting Started](getting-started.md).
- **The standard:** read the formal [Specification](specification.md) — object types, fields, and the GeoJSON relationship.
- **Guides:** browse the [Guides index](guides/index.md), or jump to [Examples](guides/examples.md), [Metadata & Properties](guides/metadata.md), [Ontology Vocabularies](guides/vocabularies.md), [Coordinate Transforms](guides/transforms.md), [Spatial Layout](guides/layout.md), [Tile Metadata](guides/tiles.md), [Validation](guides/validation.md), and [Provenance & Traceability](guides/provenance.md).
- **Reference:** the [Reference index](reference/index.md) and the [Core data-model API](reference/models.md).
- **Processing your data?** Tiling pipelines, converters, and visualization live in the separate `mudm-tools` package — see its [documentation site](https://novagenresearch.github.io/mudm-tools/) (e.g. [2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/), [3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/), [converters](https://novagenresearch.github.io/mudm-tools/guides/converters/)).
- **About:** project background and the [MIT license](license.md) on the [About](about.md) page.
