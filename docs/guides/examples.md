# Examples

A gallery of worked muDM documents. Each example shows the **JSON wire format** and, where it clarifies the API, the **equivalent Python** using the public `mudm` package. Every Python snippet is runnable top to bottom against the current `mudm`.

!!! note "muDM is GeoJSON"
    Every example here is also valid GeoJSON: standard `Feature` / `FeatureCollection` objects with `type`, `geometry`, and `properties`. muDM only *adds* optional fields (`featureClass`, `parentId`, `ref`, `vocabularies`, `provenance`) and new geometry types (`TIN`, `PolyhedralSurface`). Any GeoJSON document is valid muDM, and any muDM document is valid GeoJSON.

The public API used below comes from the package surface in `mudm` and `mudm.tilemodel`:

```python
from mudm import (
    MuDM, MuDMFeature, MuDMFeatureCollection,
    TIN, PolyhedralSurface,
    OntologyTerm, Vocabulary,
    TileModel, TileJSON,
)
from mudm.tilemodel import Multiscale, Axis, Scale, Unit, AxisType, TileLayer
```

See also: [Validation](validation.md), [Coordinate Transforms](transforms.md), [Provenance](provenance.md), [Vocabularies](vocabularies.md), and the [Core data-model API](../reference/models.md).

---

## 1. Polygon features with flat properties

The most common shape: a `FeatureCollection` of polygons, each carrying simple key/value `properties` (numbers, strings, booleans, lists). This is plain GeoJSON.

