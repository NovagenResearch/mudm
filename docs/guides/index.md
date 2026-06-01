# Guides

Task-oriented walkthroughs for each part of the `mudm` core data model. Every
guide is grounded in the real public API and runs top-to-bottom against the
current `mudm`. Pick the guide that matches what you are trying to do:

| Guide | Use it when you want to… |
| --- | --- |
| [Examples](examples.md) | Browse a gallery of complete muDM documents in both JSON wire format and equivalent Python, from a single feature to a full provenance-tagged collection. |
| [Metadata & Properties](metadata.md) | Attach arbitrary metadata to features and collections, and use the muDM members `featureClass`, `parentId`, and `ref`. |
| [Ontology Vocabularies](vocabularies.md) | Map free-text property values (e.g. `"pyramidal"`) to stable ontology URIs with `OntologyTerm` and `Vocabulary`, without changing the human-friendly strings you store. |
| [Coordinate Transforms](transforms.md) | Build a 4x4 `AffineTransform`, apply it to GeoJSON and muDM 3D geometry, and convert between voxel and physical (micrometre) space with `VoxelCoordinateSystem`. |
| [Spatial Layout](layout.md) | Arrange the features in a collection side-by-side without overlap using `geometry_bounds` and `apply_layout`, while keeping every shape unchanged. |
| [Tile Metadata](tiles.md) | Describe tiled, multi-resolution datasets with the TileJSON-style models in `mudm.tilemodel` (`TileModel`, `TileLayer`, `PyramidJSON`). |
| [Validation](validation.md) | Validate muDM and plain GeoJSON with the `MuDM` and `GeoJSON` root models, read Pydantic errors, and round-trip to and from JSON. |
| [Provenance & Traceability](provenance.md) | Attach a structured, machine-readable record of the workflows and artifacts that produced your features, and link it back to specific fields. |

!!! tip "Not sure where to start?"
    Read [Getting Started](../getting-started.md) first — it takes you from
    install to a validated muDM document in a few minutes. The
    [Specification](../specification.md) is the formal reference for the data
    model. For exact class and function signatures, see the
    [API Reference](../reference/index.md).

!!! note "Looking for processing pipelines?"
    These guides cover the **core data model** only — building, validating, and
    transforming muDM documents in pure Python. Tiling engines, format
    converters (Xenium / OBJ / GeoJSON), and exporters (GeoParquet, glTF,
    Neuroglancer) live in the separate `mudm-tools` package, documented at
    <https://novagenresearch.github.io/mudm-tools/>.
