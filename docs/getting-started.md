# Getting Started

This quickstart walks you through the four things you do most with `mudm`, end to end:

- **[1. Build your first feature](#build-your-first-feature)** — pair a geometry with microscopy metadata.
- **[2. Assemble a feature collection](#assemble-a-feature-collection)** — group features and attach collection-level metadata.
- **[3. Validate incoming data](#validate-incoming-data)** — parse a `dict` or a JSON string into typed models.
- **[4. Serialize and round-trip](#serialize-and-round-trip)** — write models back to `dict` / JSON for any GeoJSON-aware tool.

muDM (micro Data Model) is a GeoJSON-inspired data model. Backwards compatibility is a design goal: **any GeoJSON document is valid muDM, and any muDM document is valid GeoJSON.** If you already know GeoJSON, you already know most of muDM.

!!! note "Prerequisites"
    Make sure `mudm` is installed first — see **[Installation](installation.md)**. The quickest path is `pip install mudm`. Core muDM is pure Python with no compiled component, so there is nothing to build. Every example below runs top-to-bottom against the current `mudm`.

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

---

## Build your first feature

A `MuDMFeature` is a GeoJSON `Feature` with optional microscopy metadata. It pairs a geometry with a free-form `properties` dictionary. Geometry types come from `geojson-pydantic`, so import them directly.

```python
from mudm import MuDMFeature
from geojson_pydantic import Point

feature = MuDMFeature(
    type="Feature",
    geometry=Point(type="Point", coordinates=(10.0, 20.0)),
    properties={"label": "nucleus", "area": 42.0},
    featureClass="cell",
)

print(feature.model_dump_json(indent=2, exclude_unset=True))
```

This prints the GeoJSON wire format. Note that the muDM extension field uses camelCase on the wire (`featureClass`):

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [
      10.0,
      20.0
    ]
  },
  "properties": {
    "label": "nucleus",
    "area": 42.0
  },
  "featureClass": "cell"
}
```

!!! tip "Keep output compact"
    `exclude_unset=True` omits fields you never set (such as `parentId`, `ref`, or `vocabularies`). Drop it to see every field, including those left at their defaults.

The muDM-specific fields on `MuDMFeature` are all optional:

| Field | Wire name | Type | Purpose |
| --- | --- | --- | --- |
| `featureClass` | `featureClass` | `str` | Semantic class of the feature, e.g. `"cell"`, `"nucleus"`. |
| `parentId` | `parentId` | `str` or `int` | Reference to a parent feature's id (hierarchies). |
| `ref` | `ref` | `str` or `int` | A reference to an external resource holding the feature's data (e.g. a store/file URI). |
| `vocabularies` | `vocabularies` | mapping or `str` | Maps property values to formal ontology terms. |

Everything else (`type`, `geometry`, `properties`, `id`, `bbox`) is standard GeoJSON.

---

## Assemble a feature collection

A `MuDMFeatureCollection` groups features and can carry collection-level `properties` and `provenance`.

```python
from mudm import MuDMFeature, MuDMFeatureCollection
from geojson_pydantic import Point, Polygon

nucleus = MuDMFeature(
    type="Feature",
    geometry=Point(type="Point", coordinates=(10.0, 20.0)),
    properties={"label": "nucleus"},
    featureClass="organelle",
)

cell = MuDMFeature(
    type="Feature",
    geometry=Polygon(
        type="Polygon",
        coordinates=[[(0.0, 0.0), (0.0, 30.0), (30.0, 30.0), (30.0, 0.0), (0.0, 0.0)]],
    ),
    properties={"label": "cell membrane"},
    featureClass="cell",
)

collection = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[nucleus, cell],
    properties={"image": "slide_001.ome.tif"},
)

print(collection.model_dump_json(indent=2, exclude_unset=True))
```

The collection-level `provenance` field accepts a `Workflow` or `Artifact` (and their collection forms) to record how the data was produced. See **[Provenance & Traceability](guides/provenance.md)** for the full picture.

---

## Validate incoming data

When data arrives from a file, an API, or another tool, validate it against the model. Use `MuDM` — the root model that accepts a feature, a feature collection, or a bare geometry. Two equivalent entry points exist depending on whether you have a Python object or raw text.

=== "Python (dict)"

    Validate a Python `dict` with `model_validate`:

    ```python
    from mudm import MuDM

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

    obj = MuDM.model_validate(data)
    print(type(obj.root).__name__)  # MuDMFeatureCollection
    ```

=== "JSON (string)"

    Validate a JSON string directly with `model_validate_json` — no `json.loads` needed:

    ```python
    from mudm import MuDM

    raw = '{"type": "Point", "coordinates": [10, 20]}'
    obj = MuDM.model_validate_json(raw)
    print(type(obj.root).__name__)  # Point
    ```

A `pydantic.ValidationError` is raised if the data does not conform. See **[Validation](guides/validation.md)** for how to handle and interpret these errors.

!!! note "Plain GeoJSON"
    To validate a document strictly as GeoJSON (without muDM extensions), use the `GeoJSON` root model instead. Because any GeoJSON is valid muDM, `GeoJSON.model_validate(data)` succeeds on the same inputs.

    ```python
    from mudm import GeoJSON

    GeoJSON.model_validate(data)  # validates as plain GeoJSON
    ```

---

## Serialize and round-trip

Every model is a standard Pydantic v2 model, so the usual serialization helpers apply. Parse JSON into a model, then emit it as a `dict` or a JSON string.

=== "Python (dict)"

    `model_dump` returns a plain Python `dict` — handy for re-embedding in a larger structure or passing to another library.

    ```python
    from mudm import MuDM

    raw = '''{
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [10, 20]},
          "properties": {"label": "nucleus"},
          "featureClass": "cell"
        }
      ]
    }'''

    obj = MuDM.model_validate_json(raw)

    as_dict = obj.model_dump(exclude_unset=True)
    print(as_dict)
    ```

=== "JSON (string)"

    `model_dump_json` returns a JSON string — ready to write to disk or send over the wire.

    ```python
    from mudm import MuDM

    raw = '''{
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": {"type": "Point", "coordinates": [10, 20]},
          "properties": {"label": "nucleus"},
          "featureClass": "cell"
        }
      ]
    }'''

    obj = MuDM.model_validate_json(raw)

    as_json = obj.model_dump_json(indent=2, exclude_unset=True)
    print(as_json)
    ```

Because the output is valid GeoJSON, you can hand `as_dict` or `as_json` to any GeoJSON-aware tool — map viewers, GIS libraries, or web clients — without conversion.

---

## Next steps

Now that you've round-tripped data through the core model, go deeper:

- **[Specification](specification.md)** — the formal muDM specification: features, collections, geometries, and metadata fields.
- **[Examples](guides/examples.md)** — a worked-example gallery you can copy from.
- **[Metadata & Properties](guides/metadata.md)** — modelling free-form and structured metadata on features.
- **[Coordinate Transforms](guides/transforms.md)** — affine transforms and voxel/physical coordinate conversions.
- **[Tile Metadata](guides/tiles.md)** — tile metadata models (`TileJSON`, `TileModel`, `PyramidJSON`) for large pyramidal images.
- **[Provenance & Traceability](guides/provenance.md)** — tracking workflows and artifacts with `Workflow` and `Artifact`.
- **[Validation](guides/validation.md)** — validating documents and interpreting errors.
- **[Core data-model API](reference/models.md)** — the full Pydantic model reference.

Ready to process, tile, or convert your data? That work lives in the separate **`mudm-tools`** package — start at the **[mudm-tools docs site](https://novagenresearch.github.io/mudm-tools/)** (see its **[Getting Started](https://novagenresearch.github.io/mudm-tools/getting-started/)**, **[2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/)**, **[3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/)**, and **[converters](https://novagenresearch.github.io/mudm-tools/guides/converters/)** guides).