=== "JSON"

    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
          },
          "properties": { "id": 1, "label": "nucleus", "area": 100.0 }
        },
        {
          "type": "Feature",
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]]
          },
          "properties": { "id": 2, "label": "nucleus", "area": 100.0 }
        }
      ]
    }
    ```

=== "Python"

    ```python
    from mudm import MuDMFeature, MuDMFeatureCollection

    fc = MuDMFeatureCollection(
        type="FeatureCollection",
        features=[
            MuDMFeature(
                type="Feature",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]],
                },
                properties={"id": 1, "label": "nucleus", "area": 100.0},
            ),
            MuDMFeature(
                type="Feature",
                geometry={
                    "type": "Polygon",
                    "coordinates": [[[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]],
                },
                properties={"id": 2, "label": "nucleus", "area": 100.0},
            ),
        ],
    )

    assert fc.features[0].properties["label"] == "nucleus"
    print(fc.model_dump_json(exclude_none=True))
    ```

!!! tip "Closed rings"
    A polygon ring must repeat its first position as its last (here `[0, 0]` … `[0, 0]`). This is the standard GeoJSON closure rule, enforced by validation.

---

## 2. Point with a radius (circular object)

For round objects (cell centroids, detected spots), store a single `Point` and put the radius in `properties`. The point marks the center; `radius` describes the circle in the same coordinate units.

=== "JSON"

    ```json
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [256, 512] },
      "properties": { "type": "Point", "radius": 15.0, "label": "nucleus" }
    }
    ```

=== "Python"

    ```python
    from mudm import MuDMFeature

    spot = MuDMFeature(
        type="Feature",
        geometry={"type": "Point", "coordinates": [256, 512]},
        properties={"type": "Point", "radius": 15.0, "label": "nucleus"},
    )

    assert spot.properties["radius"] == 15.0
    ```

---

## 3. A multiscale coordinate system (axes + scale)

Microscopy coordinates are usually expressed in pixels/voxels, with a known physical size per pixel. A `Multiscale` records the named **axes** (with units) and the **coordinate transformations** that map index space to physical space. Here a `Scale` transformation says "each pixel is 0.5 µm on x and y".

=== "JSON"

    ```json
    {
      "axes": [
        { "name": "x", "type": "space", "unit": "micrometer" },
        { "name": "y", "type": "space", "unit": "micrometer" }
      ],
      "coordinateTransformations": [
        { "type": "scale", "scale": [0.5, 0.5] }
      ]
    }
    ```

=== "Python"

    Build it with the public `tilemodel` classes. A `Multiscale` is most often attached to a `TileModel` (the tileset metadata) rather than to an individual feature:

    ```python
    from mudm import TileModel, TileJSON
    from mudm.tilemodel import Multiscale, Axis, Scale, Unit, AxisType, TileLayer

    multiscale = Multiscale(
        axes=[
            Axis(name="x", type=AxisType.SPACE, unit=Unit.MICROMETER),
            Axis(name="y", type=AxisType.SPACE, unit=Unit.MICROMETER),
        ],
        coordinateTransformations=[Scale(scale=[0.5, 0.5])],
    )

    assert multiscale.axes[0].unit == Unit.MICROMETER
    assert multiscale.coordinateTransformations[0].scale == [0.5, 0.5]

    tileset = TileModel(
        tilejson="3.0.0",
        tiles=["{z}/{x}/{y}.pbf"],
        vector_layers=[TileLayer(id="cells", fields={"label": "String"})],
        multiscale=multiscale,
    )
    # coordinateTransformations round-trips losslessly through model_dump.
    reloaded = TileJSON.model_validate(tileset.model_dump()).root
    assert reloaded.multiscale.axes[0].name == "x"
    assert reloaded.multiscale.coordinateTransformations[0].scale == [0.5, 0.5]
    ```

`Unit` and `AxisType` are enums — `Unit.MICROMETER`, `Unit.NANOMETER`, `Unit.PIXEL`, … and `AxisType.SPACE / TIME / CHANNEL`. See [Coordinate Transforms](transforms.md) for applying transforms to geometry (`apply_transform`, `voxel_to_physical`) and [Tile Metadata](tiles.md) for the full `TileModel` / `TileJSON` surface.

!!! note "`coordinateTransformations` round-trips losslessly"
    `Multiscale.coordinateTransformations` is a discriminated union of `Identity` / `Translation` / `Scale` keyed on `type`, so the concrete `scale` / `translation` values survive `model_dump()` / `model_validate()` (and the JSON variants) intact.

---

## 4. 3D surface mesh (TIN)

`TIN` (Triangulated Irregular Network) is a triangle-mesh surface geometry from ISO 19107, added by muDM on top of GeoJSON. Each **face** is one closed triangle: a single ring of exactly **4 positions** (3 vertices plus a repeat of the first to close it). Coordinates are 3D `[x, y, z]`.

=== "JSON"

    ```json
    {
      "type": "Feature",
      "geometry": {
        "type": "TIN",
        "coordinates": [
          [[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]],
          [[[1, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]]]
        ]
      },
      "properties": { "featureClass": "membrane", "region": "CA1" }
    }
    ```

=== "Python"

    ```python
    from mudm import MuDMFeature, TIN

    mesh = TIN(
        type="TIN",
        coordinates=[
            [[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]],
            [[[1, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0, 0]]],
        ],
    )
    assert mesh.bbox3d() == (0, 0, 0, 1, 1, 0)
    assert mesh.centroid3d() is not None

    feature = MuDMFeature(
        type="Feature",
        geometry=mesh,
        properties={"featureClass": "membrane", "region": "CA1"},
    )
    print(feature.model_dump_json(exclude_none=True))
    ```

Each `TIN` exposes `bbox3d()` and `centroid3d()` helpers. A face that is not exactly 4 positions fails validation:

```python
from pydantic import ValidationError
from mudm import TIN

try:
    TIN(type="TIN", coordinates=[[[[0, 0, 0], [1, 0, 0], [0, 0, 0]]]])  # 3 positions
    raise AssertionError("expected a ValidationError")
except ValidationError:
    pass  # a triangular face must have exactly 4 positions
