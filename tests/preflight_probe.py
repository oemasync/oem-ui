#!/root/.venvs/mau/bin/python
"""The sandboxed probe behind tests/preflight-mutations.py.

Usage: tests/preflight_probe.py <harness.py> [cwd]

Prints one JSON line:
  {"rows": [[label, problem], ...], "blocked_at": "…"}   or   {"skip": "…"}

Why a sandbox: the census must NEVER run a mutation harness by importing it.
A harness without a `if __name__ == '__main__':` guard sweeps the tree at
import time, and that is not hypothetical - two timed-out census runs once
started unguarded sweeps in parallel with a queued sweep, interleaved their
writes into `src/styles/components.css`, and the leftover mutants cost a
whole queue plus a re-run of the sweep whose verdicts they invalidated.

So the harness is executed here with every vector blocked: writes through
`open`, `pathlib.Path`, `os` and `shutil`, and every way to spawn a
subprocess. Its table is defined before any of that is reached; the moment
the module tries to act, the probe stops and reports where.

An entry whose second element is a real file inside the repo and whose third
is a string can be judged; anything else is "unclassified", never "stale".
"""
import ast
import builtins
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

class Blocked(Exception):
    pass

def deny(what):
    def _f(*a, **kw):
        raise Blocked(what)
    return _f

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(json.dumps({"skip": "no target"}))
        return 1
    path = args[0]
    if len(args) > 1:
        os.chdir(args[1])
    repo = os.getcwd()

    real_open = builtins.open

    def ro_open(file, mode="r", *a, **kw):
        if any(c in str(mode) for c in "wax+"):
            raise Blocked("open(write)")
        return real_open(file, mode, *a, **kw)

    builtins.open = ro_open
    for module, names in (
        (subprocess, ("run", "Popen", "call", "check_call", "check_output")),
        (shutil, ("rmtree", "move", "copy", "copy2", "copyfile", "make_archive")),
        (os, ("remove", "unlink", "rename", "replace", "system", "rmdir",
              "removedirs", "makedirs", "mkdir", "chmod", "chown", "truncate",
              "chdir")),
        (pathlib.Path, ("write_text", "write_bytes", "unlink", "rename",
                        "replace", "mkdir", "touch", "chmod", "open")),
    ):
        for name in names:
            try:
                setattr(module, name, deny(module.__name__ + "." + name))
            except Exception:
                pass
    time.sleep = lambda *a, **kw: None

    ns = {"__name__": "__census_probe__", "__file__": path, "__builtins__": builtins,
          "__spec__": None, "__package__": None}
    blocked_at = None
    try:
        exec(compile(real_open(path, encoding="utf8").read(), path, "exec"), ns)
    except BaseException as e:      # a blocked action, or the script's own exit
        blocked_at = "%s: %s" % (type(e).__name__, e)

    table = None
    for attr in ("MUTATIONS", "MUTANTS", "MUTANTS_LIST", "PATTERNS"):
        t = ns.get(attr)
        if isinstance(t, list) and t:
            table = t
            break
    if table is None:
        print(json.dumps({"skip": "no table reached (%s)" % (blocked_at or "none found")}))
        return 0

    rows = []
    bad_detail = []
    for entry in table:
        if not isinstance(entry, (list, tuple)) or len(entry) < 3:
            continue
        label, cand, old = entry[0], entry[1], entry[2]
        if not isinstance(cand, str) or not isinstance(old, str) or not os.path.isfile(cand):
            rows.append([str(label), "unclassified"])
            continue
        if not os.path.abspath(cand).startswith(repo + os.sep):
            rows.append([str(label), "WRONG-TREE " + cand])
            continue
        try:
            body = real_open(cand, encoding="utf8").read()
        except OSError as e:
            rows.append([str(label), "unreadable %s" % e])
            continue
        if old not in body:
            rows.append([str(label), "NO-OP"])
            detail: dict = {"label": str(label), "why": "NO-OP", "path": cand, "old": old}
            if len(entry) > 3 and isinstance(entry[3], str):
                detail["new"] = entry[3]
            # The resolved entry, so a repairer knows the whole tuple even
            # when the table composes it from module constants.
            detail["entry"] = [v if isinstance(v, str) else "«%r»" % (v,) for v in entry]
            bad_detail.append(detail)
    out = {"rows": rows, "blocked_at": blocked_at}
    if "--dump" in sys.argv:
        out["bad"] = bad_detail
    print(json.dumps(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
