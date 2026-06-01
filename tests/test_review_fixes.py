"""Regression tests for the 2026-06-01 code review findings.

Each test reproduces a confirmed bug; it should fail against the pre-fix
code and pass after the fix.
"""
import pytest
from pydantic import ValidationError
from geojson_pydantic import Point, Polygon, MultiPoint, GeometryCollection

from mudm.model import TIN, PolyhedralSurface, MuDMFeature, MuDMFeatureCollection
from mudm.tilemodel import (
    TileModel, TileJSON, TileLayer, Multiscale, Axis, Scale, Translation, Identity,
)
from mudm.transforms import (
    AffineTransform, apply_transform, translate_geometry,
    VoxelCoordinateSystem, physical_to_voxel,
)
from mudm.layout import apply_layout, geometry_bounds, compute_collection_offsets


# --------------------------------------------------------------------------
# CRITICAL: Multiscale.coordinateTransformations serialization round-trip
# --------------------------------------------------------------------------

def test_multiscale_roundtrip_preserves_transforms():
    ms = Multiscale(
        axes=[Axis(name="x"), Axis(name="y")],
        coordinateTransformations=[Scale(scale=[0.5, 0.5]), Translation(translation=[1.0, 2.0])],
    )
    reloaded = Multiscale.model_validate(ms.model_dump())
    assert reloaded.coordinateTransformations[0].type == "scale"
    assert reloaded.coordinateTransformations[0].scale == [0.5, 0.5]
    assert reloaded.coordinateTransformations[1].type == "translation"
    assert reloaded.coordinateTransformations[1].translation == [1.0, 2.0]


def test_tilemodel_json_roundtrip_preserves_transforms():
    tm = TileModel(
        tilejson="3.0.0",
        tiles=["{z}/{x}/{y}.pbf"],
        vector_layers=[TileLayer(id="cells")],
        multiscale=Multiscale(axes=[Axis(name="x")], coordinateTransformations=[Scale(scale=[2.0])]),
    )
    reloaded = TileJSON.model_validate_json(tm.model_dump_json())
    cts = reloaded.root.multiscale.coordinateTransformations
    assert cts[0].type == "scale"
    assert cts[0].scale == [2.0]


# --------------------------------------------------------------------------
# MAJOR: bbox3d / centroid3d on 2D positions and on empty faces
# --------------------------------------------------------------------------

def test_tin_bbox3d_handles_2d_coordinates():
    t = TIN(type="TIN", coordinates=[[[[0, 0], [1, 0], [0, 1], [0, 0]]]])
    assert t.bbox3d() == (0, 0, 0, 1, 1, 0)
    assert t.centroid3d() is not None