```

!!! note "PolyhedralSurface for general meshes"
    For surfaces whose faces are arbitrary polygons (not just triangles), use `PolyhedralSurface`. It has the same `coordinates` structure (a list of polygon faces) and the same `bbox3d()` / `centroid3d()` helpers, but does not require 4-position triangular faces:

    ```python
    from mudm import PolyhedralSurface

    surf = PolyhedralSurface(
        type="PolyhedralSurface",
        coordinates=[[[[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]]]],
    )
    assert surf.bbox3d() == (0, 0, 0, 1, 1, 0)
    ```

    Both `TIN` and `PolyhedralSurface` can also reference external tiled data instead of inline coordinates via a `tiles` field (e.g. `tiles=["0/0/0/0"]` with empty `coordinates`). In tiled mode `bbox3d()` / `centroid3d()` return `None`. The pipelines that produce these tiles live in `mudm-tools` — see its [3D tiling guide](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/).

---

## 5. Image feature (Rectangle + URI)

To reference a raster image (a tile, a field of view, a whole slide), use a rectangular `Polygon` for its footprint and describe it with `properties`: `type: "Image"`, a `subtype` of `Rectangle`, and a `URI` pointing at the pixel data.

=== "JSON"

    ```json
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1024, 0], [1024, 1024], [0, 1024], [0, 0]]]
      },
      "properties": {
        "type": "Image",
        "subtype": "Rectangle",
        "URI": "./image_001.ome.tif"
      }
    }
    ```

=== "Python"

    ```python
    from mudm import MuDMFeature

    image = MuDMFeature(
        type="Feature",
        geometry={
            "type": "Polygon",
            "coordinates": [[[0, 0], [1024, 0], [1024, 1024], [0, 1024], [0, 0]]],
        },
        properties={
            "type": "Image",
            "subtype": "Rectangle",
            "URI": "./image_001.ome.tif",
        },
    )
    assert image.properties["type"] == "Image"
    ```

The rectangle's coordinates give the image footprint in the parent coordinate system; combine with a [multiscale](#3-a-multiscale-coordinate-system-axes-scale) to place pixels in physical space. To turn an OME-NGFF / OME-TIFF raster pyramid into tiles, see the `mudm-tools` [OME-NGFF guide](https://novagenresearch.github.io/mudm-tools/guides/ome-ngff/).

---

## 6. Hierarchy: `featureClass`, `parentId`, `ref`

muDM features carry first-class fields for typing and linking objects — these are real model fields, serialized in **camelCase** on the wire:

| Field | Type | Purpose |
| --- | --- | --- |
| `featureClass` | `str` | The class/category of the feature (e.g. `"neuron"`, `"synapse"`). |
| `parentId` | `str` or `int` | Identifies the parent feature this one belongs to. |
| `ref` | `str` or `int` | A reference to an **external resource** holding the feature's data (e.g. a store/file URI). Distinct from `parentId`, which links to another feature. |

A parent neuron and a child synapse: `parentId` links the synapse back to its neuron, while `ref` points the neuron at an external store holding its raw data:

=== "JSON"

    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "id": "neuron-001",
          "geometry": { "type": "Point", "coordinates": [0, 0] },
          "properties": { "label": "L5 pyramidal" },
          "featureClass": "neuron",
          "ref": "s3://bucket/neurons/neuron-001.zarr"
        },
        {
          "type": "Feature",
          "geometry": { "type": "Point", "coordinates": [5, 5] },
          "properties": {},
          "featureClass": "synapse",
          "parentId": "neuron-001"
        }
      ]
    }
    ```

=== "Python"

    ```python
    from mudm import MuDMFeature, MuDMFeatureCollection

    parent = MuDMFeature(
        type="Feature",
        id="neuron-001",
        geometry={"type": "Point", "coordinates": [0, 0]},
        properties={"label": "L5 pyramidal"},
        featureClass="neuron",
        ref="s3://bucket/neurons/neuron-001.zarr",  # external resource
    )
    child = MuDMFeature(
        type="Feature",
        geometry={"type": "Point", "coordinates": [5, 5]},
        properties={},
        featureClass="synapse",
        parentId="neuron-001",  # links to the parent feature
    )

    fc = MuDMFeatureCollection(type="FeatureCollection", features=[parent, child])
    assert fc.features[1].parentId == "neuron-001"
    assert fc.features[1].featureClass == "synapse"
    assert fc.features[0].ref == "s3://bucket/neurons/neuron-001.zarr"
    ```

