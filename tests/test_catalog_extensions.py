"""Catalog/descriptor extensions: foreign members (``extra='allow'``), a unified
2D/3D pyramid catalog (``PyramidEntry.kind``), and typed access ``assets``.

Rationale: muDM's own JSON (``PyramidJSON`` catalog + ``TileModel`` descriptor +
``TileLayer`` schema) is the agent-/ML-facing surface. Dataset-level *semantics*
are carried as OPEN metadata on the catalog entry (no domain fields baked into the
model); a thin schema.org/Croissant projection rides along as foreign members.
See ``mudm-data/.claude/specs/2026-06-23-local-first-agent-showcase-design.md``.
"""

from mudm.tilemodel import (
    TileJSON,
    TileModel,
    TileLayer,
    Multiscale,
    PyramidEntry,
    PyramidJSON,
    Asset,
)


def _tilemodel_dict(**extra):
    d = {
        "tilejson": "3.0.0",
        "tiles": ["https://ex.org/d/0/0/0.pbf"],
        "vector_layers": [{"id": "cells"}],
    }
    d.update(extra)
    return d


# --- foreign members survive round-trip (the schema.org/Croissant carrier) ---


def test_tilemodel_keeps_foreign_members_roundtrip():
    tm = TileModel.model_validate(
        _tilemodel_dict(**{"@context": "https://schema.org/", "@type": "Dataset"})
    )
    dumped = tm.model_dump(exclude_none=True)
    assert dumped["@context"] == "https://schema.org/"
    assert dumped["@type"] == "Dataset"


def test_tilejson_root_keeps_foreign_members():
    data = _tilemodel_dict(**{"croissant:recordSet": [{"@id": "cells"}]})
    tj = TileJSON.model_validate(data)
    assert tj.model_dump(exclude_none=True)["croissant:recordSet"] == [{"@id": "cells"}]


def test_tilelayer_keeps_foreign_members():
    layer = TileLayer.model_validate({"id": "cells", "x-extra": {"k": "v"}})
    assert layer.model_dump(exclude_none=True)["x-extra"] == {"k": "v"}


def test_multiscale_keeps_foreign_members():
    ms = Multiscale.model_validate(
        {"axes": [{"name": "x", "type": "space", "unit": "micrometer"}], "x-ome": True}
    )
    assert ms.model_dump(exclude_none=True)["x-ome"] is True


def test_pyramidjson_keeps_catalog_foreign_members():
    cat = PyramidJSON.model_validate(
        {
            "pyramids": [],
            "@context": {"mudm": "https://mudm.io/ns#"},
            "conformsTo": ["http://www.opengis.net/spec/ogcapi-records-1/1.0/conf/core"],
        }
    )
    dumped = cat.model_dump(exclude_none=True)
    assert dumped["@context"] == {"mudm": "https://mudm.io/ns#"}
    assert "conformsTo" in dumped


# --- open dataset-level metadata + unified 2D/3D catalog ---


def test_pyramidentry_open_metadata_and_kind():
    entry = PyramidEntry.model_validate(
        {
            "id": "xenium-kidney",
            "label": "Xenium kidney",
            "kind": "2d",
            "tilejson": "tilejson.json",
            "features": "features.parquet",
            # open, conventional (not model-typed) dataset semantics:
            "organism": "Homo sapiens",
            "technique": "Xenium",
            "license": "CC-BY-4.0",
        }
    )
    assert entry.kind == "2d"
    dumped = entry.model_dump(exclude_none=True)
    assert dumped["organism"] == "Homo sapiens"
    assert dumped["technique"] == "Xenium"
    assert dumped["license"] == "CC-BY-4.0"


def test_pyramidjson_unifies_2d_and_3d():
    cat = PyramidJSON.model_validate(
        {
            "version": "1.0",
            "pyramids": [
                {"id": "hemibrain", "kind": "3d", "tilejson": "tilejson3d.json"},
                {
                    "id": "xenium-kidney",
                    "kind": "2d",
                    "tilejson": "tilejson.json",
                    "features": "features.parquet",
                },
            ],
        }
    )
    assert {p.id: p.kind for p in cat.pyramids} == {
        "hemibrain": "3d",
        "xenium-kidney": "2d",
    }


def test_backward_compat_3d_entry_without_kind():
    """Existing 3D pyramids.json entries have no ``kind`` and must still validate."""
    entry = PyramidEntry.model_validate({"id": "hemibrain", "label": "Hemibrain"})
    assert entry.kind is None
    assert entry.tilejson == "tilejson3d.json"  # 3D default preserved


# --- typed access assets on the descriptor ---


def test_tilemodel_typed_assets_with_extra():
    tm = TileModel.model_validate(
        _tilemodel_dict(
            assets=[
                {
                    "role": "features",
                    "href": "https://ex.org/d/features.parquet",
                    "media_type": "application/vnd.apache.parquet",
                    "partitioned": True,  # per-asset extra rides via extra='allow'
                },
                {
                    "role": "raster",
                    "href": "https://ex.org/d/raster/0/0/0.png",
                    "media_type": "image/png",
                },
            ]
        )
    )
    assert tm.assets[0].role == "features"
    assert tm.assets[1].media_type == "image/png"
    assert tm.assets[0].model_dump(exclude_none=True)["partitioned"] is True
