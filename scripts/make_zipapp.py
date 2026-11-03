#!/usr/bin/env python3
"""Single-File .pyz Zipapp Compiler for BenchWarmer.

Bundles the pure-Python runtime, embedded SQLite database, canonical checksum,
SQL schema, and MCP JSON schema into a standalone, zero-dependency executable.
"""

from pathlib import Path
import shutil
import sys
import tempfile
import zipapp

ROOT_DIR = Path(__file__).resolve().parent.parent


def build_zipapp(target_pyz: Path) -> Path:
    target_pyz.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp_dir:
        staging_dir = Path(temp_dir) / "staging"
        staging_dir.mkdir(parents=True, exist_ok=True)

        # Copy benchwarmer package
        src_benchwarmer = ROOT_DIR / "src" / "benchwarmer"
        dest_benchwarmer = staging_dir / "benchwarmer"
        shutil.copytree(src_benchwarmer, dest_benchwarmer, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        # Verify essential packaged assets exist
        required_assets = [
            dest_benchwarmer / "data" / "benchmarks.db",
            dest_benchwarmer / "data" / "checksum.sha256",
            dest_benchwarmer / "db" / "schema.sql",
            dest_benchwarmer / "mcp_schema.json",
        ]
        for asset in required_assets:
            if not asset.exists():
                raise FileNotFoundError(f"Missing required packaged asset for zipapp: {asset}")

        # Create root __main__.py
        root_main = staging_dir / "__main__.py"
        root_main.write_text(
            "import sys\n"
            "from benchwarmer.cli import main\n\n"
            "if __name__ == '__main__':\n"
            "    sys.exit(main())\n",
            encoding="utf-8"
        )

        # Compile zipapp
        if target_pyz.exists():
            target_pyz.unlink()

        zipapp.create_archive(
            source=staging_dir,
            target=target_pyz,
            interpreter="/usr/bin/env python3",
            main=None,  # Handled by root __main__.py
            compressed=True,
        )

    return target_pyz


def main() -> int:
    target_pyz = ROOT_DIR / "dist" / "benchwarmer.pyz"
    print(f"Building single-file zipapp executable at {target_pyz}...")
    build_zipapp(target_pyz)
    size_kb = target_pyz.stat().st_size / 1024.0
    print(f"Successfully compiled {target_pyz} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
