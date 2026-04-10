# muDM

muDM (micro Data Model) is a GeoJSON-inspired data model for encoding microscopy spatial data — annotations, regions of interest, coordinate systems, and 3D mesh surfaces.

This is the **core data model package**. It provides Pydantic models for validation and serialization with minimal dependencies. For tiling pipelines, format converters, and Rust-accelerated processing, see [mudm-tools](https://github.com/NovagenResearch/mudm-tools).

## Install

```bash
pip install mudm
```

## Usage

```python
from mudm import MuDM, MuDMFeature, GeoJSON

# Validate muDM data
data = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [10, 20]},
        "properties": {"label": "nucleus"},
    }],
}
obj = MuDM.model_validate(data)

# Any GeoJSON is valid muDM
geojson = GeoJSON.model_validate(data)

# Coordinate transforms
from mudm import AffineTransform

# Tile metadata
from mudm import TileJSON, TileModel
```

## What's included

- **Model validation**: MuDM, MuDMFeature, MuDMFeatureCollection, GeoJSON
- **3D geometry types**: TIN, PolyhedralSurface, TiledGeometry
- **Tile metadata**: TileJSON, TileModel, TileLayer, PyramidJSON
- **Coordinate transforms**: AffineTransform, VoxelCoordinateSystem
- **Provenance tracking**: Workflow, Artifact, MuDMLink

## License

MIT
