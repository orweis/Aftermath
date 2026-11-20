# Aftermath

Python utility to freeze/dump interpreter state (the picklable globals and
locals of every frame in the traceback) when an exception occurs, so you can
inspect it after the crash. No third-party dependencies; Python 3.9+.

## Install

```
pip install .
```

## Usage

```python
from aftermath import Aftermath

@Aftermath.guard("debug")
def main():
    ...
```

On an exception the stack is written to `debug/<function>_<timestamp>_aftermath`
together with a loader `<same name>.py`, and the original exception is re-raised.
Run `python -i debug/<name>_aftermath.py` (or import it) to get `data`: a list with
one dict per frame (`name`, `globals`, `locals`). See `aftermath_example.py`.

Functions, modules, builtins, tracebacks and unpicklable objects are skipped.
Mark your own objects with a class attribute `__aftermath__ = "ignore"` to
exclude them. Only `Exception` subclasses trigger a dump.

## Security

- Dumps contain program state and may include passwords, tokens and personal
  data. Files are written 0600 in a 0700 directory, but there is no redaction:
  do not enable in production without considering this, and never commit or share
  dumps (`.gitignore` excludes `debug/` and `*_aftermath*` timestamped dumps).
- Loading a dump uses `pickle`, which can run arbitrary code. Only load dumps
  you created yourself on a trusted machine.
- Use a private output directory, not a shared one such as `/tmp`.

## Migrating from 1.x

2.0.0 is Python 3 only. Dump/loader permissions are now restrictive, names are
sanitized, and the loader no longer extends `sys.path` unless you pass
`extend_sys_path=True`. See [CHANGELOG.md](CHANGELOG.md).

## Development

```
pip install -e ".[dev]"
ruff check .
pytest
```

## License

No license file is currently included; contact the repository owner before reuse.
