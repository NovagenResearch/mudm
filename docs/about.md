# About muDM

muDM (micro Data Model) is a data model and Python library for representing microscopy annotations, regions of interest, and spatial metadata. Inspired by [GeoJSON](https://geojson.org), it extends the GeoJSON specification with microscopy-specific features while maintaining full backwards compatibility — any GeoJSON is valid muDM, and any muDM document is valid GeoJSON.

This is the **core data model package**. For tiling pipelines, format converters, and Rust-accelerated processing, see [mudm-tools](https://github.com/NovagenResearch/mudm-tools).

## Key Capabilities

- **Format Specification**: A JSON-based data model for 2D and 3D microscopy annotations, with support for coordinate systems, multiscale metadata, and provenance tracking.
- **Pydantic Validation**: Python models built on [Pydantic v2](https://docs.pydantic.dev/) and [geojson-pydantic](https://developmentseed.org/geojson-pydantic/) for strict schema validation.
- **3D Geometry Types**: TIN and PolyhedralSurface mesh types based on ISO 19107.
- **Coordinate Transforms**: Affine transforms, voxel-to-physical conversions, and OME-compatible multiscale metadata.
- **Provenance Tracking**: Workflow, artifact, and data lineage models.
- **Tile Metadata**: TileJSON 3.0.0 models for describing tiled datasets.

## Requirements

- Python >= 3.11, < 3.14
- Dependencies: `pydantic`, `geojson-pydantic`

## Install

```bash
pip install mudm
```

## Links

- **Repository**: [github.com/NovagenResearch/mudm](https://github.com/NovagenResearch/mudm)
- **Tools package**: [github.com/NovagenResearch/mudm-tools](https://github.com/NovagenResearch/mudm-tools)
- **License**: MIT
