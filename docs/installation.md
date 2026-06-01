# Installation

`mudm` is the **core data model** for [muDM](about.md) spatial data: a set of
[Pydantic v2](https://docs.pydantic.dev/) models for validating, serializing,
and transforming microscopy annotations. It is **pure Python** — there is no
compiled or Rust component — and it carries only two runtime dependencies.

This page covers everything you need for a working install: the supported
Python versions, the one-line install, installing from GitHub, the development
setup, and how to verify the result. If you just want the fastest path, jump to
[Quick install](#quick-install).

!!! tip "uv-first"
    This project standardizes on [`uv`](https://docs.astral.sh/uv/) for
    development. End users can still use plain `pip` — both are shown below. For
    anything inside a cloned checkout, prefer `uv` so you get the project's
    pinned environment.

## Requirements

| Requirement | Version | Notes |
| --- | --- | --- |
| Python | `>=3.11,<3.14` | 3.13 is the highest supported. |
| `pydantic` | `>=2.3.0` | Installed automatically. Powers all validation and serialization. |
| `geojson-pydantic` | `>=1.2.0` | Installed automatically. Provides the GeoJSON base types — any GeoJSON is valid muDM and vice versa. |

Both dependencies are pulled in automatically — you do not install them
separately. There is no scientific-compute stack and no Rust toolchain to set
up: `mudm` is pure Python.

## Quick install

=== "pip (end users)"

    ```bash
    pip install mudm
    ```

=== "uv (projects)"

    ```bash
    uv add mudm
    ```

This installs `mudm` together with `pydantic` and `geojson-pydantic`. Because
the package is pure Python, the same universal wheel works on every supported
platform — there is no per-platform build step.

## Install from GitHub

To install the latest unreleased code directly from the repository:

=== "uv"

    ```bash
    uv pip install "mudm @ git+https://github.com/NovagenResearch/mudm.git"
    ```

=== "pip"

    ```bash
    pip install "mudm @ git+https://github.com/NovagenResearch/mudm.git"
    ```

!!! note "No compile step"
    Unlike `mudm-tools`, a GitHub install of `mudm` does **not** build any native
    extension — it is plain Python and installs in seconds.

## Development setup

Clone the repository and let `uv` create and pin the environment:

```bash
git clone https://github.com/NovagenResearch/mudm.git
cd mudm
uv sync
```

`uv sync` installs the project plus its runtime dependencies into `.venv`.

### Run the tests

`pytest` is **not** a project dependency, so add it on the fly with `--with`:

```bash
uv run --with pytest pytest
```

### Build the docs

The documentation toolchain lives in the `docs` dependency group. Serve the
site locally with live reload:

```bash
uv run --group docs mkdocs serve
```

## Verify installation

Run this snippet to confirm the package imports, print its version, and
round-trip a tiny `FeatureCollection` through the core model:

```python
import mudm

print(f"mudm {mudm.__version__}")

obj = mudm.MuDM.model_validate({
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [10, 20]},
            "properties": {"label": "nucleus"},
        }
    ],
})
print(f"Model OK: {len(obj.root.features)} feature(s)")
```

Save it as `verify_install.py` and run it with your environment of choice:

=== "uv"

    ```bash
    uv run python verify_install.py
    ```

=== "python"

    ```bash
    python verify_install.py
    ```

Expected output (the first line shows whichever version you installed):

```text
mudm <version>
Model OK: 1 feature(s)
```

## Two packages, one ecosystem

!!! note "Two packages, one ecosystem"
    - **`mudm`** — *this* package: the core data model (Pydantic v2). It is pure Python with no compiled component. Provides `mudm.MuDM`, `mudm.model`, `mudm.tilemodel`, `mudm.transforms`, `mudm.layout`, and the provenance models.
    - **`mudm-tools`** — a **separate package** (import name `mudm_tools`) with the processing pipelines, tiling engines, and format converters, plus an optional Rust acceleration extension `mudm_tools._rs`. Its documentation lives at <https://novagenresearch.github.io/mudm-tools/>.

!!! note "Core `mudm` has no Rust/compiled component"
    The `RUST_AVAILABLE` flag, the `StreamingTileGenerator` tilers, and the
    `mudm_tools._rs` extension module belong to **`mudm-tools`**, not to this
    package. There is no `mudm._rs`. If you want high-throughput tiling or
    format conversion, install `mudm-tools` and follow its
    [installation guide](https://novagenresearch.github.io/mudm-tools/installation/).

## Next steps

- [Getting Started](getting-started.md) — build and validate your first muDM document.
- [Validation guide](guides/validation.md) — how `MuDM`, `MuDMFeature`, and `GeoJSON` accept and round-trip data.
- [Core data-model API](reference/models.md) — every public symbol in the `mudm` package.
- [muDM specification](specification.md) — the formal data model.
- For processing pipelines, tiling, and format converters, see the **mudm-tools** docs: [Getting Started](https://novagenresearch.github.io/mudm-tools/getting-started/) and the [converters guide](https://novagenresearch.github.io/mudm-tools/guides/converters/).
