"""Talemate Desktop (Standalone Portable Edition)

This module provides the desktop application lifecycle for Talemate:
1. Native desktop window powered by Microsoft Edge WebView2 (pywebview).
2. In-process execution of both frontend (Uvicorn / FastAPI) and backend (WebSockets).
3. 100% in-place portable data storage (scenes, logs, config, tts voices next to .exe).
4. Zero modifications to upstream core files (path.py, run.py, state.py, voice_library.py).

All runtime workarounds required to run upstream Talemate inside a frozen
PyInstaller bundle are encapsulated dynamically within this entry point.
"""

import asyncio
import importlib.util
import multiprocessing
import os
from pathlib import Path
import shutil
import sys
import threading
import time
import types
import urllib.request
from typing import Optional

# ---------------------------------------------------------------------------
# Workaround 1: UTF-8 Console Output Reconfiguration
# ---------------------------------------------------------------------------
# Problem: On Windows, the default console codepage is often cp1251, cp1252, or
# cp866. When Talemate logs Unicode characters (LLM tokens, emojis, non-ASCII
# scenario titles), standard print() or logging calls raise UnicodeEncodeError.
# Fix: Force stdout and stderr streams to use UTF-8 with character replacement,
# ensuring the console stays functional and never crashes on non-ASCII output.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Workaround 2: Multiprocessing Freeze Support for PyInstaller
# ---------------------------------------------------------------------------
# Problem: On Windows, multiprocessing spawns new child processes by re-executing
# sys.executable. In a PyInstaller onefile binary, child processes will re-run
# the main application from line 1 instead of executing their target function,
# resulting in an infinite recursive process spawn ("fork bomb").
# Fix: Calling freeze_support() immediately intercepts child worker processes.
multiprocessing.freeze_support()

# ---------------------------------------------------------------------------
# Workaround 3: Microsoft Edge WebView2 Interop DLL Path Resolution
# ---------------------------------------------------------------------------
# Problem: pywebview on Windows depends on native WebView2Loader.dll and C#
# interop assemblies (Microsoft.Web.WebView2.Core.dll, WebBrowserInterop.x64.dll).
# pywebview.util.interop_dll_path expects these files in its python site-packages
# folder. Inside a frozen PyInstaller onefile bundle (sys._MEIPASS), the default
# search logic fails with FileNotFoundError.
# Fix: Wrap interop_dll_path to search candidate paths in _MEIPASS and next to
# sys.executable. Also suppress non-critical architecture probes (win-arm64, etc.).
import webview
import webview.util

if sys.platform == "win32":
    _orig_interop_dll_path = webview.util.interop_dll_path

    def _patched_interop_dll_path(dll_name: str) -> str:
        try:
            return _orig_interop_dll_path(dll_name)
        except FileNotFoundError:
            base_dirs = []
            if hasattr(sys, "_MEIPASS"):
                base_dirs.append(sys._MEIPASS)
            if getattr(sys, "frozen", False):
                base_dirs.append(os.path.dirname(sys.executable))

            for base in base_dirs:
                candidates = [
                    os.path.join(
                        base, "webview", "lib", "runtimes", dll_name, "native"
                    ),
                    os.path.join(base, "webview", "lib", "runtimes", dll_name),
                    os.path.join(base, "webview", "lib", dll_name),
                    os.path.join(base, "lib", "runtimes", dll_name, "native"),
                    os.path.join(base, "lib", dll_name),
                    os.path.join(base, dll_name, "native"),
                    os.path.join(base, dll_name),
                ]
                for c in candidates:
                    if os.path.exists(c):
                        return c

            if dll_name in ("win-arm64", "win-x64", "win-x86"):
                return ""

            raise

    webview.util.interop_dll_path = _patched_interop_dll_path

