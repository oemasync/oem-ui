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

def noop(what, ret=None):
    """For file MUTATIONS: do nothing and return a plausible value, so a
    harness that sets up a scratch copy at import time still reaches its
    table. Nothing reaches the disk - the write is simply discarded."""
    def _f(*a, **kw):
        return ret
    return _f

def noop_open(what):
    """A writable handle nobody keeps: the harness can write, the bytes go
    to a string in memory and are dropped."""
    def _f(*a, **kw):
        import io
        return io.StringIO()
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

    # WHICH FILES ARE MID-MUTATION RIGHT NOW. A running sweep leaves its
    # mutant in the working tree for as long as it takes to build and test,
    # so a census reading that window would call the file's REAL pattern
    # stale. Dirty targets are reported as skipped instead - the reading is
    # honest about what it could see. This runs BEFORE the sandbox goes up
    # (the sandbox blocks the subprocess git needs).
    dirty = set()
    try:
        out = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                             text=True, timeout=30).stdout
        for line in out.splitlines():
            p = line[3:].strip()
            if p:
                dirty.add(os.path.abspath(p))
                dirty.add(p)
    except Exception:
        pass

    real_open = builtins.open

    def ro_open(file, mode="r", *a, **kw):
        if any(c in str(mode) for c in "wax+"):
            # Discarded, not refused: see noop_open.
            import io
            return io.StringIO()
        return real_open(file, mode, *a, **kw)

    builtins.open = ro_open
    for module, names in (
        (subprocess, ("run", "Popen", "call", "check_call", "check_output")),
        (shutil, ("rmtree", "move", "copy", "copy2", "copyfile", "make_archive")),
        (os, ("remove", "unlink", "rename", "replace", "system", "rmdir",
              "removedirs", "makedirs", "mkdir", "chmod", "chown", "truncate",
              "chdir")),
        (pathlib.Path, ("write_text", "write_bytes", "unlink", "rename",
                        "replace", "mkdir", "touch", "chmod")),
    ):
        for name in names:
            try:
                if module is subprocess:
                    # NEVER no-op these: a harness that starts a subprocess at
                    # import time IS the sweep. Raising is the only safe answer.
                    setattr(module, name, deny(module.__name__ + "." + name))
                else:
                    setattr(module, name, noop(module.__name__ + "." + name, "" if name in ("copy", "copy2", "copyfile", "move") else None))
            except Exception:
                pass
    try:
        pathlib.Path.open = noop_open("Path.open")
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
    def as_fields(e):
        # Two table shapes in the fleet: positional tuples
        # (name, path, old, new, who...) and dicts with the same names
        # (mutate-sync-prefix.py built its nine that way via a helper).
        if isinstance(e, dict):
            return (e.get("name"), e.get("path") or e.get("file"),
                    e.get("old"), e.get("new"))
        if isinstance(e, (list, tuple)) and len(e) >= 3:
            return (e[0], e[1], e[2], e[3] if len(e) > 3 else None)
        return None

    for _raw in table:
        fields = as_fields(_raw)
        if fields is None:
            continue
        label, cand, old, _new_field = fields
        entry = tuple(v for v in (label, cand, old, _new_field) if v is not None)
        if not isinstance(cand, str) or not isinstance(old, str) or not os.path.isfile(cand):
            rows.append([str(label), "unclassified"])
            continue
        if not os.path.abspath(cand).startswith(repo + os.sep):
            rows.append([str(label), "WRONG-TREE " + cand])
            continue
        if cand in dirty or os.path.abspath(cand) in dirty:
            # Mid-mutation: the pattern may be absent because a sweep has its
            # mutant in the file this second. Not a finding - say so.
            rows.append([str(label), "under-mutation (skipped)"])
            continue
        try:
            body = real_open(cand, encoding="utf8").read()
        except OSError as e:
            rows.append([str(label), "unreadable %s" % e])
            continue
        n = body.count(old)
        if n == 0:
            rows.append([str(label), "NO-OP"])
            detail: dict = {"label": str(label), "why": "NO-OP", "path": cand, "old": old}
            if len(entry) > 3 and isinstance(entry[3], str):
                detail["new"] = entry[3]
            # The resolved entry, so a repairer knows the whole tuple even
            # when the table composes it from module constants.
            detail["entry"] = [v if isinstance(v, str) else {"py": repr(v)} for v in entry]
            bad_detail.append(detail)
        elif n > 1:
            # The harnesses replace the FIRST match and (usually) assert
            # exactly one: an ambiguous pattern silently mutates the wrong
            # site. Measured: mutate-sidebar.py aborted a whole sweep on a
            # pattern that had grown a second occurrence.
            if any(str(v) == "all" for v in entry):
                # a `count='all'` entry asserts a claim satisfied by ANY
                # occurrence: several matches are the point, not a smell -
                # but ONE match means the sweep changes almost nothing, which
                # the harness's own preflight calls malformed too.
                if n < 2:
                    rows.append([str(label), f"TOO-NARROW ({n} match, count-all wants 2+)"])
                    bad_detail.append({"label": str(label), "why": f"TOO-NARROW ({n} match, count-all wants 2+)",
                                       "path": cand, "old": old,
                                       "entry": [v if isinstance(v, str) else {"py": repr(v)} for v in entry]})
                else:
                    rows.append([str(label), f"ok ({n} matches, count-all sweep)"])
            else:
                rows.append([str(label), f"AMBIGUOUS ({n} matches)"])
            if any(str(v) == "all" for v in entry):
                continue
            detail: dict = {"label": str(label), "why": f"AMBIGUOUS ({n} matches)",
                            "path": cand, "old": old}
            if len(entry) > 3 and isinstance(entry[3], str):
                detail["new"] = entry[3]
            detail["entry"] = [v if isinstance(v, str) else {"py": repr(v)} for v in entry]
            bad_detail.append(detail)
        elif any(str(v) == "all" for v in entry):
            # count-all with exactly ONE match: the sweep asserts a claim any
            # occurrence satisfies, so a single site means it barely sweeps -
            # the harness's own preflight calls this malformed ("needs 2+").
            rows.append([str(label), f"TOO-NARROW ({n} match, count-all wants 2+)"])
            bad_detail.append({"label": str(label), "why": f"TOO-NARROW ({n} match, count-all wants 2+)",
                               "path": cand, "old": old,
                               "entry": [v if isinstance(v, str) else {"py": repr(v)} for v in entry]})
        else:
            # THE HEALTHY CASE NEEDS A ROW TOO. Without it a clean script read
            # as "0 patterns, all match" - a census line that means nothing,
            # measured on three scripts whose patterns were all fine.
            rows.append([str(label), f"ok ({n} match)"])
    if not rows:
        # An empty read is a broken instrument, not a clean fleet. Say WHAT
        # was read, or the census reports "0 patterns, all match" and means
        # nothing. Measured: three scripts reported 0 rows for a while.
        sample = table[0] if isinstance(table, list) and table else None
        out0 = {"skip": "table read but no rows (%d entries, first=%s:%s)" % (
            len(table) if isinstance(table, list) else -1,
            type(sample).__name__, len(sample) if isinstance(sample, (list, tuple)) else "?"),
            "entry_types": [(type(e).__name__, len(e) if isinstance(e, (list, tuple)) else -1)
                            for e in (table or [])[:6]]}
        print(json.dumps(out0))
        return 0
    out = {"rows": rows, "blocked_at": blocked_at}
    if "--dump" in sys.argv:
        out["bad"] = bad_detail
    print(json.dumps(out))
    return 0

if __name__ == "__main__":
    sys.exit(main())
