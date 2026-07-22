from typing import Annotated, List, Optional, Union, Dict, Literal
from enum import StrEnum
from pydantic import BaseModel, AnyUrl, conlist, RootModel, ConfigDict
from pydantic import Field, StrictStr, field_validator, model_validator
from pathlib import Path

from .model import Vocabulary


class TileLayer(BaseModel):
    """A vector layer in a TileJSON file.

    Args:
        id (str): The unique identifier for the layer.
        fields (Union[None, Dict[str, str]]): The fields in the layer.
        minzoom (Optional[int]): The minimum zoom level for the layer.
        maxzoom (Optional[int]): The maximum zoom level for the layer.
        description (Optional[str]): A description of the layer.
        fieldranges (Optional[Dict[str, List[Union[int, float, str]]]]):
            The ranges of the fields.
        fieldenums (Optional[Dict[str, List[str]]]):
            The enums of the fields.
        fielddescriptions (Optional[Dict[str, str]]):
            The descriptions of the fields.
        vocabularies (Optional[Dict[str, Vocabulary]]):
            Ontology vocabularies mapping property values to formal terms.

    Extra members are allowed so emitters may attach a derived schema.org/
    Croissant field projection or other foreign metadata.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    fields: Union[None, Dict[str, str]] = None
    minzoom: Optional[int] = 0
    maxzoom: Optional[int] = 22
    description: Optional[str] = None
    fieldranges: Optional[Dict[str, List[Union[int, float, str]]]] = None
    fieldenums: Optional[Dict[str, List[str]]] = None
    fielddescriptions: Optional[Dict[str, str]] = None
    vocabularies: Optional[Dict[str, Vocabulary]] = None


class Unit(StrEnum):
    """A unit of measurement"""

    ANGSTROM = "angstrom"
    ATTOMETER = "attometer"
    CENTIMETER = "centimeter"
    DECIMETER = "decimeter"
    EXAMETER = "exameter"
    FEMTOMETER = "femtometer"
    FOOT = "foot"
    GIGAMETER = "gigameter"
    HECTOMETER = "hectometer"
    INCH = "inch"
    KILOMETER = "kilometer"
    MEGAMETER = "megameter"
    METER = "meter"
    MICROMETER = "micrometer"
    MILE = "mile"
    MILLIMETER = "millimeter"
    NANOMETER = "nanometer"
    PARSEC = "parsec"
    PETAMETER = "petameter"
    PICOMETER = "picometer"
    TERAMETER = "terameter"
    YARD = "yard"
    YOCTOMETER = "yoctometer"
    YOTTAMETER = "yottameter"
    ZEPTOMETER = "zeptometer"
    ZETTAMETER = "zettameter"
    PIXEL = "pixel"
    RADIAN = "radian"
    DEGREE = "degree"


class AxisType(StrEnum):
    """The type of an axis"""

    SPACE = "space"
    TIME = "time"
    CHANNEL = "channel"


class Axis(BaseModel):
    """An axis of a coordinate system

    Args:
        name (StrictStr): The name of the axis
        type (Optional[AxisType]): The type of the axis
        unit (Optional[Unit]): The unit of the axis
        description (Optional[str]): A description of the axis
    """

    name: StrictStr
    type: Optional[AxisType] = None
    unit: Optional[Unit] = None
    description: Optional[str] = None


class CoordinateTransformation(BaseModel):
    """Coordinate transformation abstract class
    harmonized with the OME model"""


class Identity(CoordinateTransformation):
    """Identity transformation for coordinates

    Args:
        type (Literal["identity"]): The type of the transformation
    """

    type: Literal["identity"] = "identity"


class Translation(CoordinateTransformation):
    """Translation transformation

    Args:
        type (Literal["translation"]): The type of the transformation
        translation (List[float]): The translation vector
    """

    type: Literal["translation"] = "translation"
    translation: List[float]


class Scale(CoordinateTransformation):
    """Scale transformation

    Args:
        type (Literal["scale"]): The type of the transformation
        scale (List[float]): The scale vector
    """

    type: Literal["scale"] = "scale"
    scale: List[float]


# A discriminated union of the concrete OME-aligned transforms that may appear
# in a serialized ``coordinateTransformations`` list. Typing the field against
# the (field-less) ``CoordinateTransformation`` base would make Pydantic drop
# each element's payload to ``{}`` on serialization; the discriminator on
# ``type`` preserves the concrete data through model_dump/validate round-trips.
# ``AffineTransform`` (mudm.transforms) is intentionally NOT included: the
# TileJSON wire form permits only identity/scale/translation here, and importing
# it would create a circular import (transforms imports tilemodel).
CoordinateTransform = Annotated[
    Union[Identity, Translation, Scale],
    Field(discriminator="type"),
]


class Multiscale(BaseModel):
    """A coordinate system for MuDM coordinates

    Args:
        axes (List[Axis]): The axes of the coordinate system
        coordinateTransformations (Optional[List[CoordinateTransform]]):
            A list of coordinate transformations (identity/translation/scale).
        transformationMatrix (Optional[List[List[float]]]):
            A single transformation matrix. Mutually exclusive with
            ``coordinateTransformations``; rows must all be the same length.
    """

    model_config = ConfigDict(extra="allow")

    axes: List[Axis]
    coordinateTransformations: Optional[List[CoordinateTransform]] = None
    transformationMatrix: Optional[List[List[float]]] = None

    @field_validator("transformationMatrix")
    @classmethod
    def _validate_rectangular(
        cls, v: Optional[List[List[float]]]
    ) -> Optional[List[List[float]]]:
        if v is not None and len({len(row) for row in v}) > 1:
            raise ValueError(
                "transformationMatrix rows must all have the same length"
            )
        return v

    @model_validator(mode="after")
    def _exclusive_transforms(self):
        if (
            self.coordinateTransformations is not None
            and self.transformationMatrix is not None
        ):
            raise ValueError(
                "Multiscale must not set both coordinateTransformations and "
                "transformationMatrix; choose one."
            )
        return self


class Asset(BaseModel):
    """A typed, dereferenceable data asset of a tiled dataset.

    Declares *how* to access a dataset's bytes: a ``role`` (e.g. ``raster``,
    ``vector``, ``features``, ``tiles3d``, ``download``), an ``href`` (absolute
    URL or relative path) and an optional ``media_type``. Extra members are
    allowed so emitters may attach access hints (``partitioned``, ``range``,
    ``bytes``, …).

    Args:
        role (str): The asset's role/kind.
        href (str): Absolute URL or relative path to the asset.
        media_type (Optional[str]): IANA media type of the asset.
        title (Optional[str]): Human-readable label.
    """

    model_config = ConfigDict(extra="allow")

    role: str
    href: str
    media_type: Optional[str] = None
    title: Optional[str] = None


class TileModel(BaseModel):
    """A TileJSON object.

    Args:
        tilejson (str): The TileJSON version.
        tiles (List[Union[Path, AnyUrl]]): The list of tile URLs.
        name (Optional[str]): The name of the tileset.
        description (Optional[str]): The description of the tileset.
        version (Optional[str]): The version of the tileset.
        attribution (Optional[str]): The attribution of the tileset.
        template (Optional[str]): The template of the tileset.
        legend (Optional[str]): The legend of the tileset.
        scheme (Optional[str]): The scheme of the tileset.
        grids (Optional[Union[Path, AnyUrl]]): The grids of the tileset.
        data (Optional[Union[Path, AnyUrl]]): The data of the tileset.
        minzoom (Optional[int]): The minimum zoom level of the tileset.
        maxzoom (Optional[int]): The maximum zoom level of the tileset.
        bounds (Optional[conlist(float, min_length=4, max_length=10)]):
            The bounds of the tileset.
        center (Optional[conlist(float, min_length=3, max_length=6)]):
            The center of the tileset.
        fillzoom (Optional[int]): The fill zoom level of the tileset.
        vector_layers (List[TileLayer]): The vector layers of the tileset.
        assets (Optional[List[Asset]]): Typed access assets (raster, vector,
            features, tiles3d, download, …) with absolute URLs or relative paths.

    Extra members are allowed so a derived schema.org/Croissant projection
    (``@context``, ``@type``, ``distribution`` …) can ride along in-document.
    """

    model_config = ConfigDict(extra="allow")

    tilejson: str
    tiles: List[Union[Path, AnyUrl]]
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    attribution: Optional[str] = None
    template: Optional[str] = None
    legend: Optional[str] = None
    scheme: Optional[str] = None
    grids: Optional[Union[Path, AnyUrl]] = None
    data: Optional[Union[Path, AnyUrl]] = None
    minzoom: Optional[int] = 0
    maxzoom: Optional[int] = 22
    bounds: Optional[conlist(float, min_length=4, max_length=10)] = None  # type: ignore
    center: Optional[conlist(float, min_length=3, max_length=6)] = None  # type: ignore
    fillzoom: Optional[int] = None
    vector_layers: List[TileLayer]
    multiscale: Optional[Multiscale] = None
    scale_factor: Optional[float] = None
    assets: Optional[List[Asset]] = None


class TileJSON(RootModel):
    """The root object of a TileJSON file."""

    root: TileModel


class PyramidEntry(BaseModel):
    """One pyramid (dataset) in a PyramidJSON catalog, spanning 2D and 3D.

    Dataset-level *semantics* (organism, technique, license, …) are deliberately
    NOT modelled as fixed fields — they are carried as OPEN metadata (extra
    members), keeping the model domain-agnostic; emitters adopt a documented key
    convention so consumers see consistent, canonical values.

    Attributes:
        id: Unique identifier for this pyramid (used as directory name).
        label: Human-readable display label.
        kind: Dataset dimensionality, ``"2d"`` or ``"3d"`` (None if unspecified).
        tilejson: Relative path to the TileJSON descriptor (``tilejson3d.json``
            for 3D, ``tilejson.json`` for 2D).
        features: Relative path to the MuDM FeatureCollection (3D) or the
            ``features.parquet`` partition root (2D).
        tiles: Total number of tile files.
        feature_count: Number of unique features.
        size_bytes: Total size on disk in bytes.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    label: Optional[str] = None
    kind: Optional[Literal["2d", "3d"]] = None
    tilejson: str = "tilejson3d.json"
    features: Optional[str] = "features.json"
    tiles: Optional[int] = None
    feature_count: Optional[int] = None
    size_bytes: Optional[int] = None


class PyramidJSON(BaseModel):
    """Root manifest (catalog) listing all available pyramids — 2D and 3D.

    Extra members are allowed, so a thin schema.org/Croissant or OGC API-Records
    projection (``@context``, ``conformsTo``, ``links`` …) can ride along inside
    the same document instead of in a separate sidecar format.

    Attributes:
        version: Manifest format version.
        pyramids: List of pyramid entries.
    """

    model_config = ConfigDict(extra="allow")

    version: str = "1.0"
    pyramids: List[PyramidEntry]