# ---------------------------------------------------------------------------
# Workaround 4: Early Path Bootstrapping for 100% Upstream Purity
# ---------------------------------------------------------------------------
# Problem: Upstream talemate.path computes TALEMATE_ROOT via Path(__file__).parent...
# In PyInstaller, __file__ points to the temporary extraction folder (sys._MEIPASS).
# If unpatched, all user data (config.yaml, scenes/, logs/) would be written to
# %TEMP% and discarded when the app closes.
#
# Why not edit src/talemate/path.py directly?
# Editing path.py causes git merge conflicts whenever pulling new upstream commits.
# To keep path.py 100% identical to upstream origin/main:
# 1. We create a dummy 'talemate' module in sys.modules.
# 2. We import talemate.path early and redirect paths to exec_root (portable folder).
# 3. We remove dummy 'talemate' and allow standard 'import talemate' to proceed.
if getattr(sys, "frozen", False):
    bundle_root = Path(getattr(sys, "_MEIPASS", sys.executable)).resolve()
    exec_root = Path(sys.executable).resolve().parent
    if (
        sys.platform == "darwin"
        and exec_root.name == "MacOS"
        and exec_root.parent.name == "Contents"
        and exec_root.parent.parent.suffix == ".app"
    ):
        exec_root = exec_root.parent.parent.parent

    _spec = importlib.util.find_spec("talemate")
    _dummy_talemate = types.ModuleType("talemate")
    _dummy_talemate.__path__ = list(_spec.submodule_search_locations)
    _dummy_talemate.__package__ = "talemate"
    _dummy_talemate.__spec__ = _spec
    sys.modules["talemate"] = _dummy_talemate

    import talemate.path

    talemate.path.TALEMATE_ROOT = exec_root
    talemate.path.SCENES_DIR = exec_root / "scenes"
    talemate.path.TEMPLATES_DIR = (
        exec_root / "templates"
        if (exec_root / "templates").exists()
        else bundle_root / "templates"
    )
    talemate.path.TTS_DIR = exec_root / "tts"
    talemate.path.LOGS_DIR = exec_root / "logs"
    talemate.path.CONFIG_FILE = exec_root / "config.yaml"

    _path_mod = talemate.path
    del sys.modules["talemate"]
else:
    bundle_root = Path(__file__).resolve().parent.parent.parent
    _path_mod = None

import talemate

if _path_mod is not None:
    talemate.path = _path_mod
import talemate.path
import talemate.agents.tts.voice_library as _voice_lib
import talemate.server.run as server_run
import structlog

# ---------------------------------------------------------------------------
# Workaround 5: Dynamic TTS Voice Library Redirection & Safe Saving
# ---------------------------------------------------------------------------
# Problem: Upstream src/talemate/agents/tts/voice_library.py hardcodes:
#   VOICE_LIBRARY_PATH = Path(__file__).parent.parent.parent.parent.parent / "tts" / "voice" / "voice-library.json"
# In frozen mode, traversing 5 levels from __file__ points to the system %TEMP% dir.
# Furthermore, upstream save_voice_library() does not create parent directories
# before open(VOICE_LIBRARY_PATH, "w"), throwing FileNotFoundError: [Errno 2]
# if tts/voice/ does not exist yet on clean start.
#
# To keep voice_library.py 100% identical to upstream origin/main:
# 1. We dynamically point _voice_lib.VOICE_LIBRARY_PATH to portable TTS_DIR.
# 2. We wrap _voice_lib.save_voice_library to guarantee parent directory creation.
_voice_lib.VOICE_LIBRARY_PATH = talemate.path.TTS_DIR / "voice" / "voice-library.json"
_orig_save_voice_lib = _voice_lib.save_voice_library


async def _safe_save_voice_library(library):
    _voice_lib.VOICE_LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    return await _orig_save_voice_lib(library)


_voice_lib.save_voice_library = _safe_save_voice_library

log = structlog.get_logger("talemate.desktop")