For more on first-class fields versus free-form `properties`, see [Metadata & Properties](metadata.md).

---

## 7. Ontology vocabularies

To make property values machine-interpretable, attach a `vocabularies` map that links each value to a formal `OntologyTerm` (a URI plus an optional label). Vocabularies can sit on a feature or on a `FeatureCollection`.

=== "JSON"

    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": { "type": "Point", "coordinates": [5, 5] },
          "properties": { "cellType": "pyramidal neuron" }
        }
      ],
      "vocabularies": {
        "cellType": {
          "namespace": "http://purl.obolibrary.org/obo/CL_",
          "terms": {
            "pyramidal neuron": {
              "uri": "http://purl.obolibrary.org/obo/CL_0000598",
              "label": "pyramidal neuron"
            }
          }
        }
      }
    }
    ```

=== "Python"

    ```python
    from mudm import MuDMFeature, MuDMFeatureCollection, OntologyTerm, Vocabulary

    cell_types = Vocabulary(
        namespace="http://purl.obolibrary.org/obo/CL_",
        terms={
            "pyramidal neuron": OntologyTerm(
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
                geometry={"type": "Point", "coordinates": [5, 5]},
                properties={"cellType": "pyramidal neuron"},
            )
        ],
        vocabularies={"cellType": cell_types},
    )

    term = fc.vocabularies["cellType"].terms["pyramidal neuron"]
    assert term.uri == "http://purl.obolibrary.org/obo/CL_0000598"
    ```

See [Vocabularies](vocabularies.md) for the full model, including per-layer vocabularies on tile layers.

---

## Validating any of the above

Use the `MuDM` root model to validate a complete document parsed from JSON or built in Python:

```python
import json
from mudm import MuDM

doc = json.loads(fc.model_dump_json())
parsed = MuDM.model_validate(doc)          # raises pydantic.ValidationError if invalid
assert parsed.root.features[0].properties["cellType"] == "pyramidal neuron"
```

See [Validation](validation.md) for the `GeoJSON` vs `MuDM` root models and error handling.

---

## Where to next

- [Validation](validation.md) — the `GeoJSON` vs `MuDM` root models and how parse errors are reported.
- [Coordinate Transforms](transforms.md) — `apply_transform`, `translate_geometry`, and voxel↔physical conversion.
- [Spatial Layout](layout.md) — computing bounds and laying out collections in space.
- [Tile Metadata](tiles.md) — `TileModel`, `TileJSON`, and per-layer field descriptions.
- [Vocabularies](vocabularies.md) — `OntologyTerm` / `Vocabulary` in full.
- [Provenance & Traceability](provenance.md) — recording how a document was produced.
- [Core data-model API](../reference/models.md) — the autodoc reference for every model on this page.

!!! note "Two packages, one ecosystem"
    `mudm` (this package) is the **core data model** — the models, validation, transforms, and provenance shown above. It is pure Python with no compiled component. For building tilesets, converting real datasets (e.g. 10x Xenium, OBJ, GeoJSON), GeoParquet / glTF interop, and Rust-accelerated tiling, use the separate **`mudm-tools`** package (import name `mudm_tools`). Start at its [Getting Started](https://novagenresearch.github.io/mudm-tools/getting-started/) and its [Converters](https://novagenresearch.github.io/mudm-tools/guides/converters/) and [GeoParquet & glTF](https://novagenresearch.github.io/mudm-tools/guides/geoparquet-gltf/) guides. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.
