# Ontology Vocabularies

Attach formal ontology meaning to the free-text values you store in a muDM feature's `properties`. By mapping a human-friendly string like `"pyramidal"` to a stable URI such as `http://purl.obolibrary.org/obo/CL_0000598`, your data becomes machine-resolvable against community ontologies (Cell Ontology, UBERON, and others) — without changing the simple strings biologists actually read.

!!! note "Fully optional and backwards compatible"
    Vocabularies are an additive layer. Any GeoJSON is valid muDM and any muDM document is valid GeoJSON — the `vocabularies` member is optional and defaults to `None`. Existing data and existing readers are unaffected.

## Why vocabularies?

A muDM feature carries arbitrary key/value metadata in its GeoJSON `properties`:

```python
from mudm import MuDMFeature
from geojson_pydantic import Point

feat = MuDMFeature(
    type="Feature",
    geometry=Point(type="Point", coordinates=(1.0, 2.0)),
    properties={"cell_type": "pyramidal", "brain_region": "hippocampus_CA1"},
)
```

Strings like `"pyramidal"` are convenient for humans but ambiguous for machines: another lab might write `"pyr"`, `"pyramidal cell"`, or `"PC"` for the same concept. A **vocabulary** records, alongside the data, exactly which ontology term each value stands for. Tools can then resolve `"pyramidal"` to a canonical URI, follow it to an ontology, and reason about it (e.g. "is this a subtype of neuron?").

muDM models this with two small, plain objects, both importable from the top-level package:

