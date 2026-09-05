import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "talemate_frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


def build_frontend():
    print("Checking frontend build...")
    if not (FRONTEND_DIST / "index.html").exists():
        print("Frontend dist not found. Building frontend with pnpm...")
        pnpm_bin = shutil.which("pnpm") or "pnpm"
        cmd = [pnpm_bin, "build"]
        result = subprocess.run(
            cmd, cwd=str(FRONTEND_DIR), shell=(sys.platform == "win32")
        )
        if result.returncode != 0:
            print("Error: Frontend build failed!")
            sys.exit(result.returncode)
    else:
        print("Frontend build found at:", FRONTEND_DIST)


def build_portable(mode="onefile"):
    build_frontend()

    platform_name = (
        "Windows"
        if sys.platform == "win32"
        else (
            "macOS"
            if sys.platform == "darwin"
            else "Linux" if sys.platform.startswith("linux") else sys.platform
        )
    )
    print(f"Building portable Talemate for {platform_name} (mode: {mode})...")

    sep = ";" if os.name == "nt" else ":"
    entry_point = ROOT_DIR / "src" / "talemate" / "desktop" / "app.py"

    embedded_py = ROOT_DIR / "embedded_python"
    if embedded_py.exists():
        os.environ["PATH"] = str(embedded_py) + os.pathsep + os.environ.get("PATH", "")

    python_exe = (
        str(embedded_py / "python.exe") if embedded_py.exists() else sys.executable
    )
    site_packages = ROOT_DIR / ".venv" / "Lib" / "site-packages"
    if not site_packages.exists():
        site_packages = (
            ROOT_DIR
            / ".venv"
            / "lib"
            / f"python{sys.version_info.major}.{sys.version_info.minor}"
            / "site-packages"
        )

    spec_file = ROOT_DIR / "packaging" / "Talemate-Desktop.spec"
    if mode == "onefile" and spec_file.exists():
        pyinstaller_args = [
            python_exe,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(spec_file),
        ]
    else:
        pyinstaller_args = [
            python_exe,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--name",
            "Talemate",
            f"--{mode}",
            "--paths",
            str(ROOT_DIR),
            "--paths",
            str(ROOT_DIR / "src"),
        ]

        if site_packages.exists():
            pyinstaller_args.extend(["--paths", str(site_packages)])

        icon_path = ROOT_DIR / "talemate_frontend" / "public" / "favicon.ico"
        if icon_path.exists():
            pyinstaller_args.extend(["--icon", str(icon_path)])

        pyinstaller_args.extend(
            [
                # Add frontend distribution
                "--add-data",
                f"{ROOT_DIR / 'talemate_frontend' / 'dist'}{sep}talemate_frontend/dist",
                # Add root templates
                "--add-data",
                f"{ROOT_DIR / 'templates'}{sep}templates",
                # Add prompt templates
                "--add-data",
                f"{ROOT_DIR / 'src' / 'talemate' / 'prompts' / 'templates'}{sep}talemate/prompts/templates",
                # Add default config example
                "--add-data",
                f"{ROOT_DIR / 'config.example.yaml'}{sep}.",
            ]
        )

        voice_lib = ROOT_DIR / "tts" / "voice" / "voice-library.json"
        if voice_lib.exists():
            pyinstaller_args.extend(["--add-data", f"{voice_lib}{sep}tts/voice"])

        pyinstaller_args.extend(
            [
                # Custom hooks directory (e.g. override NLTK hook to avoid bundling all AppData)
                "--additional-hooks-dir",
                str(ROOT_DIR / "packaging" / "hooks"),
                # Collect Talemate package metadata and data
                "--collect-all",
                "talemate",
                "--collect-all",
                "tiktoken",
                "--collect-all",
                "tiktoken_ext",
                "--collect-all",
                "uvicorn",
                "--copy-metadata",
                "fastapi",
                "--copy-metadata",
                "starlette",
                "--copy-metadata",
                "structlog",
                "--copy-metadata",
                "pydantic",
                "--copy-metadata",
                "jinja2",
                "--hidden-import",
                "tiktoken_ext",
                "--hidden-import",
                "tiktoken_ext.openai_public",
                # Essential hidden imports for ASGI / Uvicorn / WebSockets
                "--hidden-import",
                "uvicorn",
                "--hidden-import",
                "uvicorn.logging",
                "--hidden-import",
                "uvicorn.loops",
                "--hidden-import",
                "uvicorn.loops.auto",
                "--hidden-import",
                "uvicorn.protocols",
                "--hidden-import",
                "uvicorn.protocols.http",
                "--hidden-import",
                "uvicorn.protocols.http.auto",
                "--hidden-import",
                "uvicorn.protocols.websockets",
                "--hidden-import",
                "uvicorn.protocols.websockets.auto",
                "--hidden-import",
                "uvicorn.lifespan",
                "--hidden-import",
                "uvicorn.lifespan.on",
                "--hidden-import",
                "websockets",
                "--hidden-import",
                "websockets.legacy",
                "--hidden-import",
                "websockets.legacy.server",
                "--hidden-import",
                "frontend_wsgi",
                # Desktop WebView imports
                "--hidden-import",
                "webview",
                "--hidden-import",
                "webview.platforms.winforms",
                "--hidden-import",
                "clr_loader",
                "--hidden-import",
                "pythonnet",
                # Exclude heavy ML/Torch libraries for the Lite build
                "--exclude-module",
                "torch",
                "--exclude-module",
                "torchvision",
                "--exclude-module",
                "torchaudio",
                "--exclude-module",
                "torchcodec",
                "--exclude-module",
                "transformers",
                "--exclude-module",
                "sentence_transformers",
                "--exclude-module",
                "scipy",
                "--exclude-module",
                "matplotlib",
                "--exclude-module",
                "pandas",
                "--exclude-module",
                "f5_tts",
                "--exclude-module",
                "kokoro",
                "--exclude-module",
                "chatterbox",
                "--exclude-module",
                "pocket_tts",
                "--exclude-module",
                "bitsandbytes",
                "--exclude-module",
                "numba",
                "--exclude-module",
                "spacy",
                "--exclude-module",
                "pyarrow",
                "--exclude-module",
                "sklearn",
                "--exclude-module",
                "scikit_learn",
                "--exclude-module",
                "onnx",
                "--exclude-module",
                "onnxruntime",
                "--exclude-module",
                "diffusers",
                "--exclude-module",
                "llvmlite",
                "--exclude-module",
                "resemble_perth",
                "--exclude-module",
                "wandb",
                "--exclude-module",
                "gradio",
                "--exclude-module",
                "sympy",
                "--exclude-module",
                "datasets",
                "--exclude-module",
                "librosa",
                "--exclude-module",
                "boto3",
                "--exclude-module",
                "botocore",
                "--exclude-module",
                "safetensors",
                "--exclude-module",
                "hf_xet",
                "--exclude-module",
                "tkinter",
                "--exclude-module",
                "_tkinter",
                "--exclude-module",
                "tcl",
                "--exclude-module",
                "tk",
                "--exclude-module",
                "turtle",
                # Exclude dev & testing tools
                "--exclude-module",
                "pytest",
                "--exclude-module",
                "_pytest",
                "--exclude-module",
                "mypy",
                "--exclude-module",
                "pygments",
                "--exclude-module",
                "black",
                "--exclude-module",
                "isort",
                "--exclude-module",
                "pre_commit",
                "--exclude-module",
                "mkdocs",
                str(entry_point),
            ]
        )

    print("Running PyInstaller...")
    print("Command:", " ".join(pyinstaller_args))
    result = subprocess.run(pyinstaller_args, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        print("Error: PyInstaller build failed!")
        sys.exit(result.returncode)

    out_dir = ROOT_DIR / "dist"
    if mode == "onefile":
        out_file = out_dir / (
            "Talemate-Desktop.exe" if os.name == "nt" else "Talemate-Desktop"
        )
        if out_file.exists():
            size_mb = out_file.stat().st_size / (1024 * 1024)
            print(
                f"\nSUCCESS! Portable executable created: {out_file} ({size_mb:.2f} MB)"
            )
        if (out_dir / "Talemate-Desktop.app").exists():
            print(f"SUCCESS! macOS application bundle created: {out_dir / 'Talemate-Desktop.app'}")
    else:
        out_folder = out_dir / "Talemate-Desktop"
        print(f"\nSUCCESS! Portable folder created: {out_folder}")


def main():
    parser = argparse.ArgumentParser(description="Build Talemate Lite Portable")
    parser.add_argument(
        "--mode",
        choices=["onefile", "onedir"],
        default="onefile",
        help="Build mode: onefile (single .exe) or onedir (portable directory)",
    )
    args = parser.parse_args()
    build_portable(mode=args.mode)


if __name__ == "__main__":
    main()
