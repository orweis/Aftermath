# Changelog

## 2.0.0

### Breaking
- Python 3 only (3.10+). The module no longer imports on Python 2.
- Dump files and the quick loader are created exclusively (never overwriting or
  following symlinks) with mode 0600, and the dump directory with 0700. Names
  are sanitized to a single safe path component; same-second collisions get a
  numeric suffix.
- Dumps use the Python 3 default pickle protocol and cannot be read by
  Python 2.

### Changed
- A failure while writing a dump no longer masks the original exception; it is
  reported on stderr and the original is re-raised.
- `guard` preserves the wrapped function's metadata (`functools.wraps`).
- `can_pickle` catches `Exception` only (not KeyboardInterrupt/SystemExit).

- `guard` / `save_stack_to_file` / `create_quick_loader` accept
  `extend_sys_path` (default `True`, matching earlier behaviour); pass `False`
  to omit the crashing process's `sys.path` from the loader.
- The dump and its loader are reserved together, so a pre-existing `<dump>.py`
  is skipped rather than leaving an orphan dump. Names are capped at 100 chars.

### Added
- Packaging (`pyproject.toml`), `__version__`, pytest suite, CI, `.gitignore`,
  security notes in the README.

## Unversioned (2015)
- Initial Python 2 code, marked work in progress. No release was tagged.
