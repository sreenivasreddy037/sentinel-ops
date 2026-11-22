"""Build a relocatable same-platform runtime bundle on a trusted CI runner.

Third-party binaries come from the locked dependencies and Astral's managed Python.
"""

import hashlib
import json
import platform
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from export_desktop import ENTRIES  # noqa: E402


def ignore_caches(directory, names):
    return {name for name in names if name == "__pycache__" or name.endswith(".pyc")}


def main():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This bundle target is Apple silicon macOS")
    tools = ROOT / ".tools"
    tools.mkdir(exist_ok=True)
    # uv's venv executable resolves to the managed, relocatable standalone interpreter.
    interpreter_root = Path(sys.executable).resolve().parents[1]
    if "cpython-" not in interpreter_root.name or not (interpreter_root / "lib/python3.12").is_dir():
        raise SystemExit("Expected a managed standalone Python 3.12 installation")
    shutil.copytree(interpreter_root, tools / "python-runtime", symlinks=True, ignore=ignore_caches)
    packages = Path(sys.prefix) / "lib/python3.12/site-packages"
    shutil.copytree(packages, tools / "site-packages", symlinks=True, ignore=ignore_caches)
    (tools / "site-packages/bin").mkdir(exist_ok=True)
    shutil.copy2(Path(sys.prefix) / "bin/ruff", tools / "site-packages/bin/ruff")
    uv = shutil.which("uv")
    if uv:
        (tools / "bin").mkdir(exist_ok=True)
        shutil.copy2(uv, tools / "bin/uv")
    manifest = {"system": platform.system(), "machine": platform.machine(),
                "python": platform.python_version(), "lock_sha256": hashlib.sha256(
                    (ROOT / "uv.lock").read_bytes()).hexdigest()}
    (tools / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    output = ROOT / "dist/SentinelOps-macos-arm64.tar.gz"
    output.parent.mkdir(exist_ok=True)
    with tarfile.open(output, "w:gz", compresslevel=1) as archive:
        for entry in ENTRIES + [".tools"]:
            source = ROOT / entry
            if source.exists():
                archive.add(source, arcname="SentinelOps/" + entry,
                            filter=lambda info: None if "__pycache__" in info.name else info)
    print(f"Prepared {output} ({output.stat().st_size / 1024 / 1024:.1f} MiB)")


if __name__ == "__main__":
    main()
