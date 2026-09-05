# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

ROOT_DIR = Path(SPECPATH).resolve().parent

site_packages = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if not site_packages.exists():
    site_packages = (
        ROOT_DIR
        / ".venv"
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )
if not site_packages.exists():
    lib_dir = ROOT_DIR / ".venv" / "lib"
    if lib_dir.exists():
        py_dirs = list(lib_dir.glob("python*/site-packages"))
        if py_dirs:
            site_packages = py_dirs[0]

pathex = [str(ROOT_DIR), str(ROOT_DIR / "src")]
if site_packages.exists():
    pathex.append(str(site_packages))

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

datas = [
    (str(ROOT_DIR / "talemate_frontend" / "dist"), "talemate_frontend/dist"),
    (str(ROOT_DIR / "templates"), "templates"),
    (
        str(ROOT_DIR / "src" / "talemate" / "prompts" / "templates"),
        "talemate/prompts/templates",
    ),
    (str(ROOT_DIR / "config.example.yaml"), "."),
]

voice_lib = ROOT_DIR / "tts" / "voice" / "voice-library.json"
if voice_lib.exists():
    datas.append((str(voice_lib), "tts/voice"))

if (ROOT_DIR / "talemate.ico").exists():
    datas.append((str(ROOT_DIR / "talemate.ico"), "."))

binaries = []
hiddenimports = [
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "frontend_wsgi",
    "webview",
]

# Platform-specific GUI backends and dependencies
if IS_WIN:
    hiddenimports += [
        "webview.platforms.winforms",
        "clr_loader",
        "pythonnet",
    ]
elif IS_MAC:
    # macOS: Cocoa / WebKit (WKWebView) via PyObjC
    hiddenimports += [
        "webview.platforms.cocoa",
        "objc",
        "AppKit",
        "Foundation",
        "WebKit",
        "PyObjCTools",
        "PyObjCTools.AppHelper",
    ]
elif IS_LINUX:
    # Linux: WebKitGTK / GTK
    hiddenimports += [
        "webview.platforms.gtk",
        "gi",
        "gi.repository.Gtk",
        "gi.repository.Gdk",
        "gi.repository.Gio",
        "gi.repository.GLib",
        "gi.repository.WebKit2",
        "gi.repository.Soup",
        "gi.repository.JavaScriptCore",
    ]

for pkg in ["fastapi", "starlette", "structlog", "pydantic", "jinja2"]:
    datas += copy_metadata(pkg)

for pkg in ["talemate", "tiktoken", "tiktoken_ext", "uvicorn", "webview"]:
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

if IS_MAC:
    for pkg in ["objc", "AppKit", "Foundation", "WebKit"]:
        try:
            pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
            datas += pkg_datas
            binaries += pkg_binaries
            hiddenimports += pkg_hidden
        except Exception:
            pass

# Windows-specific: bundle Microsoft Edge WebView2 interop libraries and native loaders
if IS_WIN:
    wv_lib = site_packages / "webview" / "lib"
    if wv_lib.exists():
        datas += [
            (str(wv_lib / "Microsoft.Web.WebView2.Core.dll"), "."),
            (str(wv_lib / "Microsoft.Web.WebView2.WinForms.dll"), "."),
            (str(wv_lib / "WebBrowserInterop.x64.dll"), "."),
            (str(wv_lib / "WebBrowserInterop.x86.dll"), "."),
            (
                str(wv_lib / "runtimes" / "win-x64" / "native" / "WebView2Loader.dll"),
                "win-x64",
            ),
            (
                str(wv_lib / "runtimes" / "win-arm64" / "native" / "WebView2Loader.dll"),
                "win-arm64",
            ),
            (
                str(wv_lib / "runtimes" / "win-x86" / "native" / "WebView2Loader.dll"),
                "win-x86",
            ),
        ]

if IS_WIN:
    icon_path = str(ROOT_DIR / "talemate.ico")
elif IS_MAC:
    icon_path = str(ROOT_DIR / "talemate.icns")
else:
    icon_path = str(ROOT_DIR / "talemate.ico")

a = Analysis(
    [str(ROOT_DIR / "src" / "talemate" / "desktop" / "app.py")],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(ROOT_DIR / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ML / Torch heavy libraries
        "torch",
        "torchvision",
        "torchaudio",
        "torchcodec",
        "transformers",
        "sentence_transformers",
        "scipy",
        "matplotlib",
        "pandas",
        "f5_tts",
        "kokoro",
        "chatterbox",
        "pocket_tts",
        "bitsandbytes",
        "numba",
        "spacy",
        "pyarrow",
        "sklearn",
        "scikit_learn",
        "onnx",
        "onnxruntime",
        "diffusers",
        "llvmlite",
        "resemble_perth",
        "wandb",
        "gradio",
        "sympy",
        "datasets",
        "librosa",
        "boto3",
        "botocore",
        "safetensors",
        "hf_xet",
        "tkinter",
        "_tkinter",
        "tcl",
        "tk",
        "turtle",
        # Dev & testing tools
        "pytest",
        "_pytest",
        "mypy",
        "pygments",
        "black",
        "isort",
        "pre_commit",
        "mkdocs",
    ],
    noarchive=False,
    optimize=0,
)

# Filter out heavy ML / unused binary DLLs and deduplicate OpenBLAS
EXCLUDED_BINARY_PATTERNS = (
    "arrow",
    "parquet",
    "onnxruntime",
    "hf_xet",
    "safetensors",
    "tcl8",
    "tk8",
    "torch",
    "c10",
    "perth",
    "llvmlite",
    "sklearn",
    "librosa",
)

seen_openblas = False
unique_binaries = []
for item in a.binaries:
    dest, src, typ = item
    fname = os.path.basename(dest).lower()

    # Always preserve OpenBLAS DLL (required by NumPy), deduplicating if multiple copies exist
    if "openblas" in fname:
        if seen_openblas:
            continue
        seen_openblas = True
        unique_binaries.append(item)
        continue

    if any(p in fname for p in EXCLUDED_BINARY_PATTERNS):
        continue

    unique_binaries.append(item)
a.binaries = unique_binaries

# Filter out heavy unused data packages (e.g. AWS botocore schemas, Tcl/Tk data)
EXCLUDED_DATA_PREFIXES = (
    "botocore",
    "tcl",
    "tk",
    "torch",
    "transformers",
    "sentence_transformers",
    "sklearn",
    "pandas",
)
filtered_datas = []
for item in a.datas:
    dest, src, typ = item
    dest_lower = dest.lower()
    if any(dest_lower.startswith(p) for p in EXCLUDED_DATA_PREFIXES):
        continue
    filtered_datas.append(item)
a.datas = filtered_datas

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Talemate-Desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if os.path.exists(icon_path) else None,
)

if IS_MAC:
    # macOS application bundle (.app)
    app = BUNDLE(
        exe,
        name="Talemate-Desktop.app",
        icon=icon_path if os.path.exists(icon_path) else None,
        bundle_identifier="ai.vegu.talemate",
        info_plist={
            "CFBundleShortVersionString": "0.39.0",
            "CFBundleIdentifier": "ai.vegu.talemate",
            "CFBundleName": "Talemate Desktop",
            "NSHighResolutionCapable": "True",
            "LSBackgroundOnly": "False",
            "NSRequiresAquaSystemAppearance": "False",
            "NSAppTransportSecurity": {
                "NSAllowsArbitraryLoads": True,
            },
        },
    )