def test_polyhedral_bbox3d_handles_2d_coordinates():
    p = PolyhedralSurface(type="PolyhedralSurface", coordinates=[[[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]])
    assert p.bbox3d() == (0, 0, 0, 2, 2, 0)


def test_polyhedral_empty_face_returns_none_not_crash():
    p = PolyhedralSurface(type="PolyhedralSurface", coordinates=[[]])
    assert p.bbox3d() is None
    assert p.centroid3d() is None


# --------------------------------------------------------------------------
# MAJOR: apply_transform on GeometryCollection; preserves tiles
# --------------------------------------------------------------------------

def test_apply_transform_geometry_collection():
    gc = GeometryCollection(type="GeometryCollection", geometries=[
        Point(type="Point", coordinates=(1, 2, 3)),
        MultiPoint(type="MultiPoint", coordinates=[(0, 0, 0), (5, 5, 5)]),
    ])
    t = AffineTransform(matrix=[[1, 0, 0, 10], [0, 1, 0, 20], [0, 0, 1, 30], [0, 0, 0, 1]])
    out = apply_transform(gc, t)
    assert out.type == "GeometryCollection"
    assert out.geometries[0].coordinates[0] == pytest.approx(11)
    assert out.geometries[1].coordinates[1][2] == pytest.approx(35)


def test_apply_transform_preserves_tiles():
    t = TIN(type="TIN", coordinates=[[[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]]], tiles=["a", "b"])
    out = translate_geometry(t, 10, 20, 30)
    assert out.tiles == ["a", "b"]
    assert out.coordinates[0][0][0][0] == pytest.approx(10)


def test_apply_transform_tiles_only_no_crash():
    t = TIN(type="TIN", coordinates=[], tiles=["m0"])
    out = translate_geometry(t, 1, 2, 3)
    assert out.tiles == ["m0"]
    assert out.coordinates == []


# --------------------------------------------------------------------------
# MAJOR: top-level provenance exports
# --------------------------------------------------------------------------

def test_provenance_types_exported_top_level():
    from mudm import (
        Workflow, WorkflowCollection, WorkflowProvenance,
        Artifact, ArtifactCollection, MuDMLink,
    )
    assert all(x is not None for x in [
        Workflow, WorkflowCollection, WorkflowProvenance,
        Artifact, ArtifactCollection, MuDMLink,
    ])


# --------------------------------------------------------------------------
# MAJOR: apply_layout robustness (tiled meshes, GeometryCollection)
# --------------------------------------------------------------------------

def _poly(xy):
    x, y = xy
    return Polygon(type="Polygon", coordinates=[[(x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1), (x, y)]])


def test_apply_layout_tiled_mesh_no_crash():
    feats = [
        MuDMFeature(type="Feature", geometry=_poly((0, 0)), properties={}),
        MuDMFeature(type="Feature", geometry=TIN(type="TIN", coordinates=[], tiles=["m0"]), properties={}),
    ]
    fc = MuDMFeatureCollection(type="FeatureCollection", features=feats)
    out = apply_layout(fc, spacing=100.0)
    assert out.features[1].geometry.tiles == ["m0"]


def test_geometry_bounds_geometry_collection():
    gc = GeometryCollection(type="GeometryCollection", geometries=[
        Point(type="Point", coordinates=(0, 0, 0)),
        Point(type="Point", coordinates=(4, 6, 8)),
    ])
    assert geometry_bounds(gc) == (0, 0, 0, 4, 6, 8)


def test_apply_layout_geometry_collection_no_crash():
    gc = GeometryCollection(type="GeometryCollection", geometries=[Point(type="Point", coordinates=(0, 0, 0))])
    feats = [
        MuDMFeature(type="Feature", geometry=_poly((0, 0)), properties={}),
        MuDMFeature(type="Feature", geometry=gc, properties={}),
    ]
    fc = MuDMFeatureCollection(type="FeatureCollection", features=feats)
    out = apply_layout(fc, spacing=10.0)
    assert out.features[1].geometry.type == "GeometryCollection"


# --------------------------------------------------------------------------
# MINOR / harmonization
# --------------------------------------------------------------------------

def test_multiscale_importable_from_model():
    from mudm.model import Multiscale as M
    assert M is Multiscale


def test_tilemodel_and_provenance_types_exported_top_level():
    from mudm import (
        Multiscale as Ms, Axis as Ax, Unit, AxisType,
        Identity as Id, Translation as Tr, Scale as Sc, CoordinateTransformation,
    )
    assert all(x is not None for x in [Ms, Ax, Unit, AxisType, Id, Tr, Sc, CoordinateTransformation])


def test_affine_rejects_non_identity_bottom_row():
    with pytest.raises(ValidationError):
        AffineTransform(matrix=[[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [9, 9, 9, 9]])


def test_affine_accepts_standard_bottom_row():
    t = AffineTransform(matrix=[[1, 0, 0, 5], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
    assert t.matrix[3] == [0, 0, 0, 1]


def test_physical_to_voxel_zero_resolution_raises_valueerror():
    vcs = VoxelCoordinateSystem(axes=["x", "y", "z"], units=["um", "um", "um"], resolution=[0.0, 1.0, 1.0])
    with pytest.raises(ValueError):
        physical_to_voxel((1.0, 2.0, 3.0), vcs)


def test_multiscale_rejects_both_transform_forms():
    with pytest.raises(ValidationError):
        Multiscale(
            axes=[Axis(name="x")],
            coordinateTransformations=[Scale(scale=[1.0])],
            transformationMatrix=[[1.0, 0.0], [0.0, 1.0]],
        )


def test_multiscale_rejects_ragged_matrix():
    with pytest.raises(ValidationError):
        Multiscale(axes=[Axis(name="x")], transformationMatrix=[[1.0, 2.0], [3.0]])


def _points(n):
    return [
        MuDMFeature(type="Feature", geometry=Point(type="Point", coordinates=(0, 0, 0)), properties={})
        for _ in range(n)
    ]


def test_grid_layout_zero_cell_count_raises_valueerror():
    with pytest.raises(ValueError):
        compute_collection_offsets(_points(4), spacing=1.0, grid_max_x=0)


def test_grid_layout_requires_grid_max_x():
    with pytest.raises(ValueError):
        compute_collection_offsets(_points(4), grid_max_y=2)


def test_row_layout_zero_width_features_spread():
    offsets = compute_collection_offsets(_points(3), spacing=0.0)
    xs = [o[0] for o in offsets]
    assert len(set(xs)) == 3
