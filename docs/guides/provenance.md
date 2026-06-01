# Provenance & Traceability

muDM lets you attach a structured, machine-readable record of *where your features came from* — the workflows that produced them and the files (artifacts) involved — and link those records back to specific features and fields. This page shows you how to build provenance, attach it to a feature collection, and validate the result.

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

New to the core model? Start with [Getting Started](../getting-started.md) and the [Core data-model API](../reference/models.md). Provenance is generated automatically when `mudm-tools` pipelines produce processed or tiled outputs — see its [2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/), [3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/), and [converters](https://novagenresearch.github.io/mudm-tools/guides/converters/) guides.

## Why provenance

GeoJSON gives you a robust way to represent spatial features, but it has no standard mechanism for tracing data provenance — the workflows and processing steps that generate or modify those features. muDM adds an optional `provenance` member to a feature collection to bridge that gap.

This stays fully backward compatible: any GeoJSON document is still valid muDM, and a muDM document with provenance is still valid GeoJSON (the extra member is simply foreign to plain GeoJSON readers). You only pay for the complexity you use — a single artifact is enough, and you can grow up to nested workflow collections when you need them.

The model is built around four goals:

- **Workflow integration** — link muDM features to the analytical workflows that produced them, for reproducibility and transparency.
- **Flexible run tracking** — capture run details (operator, duration, parameters) via free-form property dictionaries.
- **Workflow and artifact linking** — reference the specific workflows and files involved, giving a complete view of data processing.
- **Scale to the use case** — from one standalone artifact up to nested collections of workflows.

## Model at a glance

The provenance model is composed of six objects, all importable from `mudm.provenance`:

| Object | Purpose |
| --- | --- |
| `Workflow` | A single workflow, optionally with nested sub-workflows and one execution record. |
| `WorkflowCollection` | Several workflows that together contributed to the features. |
| `WorkflowProvenance` | A single execution of a workflow, with run properties and output artifacts. |
| `Artifact` | A single file or directory (a `uri`), with links back to muDM features. |
| `ArtifactCollection` | A collection of artifacts. |
| `MuDMLink` | A traceability link from an artifact to a muDM feature (and optionally a field). |

Any of `Workflow`, `WorkflowCollection`, `Artifact`, or `ArtifactCollection` may serve as the **top object** of the `provenance` member on a feature collection. The `MuDMFeatureCollection` carries it as an optional member typed `Optional[Union[Workflow, WorkflowCollection, Artifact, ArtifactCollection]]`; the validator selects the correct object from its `type` discriminator (`"Workflow"`, `"WorkflowCollection"`, `"Artifact"`, or `"ArtifactCollection"`).

### The traceability link

`MuDMLink` connects an artifact back to the muDM feature(s) it pertains to:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `mudmId` | `str` or `list[str]` | yes | The `id` of one or more muDM features this artifact relates to. |
| `mudmField` | `str` | no | The specific field within the feature that is pertinent. |

If `mudmField` is omitted, the entire muDM feature is considered pertinent.

!!! tip "`mudmId`, not `mudmTd`"
    The field is spelled `mudmId` (an *I*, as in identifier). It accepts either a single id string or a list of id strings.

## Field reference

=== "`Artifact`"

    | Field | Type | Required | Notes |
    | --- | --- | --- | --- |
    | `type` | `"Artifact"` | yes | Literal discriminator. |
    | `id` | `str` | no | Optional identifier for the artifact. |
    | `uri` | `str` | yes | Location of the file or directory, e.g. `file://path/to/image.tif`. |
    | `properties` | `dict[str, str \| float \| int]` | no | Free-form metadata. |
    | `mudmLinks` | `list[MuDMLink]` | yes | Links back to the muDM features the artifact pertains to. |

=== "`ArtifactCollection`"

    | Field | Type | Required | Notes |
    | --- | --- | --- | --- |
    | `type` | `"ArtifactCollection"` | yes | Literal discriminator. |
    | `artifacts` | `list[Artifact]` | yes | The contained artifacts. |

=== "`Workflow`"

    | Field | Type | Required | Notes |
    | --- | --- | --- | --- |
    | `type` | `"Workflow"` | yes | Literal discriminator. |
    | `id` | `str` | no | Optional identifier for the workflow. |
    | `properties` | `dict[str, str \| float \| int]` | no | Descriptive metadata. |
    | `subWorkflows` | `list[Workflow]` | no | Nested workflows. |
    | `workflowProvenance` | `WorkflowProvenance` | no | A single execution record. |

=== "`WorkflowProvenance`"

    | Field | Type | Required | Notes |
    | --- | --- | --- | --- |
    | `type` | `"WorkflowProvenance"` | yes | Literal discriminator. |
    | `properties` | `dict[str, str \| float \| int]` | no | Run details: operator, duration, parameters. |
    | `outputArtifacts` | `Artifact \| ArtifactCollection` | no | What the run produced. |

=== "`WorkflowCollection`"

    | Field | Type | Required | Notes |
    | --- | --- | --- | --- |
    | `type` | `"WorkflowCollection"` | yes | Literal discriminator. |
    | `workflows` | `list[Workflow]` | yes | The contained workflows. |

!!! warning "Use camelCase field names"
    On the wire, the fields are `subWorkflows`, `workflowProvenance`, `outputArtifacts`, `mudmLinks`, `mudmId`, and `mudmField`. Because the optional fields default to `None`, a document using snake_case keys like `sub_workflows` will still *validate* — but those values are silently dropped rather than parsed. Always use the camelCase spellings shown above.

## A feature collection with a single artifact

The simplest form of provenance: one `Artifact` recording the source image, linked to a feature via `mudmLinks`. Validate it exactly as the test suite does, with `MuDM.model_validate(...)`.

=== "Python"

    ```python
    from mudm import MuDM

    artifact_doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0.0, 0.0], [0.0, 50.0], [50.0, 50.0], [50.0, 0.0], [0.0, 0.0]]
                    ],
                },
                "properties": {"well": "A1", "cellCount": 5},
            }
        ],
        "provenance": {
            "type": "Artifact",
            "id": "artifact_1",
            "uri": "file://path/to/image.tif",
            "properties": {"imageType": "TIFF", "analysisType": "Cell counting"},
            "mudmLinks": [
                {"mudmId": "1", "mudmField": "properties.well"}
            ],
        },
    }

    doc = MuDM.model_validate(artifact_doc)
    prov = doc.root.provenance
    print(type(prov).__name__)          # Artifact
    print(prov.uri)                     # file://path/to/image.tif
    print(prov.mudmLinks[0].mudmId)     # 1
    ```

=== "JSON"

    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "id": "1",
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 50.0], [50.0, 50.0], [50.0, 0.0], [0.0, 0.0]]]
          },
          "properties": { "well": "A1", "cellCount": 5 }
        }
      ],
      "provenance": {
        "type": "Artifact",
        "id": "artifact_1",
        "uri": "file://path/to/image.tif",
        "properties": { "imageType": "TIFF", "analysisType": "Cell counting" },
        "mudmLinks": [
          { "mudmId": "1", "mudmField": "properties.well" }
        ]
      }
    }
    ```

## A workflow collection producing an artifact

A richer record: a `WorkflowCollection` containing one `Workflow`, whose `workflowProvenance` describes a single run and points at the `outputArtifacts` it produced. The artifact's `mudmLinks` ties the result back to two features at once by passing a list to `mudmId`.

=== "Python"

    ```python
    from mudm import MuDM

    workflow_doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0.0, 0.0], [0.0, 50.0], [50.0, 50.0], [50.0, 0.0], [0.0, 0.0]]
                    ],
                },
                "properties": {"well": "A1", "cellCount": 5},
            }
        ],
        "provenance": {
            "type": "WorkflowCollection",
            "workflows": [
                {
                    "type": "Workflow",
                    "id": "workflow_1",
                    "properties": {"description": "Image processing workflow"},
                    "subWorkflows": [],
                    "workflowProvenance": {
                        "type": "WorkflowProvenance",
                        "properties": {"operator": "acquisition-robot", "durationSeconds": 42},
                        "outputArtifacts": {
                            "type": "Artifact",
                            "id": "artifact_1",
                            "uri": "file://path/to/image.tif",
                            "properties": {"imageType": "TIFF"},
                            "mudmLinks": [
                                {"mudmId": ["1", "2"], "mudmField": "properties.cellCount"}
                            ],
                        },
                    },
                }
            ],
        },
    }

    doc = MuDM.model_validate(workflow_doc)
    wf = doc.root.provenance.workflows[0]
    print(wf.id)                                       # workflow_1
    print(wf.workflowProvenance.outputArtifacts.uri)   # file://path/to/image.tif
    print(wf.workflowProvenance.outputArtifacts.mudmLinks[0].mudmId)  # ['1', '2']
    ```

=== "JSON"

    ```json
    {
      "type": "FeatureCollection",
      "features": [
        {
          "type": "Feature",
          "id": "1",
          "geometry": {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 50.0], [50.0, 50.0], [50.0, 0.0], [0.0, 0.0]]]
          },
          "properties": { "well": "A1", "cellCount": 5 }
        }
      ],
      "provenance": {
        "type": "WorkflowCollection",
        "workflows": [
          {
            "type": "Workflow",
            "id": "workflow_1",
            "properties": { "description": "Image processing workflow" },
            "subWorkflows": [],
            "workflowProvenance": {
              "type": "WorkflowProvenance",
              "properties": { "operator": "acquisition-robot", "durationSeconds": 42 },
              "outputArtifacts": {
                "type": "Artifact",
                "id": "artifact_1",
                "uri": "file://path/to/image.tif",
                "properties": { "imageType": "TIFF" },
                "mudmLinks": [
                  { "mudmId": ["1", "2"], "mudmField": "properties.cellCount" }
                ]
              }
            }
          }
        ]
      }
    }
    ```

## Building provenance with the Python classes

Instead of raw dicts, you can assemble provenance from the typed classes, then serialise with `model_dump(by_alias=True)` and validate. The `by_alias=True` keyword emits the camelCase field names; `exclude_none=True` keeps the document compact.

```python
from mudm import MuDM
from mudm.provenance import (
    MuDMLink,
    Artifact,
    Workflow,
    WorkflowProvenance,
    WorkflowCollection,
)

