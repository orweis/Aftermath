# Changelog

## 2.0.0

### Breaking
- Python 3 only (3.9+). The module no longer imports on Python 2.
- Dump files and the quick loader are created exclusively (never overwriting or
  following symlinks) with mode 0600, and the dump directory with 0700. Names
  are sanitized to a single safe path component; same-second collisions get a
  numeric suffix.
- The generated quick loader no longer extends `sys.path` with the crashing
  process's path by default; pass `extend_sys_path=True` to `guard` /
  `save_stack_to_file` to restore the old behaviour.

### Changed
- A failure while writing a dump no longer masks the original exception; it is
  reported on stderr and the original is re-raised.
- `guard` preserves the wrapped function's metadata (`functools.wraps`).
- `can_pickle` catches `Exception` only (not KeyboardInterrupt/SystemExit).

### Added
- Packaging (`pyproject.toml`), `__version__`, pytest suite, CI, `.gitignore`,
  security notes in the README.

## 1.0.0 (2015)
- Initial Python 2 release.
