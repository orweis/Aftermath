import os
import stat
import subprocess
import sys
import time

import pytest

import aftermath
from aftermath import Aftermath


def _crash():
    secret_local = {"a": 1}  # noqa: F841
    raise ValueError("boom")


def _tb():
    try:
        _crash()
    except ValueError:
        return sys.exc_info()[2]


def test_traceback_iterator_walks_chain():
    names = [t.tb_frame.f_code.co_name for t in Aftermath.traceback_iterator(_tb())]
    assert names == ["_tb", "_crash"]
    assert list(Aftermath.traceback_iterator(None)) == []


@pytest.mark.parametrize("obj", [1, "s", [1, {"a": None}], (1, 2), Aftermath])
def test_can_pickle_true(obj):
    assert Aftermath.can_pickle(obj)


@pytest.mark.parametrize("obj", [sys, len, Ellipsis, lambda: 1, _crash, _tb(), (i for i in ())])
def test_can_pickle_false(obj):
    assert not Aftermath.can_pickle(obj)


def test_can_pickle_respects_ignore_marker_and_bad_getattr():
    class Marked:
        __aftermath__ = "ignore"

    class Explosive:
        def __getattr__(self, item):
            raise RuntimeError("no")

    assert not Aftermath.can_pickle(Marked())
    assert not Aftermath.can_pickle(Explosive())


def test_extract_stack_one_entry_per_frame():
    stack = Aftermath.extract_stack(_tb())
    assert [e["name"] for e in stack] == ["_tb", "_crash"]
    assert stack[-1]["locals"]["secret_local"] == {"a": 1}
    assert "sys" not in stack[-1]["globals"]  # modules skipped


def test_save_creates_loadable_private_dump(tmp_path):
    d = tmp_path / "dumps"
    Aftermath.save_stack_to_file(_tb(), str(d))
    assert stat.S_IMODE(d.stat().st_mode) == 0o700
    files = sorted(os.listdir(d))
    assert len(files) == 2 and files[1] == files[0] + ".py"
    for f in files:
        assert stat.S_IMODE((d / f).stat().st_mode) == 0o600
    code = (
        "import runpy,sys;g=runpy.run_path(sys.argv[1]);"
        "print(g['data'][-1]['locals']['secret_local'])"
    )
    # No PYTHONPATH: the loader must work as documented (python debug/<name>.py).
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    out = subprocess.run(
        [sys.executable, "-c", code, str(d / files[1])],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "{'a': 1}"


def test_example_end_to_end(tmp_path):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = {**os.environ, "PYTHONPATH": repo}
    run = subprocess.run(
        [sys.executable, os.path.join(repo, "aftermath_example.py")],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 1 and "boom" in run.stderr
    loader = next(f for f in (tmp_path / "debug").iterdir() if f.suffix == ".py")
    env.pop("PYTHONPATH")
    code = "import runpy,sys;g=runpy.run_path(sys.argv[1]);print(g['data'][-1]['name'])"
    out = subprocess.run(
        [sys.executable, "-c", code, str(loader)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.strip() == "sub_test"


def test_planted_loader_name_is_skipped_and_dump_not_orphaned(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "strftime", lambda fmt: "_T")
    (tmp_path / "n_T_aftermath.py").write_text("planted")
    Aftermath.save_stack_to_file(_tb(), str(tmp_path), name="n")
    assert (tmp_path / "n_T_aftermath.py").read_text() == "planted"
    assert sorted(os.listdir(tmp_path)) == [
        "n_T_aftermath.py",
        "n_T_aftermath_1",
        "n_T_aftermath_1.py",
    ]


def test_long_name_is_truncated(tmp_path):
    Aftermath.save_stack_to_file(_tb(), str(tmp_path), name="x" * 500)
    assert len(os.listdir(tmp_path)) == 2


def test_same_second_collisions_do_not_overwrite(tmp_path):
    for _ in range(3):
        Aftermath.save_stack_to_file(_tb(), str(tmp_path), name="same")
    assert len([f for f in os.listdir(tmp_path) if not f.endswith(".py")]) == 3


@pytest.mark.parametrize("name", ["../evil", "/etc/passwd", "a/b", "<module>", "..", ""])
def test_name_cannot_escape_dir(tmp_path, name):
    d = tmp_path / "out"
    Aftermath.save_stack_to_file(_tb(), str(d), name=name)
    assert os.listdir(tmp_path) == ["out"]
    assert len(os.listdir(d)) == 2


def test_symlink_not_followed(tmp_path):
    target = tmp_path / "victim"
    target.write_text("keep")
    d = tmp_path / "d"
    d.mkdir()
    for off in range(-1, 3):
        ts = time.strftime("_%Y_%m_%d_%H_%M_%S", time.localtime(time.time() + off))
        os.symlink(target, d / ("n" + ts + "_aftermath"))
    Aftermath.save_stack_to_file(_tb(), str(d), name="n")
    assert target.read_text() == "keep"


def test_loader_sys_path_default_opt_out_and_safely_quoted(tmp_path, monkeypatch):
    nasty = ["/x'; import os #", 'q"\n\\']
    monkeypatch.setattr(sys, "path", list(nasty))
    Aftermath.create_quick_loader(str(tmp_path / "a"), extend_sys_path=False)
    Aftermath.create_quick_loader(str(tmp_path / "b"))  # default: extend (1.x behaviour)
    opt_out_src = (tmp_path / "a.py").read_text()
    opt_in_src = (tmp_path / "b.py").read_text()
    assert "sys.path.extend([])" in opt_out_src
    compile(opt_in_src, "loader", "exec")
    # Evaluate only the extend call: paths must round-trip as plain strings.
    start = opt_in_src.index("sys.path.extend(") + len("sys.path.extend(")
    literal = opt_in_src[start : opt_in_src.index(")\n", start)]
    assert eval(literal, {"__builtins__": {}}) == nasty  # noqa: S307


def test_guard_reraises_dumps_and_preserves_metadata(tmp_path):
    @Aftermath.guard(str(tmp_path))
    def fn(x):
        """doc"""
        raise KeyError(x)

    assert fn.__name__ == "fn" and fn.__doc__ == "doc"
    assert fn.__aftermath__ == "ignore"
    with pytest.raises(KeyError):
        fn("k")
    assert len(os.listdir(tmp_path)) == 2


def test_guard_passes_through_return_value_and_base_exceptions(tmp_path):
    @Aftermath.guard(str(tmp_path))
    def ok(a, b=1):
        return a + b

    @Aftermath.guard(str(tmp_path))
    def interrupted():
        raise KeyboardInterrupt

    assert ok(1, b=2) == 3
    with pytest.raises(KeyboardInterrupt):
        interrupted()
    assert os.listdir(tmp_path) == []


def test_dump_failure_does_not_mask_original_exception(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x")

    @Aftermath.guard(str(blocker / "sub"))  # cannot mkdir under a file
    def fn():
        raise ValueError("original")

    with pytest.raises(ValueError, match="original"):
        fn()
    assert "failed to write dump" in capsys.readouterr().err


def test_version():
    assert aftermath.__version__ == "2.0.0"
