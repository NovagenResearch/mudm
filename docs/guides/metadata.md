# Metadata & Properties

Every muDM feature can carry arbitrary metadata in a `properties` object, and every feature collection can carry metadata that applies to all of its features. This page shows how to attach metadata at both levels, how to use the muDM-specific feature members (`featureClass`, `parentId`, `ref`), and when to reach for a formal ontology vocabulary instead of free-form values.

!!! note "Backwards compatible by design"
    `properties` is the same object GeoJSON has always used. Any GeoJSON feature is a valid muDM feature, and any muDM feature is a valid GeoJSON feature. The muDM additions (`featureClass`, `parentId`, `ref`, `vocabularies`) are optional foreign members that GeoJSON parsers will simply ignore.

## The `properties` object

`properties` is a free-form JSON object hanging off each feature. Values can be any JSON type: strings, numbers, booleans, `null`, arrays, and nested objects. Use it for whatever describes the feature — labels, measurements, acquisition settings, per-channel arrays, and so on.

The two tabs below show the *same document* in both forms: the canonical JSON on the wire, and the [`MuDMFeature`](../reference/models.md) model that produces it. Construct the model from a plain `properties` dict and emit canonical JSON with `model_dump_json`.

=== "Python"

    ```python
    from mudm import MuDMFeature

    feature = MuDMFeature(
        type="Feature",
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [100.0, 0.0],
                [101.0, 0.0],
                [101.0, 1.0],
                [100.0, 1.0],
                [100.0, 0.0],
            ]],
        },
        properties={
            "name": "Sample Polygon",
            "description": "A rectangular ROI.",
            "cellCount": 5000,                    # number
            "ratioInfectivity": [0.2, 0.5, 0.8],  # array
            "acquisition": {                      # nested object
                "channel": "DAPI",
                "exposureMs": 120,
            },
        },
        featureClass="well",
        parentId="plate-1",
        ref="s3://mybucket/well-A1.tif",
    )

    print(feature.model_dump_json(indent=2, exclude_unset=True))
    ```

=== "JSON"

    ```json
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [100.0, 0.0],
            [101.0, 0.0],
            [101.0, 1.0],
            [100.0, 1.0],
            [100.0, 0.0]
          ]
        ]
      },
      "properties": {
        "name": "Sample Polygon",
        "description": "A rectangular ROI.",
        "cellCount": 5000,
        "ratioInfectivity": [0.2, 0.5, 0.8],
        "acquisition": { "channel": "DAPI", "exposureMs": 120 }
      },
      "featureClass": "well",
      "parentId": "plate-1",
      "ref": "s3://mybucket/well-A1.tif"
    }
    ```

!!! tip "`exclude_unset=True`"
    Passing `exclude_unset=True` keeps optional members you never set (like `bbox` or `vocabularies`) out of the output, so the JSON stays close to what you typed.

## Feature-level vs. collection-level properties

Properties exist at two levels, and the distinction matters:

| Level | Where it lives | Scope |
| --- | --- | --- |
| Feature-level | `properties` on each `MuDMFeature` | Describes that single feature only |
| Collection-level | `properties` on the `MuDMFeatureCollection` | Shared context that applies to every feature in the collection |

Put per-object measurements (a cell's area, a well's infectivity ratio) on the individual feature. Put shared experimental context (pixel size, stain, experiment ID) on the collection so you write it once instead of repeating it on every feature.

```python
from mudm import MuDMFeature, MuDMFeatureCollection

region = MuDMFeature(
    type="Feature",
    id="region-1",
    geometry={
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0], [0.0, 200.0], [200.0, 200.0], [200.0, 0.0], [0.0, 0.0],
        ]],
    },
    properties={"name": "Cortex ROI"},
    featureClass="region",
)

cell = MuDMFeature(
    type="Feature",
    id="cell-1",
    geometry={"type": "Point", "coordinates": [100.0, 100.0]},
    properties={"cellType": "pyramidal neuron", "area": 42.5},
    featureClass="cell",
    parentId="region-1",  # this cell belongs to region-1
)

collection = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[region, cell],
    properties={                 # applies to ALL features below
        "experiment": "exp-2026-05",
        "pixelSizeUm": 0.325,
        "stain": "Nissl",
    },
)

print(collection.model_dump_json(indent=2, exclude_unset=True))
```