| Object | Role |
| --- | --- |
| [`OntologyTerm`](#api-reference) | A single term: a required `uri`, plus an optional human `label` and `description`. |
| [`Vocabulary`](#api-reference) | A mapping for one property: an optional `namespace` and `description`, plus a `terms` dict from property value to `OntologyTerm`. |

## The building blocks

### `OntologyTerm`

A term is a reference to an entry in some ontology. Only `uri` is required.

```python
from mudm import OntologyTerm

# Full term
term = OntologyTerm(
    uri="http://purl.obolibrary.org/obo/CL_0000598",
    label="pyramidal neuron",
    description="A projection neuron",
)

# Minimal term — just the URI
minimal = OntologyTerm(uri="http://example.org/term/1")
assert minimal.label is None
assert minimal.description is None
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `uri` | `str` | yes | Full URI of the ontology term, e.g. `http://purl.obolibrary.org/obo/CL_0000598`. |
| `label` | `str` or `None` | no | Human-readable label, e.g. `"pyramidal neuron"`. |
| `description` | `str` or `None` | no | Optional longer description of the term. |

### `Vocabulary`

A `Vocabulary` describes the allowed values for a single property and maps each value to its term. The `terms` dict is keyed by the exact string that appears in `properties`.

```python
from mudm import OntologyTerm, Vocabulary

cell_types = Vocabulary(
    namespace="http://purl.obolibrary.org/obo/CL_",
    description="Cell ontology",
    terms={
        "pyramidal": OntologyTerm(
            uri="http://purl.obolibrary.org/obo/CL_0000598",
            label="pyramidal neuron",
        ),
        "interneuron": OntologyTerm(
            uri="http://purl.obolibrary.org/obo/CL_0000099",
        ),
    },
)

assert "pyramidal" in cell_types.terms
assert cell_types.namespace == "http://purl.obolibrary.org/obo/CL_"
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `namespace` | `str` or `None` | no | Common URI prefix for the ontology, e.g. `http://purl.obolibrary.org/obo/CL_`. |
| `description` | `str` or `None` | no | Optional description of the vocabulary. |
| `terms` | `dict[str, OntologyTerm]` | yes | Mapping from a property value (the dict key) to its `OntologyTerm`. |

A minimal vocabulary needs only `terms`:

```python
from mudm import OntologyTerm, Vocabulary

v = Vocabulary(terms={"a": OntologyTerm(uri="http://example.org/a")})
assert v.namespace is None
```

## Attaching vocabularies to data

Both `MuDMFeature` and `MuDMFeatureCollection` expose a `vocabularies` member with the same signature:

```python
vocabularies: Optional[Union[Dict[str, Vocabulary], str]] = None
```

It accepts **either** of two shapes:

- a **dict** `{propertyName: Vocabulary}` — inline definitions, keyed by property name; or
- a **string URI** pointing to an external vocabulary document.

### Inline vocabularies on a collection

Define vocabularies once on the collection and let every feature inherit them. The dict key (`"cell_type"`) matches the property key used inside `properties`.

```python
from mudm import MuDMFeature, MuDMFeatureCollection, OntologyTerm, Vocabulary
from geojson_pydantic import Point

fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(
            type="Feature",
            geometry=Point(type="Point", coordinates=(1.0, 2.0)),
            properties={"cell_type": "pyramidal"},
        ),
    ],
    vocabularies={
        "cell_type": Vocabulary(
            namespace="http://purl.obolibrary.org/obo/CL_",
            terms={
                "pyramidal": OntologyTerm(
                    uri="http://purl.obolibrary.org/obo/CL_0000598",
                    label="pyramidal neuron",
                ),
            },
        ),
    },
)

assert "cell_type" in fc.vocabularies
assert fc.vocabularies["cell_type"].terms["pyramidal"].label == "pyramidal neuron"
```

### Referencing an external vocabulary document

For large or shared vocabularies, store a URI instead of inlining. The value is a plain string; resolving and fetching it is left to the consuming tool.

=== "On a collection"

    ```python
    from mudm import MuDMFeature, MuDMFeatureCollection
    from geojson_pydantic import Point

    fc = MuDMFeatureCollection(
        type="FeatureCollection",
        features=[
            MuDMFeature(
                type="Feature",
                geometry=Point(type="Point", coordinates=(1.0, 2.0)),
                properties={},
            ),
        ],
        vocabularies="https://neuromorpho.org/vocab/neuroscience-v1.json",
    )

    assert fc.vocabularies == "https://neuromorpho.org/vocab/neuroscience-v1.json"
    ```

=== "On a feature"

    ```python
    from mudm import MuDMFeature
    from geojson_pydantic import Point

    feat = MuDMFeature(
        type="Feature",
        geometry=Point(type="Point", coordinates=(1.0, 2.0)),
        properties={},
        vocabularies="https://example.org/vocab.json",
    )
    assert feat.vocabularies == "https://example.org/vocab.json"
    ```

### Multiple property vocabularies on one collection

The dict form lets one collection carry independent vocabularies for several properties — for example a cell-type vocabulary drawn from Cell Ontology and a brain-region vocabulary drawn from UBERON.

```python
from mudm import MuDMFeature, MuDMFeatureCollection, OntologyTerm, Vocabulary
from geojson_pydantic import Point

fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(
            type="Feature",
            geometry=Point(type="Point", coordinates=(1.0, 2.0)),
            properties={"cell_type": "pyramidal", "brain_region": "hippocampus_CA1"},
        ),
    ],
    vocabularies={
        "cell_type": Vocabulary(
            namespace="http://purl.obolibrary.org/obo/CL_",
            terms={
                "pyramidal": OntologyTerm(uri="http://purl.obolibrary.org/obo/CL_0000598"),
            },
        ),
        "brain_region": Vocabulary(
            namespace="http://purl.obolibrary.org/obo/UBERON_",
            terms={
                "hippocampus_CA1": OntologyTerm(
                    uri="http://purl.obolibrary.org/obo/UBERON_0003881"
                ),
            },
        ),
    },
)

assert len(fc.vocabularies) == 2
assert (
    fc.vocabularies["brain_region"].terms["hippocampus_CA1"].uri
    == "http://purl.obolibrary.org/obo/UBERON_0003881"
)
```

## Resolution order: feature overrides collection

A feature may define its own `vocabularies` to override the collection's for the same property. The model does not merge these for you — resolution is a deliberate choice made by the reader. The canonical pattern is a single `or`: prefer the feature's vocabularies, falling back to the collection's when the feature has none.

```python
resolved = feat.vocabularies or fc.vocabularies
```

A full example where the feature wins:

```python
from mudm import MuDMFeature, MuDMFeatureCollection, OntologyTerm, Vocabulary
from geojson_pydantic import Point

collection_vocab = {
    "cell_type": Vocabulary(
        terms={"pyramidal": OntologyTerm(uri="http://example.org/COLLECTION")},
    ),
}
feature_vocab = {
    "cell_type": Vocabulary(
        terms={"pyramidal": OntologyTerm(uri="http://example.org/FEATURE")},
    ),
}

feat = MuDMFeature(
    type="Feature",
    geometry=Point(type="Point", coordinates=(1.0, 2.0)),
    properties={"cell_type": "pyramidal"},
    vocabularies=feature_vocab,
)
fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[feat],
    vocabularies=collection_vocab,
)

# Resolution: check the feature first, then fall back to the collection.
resolved = feat.vocabularies or fc.vocabularies
assert resolved["cell_type"].terms["pyramidal"].uri == "http://example.org/FEATURE"
```

!!! tip "Whole-object override, not per-key merge"
    `feat.vocabularies or fc.vocabularies` selects one object or the other in its entirety. If a feature defines `vocabularies` at all, the collection's vocabularies are not consulted for that feature — even for property keys the feature does not redefine. If you need per-key fallback, merge the two dicts yourself before resolving.

## Backwards compatibility

`vocabularies` is optional on both models and defaults to `None`. A feature or collection that never sets it behaves exactly like plain GeoJSON.

```python
from mudm import MuDMFeature, MuDMFeatureCollection
from geojson_pydantic import Point

feat = MuDMFeature(
    type="Feature",
    geometry=Point(type="Point", coordinates=(1.0, 2.0)),
    properties={},
)
assert feat.vocabularies is None

fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[feat],
)
assert fc.vocabularies is None
```

Because the member is omitted when `None`, documents without vocabularies serialize to ordinary GeoJSON, and any GeoJSON loads cleanly into muDM. See [Coordinate Transforms](transforms.md) for the same additive philosophy applied to coordinate systems.

## JSON on the wire

Vocabularies serialize and deserialize losslessly. The two forms below are the same feature collection — one built in Python, one as it appears on disk.

=== "Python"

    ```python
    from mudm import MuDMFeature, MuDMFeatureCollection, OntologyTerm, Vocabulary
    from geojson_pydantic import Point

    fc = MuDMFeatureCollection(
        type="FeatureCollection",
        features=[
            MuDMFeature(
                type="Feature",
                geometry=Point(type="Point", coordinates=(1.0, 2.0)),
                properties={"cell_type": "pyramidal"},
            ),
        ],
        vocabularies={
            "cell_type": Vocabulary(
                namespace="http://purl.obolibrary.org/obo/CL_",
                description="Cell ontology",
                terms={
                    "pyramidal": OntologyTerm(
                        uri="http://purl.obolibrary.org/obo/CL_0000598",
                        label="pyramidal neuron",
                    ),
                },
            ),
        },
    )
    ```

=== "JSON"

    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "geometry": { "type": "Point", "coordinates": [1.0, 2.0] },
          "properties": { "cell_type": "pyramidal" }
        }
      ],
      "vocabularies": {
        "cell_type": {
          "namespace": "http://purl.obolibrary.org/obo/CL_",
          "description": "Cell ontology",
          "terms": {
            "pyramidal": {
              "uri": "http://purl.obolibrary.org/obo/CL_0000598",
              "label": "pyramidal neuron"
            }
          }
        }
      }
    }
    ```

Round-tripping through Python preserves every field:

```python
from mudm import MuDMFeature, MuDMFeatureCollection, OntologyTerm, Vocabulary
from geojson_pydantic import Point

