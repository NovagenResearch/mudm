# Reference

Look-up material for the `mudm` core package. For step-by-step, task-oriented
walkthroughs, see the [Guides](../guides/index.md); this section is the precise
signature surface — the symbols, fields, and return types you import from
`mudm`.

`mudm` is pure Python with no compiled component. Everything documented here is
importable directly from the package (`from mudm import ...`) and is stable
across the 0.5.x line. Backwards compatibility is a core promise: any valid
GeoJSON is a valid muDM document and vice versa, so the models below accept
plain GeoJSON unchanged.

| Page | Contents |
| --- | --- |
| [Core data-model API](models.md) | The GeoJSON-compatible Pydantic v2 models: `MuDM`, `MuDMFeature`, `MuDMFeatureCollection`, `GeoJSON`, the 3D geometry types `TIN` and `PolyhedralSurface`, and the ontology types `OntologyTerm` and `Vocabulary`. |

## API reference by module

The remaining public modules are documented **in the guide that uses them**, so
the rendered signatures sit next to the worked examples that motivate them. Use
the table below to jump straight to each module's autodoc block.

| Module | Public surface | API reference |
| --- | --- | --- |
| `mudm.transforms` | `AffineTransform`, `VoxelCoordinateSystem`, `apply_transform`, `translate_geometry`, `voxel_to_physical`, `physical_to_voxel` | [Coordinate Transforms API](../guides/transforms.md#api-reference) |
| `mudm.tilemodel` | `TileJSON`, `TileModel`, `TileLayer`, `Asset`, `Multiscale`, `Axis`, `PyramidJSON`, `PyramidEntry` | [Tile Metadata API](../guides/tiles.md#api-reference) |
| `mudm.layout` | `geometry_bounds`, `apply_layout` | [Spatial Layout API](../guides/layout.md#api-reference) |
| `mudm.model` (ontology) | `OntologyTerm`, `Vocabulary` | [Vocabularies API](../guides/vocabularies.md#api-reference) |
| `mudm.provenance` | `Artifact`, `ArtifactCollection`, `Workflow`, `WorkflowProvenance`, `WorkflowCollection`, `MuDMLink` | [Provenance API](../guides/provenance.md#api-reference) |

!!! info "Where the full autodoc lives"
    To keep each symbol documented in exactly one place, the rendered
    signatures, parameters, and return types appear **in the guide** that uses
    them. This page is the index that routes you there. The
    [Core data-model API](models.md) page is the one exception: it carries the
    autodoc for the foundational data model that every other module builds on.

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure
      Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`,
      `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance
      models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with
      the processing pipelines, tiling engines, and format converters, plus an
      optional Rust acceleration extension `mudm_tools._rs`. Its documentation
      lives at <https://novagenresearch.github.io/mudm-tools/>.

## The public import surface

A single import statement covers everything in the reference. The names group by
the module they come from:

```python
# Core data model — see reference/models.md
from mudm import (
    MuDM,
    GeoJSON,
    MuDMFeature,
    MuDMFeatureCollection,
    TiledGeometry,
    PolyhedralSurface,
    TIN,
    OntologyTerm,
    Vocabulary,
)

# Tile metadata — see guides/tiles.md
from mudm.tilemodel import TileJSON, TileModel, TileLayer, Asset, PyramidEntry, PyramidJSON

# Coordinate transforms — see guides/transforms.md
from mudm.transforms import (
    AffineTransform,
    VoxelCoordinateSystem,
    apply_transform,
    translate_geometry,
    voxel_to_physical,
    physical_to_voxel,
)

# Spatial layout — see guides/layout.md
from mudm.layout import geometry_bounds, apply_layout

# Provenance & traceability — see guides/provenance.md
from mudm.provenance import (
    Artifact,
    ArtifactCollection,
    Workflow,
    WorkflowProvenance,
    WorkflowCollection,
    MuDMLink,
)

print(MuDM.__name__, "ready")  # MuDM ready
```

!!! tip "Check your installed version"
    This reference tracks the latest `mudm` release. Confirm which version you
    have installed:

    ```python
    import mudm

    print(mudm.__version__)
    ```

## Processing side: `mudm-tools`

`mudm` defines and validates the data; turning it into tile pyramids, glTF,
GeoParquet, or OME-NGFF — and visualising it — is the job of the separate
`mudm-tools` package. Its API is documented on its own site:

- [mudm-tools Python API reference](https://novagenresearch.github.io/mudm-tools/reference/python-api/) — the `mudm_tools` public API map.
- [mudm-tools TileJSON reference](https://novagenresearch.github.io/mudm-tools/reference/tilejson/) — the tileset-metadata specification used by the viewer.

## Where to next

- [Core data-model API](models.md) — the full Pydantic model reference.
- [Guides](../guides/index.md) — task-oriented walkthroughs with the in-context autodoc.
- [Specification](../specification.md) — the formal muDM schema.
- [mudm-tools docs](https://novagenresearch.github.io/mudm-tools/) — pipelines, tiling engines, and format converters for the processing side.