artifact = Artifact(
    type="Artifact",
    id="artifact_1",
    uri="file://path/to/image.tif",
    properties={"imageType": "TIFF"},
    mudmLinks=[MuDMLink(mudmId="1", mudmField="properties.well")],
)
run = WorkflowProvenance(
    type="WorkflowProvenance",
    properties={"operator": "robot"},
    outputArtifacts=artifact,
)
workflow = Workflow(type="Workflow", id="workflow_1", workflowProvenance=run)
collection = WorkflowCollection(type="WorkflowCollection", workflows=[workflow])

doc = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "1",
            "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
            "properties": {"well": "A1"},
        }
    ],
    "provenance": collection.model_dump(by_alias=True, exclude_none=True),
}

validated = MuDM.model_validate(doc)
print(type(validated.root.provenance).__name__)   # WorkflowCollection
```

!!! example "Provenance from pipelines"
    When you tile or convert data with `mudm-tools`, the output documents already carry a `provenance` member describing the run that produced them. Read those documents back with `MuDM.model_validate(...)` to inspect or extend the record. See the `mudm-tools` [2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/) and [converters](https://novagenresearch.github.io/mudm-tools/guides/converters/) guides.

## Where to next

- [Validation](validation.md) — how `MuDM.model_validate` checks a document end to end.
- [Metadata & Properties](metadata.md) — modelling feature properties that provenance links to.
- [Vocabularies](vocabularies.md) — linking property values to formal ontology terms.
- [Examples](examples.md) — the worked-example gallery, including full documents with provenance.
- [Core data-model API](../reference/models.md) — features, geometry, and the `MuDM` root object.
- Generating provenance from pipelines: the `mudm-tools` [docs site](https://novagenresearch.github.io/mudm-tools/), [2D tiling](https://novagenresearch.github.io/mudm-tools/guides/2d-tiling/), and [3D tiling](https://novagenresearch.github.io/mudm-tools/guides/3d-tiling/) guides.

## API reference

::: mudm.provenance.MuDMLink

::: mudm.provenance.Artifact

::: mudm.provenance.ArtifactCollection

::: mudm.provenance.Workflow

::: mudm.provenance.WorkflowProvenance

::: mudm.provenance.WorkflowCollection