fc = MuDMFeatureCollection(
    type="FeatureCollection",
    features=[
        MuDMFeature(
            type="Feature",
            geometry=Point(type="Point", coordinates=(1.0, 2.0)),
            properties={"cell_type": "pyramidal"},
        ),
    ],
    vocabularies={
        "cell_type": Vocabulary(
            terms={
                "pyramidal": OntologyTerm(
                    uri="http://purl.obolibrary.org/obo/CL_0000598"
                ),
            },
        ),
    },
)

data = fc.model_dump()
fc2 = MuDMFeatureCollection(**data)
assert fc2.vocabularies["cell_type"].terms["pyramidal"].uri == (
    "http://purl.obolibrary.org/obo/CL_0000598"
)
```

When a string URI is used instead of an inline dict, the `vocabularies` member is simply that string in the JSON.

## Where to next

- [Metadata & Properties](metadata.md) — the `properties` member that vocabularies annotate.
- [Coordinate Transforms](transforms.md) — physical/voxel coordinate systems, another optional metadata layer.
- [Provenance & Traceability](provenance.md) — record how a document was produced.
- [Worked examples](examples.md) — end-to-end documents that combine these layers.
- For pipelines, converters, tiling, and visualization that consume these vocabularies, see the [mudm-tools documentation](https://novagenresearch.github.io/mudm-tools/).

## API reference

::: mudm.model.OntologyTerm

::: mudm.model.Vocabulary