!!! note "muDM does not auto-merge the two levels"
    Collection-level `properties` is *shared context*, not an inherited default. The model stores both objects as-is; deciding how to combine them (for example, treating `pixelSizeUm` as the default for features that lack their own) is up to your application code.

## muDM feature members: `featureClass`, `parentId`, `ref`

Beyond `properties`, `MuDMFeature` adds three optional top-level members. They live *next to* `properties` (not inside it) because they have defined meaning across muDM tooling.

| Member | Type | Purpose |
| --- | --- | --- |
| `featureClass` | string | The kind of thing this feature is (`"cell"`, `"well"`, `"region"`). A lightweight type label. |
| `parentId` | string or int | The `id` of another feature this one belongs to. Builds parent/child hierarchies. |
| `ref` | string or int | A reference to external data this feature points at — for example a file URI or an external record id. |

The `parentId` of the child should match the `id` of the parent feature. In the example above, `cell-1` sets `parentId="region-1"` to record that the cell sits inside the cortex ROI. Use `ref` when a feature is backed by an external artifact, such as a source image:

```python
from mudm import MuDMFeature

path = MuDMFeature(
    type="Feature",
    id="2",
    geometry={
        "type": "LineString",
        "coordinates": [[100.0, 100.0], [200.0, 200.0], [300.0, 100.0]],
    },
    properties={"name": "Cell Path", "color": "blue"},
    featureClass="cellpath",
    ref="s3://mybucket/myfile.tif",  # external data this feature references
)

print(path.model_dump_json(indent=2, exclude_unset=True))
```

Because these are foreign members, a plain GeoJSON parser ignores them while muDM tooling can act on them. See [Validation](validation.md) for how documents are checked and the [Core data-model API](../reference/models.md) for the full field reference.

## Free-form properties vs. formal vocabularies

Free-form `properties` are perfect for prototyping and for values that are local to one dataset. But strings like `"pyramidal neuron"` are ambiguous across labs and tools — spelling, casing, and synonyms drift. When you need values that are machine-comparable and traceable to a shared standard, attach a `Vocabulary` that maps property values to formal ontology terms.

```python
from mudm import MuDMFeature, MuDMFeatureCollection, Vocabulary, OntologyTerm

cell = MuDMFeature(
    type="Feature",
    id="cell-1",
    geometry={"type": "Point", "coordinates": [100.0, 100.0]},
    properties={"cellType": "pyramidal neuron"},  # free-form value...
    featureClass="cell",
)

collection = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[cell],
    vocabularies={
        # ...grounded to a formal ontology term
        "cellType": Vocabulary(
            namespace="http://purl.obolibrary.org/obo/CL_",
            terms={
                "pyramidal neuron": OntologyTerm(
                    uri="http://purl.obolibrary.org/obo/CL_0000598",
                    label="pyramidal neuron",
                ),
            },
        ),
    },
)

print(collection.model_dump_json(indent=2, exclude_unset=True))
```

Here the feature still carries a plain `"cellType": "pyramidal neuron"` value, but the collection's `vocabularies` block records exactly which ontology term that value means. `vocabularies` is available on both `MuDMFeature` and `MuDMFeatureCollection`. For the full mapping rules, term structure, and guidance on choosing ontologies, see [Vocabularies](vocabularies.md).

!!! note "Two packages, one ecosystem"
    Everything on this page is the core **`mudm`** data model — pure Python, no compiled component. Once your features carry the right metadata, the separate **`mudm-tools`** package (import name `mudm_tools`) turns them into tiles, converts real datasets, and visualizes them. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

## Where to next

- [Vocabularies](vocabularies.md) — map property values to formal ontology terms (`OntologyTerm` / `Vocabulary`).
- [Validation](validation.md) — how muDM documents are validated.
- [Provenance & Traceability](provenance.md) — record where a collection came from.
- [Worked examples](examples.md) — end-to-end muDM documents you can copy.
- [Core data-model API](../reference/models.md) — the full `MuDMFeature` / `MuDMFeatureCollection` field reference.
- For tiling pipelines, converters, and Rust-accelerated processing, head to the [mudm-tools Getting Started guide](https://novagenresearch.github.io/mudm-tools/getting-started/).
