# DevCommand

> A production-grade developer command center for your terminal.

[![CI](https://github.com/chinmayk/DevCommand/actions/workflows/ci.yml/badge.svg)](https://github.com/chinmayk/DevCommand/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What is DevCommand?

DevCommand is a cross-platform TUI (Terminal User Interface) that consolidates developer tools into a single dashboard — system metrics, Docker containers, Git status, server health, and TODO tracking — all refreshing in real time.

## Features

- **System monitoring** — CPU, memory, disk, network, top processes
- **Docker dashboard** — container status, images, ports
- **Git overview** — branch, staged/modified files, recent commits
- **Server health** — endpoint monitoring with response times
- **TODO tracker** — persistent task list with priorities
- **Plugin system** — extend with custom panels and services
- **5 built-in themes** — Dark, Light, Nord, Dracula, Solarized
- **Central scheduler** — async polling with per-service timeouts and exponential backoff
- **Structured logging** — JSON file logs, configurable verbosity
- **Performance profiling** — nanosecond precision, zero overhead when off
- **Cross-platform** — macOS, Linux, Windows (pathlib throughout)

## Installation

```bash
# Clone and install in development mode
git clone https://github.com/chinmayk/DevCommand.git
cd DevCommand
pip install -e ".[dev]"
```

## Usage

```bash
# Launch the TUI
devcmd

# With options
devcmd --debug                  # verbose logging
devcmd --refresh 0.5            # faster refresh cycle
devcmd --workspace /path/to/project
devcmd --no-plugins             # skip plugin loading
devcmd --profile                # enable performance profiling
devcmd --version                # print version and exit

# Make targets
make test                       # run test suite
make lint                       # ruff check
make test-cov                   # tests with coverage report
make run-debug                  # launch with debug logging
```

## Configuration

Create `.devcommand.yml` in your project root:

```yaml
debug_mode: false
workspace_path: /path/to/workspace

ui:
  refresh_interval: 2.0
  theme: nord
  enabled_panels:
    - system
    - docker
    - git

scheduler:
  tick_interval: 3.0
  default_timeout: 15.0

docker:
  enabled: true

git:
  enabled: true

plugins:
  enabled: true
  disabled:
    - broken_plugin
```

Falls back to `~/.devcommand/config.toml` → built-in defaults. Never crashes on missing config.

## Architecture

```
devcommand/
├── __version__.py      # single version source
├── app.py              # Textual TUI + lifecycle
├── cli.py              # argparse CLI
├── core/
│   ├── platform.py     # cross-platform detection
│   ├── scheduler.py    # async service scheduler
│   ├── app_state.py    # reactive state container
│   └── event_bus.py    # pub/sub event system
├── config/
│   ├── settings.py     # Pydantic config models
│   └── themes.py       # colour palettes
├── services/           # data providers (async)
├── panels/             # Rich-based TUI panels
├── plugins/            # dynamic extension system
├── models/             # Pydantic data models
├── utils/
│   ├── logging.py      # structured JSON logging
│   └── profiling.py    # performance instrumentation
└── widgets/            # reusable TUI components
```

## Roadmap

- [ ] Interactive TODO CRUD
- [ ] Log viewer panel
- [ ] Plugin marketplace
- [ ] Remote machine monitoring
- [ ] PyPI release
- [ ] Homebrew formula

## License

[MIT](LICENSE)