def wait_for_server(url: str, timeout: float = 30.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


# ---------------------------------------------------------------------------
# Workaround 6: In-Process Frontend Server Thread
# ---------------------------------------------------------------------------
# Problem: Upstream Talemate serves its compiled Vue 3 frontend by invoking
# an external shell subprocess: 'uvicorn frontend_wsgi:application --port 8082'
# in server/run.py. In a portable standalone .exe, there is no external python.exe
# or uvicorn.exe on the user's PATH, causing subprocess spawning to fail or open
# an unwanted secondary command prompt window.
#
# Fix: Run Uvicorn directly in-process within a dedicated background daemon thread.
# We explicitly set lifespan="off" because the WSGI/ASGI frontend wrapper only serves
# static dist/ assets without ASGI lifespan event handlers, avoiding any shutdown hangs.
class FrontendServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 8082):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server: Optional[object] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        import uvicorn
        from frontend_wsgi import application

        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        config = uvicorn.Config(
            app=application,
            host=self.host,
            port=self.port,
            log_level="warning",
            access_log=False,
            lifespan="off",
        )
        self.server = uvicorn.Server(config)
        try:
            self.loop.run_until_complete(self.server.serve())
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        except Exception as exc:
            log.error("Frontend server error", error=str(exc))
        finally:
            try:
                tasks = [t for t in asyncio.all_tasks(self.loop) if not t.done()]
                for t in tasks:
                    t.cancel()
                if tasks:
                    self.loop.run_until_complete(
                        asyncio.gather(*tasks, return_exceptions=True)
                    )
            except Exception:
                pass

    def stop(self):
        if self.server and hasattr(self.server, "should_exit"):
            self.server.should_exit = True
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


# ---------------------------------------------------------------------------
# Workaround 7: In-Process Backend Server Thread with backend_only = True
# ---------------------------------------------------------------------------
# Problem: Upstream server_run.run_server(args) defaults to orchestrating both
# backend and frontend processes.
#
# Fix: Pass a synthetic args object with args.backend_only = True. This instructs
# upstream run_server() to only start the WebSocket API and client/agent pipelines,
# leaving frontend serving to our in-process FrontendServerThread above.
class BackendServerThread(threading.Thread):
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5050,
        frontend_host: str = "127.0.0.1",
        frontend_port: int = 8082,
    ):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.frontend_host = frontend_host
        self.frontend_port = frontend_port
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        class ServerArgs:
            pass

        args = ServerArgs()
        args.command = "runserver"
        args.host = self.host
        args.port = self.port
        args.frontend_host = self.frontend_host
        args.frontend_port = self.frontend_port
        args.backend_only = True

        try:
            server_run.run_server(args)
        except Exception as exc:
            log.error("Backend server stopped with error", error=str(exc))

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


# ---------------------------------------------------------------------------
# Workaround 8: Portable In-Place Storage & Environment Initialization
# ---------------------------------------------------------------------------
# Problem: On first launch in a clean portable directory, no config.yaml or
# data folders exist. Upstream expects config.yaml to exist and raises errors
# if directories are missing.
#
# Fix:
# 1. Automatically copy config.example.yaml -> config.yaml next to the .exe.
# 2. Ensure scenes/, logs/, and tts/voice/ directories exist before server boot.
def ensure_environment():
    talemate.path.SCENES_DIR.mkdir(parents=True, exist_ok=True)
    talemate.path.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    (talemate.path.TTS_DIR / "voice").mkdir(parents=True, exist_ok=True)

    if not talemate.path.CONFIG_FILE.exists():
        example_config = bundle_root / "config.example.yaml"
        if not example_config.exists():
            example_config = talemate.path.TALEMATE_ROOT / "config.example.yaml"
        if example_config.exists():
            log.info(
                "Creating default config from example",
                target=str(talemate.path.CONFIG_FILE),
            )
            shutil.copyfile(example_config, talemate.path.CONFIG_FILE)

    voice_lib_target = talemate.path.TTS_DIR / "voice" / "voice-library.json"
    if not voice_lib_target.exists():
        voice_lib_source = bundle_root / "tts" / "voice" / "voice-library.json"
        if voice_lib_source.exists():
            shutil.copyfile(voice_lib_source, voice_lib_target)


