#!/usr/bin/env python3
"""Regenerate custom_components/nature_remo/models.py from the Nature API spec.

The upstream OpenAPI document describes the whole Nature API (131 schemas), most
of which this integration never touches.  The spec is therefore pruned to the
endpoints in ``USED_OPERATIONS`` plus the transitive closure of the schemas they
reference, and dataclasses are generated from the result.

Usage::

    python3 script/generate_models.py            # fetch the spec and generate
    python3 script/generate_models.py --spec /path/to/swagger.json

Requires ``datamodel-code-generator``; it is run through ``uvx`` when it is not
importable, so no permanent dependency is added.  Both the version and the
formatter extra are pinned, so that regenerating reformats nothing by itself.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request

SPEC_URL = "https://swagger.nature.global/swagger.json"

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "custom_components" / "nature_remo" / "models.py"

# The operations the integration actually calls.  Keep in sync with api.py.
USED_OPERATIONS = {
    "/1/users/me": ["get"],
    "/1/devices": ["get"],
    "/1/appliances": ["get"],
    "/1/signals/{signalid}/send": ["post"],
    "/1/appliances/{applianceid}/aircon_settings": ["post"],
    "/1/appliances/{applianceid}/light": ["post"],
}

CODEGEN_VERSION = "0.79.0"

CODEGEN_ARGS = [
    "--input-file-type",
    "openapi",
    "--output-model-type",
    "dataclasses.dataclass",
    "--target-python-version",
    "3.11",
    "--use-standard-collections",
    "--use-union-operator",
    # Without this, a property that is both required and nullable loses its
    # nullability: the spec marks 19 of them, LightResponse.buttons and
    # AirConRangeResponse.modes among them, and the annotations would promise a
    # list where the API is allowed to send null.
    "--strict-nullable",
    # Inline enums would otherwise become classes named Kind1/Type6/...; as
    # Literals they stay readable and need no runtime coercion when decoding.
    "--enum-field-as-literal",
    "all",
    # Field names are deliberately NOT snake_cased: they must match the wire
    # format so pydantic can map JSON keys straight onto fields.
    # ruff rather than black/isort: it is what Home Assistant formats with, it
    # is one flag rather than two (--formatters is nargs="+", so repeating the
    # flag would silently keep only the last one), and the codegen deprecates
    # its black/isort path.
    "--formatters",
    "ruff-check",
    "ruff-format",
]

HEADER = """\
\"\"\"Data types of the Nature API, generated from its OpenAPI specification.

DO NOT EDIT BY HAND.  Regenerate with::

    python3 script/generate_models.py

Field names match the JSON wire format exactly (including ``tempUnit`` and
``fixedButtons``), which is what lets pydantic map a payload onto these
dataclasses without a name translation table.
\"\"\"

"""


def collect_refs(node: object, found: set[str]) -> None:
    """Collect every schema name referenced by ``node``."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                found.add(value.rsplit("/", 1)[-1])
            else:
                collect_refs(value, found)
    elif isinstance(node, list):
        for value in node:
            collect_refs(value, found)


def prune(spec: dict) -> dict:
    """Reduce ``spec`` to the used operations and the schemas they need."""
    schemas = spec["components"]["schemas"]
    paths: dict[str, dict] = {}
    seeds: set[str] = set()
    for path, methods in USED_OPERATIONS.items():
        paths[path] = {method: spec["paths"][path][method] for method in methods}
        collect_refs(paths[path], seeds)

    closure: set[str] = set()
    queue = list(seeds)
    while queue:
        name = queue.pop()
        if name in closure:
            continue
        closure.add(name)
        referenced: set[str] = set()
        collect_refs(schemas[name], referenced)
        queue.extend(referenced - closure)

    return {
        "openapi": spec["openapi"],
        "info": spec["info"],
        "servers": spec["servers"],
        "paths": paths,
        "components": {"schemas": {name: schemas[name] for name in sorted(closure)}},
    }


def codegen_command() -> list[str]:
    """Return the argv prefix that runs datamodel-codegen."""
    if shutil.which("datamodel-codegen"):
        return ["datamodel-codegen"]
    if shutil.which("uvx"):
        return [
            "uvx",
            "--from",
            f"datamodel-code-generator[ruff]=={CODEGEN_VERSION}",
            "datamodel-codegen",
        ]
    sys.exit("datamodel-code-generator not found; install it or install uv")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", help="local spec file instead of fetching SPEC_URL")
    args = parser.parse_args()

    if args.spec:
        spec = json.loads(pathlib.Path(args.spec).read_text(encoding="utf-8"))
    else:
        print(f"fetching {SPEC_URL}")
        with urllib.request.urlopen(SPEC_URL, timeout=60) as response:
            spec = json.load(response)

    pruned = prune(spec)
    print(
        f"pruned to {len(pruned['paths'])} paths and "
        f"{len(pruned['components']['schemas'])} schemas "
        f"(of {len(spec['components']['schemas'])})"
    )

    with tempfile.TemporaryDirectory() as tmp:
        pruned_path = pathlib.Path(tmp) / "swagger_pruned.json"
        generated_path = pathlib.Path(tmp) / "models.py"
        pruned_path.write_text(json.dumps(pruned, indent=1), encoding="utf-8")
        subprocess.run(
            [
                *codegen_command(),
                "--input",
                str(pruned_path),
                "--output",
                str(generated_path),
                *CODEGEN_ARGS,
            ],
            check=True,
        )
        generated = generated_path.read_text(encoding="utf-8")

    # Drop the generator's own banner: it carries a timestamp and the temporary
    # input path, so keeping it would make every regeneration a diff.
    body = (
        generated.split("\n\n", 1)[1]
        if generated.startswith("# generated")
        else generated
    )
    OUTPUT.write_text(HEADER + body.lstrip("\n"), encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
