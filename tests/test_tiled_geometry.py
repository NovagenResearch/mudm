"""Tests for TiledGeometry base class and tiled mode on TIN/PolyhedralSurface."""
import pytest
from pydantic import ValidationError
from mudm.model import TIN, PolyhedralSurface


class TestTINTiledMode:
    """TIN with tiles instead of inline coordinates."""

    def test_tin_with_tiles_valid(self):
        """TIN with tiles and empty coordinates is valid."""
        t = TIN(type="TIN", coordinates=[], tiles=["0/0/0/0", "2/0/0/0"])
        assert t.tiles == ["0/0/0/0", "2/0/0/0"]
        assert t.coordinates == []

    def test_tin_inline_still_works(self):
        """Existing TIN with inline coordinates still validates."""
        face = [[[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]]]
        t = TIN(type="TIN", coordinates=face)
        assert len(t.coordinates) == 1
        assert t.tiles is None

    def test_tin_both_empty_fails(self):
        """TIN with no coordinates and no tiles must fail."""
        with pytest.raises(ValidationError, match="requires either coordinates or tiles"):
            TIN(type="TIN", coordinates=[])

    def test_tin_both_present_ok(self):
        """TIN with both coordinates and tiles is allowed (preview + full tiles)."""
        face = [[[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]]]
        t = TIN(type="TIN", coordinates=face, tiles=["0/0/0/0"])
        assert len(t.coordinates) == 1
        assert t.tiles == ["0/0/0/0"]

    def test_tin_tiles_none_with_coords_ok(self):
        """TIN with tiles=None and valid coordinates is fine (original behavior)."""
        face = [[[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]]]
        t = TIN(type="TIN", coordinates=face)
        assert t.tiles is None

    def test_tin_bbox3d_returns_none_in_tiled_mode(self):
        """bbox3d returns None when coordinates are empty (tiled mode)."""
        t = TIN(type="TIN", coordinates=[], tiles=["0/0/0/0"])
        assert t.bbox3d() is None

    def test_tin_centroid3d_returns_none_in_tiled_mode(self):
        """centroid3d returns None when coordinates are empty (tiled mode)."""
        t = TIN(type="TIN", coordinates=[], tiles=["0/0/0/0"])
        assert t.centroid3d() is None

    def test_tin_bbox3d_works_with_coords(self):
        """bbox3d still works with inline coordinates."""
        face = [[[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]]]
        t = TIN(type="TIN", coordinates=face)
        bbox = t.bbox3d()
        assert bbox is not None
        assert bbox == (0, 0, 0, 1, 1, 0)

    def test_tin_triangle_validation_still_enforced(self):
        """Triangle validation still runs when coordinates are non-empty."""
        bad_face = [[[[0, 0, 0], [1, 0, 0], [0, 0, 0]]]]  # only 3 positions
        with pytest.raises(ValidationError):
            TIN(type="TIN", coordinates=bad_face)


class TestPolyhedralSurfaceTiledMode:
    """PolyhedralSurface with tiles instead of inline coordinates."""

    def test_polyhedral_with_tiles_valid(self):
        """PolyhedralSurface with tiles and empty coordinates is valid."""
        p = PolyhedralSurface(type="PolyhedralSurface", coordinates=[], tiles=["0/0/0/0"])
        assert p.tiles == ["0/0/0/0"]

    def test_polyhedral_both_empty_fails(self):
        """PolyhedralSurface with no coordinates and no tiles must fail."""
        with pytest.raises(ValidationError, match="requires either coordinates or tiles"):
            PolyhedralSurface(type="PolyhedralSurface", coordinates=[])

    def test_polyhedral_bbox3d_returns_none_in_tiled_mode(self):
        """bbox3d returns None when coordinates are empty (tiled mode)."""
        p = PolyhedralSurface(type="PolyhedralSurface", coordinates=[], tiles=["0/0/0/0"])
        assert p.bbox3d() is None

    def test_polyhedral_centroid3d_returns_none_in_tiled_mode(self):
        """centroid3d returns None when coordinates are empty (tiled mode)."""
        p = PolyhedralSurface(type="PolyhedralSurface", coordinates=[], tiles=["0/0/0/0"])
        assert p.centroid3d() is None

    def test_polyhedral_inline_still_works(self):
        """Existing PolyhedralSurface with inline coordinates still validates."""
        face = [[[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 0]]]]
        p = PolyhedralSurface(type="PolyhedralSurface", coordinates=face)
        assert len(p.coordinates) == 1


from mudm.tilemodel import PyramidEntry, PyramidJSON


class TestPyramidJSON:
    """PyramidJSON manifest model."""

    def test_minimal_pyramid_entry(self):
        entry = PyramidEntry(id="hemibrain")
        assert entry.id == "hemibrain"
        assert entry.tilejson == "tilejson3d.json"
        assert entry.features == "features.json"

    def test_full_pyramid_entry(self):
        entry = PyramidEntry(
            id="hemibrain_full",
            label="Hemibrain v1.2.1",
            tiles=2835,
            feature_count=5099,
            size_bytes=31440000000,
        )
        assert entry.feature_count == 5099

    def test_pyramid_json_with_version(self):
        manifest = PyramidJSON(pyramids=[
            PyramidEntry(id="hemibrain"),
            PyramidEntry(id="mouselight_2018-04-25"),
        ])
        assert manifest.version == "1.0"
        assert len(manifest.pyramids) == 2

    def test_pyramid_json_roundtrip(self):
        """Serialize to JSON and back."""
        manifest = PyramidJSON(pyramids=[
            PyramidEntry(id="test", label="Test Pyramid", tiles=100,
                         feature_count=50, size_bytes=1000000),
        ])
        json_str = manifest.model_dump_json()
        loaded = PyramidJSON.model_validate_json(json_str)
        assert loaded.pyramids[0].id == "test"
        assert loaded.version == "1.0"
