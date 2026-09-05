# Talemate Desktop (Portable Edition)

> [!NOTE]
> **This repository is a fork of [vegu-ai/talemate](https://github.com/vegu-ai/talemate)** dedicated to providing a **zero-install, portable desktop application** with a native GUI window and fully self-contained local storage.
>
> 📦 **Download Pre-built Releases**: Download the latest portable package for your platform from the [**Releases**](../../releases) page!

### Key Features of Portable Edition

- **Zero-Install Single Executable**: Run Talemate with a single click. No need to install Python, Node.js, pnpm, C++ build tools, or Git on your machine.
- **Native Desktop GUI**: Runs inside a dedicated desktop window powered by native WebView (Microsoft Edge WebView2 on Windows, WebKitGTK on Linux, WebKit/Cocoa on macOS). No terminal or external browser required.
- **100% In-Place Portable Storage**: All user data (`config.yaml`, scenes directory `scenes/`, logs `logs/`, and custom voices `tts/`) are created and stored directly next to the executable. Nothing is written to the registry or system directories.
- **Lightweight (~90 MB)**: Heavy local PyTorch/ML frameworks (~10 GB) are excluded from the portable bundle. Full support for all remote and local API providers (OpenAI, Anthropic, Gemini, OpenRouter, Mistral, Cohere, Groq, KoboldCpp, LMStudio, Ollama, ElevenLabs, etc.).
- **Clean Process Lifecycle**: Frontend and backend servers run in-process with graceful shutdown upon closing the desktop window — zero background zombie processes.

### Platform Support & Call for Contributors

| Platform | Status | Details |
|---|---|---|
| **Windows (x64)** | **Tested & Working** | Native Edge WebView2, single-file `Talemate-Desktop.exe` |
| **Linux (x86_64)** | *CI Built / Testing Wanted* | Native WebKitGTK, single-file portable `Talemate-Desktop` |
| **macOS (Apple Silicon)** | *CI Built / Testing Wanted* | Native Cocoa / WKWebView, portable `.app` bundle |

> [!TIP]
> **Contributors & Testers Welcome**: Portable builds for Linux and macOS are experimental and have not been tested. If you are on Linux or macOS, please help test the packaging workflows and submit PRs or feedback!

---

# Talemate

Roleplay with AI with a focus on strong narration and consistent world and game state tracking.

<div align="center">

|<img src="docs/img/ss-1.png" width="400" height="250" alt="Screenshot 1">|<img src="docs/img/ss-2.png" width="400" height="250" alt="Screenshot 2">|
|------------------------------------------|------------------------------------------|
|<img src="docs/img/ss-3.png" width="400" height="250" alt="Screenshot 3">|<img src="docs/img/ss-4.png" width="400" height="250" alt="Screenshot 4">|

</div>

## Core Features

- Multiple agents for dialogue, narration, summarization, direction, editing, world state management, character/scenario creation, text-to-speech, and visual generation
- Supports per agent API selection
- Long-term memory and passage of time tracking
- Narrative world state management to reinforce character and world truths
- Creative tools for managing NPCs, AI-assisted character, and scenario creation with template support
- Node editor for creating complex scenarios and re-usable modules
- Context management for character details, world information, past events, and pinned information
- Customizable templates for all prompts using Jinja2
- Modern, responsive UI

## Documentation

- [Installation and Getting started](https://vegu-ai.github.io/talemate/)
- [User Guide](https://vegu-ai.github.io/talemate/user-guide/interacting/)

## Discord Community

Need help? Join the new [Discord community](https://discord.gg/8bGNRmFxMj)

## Supported APIs

- [OpenAI](https://platform.openai.com/overview)
- [Anthropic](https://www.anthropic.com/)
- [mistral.ai](https://mistral.ai/)
- [Cohere](https://www.cohere.com/)
- [Groq](https://www.groq.com/)
- [Google Gemini](https://console.cloud.google.com/)
- [OpenRouter](https://openrouter.ai/)

Supported self-hosted APIs:
- [KoboldCpp](https://koboldai.org/cpp) ([Local](https://koboldai.org/cpp), [Runpod](https://koboldai.org/runpodcpp), [VastAI](https://koboldai.org/vastcpp), also includes image gen support)
- [oobabooga/text-generation-webui](https://github.com/oobabooga/text-generation-webui) (local or with runpod support)
- [LMStudio](https://lmstudio.ai/)
- [TabbyAPI](https://github.com/theroyallab/tabbyAPI/)
- [Ollama](https://ollama.com/)

Generic OpenAI api implementations (tested and confirmed working):
- [DeepInfra](https://deepinfra.com/)
- [llamacpp](https://github.com/ggerganov/llama.cpp) with the `api_like_OAI.py` wrapper
- let me know if you have tested any other implementations and they failed / worked or landed somewhere in between
