# Tile Metadata

muDM describes tiled, multi-resolution datasets with a small set of Pydantic models in `mudm.tilemodel`. These follow the [TileJSON 3.0](https://github.com/mapbox/tilejson-spec) convention used by web maps, adapted for microscopy: physical units, multi-axis coordinate systems, and ontology-aware field metadata. This guide shows how to build and validate that metadata in Python.

!!! note "These models *describe* tiles — they do not *make* them"
    The models on this page only **describe** a tiled dataset: where the tiles live, what zoom levels exist, the coordinate system, and the property schema each layer carries. The tiling **engines and pipelines** — slicing a `FeatureCollection` into tiles across zoom levels, writing tile files, and emitting these manifests — live in the separate `mudm-tools` package. Start there for processing work:

    - [2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/) and [3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/) guides.
    - The [TileJSON reference](https://novagenresearch.github.io/mudm-tools/reference/tilejson/), which documents these **same `mudm.tilemodel` models** from the consumer/producer side, including the formal field-by-field spec.

!!! note "Why TileJSON?"
    A microscopy slide is often gigapixels in size. As with web maps, you cannot load it all at once, so it is split into tiles across zoom levels (a pyramid). TileJSON is the well-understood manifest format describing such a pyramid; muDM reuses it so existing map tooling concepts transfer directly.

## The tile manifest at a glance

A tile manifest is a `TileModel`. At minimum it needs a `tilejson` version string, a list of `tiles` URLs/paths, and one or more `vector_layers`. The placeholders `{zlvl}`, `{x}`, `{y}` are filled in by the tile reader at request time — `{zlvl}` is the zoom level, `{x}` / `{y}` the tile column and row.

=== "JSON"

    ```json
    {
        "tilejson": "3.0.0",
        "tiles": ["http://localhost:8080/tiles/{zlvl}/{x}/{y}.json"],
        "vector_layers": [
            { "id": "cells", "fields": { "name": "string" } }
        ]
    }
    ```

=== "Python"

    ```python
    from mudm import TileModel, TileLayer

    tileset = TileModel(
        tilejson="3.0.0",
        tiles=["http://localhost:8080/tiles/{zlvl}/{x}/{y}.json"],
        vector_layers=[TileLayer(id="cells", fields={"name": "string"})],
    )
    print(tileset.minzoom, tileset.maxzoom)  # 0 22  (defaults)
    ```

## Build and validate a tile manifest

The following example builds a complete manifest in Python, then validates it through `TileJSON`, the root wrapper used to parse manifests from disk or the network.

```python
from mudm import TileModel, TileJSON, TileLayer
from mudm.tilemodel import Multiscale, Axis, AxisType, Unit, Scale, Translation

# A vector layer: the features carried by these tiles and their property schema.
cells = TileLayer(
    id="cells",
    description="Segmented cell nuclei",
    minzoom=0,
    maxzoom=10,
    fields={"cellType": "String", "area_um2": "Number"},
    fieldranges={"area_um2": [0.0, 250.0]},
    fieldenums={"cellType": ["neuron", "astrocyte", "microglia"]},
    fielddescriptions={"area_um2": "Cross-sectional area in square microns"},
)

# A physical coordinate system for the dataset (see "Coordinate systems" below).
coords = Multiscale(
    axes=[
        Axis(name="x", type=AxisType.SPACE, unit=Unit.MICROMETER, description="x-axis"),
        Axis(name="y", type=AxisType.SPACE, unit=Unit.MICROMETER, description="y-axis"),
    ],
    coordinateTransformations=[Scale(scale=[0.325, 0.325]), Translation(translation=[0.0, 0.0])],
)

tileset = TileModel(
    tilejson="3.0.0",
    name="Mouse cortex section 12",
    description="DAPI + GFAP overlay, 20x objective.",
    version="1.0.0",
    tiles=["http://localhost:8080/tiles/{zlvl}/{x}/{y}.json"],
    minzoom=0,
    maxzoom=10,
    bounds=[0.0, 0.0, 24000.0, 24000.0],
    center=[12000.0, 12000.0, 0.0],
    vector_layers=[cells],
    multiscale=coords,
    scale_factor=2.0,
)

# Round-trip through the root model to confirm it is a valid manifest.
doc = TileJSON.model_validate(tileset.model_dump())
print(doc.root.name)                  # Mouse cortex section 12
print(doc.root.vector_layers[0].id)   # cells
```

!!! note "`multiscale` transforms round-trip losslessly"
    `Multiscale.coordinateTransformations` is a discriminated union of
    `Identity` / `Translation` / `Scale` keyed on `type`, so the concrete
    `scale` / `translation` payloads survive `model_dump()` /
    `model_validate()` and `model_dump_json()` / `model_validate_json()`
    intact. (`AffineTransform` is applied to geometry separately — see
    [Coordinate Transforms](transforms.md) — and is not a member of this list.)

To load a manifest from JSON (e.g. a file served by your tile host), validate the parsed dict:

```python
import json
from mudm import TileJSON

raw = """
{
    "tilejson": "3.0.0",
    "tiles": ["http://localhost:8080/tiles/{zlvl}/{x}/{y}.json"],
    "vector_layers": [{ "id": "cells", "fields": { "name": "string" } }]
}
"""
doc = TileJSON.model_validate(json.loads(raw))
print(doc.root.minzoom, doc.root.maxzoom)  # 0 22  (defaults)
```

### `TileModel` fields

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `tilejson` | `str` | — (required) | TileJSON spec version, e.g. `"3.0.0"`. |
| `tiles` | `list[Path \| URL]` | — (required) | Tile URL/path templates with `{zlvl}` `{x}` `{y}` placeholders. |
| `name` | `str` | `None` | Human-readable dataset name. |
| `description` | `str` | `None` | Free-text description. |
| `version` | `str` | `None` | Version of the tileset (not the spec). |
| `attribution` | `str` | `None` | Attribution string (may contain HTML). |
| `template` | `str` | `None` | Mustache template for interactivity. |
| `legend` | `str` | `None` | Legend content. |
| `scheme` | `str` | `None` | Tile addressing scheme (e.g. `"xyz"`). |
| `grids` | `Path \| URL` | `None` | UTFGrid interaction data location. |
| `data` | `Path \| URL` | `None` | Companion data location. |
| `minzoom` | `int` | `0` | Lowest (most zoomed-out) zoom level. |
| `maxzoom` | `int` | `22` | Highest (most detailed) zoom level. |
| `bounds` | `list[float]` (4–10) | `None` | Bounding box. 4 values for 2D `[minx, miny, maxx, maxy]`; up to 10 for higher-dimensional extents. |
| `center` | `list[float]` (3–6) | `None` | Default center. 3 values for `[x, y, zoom]`; up to 6 for higher dimensions. |
| `fillzoom` | `int` | `None` | Zoom level whose tiles are overzoomed to fill higher levels. |
| `vector_layers` | `list[TileLayer]` | — (required) | The layers carried by the tiles. |
| `multiscale` | `Multiscale` | `None` | Physical coordinate system (see below). |
| `scale_factor` | `float` | `None` | Linear downscale factor between adjacent zoom levels (commonly `2.0`). |
| `assets` | `list[Asset]` | `None` | Typed, dereferenceable data assets (raster, vector, features, tiles3d, download, …) — see [Assets](#assets). |

!!! warning "Length constraints"
    `bounds` must have **4 to 10** floats and `center` **3 to 6** floats. Passing the wrong count raises a `pydantic.ValidationError` — this is exactly the kind of malformed manifest the validation tests reject. See [Validation](validation.md) for how muDM tests accept valid documents and reject malformed ones.

## Layers and field metadata

A `TileLayer` declares one vector layer and, crucially, the *schema and semantics* of its feature properties. Readers use this to build legends, filter UIs, and tooltips without scanning every feature.

```python
from mudm import TileLayer

layer = TileLayer(
    id="cells",
    description="Segmented cell nuclei",
    minzoom=0,
    maxzoom=10,
    # Property name -> type label (free-form, e.g. "String", "Number", "Bool").
    fields={"cellType": "String", "area_um2": "Number"},
    # Min/max (or allowed list) per numeric/ordinal field.
    fieldranges={"area_um2": [0.0, 250.0]},
    # Allowed categorical values per field.
    fieldenums={"cellType": ["neuron", "astrocyte", "microglia"]},
    # Human-readable description per field.
    fielddescriptions={"area_um2": "Cross-sectional area in square microns"},
)
```

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `str` | Unique layer identifier (required). |
| `fields` | `dict[str, str]` | Maps property name to a type label. |
| `minzoom` / `maxzoom` | `int` | Zoom range where this layer is present (defaults `0` / `22`). |
| `description` | `str` | Layer description. |
| `fieldranges` | `dict[str, list]` | Numeric/ordinal range hints per field. |
| `fieldenums` | `dict[str, list[str]]` | Allowed categorical values per field. |
| `fielddescriptions` | `dict[str, str]` | Per-field human-readable descriptions. |
| `vocabularies` | `dict[str, Vocabulary]` | Ontology bindings for property values (see below). |

!!! tip "Deriving the schema automatically"
    You rarely hand-write `fields`, `fieldranges`, and `fieldenums`. The `mudm-tools` tiling pipeline scans a muDM file's feature properties and fills these in for you. See the [2D tiling guide](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/) for the end-to-end recipe.

### Binding fields to an ontology

`vocabularies` maps a field name to a `Vocabulary`, which resolves raw property values to formal ontology terms. This makes the data FAIR-friendly: a downstream tool can turn `"neuron"` into a Cell Ontology URI.

```python
from mudm import TileLayer, Vocabulary, OntologyTerm

layer = TileLayer(
    id="cells",
    fields={"cellType": "String"},
    fieldenums={"cellType": ["neuron", "astrocyte"]},
    vocabularies={
        "cellType": Vocabulary(
            namespace="http://purl.obolibrary.org/obo/CL_",
            description="Cell Ontology types",
            terms={
                "neuron": OntologyTerm(uri="http://purl.obolibrary.org/obo/CL_0000540", label="neuron"),
                "astrocyte": OntologyTerm(uri="http://purl.obolibrary.org/obo/CL_0000127", label="astrocyte"),
            },
        )
    },
)
```

The `Vocabulary` and `OntologyTerm` models are documented in full on the [Ontology Vocabularies](vocabularies.md) guide.

## Assets

Beyond the `{zlvl}/{x}/{y}` tile templates, a `TileModel` can advertise **typed, dereferenceable data assets** through the `assets` field — a list of `Asset` objects. Where `tiles` says *how to fetch one tile*, an `Asset` points at a whole dataset artifact and says how to reach it: the full-resolution raster, a vector/features partition, a 3D Tiles entry point, or a bulk download.

```python
from mudm import TileModel, TileLayer, Asset

tileset = TileModel(
    tilejson="3.0.0",
    tiles=["http://localhost:8080/tiles/{zlvl}/{x}/{y}.json"],
    vector_layers=[TileLayer(id="cells", fields={"name": "string"})],
    assets=[
        Asset(
            role="raster",
            href="https://data.example.org/cortex/raster.ome.tif",
            media_type="image/tiff; application=ome-tiff",
            title="Full-resolution OME-TIFF",
        ),
        Asset(role="features", href="features.parquet",
              media_type="application/vnd.apache.parquet"),
        Asset(role="download", href="cortex.zip"),
    ],
)
print(tileset.assets[0].role)   # raster
```

| `Asset` field | Type | Default | Meaning |
|---------------|------|---------|---------|
| `role` | `str` | — (required) | The asset's role/kind, e.g. `"raster"`, `"vector"`, `"features"`, `"tiles3d"`, `"download"`. |
| `href` | `str` | — (required) | Absolute URL or relative path to the asset. |
| `media_type` | `str` | `None` | IANA media type of the asset (e.g. `"image/tiff"`). |
| `title` | `str` | `None` | Human-readable label. |

!!! tip "Per-asset access hints"
    `Asset` allows extra members, so an emitter may attach access hints such as
    `partitioned`, `range`, or `bytes` alongside the four typed fields above —
    see [Foreign members](#foreign-members).

## Coordinate systems

The `multiscale` field attaches a physical coordinate system to the tileset via `Multiscale`, harmonized with the OME-NGFF model. It answers: what are the axes, in what units, and how do pixel/tile coordinates map to physical space?

```python
from mudm.tilemodel import Multiscale, Axis, AxisType, Unit, Scale, Translation

coords = Multiscale(
    axes=[
        Axis(name="x", type=AxisType.SPACE, unit=Unit.MICROMETER),
        Axis(name="y", type=AxisType.SPACE, unit=Unit.MICROMETER),
        Axis(name="c", type=AxisType.CHANNEL),
        Axis(name="t", type=AxisType.TIME, unit=Unit.MICROMETER),  # any Unit may be attached
    ],
    coordinateTransformations=[
        Scale(scale=[0.325, 0.325, 1.0, 1.0]),       # microns per pixel on x/y
        Translation(translation=[0.0, 0.0, 0.0, 0.0]),
    ],
)
```

### Axes

An `Axis` has a `name`, an optional `type`, an optional `unit`, and a `description`.

`AxisType` is a `StrEnum` with three members:

| `AxisType` | Wire value |
|------------|------------|
| `AxisType.SPACE` | `"space"` |
| `AxisType.TIME` | `"time"` |
| `AxisType.CHANNEL` | `"channel"` |

### Units

`Unit` is a `StrEnum` covering SI length scales plus a few microscopy-relevant extras. Because it is a `StrEnum`, the value equals the lowercase string (`Unit.MICROMETER == "micrometer"`), so it serializes cleanly to JSON.

Notable members:

| `Unit` | Wire value |
|--------|------------|
| `Unit.MICROMETER` | `"micrometer"` |
| `Unit.NANOMETER` | `"nanometer"` |
| `Unit.MILLIMETER` | `"millimeter"` |
| `Unit.METER` | `"meter"` |
| `Unit.CENTIMETER` | `"centimeter"` |
| `Unit.ANGSTROM` | `"angstrom"` |
| `Unit.PIXEL` | `"pixel"` |
| `Unit.DEGREE` | `"degree"` |
| `Unit.RADIAN` | `"radian"` |

The full SI ladder is available too — from `Unit.YOCTOMETER` through `Unit.YOTTAMETER` — along with imperial units (`Unit.INCH`, `Unit.FOOT`, `Unit.YARD`, `Unit.MILE`) and `Unit.PARSEC`.

### Coordinate transformations

`coordinateTransformations` is an ordered list applied in sequence. The `mudm.tilemodel` module defines three OME-aligned transformation types, all subclasses of `CoordinateTransformation`:

| Class | `type` value | Payload |
|-------|--------------|---------|
| `Identity` | `"identity"` | none |
| `Translation` | `"translation"` | `translation: list[float]` |
| `Scale` | `"scale"` | `scale: list[float]` |

```python
from mudm.tilemodel import Identity, Scale, Translation

print(Identity().type)                            # identity
print(Scale(scale=[0.325, 0.325]).type)           # scale
print(Translation(translation=[0.0, 0.0]).type)   # translation
```

!!! tip "A fourth transform: `AffineTransform`"
    A fourth `CoordinateTransformation` subclass, [`AffineTransform`](transforms.md) (`type: "affine"`, a 4×4 matrix), lives in `mudm.transforms`. It is **not** a member of the serialized `coordinateTransformations` list — that list admits only the three types above, the OME/TileJSON wire form. Use `AffineTransform` to apply a full affine to geometry (see [Coordinate Transforms](transforms.md)), or record a single affine in `Multiscale.transformationMatrix`.

`Multiscale` also accepts a raw `transformationMatrix` (`list[list[float]]`) as an alternative to the transformation list — useful when you already have an affine matrix.

!!! tip "Applying transforms to geometry"
    The `multiscale` block *describes* a coordinate system. To actually *apply* transforms to geometry — converting between voxel and physical coordinates, composing affines — see [Coordinate Transforms](transforms.md), which documents `mudm.transforms.AffineTransform` and the voxel/physical helpers.

## Pyramid manifests

A single physical dataset often contains several pyramids at once — for example one per imaging channel. `PyramidJSON` is a top-level manifest that lists them, each as a `PyramidEntry`.

```python
from mudm import PyramidJSON, PyramidEntry

manifest = PyramidJSON(
    pyramids=[
        PyramidEntry(
            id="dapi",
            label="DAPI channel",
            tilejson="dapi/tilejson3d.json",
            features="dapi/features.json",
            tiles=4096,
            feature_count=18234,
            size_bytes=734003200,
        ),
        PyramidEntry(id="gfap", label="GFAP channel"),  # paths fall back to defaults
    ]
)

print(manifest.version)               # 1.0
print(manifest.pyramids[1].tilejson)  # tilejson3d.json  (default)
print(manifest.pyramids[1].features)  # features.json    (default)
```

| `PyramidEntry` field | Type | Default | Meaning |
|----------------------|------|---------|---------|
| `id` | `str` | — (required) | Unique identifier, used as the directory name. |
| `label` | `str` | `None` | Human-readable display label. |
| `kind` | `"2d" \| "3d"` | `None` | Dataset dimensionality (`None` if unspecified). |
| `tilejson` | `str` | `"tilejson3d.json"` | Relative path to the tile metadata file. |
| `features` | `str` | `"features.json"` | Relative path to the muDM `FeatureCollection`. |
| `tiles` | `int` | `None` | Total number of tile files. |
| `feature_count` | `int` | `None` | Number of unique features. |
| `size_bytes` | `int` | `None` | Total size on disk in bytes. |

`PyramidJSON.version` defaults to `"1.0"`.

!!! note "GeoJSON compatibility"
    The `features` file referenced by each pyramid is a standard muDM `FeatureCollection`, which is itself valid GeoJSON. Any GeoJSON is valid muDM, and any muDM document is valid GeoJSON — see the [Core data-model reference](../reference/models.md) for the feature models.

## Foreign members

Every model on this page — `TileModel`, `TileLayer`, `Multiscale`, `Asset`, `PyramidJSON`, and `PyramidEntry` — **allows extra members**. Anything you pass that is not a declared field is preserved on the object and round-trips through `model_dump()` / `model_validate()` untouched, exactly the way [foreign members](../specification.md#mudm-object) work on muDM features.

This lets a producer project a tile or pyramid manifest into a companion metadata vocabulary **in the same document**, rather than emitting a separate sidecar file. The primary use is a [schema.org](https://schema.org/) / [Croissant](https://mlcommons.org/croissant/) projection — `@context`, `@type`, `distribution`, `conformsTo`, … — so a `PyramidJSON` catalog is simultaneously a valid muDM manifest and a discoverable dataset record:

```python
from mudm import PyramidJSON, PyramidEntry

manifest = PyramidJSON(
    pyramids=[PyramidEntry(id="dapi", label="DAPI channel", kind="2d")],
    # foreign members: a schema.org / Croissant projection riding along
    **{
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "name": "Mouse cortex section 12",
        "license": "https://creativecommons.org/licenses/by/4.0/",
    },
)

dumped = manifest.model_dump()
print(dumped["@type"])                 # Dataset
print(dumped["pyramids"][0]["kind"])   # 2d
```

Consumers that only understand muDM ignore the extra members; consumers that understand schema.org/Croissant can index the dataset without a separate manifest. `Asset` allows extra members too, so per-asset access hints (`partitioned`, `range`, `bytes`, …) travel next to `role` / `href`.

## Where the tiling happens

Everything above is metadata. To actually generate pyramids — slicing a `FeatureCollection` into tiles across zoom levels, writing the tile files, and emitting these manifests — use `mudm-tools`, the companion pipeline package:

- [2D tiling guide](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/)
- [3D tiling guide](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/)
- [TileJSON reference](https://novagenresearch.github.io/mudm-tools/reference/tilejson/) — the same `mudm.tilemodel` models, documented from the producer/consumer side.

## API reference

::: mudm.tilemodel.TileJSON

::: mudm.tilemodel.TileModel

::: mudm.tilemodel.TileLayer

::: mudm.tilemodel.Asset

::: mudm.tilemodel.Multiscale

::: mudm.tilemodel.Axis

::: mudm.tilemodel.PyramidJSON

::: mudm.tilemodel.PyramidEntry

## Where to next

- [Coordinate Transforms](transforms.md) — apply the transforms a `Multiscale` describes to actual geometry.
- [Spatial Layout](layout.md) — compute bounds and lay out features in a coordinate system.
- [Ontology Vocabularies](vocabularies.md) — the `Vocabulary` / `OntologyTerm` models used in layer `vocabularies`.
- [Validation](validation.md) — how muDM accepts valid manifests and rejects malformed ones.
- [Core data-model reference](../reference/models.md) — the feature/geometry models that fill the tiles.
- The `mudm-tools` site for the tiling pipelines themselves: [2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/), [3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/), and the [TileJSON reference](https://novagenresearch.github.io/mudm-tools/reference/tilejson/).