# ---------------------------------------------------------------------------
# Workaround 9 & 10: Desktop Window Lifecycle & Clean Process Shutdown
# ---------------------------------------------------------------------------
# Problem: When the desktop window is closed via the 'X' button or Alt+F4,
# standard Python programs with daemon threads often leave orphaned ("zombie")
# background processes running in Task Manager holding TCP ports 5050 and 8082,
# preventing subsequent launches.
#
# Fix: The finally block below intercepts window close, signals both server
# threads to terminate cleanly, awaits their joins, and calls sys.exit(0).
def launch_desktop(
    host: str = "127.0.0.1",
    port: int = 5050,
    frontend_host: str = "127.0.0.1",
    frontend_port: int = 8082,
    width: int = 1400,
    height: int = 900,
):
    ensure_environment()

    frontend_thread = FrontendServerThread(host=frontend_host, port=frontend_port)
    frontend_thread.start()

    backend_thread = BackendServerThread(
        host=host,
        port=port,
        frontend_host=frontend_host,
        frontend_port=frontend_port,
    )
    backend_thread.start()

    frontend_url = f"http://{frontend_host}:{frontend_port}"
    log.info("Waiting for Talemate frontend server...", url=frontend_url)
    wait_for_server(frontend_url, timeout=25.0)

    window = webview.create_window(
        title="Talemate Desktop",
        url=frontend_url,
        width=width,
        height=height,
        min_size=(1024, 700),
        text_select=True,
    )

    # Resolve multi-resolution window icon
    icon_file = bundle_root / "talemate.ico"
    if not icon_file.exists():
        icon_file = Path(__file__).resolve().parent / "talemate.ico"
    if not icon_file.exists():
        icon_file = talemate.path.TALEMATE_ROOT / "talemate.ico"
    if not icon_file.exists() and sys.platform != "win32":
        png_icon = bundle_root / "talemate_frontend" / "dist" / "favicon.ico"
        if png_icon.exists():
            icon_file = png_icon
    icon_arg = str(icon_file) if icon_file.exists() else None

    try:
        if sys.platform == "win32":
            webview.start(gui="edgechromium", debug=False, icon=icon_arg)
        elif sys.platform == "darwin":
            webview.start(gui="cocoa", debug=False, icon=icon_arg)
        else:
            try:
                webview.start(gui="gtk", debug=False, icon=icon_arg)
            except Exception:
                webview.start(debug=False, icon=icon_arg)
    except Exception as exc:
        log.exception("Webview failed to run", error=str(exc))
    finally:
        log.info("Window closed, shutting down servers...")
        frontend_thread.stop()
        backend_thread.stop()
        frontend_thread.join(timeout=1.5)
        backend_thread.join(timeout=1.5)
        sys.exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Talemate Desktop")
    subparser = parser.add_subparsers(dest="command")

    runserver_parser = subparser.add_parser(
        "runserver", help="Run the talemate server in headless mode"
    )
    runserver_parser.add_argument(
        "--host", default="127.0.0.1", help="Backend Hostname"
    )
    runserver_parser.add_argument(
        "--port", type=int, default=5050, help="Backend Port"
    )
    runserver_parser.add_argument(
        "--frontend-host", default="127.0.0.1", help="Frontend Hostname"
    )
    runserver_parser.add_argument(
        "--frontend-port", type=int, default=8082, help="Frontend Port"
    )
    runserver_parser.add_argument(
        "--backend-only", action="store_true", help="Run only backend"
    )

    desktop_parser = subparser.add_parser(
        "desktop", help="Run the talemate desktop GUI application"
    )
    desktop_parser.add_argument(
        "--host", default="127.0.0.1", help="Backend Hostname"
    )
    desktop_parser.add_argument(
        "--port", type=int, default=5050, help="Backend Port"
    )
    desktop_parser.add_argument(
        "--frontend-host", default="127.0.0.1", help="Frontend Hostname"
    )
    desktop_parser.add_argument(
        "--frontend-port", type=int, default=8082, help="Frontend Port"
    )

    args = parser.parse_args()

    if args.command == "runserver":
        ensure_environment()
        server_run.run_server(args)
    elif args.command == "desktop":
        launch_desktop(
            host=args.host,
            port=args.port,
            frontend_host=args.frontend_host,
            frontend_port=args.frontend_port,
        )
    else:
        launch_desktop()


if __name__ == "__main__":
    main()
