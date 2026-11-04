"""Post-installation lifecycle hook for BenchWarmer.

Ensures Tcl/Tk runtime assets are fully linked/copied into the sovereign
environment's lib directory so the desktop Tkinter GUI runs out of the box
on all host platforms without requiring external environment variables.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-dir", type=str, required=True)
    parser.add_argument("--bundle-dir", type=str, default="")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--hook", type=str, default="post_install")
    args, _ = parser.parse_known_args()

    install_dir = Path(args.install_dir).resolve()
    print(f"[benchwarmer hook] Running post-install in {install_dir}...")

    # On Windows, ensure Tcl/Tk libraries exist in install_dir / lib / tcl9.0 etc.
    if sys.platform == "win32":
        tcl_dest = install_dir / "lib" / "tcl9.0"
        if not tcl_dest.exists():
            # Search for source tcl library in base interpreter or bootstrapped python
            candidates = [
                install_dir / "base" / "Library" / "lib",
                Path(sys.base_prefix) / "Library" / "lib",
                Path(sys.prefix) / "Library" / "lib",
                Path(r"C:\dev\auraseed\.bootstrapped_python\Library\lib"),
            ]
            for cand in candidates:
                if cand.exists() and (cand / "tcl9.0").exists():
                    print(f"[benchwarmer hook] Copying Tcl/Tk runtime assets from {cand}...")
                    dest_lib = install_dir / "lib"
                    dest_lib.mkdir(parents=True, exist_ok=True)
                    for item in cand.iterdir():
                        dest_item = dest_lib / item.name
                        if not dest_item.exists():
                            if item.is_dir():
                                shutil.copytree(item, dest_item)
                            else:
                                shutil.copy2(item, dest_item)
                    break

    print("[benchwarmer hook] Post-install configuration complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
