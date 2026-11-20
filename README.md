# Aftermath

Python utility to freeze/dump interpreter state (the picklable globals and
locals of every frame in the traceback) when an exception occurs, so you can
inspect it after the crash. No third-party dependencies; Python 3.10+.

## Install

```
pip install .
```

## Usage

```python
from aftermath import Aftermath


@Aftermath.guard("debug")
def main(): ...
```

On an exception the stack is written to `debug/<function>_<timestamp>_aftermath`
together with a loader `<same name>.py`, and the original exception is re-raised.
Run `python -i debug/<name>_aftermath.py` (or import it) to get `data`: a list with
one dict per frame (`name`, `globals`, `locals`). See `aftermath_example.py`.

By default the loader adds the crashing process's `sys.path` so pickled classes
from your program can be imported. Pass `extend_sys_path=False` to
`guard`/`save_stack_to_file` to omit it; the loader then fails with
`ModuleNotFoundError` unless your project is on `PYTHONPATH`:
`PYTHONPATH=<project> python -i debug/<name>_aftermath.py`.

Functions, modules, builtins, tracebacks and unpicklable objects are skipped.
Mark your own objects with a class attribute `__aftermath__ = "ignore"` to
exclude them. Only `Exception` subclasses trigger a dump.

## Security

- Dumps contain program state and may include passwords, tokens and personal
  data. Files are written 0600, and a directory that Aftermath creates is 0700 (an
  existing directory keeps its permissions, so check them), but there is no redaction:
  do not enable in production without considering this, and never commit or share
  dumps (`.gitignore` excludes `debug/` and `*_aftermath*` timestamped dumps).
- Loading a dump uses `pickle`, which can run arbitrary code. Only load dumps
  you created yourself on a trusted machine.
- Use a private output directory, not a shared one such as `/tmp`.

## Migrating from 1.x

2.0.0 is Python 3 only (3.10+). Dumps are now written with the Python 3
default pickle protocol and cannot be read by Python 2. Dump/loader permissions
are restrictive, names are sanitized, and existing files are never overwritten.
`extend_sys_path` still defaults to `True`. See [CHANGELOG.md](CHANGELOG.md).

## Development

```
pip install -e ".[dev]"
ruff check .
pytest
```

## License

No license file is currently included; contact the repository owner before reuse.
