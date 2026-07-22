# About muDM

muDM (micro Data Model) is a data model and Python library for representing microscopy annotations, regions of interest, and spatial metadata. Inspired by [GeoJSON](https://geojson.org), it extends the GeoJSON specification with microscopy-specific features while staying fully backwards compatible.

!!! note "Backwards compatible by design"
    Any GeoJSON document is valid muDM, and any muDM document is valid GeoJSON. You can adopt muDM incrementally and keep using existing GeoJSON tooling.

## Two packages, one ecosystem

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

This repository is the **core data model package** — Pydantic models for validation and serialization with minimal dependencies. For tiling pipelines, format converters, and Rust-accelerated processing, read the [mudm-tools documentation](https://novagenresearch.github.io/mudm-tools/). Publications and supporting material live in the separate `mudm-paper` repository.

## Key capabilities

| Capability | What it gives you |
|------------|-------------------|
| Format specification | A JSON-based data model for 2D and 3D microscopy annotations, with coordinate systems, multiscale metadata, and provenance tracking. |
| Pydantic v2 validation | Strict schema validation and serialization built on [Pydantic v2](https://docs.pydantic.dev/) and [geojson-pydantic](https://developmentseed.org/geojson-pydantic/). |
| 3D geometry types | `TIN` and `PolyhedralSurface` mesh types based on ISO 19107, plus `TiledGeometry`. |
| Coordinate transforms | Affine transforms, voxel-to-physical conversions, and OME-compatible multiscale metadata. |
| Spatial layout | Bounds computation and grid layout helpers for arranging feature collections. |
| Ontology vocabularies | `OntologyTerm` and `Vocabulary` for mapping property values to formal ontology terms. |
| Provenance tracking | `Workflow`, `Artifact`, and `MuDMLink` models for data lineage. |
| Tile metadata | TileJSON 3.0.0 models (`TileModel`, `TileJSON`, `TileLayer`, `Asset`, `PyramidJSON`) for describing tiled datasets, including typed data assets. |

## A first look

The public surface is importable directly from the `mudm` package. Any plain GeoJSON `FeatureCollection` validates as muDM, and the same document round-trips as GeoJSON:

=== "Python"

    ```python
    from mudm import MuDM, GeoJSON

    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [10, 20]},
                "properties": {"label": "nucleus"},
            }
        ],
    }

    # Validate as muDM
    obj = MuDM.model_validate(data)

    # The same document is also valid GeoJSON
    geojson = GeoJSON.model_validate(data)

    # MuDM is a root model; the validated collection is on `.root`
    feature = obj.root.features[0]
    print(feature.properties["label"])  # "nucleus"
    ```

=== "JSON"

    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": { "type": "Point", "coordinates": [10, 20] },
          "properties": { "label": "nucleus" }
        }
      ]
    }
    ```

Apply a coordinate transform to a geometry — the affine matrix is a 4x4 row-major matrix:

```python
from mudm import AffineTransform, apply_transform

# Translate +5 in x and +7 in y
transform = AffineTransform(matrix=[
    [1, 0, 0, 5],
    [0, 1, 0, 7],
    [0, 0, 1, 0],
    [0, 0, 0, 1],
])

moved = apply_transform(feature.geometry, transform)
# Prints Position2D(longitude=15.0, latitude=27.0) — the lon/lat names are
# inherited from the reused GeoJSON Position type; in muDM these are X=15.0, Y=27.0.
print(moved.coordinates)
```

See the [Coordinate Transforms](guides/transforms.md) guide and the rest of the guide gallery for 3D geometry, ontology vocabularies, provenance, and tile metadata.

## Requirements

- Python `>=3.11, <3.14`
- Dependencies: `pydantic` (>=2.3.0) and `geojson-pydantic` (>=1.2.0)

The core package is **pure Python with no compiled component** — there is no Rust extension here. The optional Rust acceleration belongs to the separate `mudm-tools` package.

## Install

=== "pip (end users)"

    ```bash
    pip install mudm
    ```

=== "uv (projects)"

    ```bash
    uv add mudm
    ```

See [Installation](installation.md) for the full setup, including the development workflow and building the documentation.

## Links

- **Repository**: [github.com/NovagenResearch/mudm](https://github.com/NovagenResearch/mudm)
- **Tools documentation**: <https://novagenresearch.github.io/mudm-tools/>
- **Tools repository**: [github.com/NovagenResearch/mudm-tools](https://github.com/NovagenResearch/mudm-tools)
- **Publications**: the `mudm-paper` repository
- **License**: MIT. Copyright muDM contributors. See [License](license.md).

## Where to next

- **New here?** Start with [Installation](installation.md), then [Getting Started](getting-started.md).
- **Learn the model:** the [Formal specification](specification.md) and the [Core data-model API](reference/models.md).
- **Guides:** [Metadata & Properties](guides/metadata.md), [Ontology Vocabularies](guides/vocabularies.md), [Coordinate Transforms](guides/transforms.md), [Spatial Layout](guides/layout.md), [Tile Metadata](guides/tiles.md), [Validation](guides/validation.md), and [Provenance & Traceability](guides/provenance.md).
- **Worked examples:** the [example gallery](guides/examples.md).
- **Processing & pipelines:** for tiling, converters, and visualization, read the [mudm-tools documentation](https://novagenresearch.github.io/mudm-tools/) — start with its [Getting Started](https://novagenresearch.github.io/mudm-tools/getting-started/).
