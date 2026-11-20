"""Freeze interpreter state when an exception occurs, and review it post crash.

SECURITY: dumps contain the (picklable) globals and locals of every frame in
the traceback, which may include credentials and personal data. Loading a dump
unpickles it, which can execute arbitrary code: only load dumps you created.
"""

import functools
import inspect
import os
import pickle
import re
import sys
import time

__version__ = "2.0.0"

__all__ = ["Aftermath", "__version__"]

_UNSAFE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_.-]")

QUICK_LOADER = '''\
# Aftermath quick loader.
# WARNING: this unpickles the dump next to this file. Unpickling can execute
# arbitrary code. Only run this if you created the dump on a machine you trust.
import os
import pickle
import sys

sys.path.extend(%(extra_paths)s)

with open(os.path.splitext(__file__)[0], "rb") as src:
    data = pickle.load(src)
'''


def _open_private(path):
    """Create `path` exclusively (no overwrite, no symlink follow), mode 0600."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    return os.fdopen(fd, "wb")


def _sanitize_name(name):
    """Reduce `name` to a safe single path component."""
    name = _UNSAFE_NAME_CHARS.sub("_", str(name)).lstrip(".")
    return name or "aftermath"


class Aftermath:
    """Namespace of static helpers; use :meth:`guard` as a decorator."""

    @staticmethod
    def traceback_iterator(tb):
        """Yield each traceback object in the chain starting at `tb`."""
        while tb is not None:
            yield tb
            tb = tb.tb_next

    @staticmethod
    def can_pickle(obj):
        """Return True if `obj` should and can be included in a dump."""
        if inspect.isbuiltin(obj) or inspect.ismodule(obj) or inspect.istraceback(obj):
            return False
        if not inspect.isclass(obj) and isinstance(obj, type(Ellipsis)):
            return False
        # Functions are skipped for slimness and decorator issues.
        if inspect.isfunction(obj):
            return False
        try:
            if getattr(obj, "__aftermath__", None) == "ignore":
                return False
            pickle.dumps(obj)
        except Exception:
            return False
        return True

    @staticmethod
    def extract_stack(tb):
        """Return one dict (name, globals, locals) per frame, picklable values only."""
        stack = []
        for trace in Aftermath.traceback_iterator(tb):
            frame = trace.tb_frame
            stack.append(
                {
                    "name": frame.f_code.co_name,
                    "globals": {
                        k: v for k, v in list(frame.f_globals.items()) if Aftermath.can_pickle(v)
                    },
                    "locals": {
                        k: v for k, v in list(frame.f_locals.items()) if Aftermath.can_pickle(v)
                    },
                }
            )
        return stack

    @staticmethod
    def create_quick_loader(dump_file_path, extend_sys_path=False):
        """Write `<dump>.py`, a script that loads the dump into `data`.

        The crashing process's sys.path is only embedded when `extend_sys_path`
        is true, since it would let the loader import from those directories.
        """
        paths = [str(p) for p in sys.path] if extend_sys_path else []
        source = QUICK_LOADER % {"extra_paths": repr(paths)}
        with _open_private(dump_file_path + ".py") as q:
            q.write(source.encode("utf-8"))

    @staticmethod
    def save_stack_to_file(tb, dir_path, name=None, extend_sys_path=False):
        """Dump the stack of `tb` under `dir_path` (created 0700, files 0600)."""
        stack = Aftermath.extract_stack(tb)
        if name is None:
            name = stack[-1]["name"] if stack else "aftermath"
        name = _sanitize_name(name)
        os.makedirs(dir_path, mode=0o700, exist_ok=True)
        base = os.path.join(dir_path, name + time.strftime("_%Y_%m_%d_%H_%M_%S") + "_aftermath")
        path, counter = base, 0
        while True:
            try:
                dest = _open_private(path)
                break
            except FileExistsError:
                counter += 1
                path = f"{base}_{counter}"
        with dest:
            pickle.dump(stack, dest)
        Aftermath.create_quick_loader(path, extend_sys_path=extend_sys_path)
        return stack

    @staticmethod
    def guard(dir_path, extend_sys_path=False):
        """Decorator: on Exception, dump the stack to `dir_path` and re-raise.

        A failure to write the dump never replaces the original exception; it
        is reported as a warning on stderr. Only `Exception` subclasses are
        handled (not KeyboardInterrupt/SystemExit).
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    tb = sys.exc_info()[2]
                    try:
                        Aftermath.save_stack_to_file(tb, dir_path, extend_sys_path=extend_sys_path)
                    except Exception as dump_error:
                        print(
                            f"aftermath: failed to write dump: {dump_error!r}",
                            file=sys.stderr,
                        )
                    raise

            wrapper.__aftermath__ = "ignore"
            return wrapper

        return decorator
