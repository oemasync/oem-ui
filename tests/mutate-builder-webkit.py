"""Mutation sweep for tests/measure-builder-webkit.py.

Each mutant: copy the worktree (minus node_modules/dist/.git), apply ONE
string replacement that must match exactly once, build, serve on its own
port, run the probe. A mutant is KILLED only if the probe exits non-zero
AND the expected check is among the failures - a mutant killed by an
unrelated check is a harness fault, not a kill.
"""
import concurrent.futures as cf
import os
import shutil
import subprocess
import sys
import time

SRC = "/reiki/projects/oem-ui-wt-cards"
WORK = "/root/.hermes/cache/scratch/oemui-mut"
PROBE = os.path.join(SRC, "tests/measure-builder-webkit.py")

ONLY = set(sys.argv[1:])
MUTANTS = [
    ("up-not-disabled", "src/js/cli-mono.js",
     "if (btn.hasAttribute('data-cm-repeater-up')) btn.disabled = i === 0;",
     "if (btn.hasAttribute('data-cm-repeater-up')) btn.disabled = false;",
     "first up / last down disabled"),
    ("scope-leaks-to-parent", "src/js/cli-mono.js",
     "\t\t\treturn el.closest('[data-cm-repeater]') === rep;\n",
     "\t\t\treturn true;\n",
     "outer add clones the outer template"),
    ("focus-falls-to-body", "src/js/cli-mono.js",
     "\t\t\tcmFocus(target);\n\t\t\treturn;\n",
     "\t\t\treturn;\n",
     "focus after remove is not <body>"),
    ("no-clamp-at-max", "src/js/cli-mono.js",
     "\t\t\tnext = v + dir * step;\n\t\t\tif (min !== null && next < min) next = min;\n\t\t\tif (max !== null && next > max) next = max;\n",
     "\t\t\tnext = v + dir * step;\n\t\t\tif (min !== null && next < min) next = min;\n",
     "a step from an off-grid value clamps to max"),
    ("ring-under-frame", "src/styles/components.css",
     ".cm-artwork__pick:has(> .cm-artwork__radio:checked) > .cm-artwork__item::before {\n\tbox-shadow: inset 0 0 0 3px var(--ink);\n}",
     ".cm-artwork__pick:has(> .cm-artwork__radio:checked) > .cm-artwork__item {\n\tbox-shadow: inset 0 0 0 3px var(--ink);\n}",
     "chosen tile paints a ring"),
    ("input-loses-specificity", "src/styles/components.css",
     ".cm-number > input.cm-number__input:not([type='checkbox']):not([type='radio']):not([type='range']):not(.cm-inline__input):not(.cm-search__input) {\n\twidth: calc(4ch",
     ".cm-number__input {\n\twidth: calc(4ch",
     "stepper input has no border of its own"),
]


def run(i, m):
    name, rel, old, new, expect = m
    d = os.path.join(WORK, name)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(SRC, d, ignore=shutil.ignore_patterns("node_modules", "dist", ".git", ".astro"))
    os.symlink("/reiki/projects/oem-ui/node_modules", os.path.join(d, "node_modules"))
    f = os.path.join(d, rel)
    text = open(f).read()
    n = text.count(old)
    if n != 1:
        return name, "PATTERN", f"matched {n} times", ""
    open(f, "w").write(text.replace(old, new))
    b = subprocess.run(["npx", "astro", "build"], cwd=d, capture_output=True, text=True, timeout=600)
    if b.returncode != 0:
        return name, "BUILD-FAIL", b.stderr[-400:], ""
    # A fixed port collided with an unrelated service already on :4400, so the
    # probe measured someone else's app. Ask the kernel for a free port, then
    # prove the server answering is ours (it serves this mutant's own dist).
    import socket, urllib.request
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        port = so.getsockname()[1]
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
                            "--directory", os.path.join(d, "dist")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        mine = open(os.path.join(d, "dist", "index.html"), "rb").read()
        for _ in range(40):
            try:
                if urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=5).read() == mine:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            return name, "SERVE-FAIL", f"port {port} never served this mutant's dist", ""
        r = subprocess.run(["/usr/bin/python3", PROBE, f"http://127.0.0.1:{port}/"],
                           capture_output=True, text=True, timeout=1500)
    finally:
        srv.kill()
    fails = [l for l in r.stdout.splitlines() if l.startswith("FAIL")]
    hit = any(expect in l for l in fails)
    verdict = "KILLED" if (r.returncode != 0 and hit) else ("OFF-TARGET" if r.returncode != 0 else "SURVIVED")
    return name, verdict, f"{len(fails)} fail(s); expected '{expect}' hit={hit}", "\n".join(fails[:6]) + ("\n" + r.stderr[-600:] if not fails and r.returncode != 0 else "")


os.makedirs(WORK, exist_ok=True)
with cf.ThreadPoolExecutor(max_workers=3) as ex:
    futs = [ex.submit(run, i, m) for i, m in enumerate(MUTANTS) if not ONLY or m[0] in ONLY]
    results = [f.result() for f in futs]
bad = 0
for name, verdict, detail, fails in results:
    print(f"{verdict:10} {name}: {detail}")
    if fails:
        print("           " + fails.replace("\n", "\n           "))
    bad += verdict != "KILLED"
print(f"\n{len(results) - bad}/{len(results)} killed")
shutil.rmtree(WORK, ignore_errors=True)
sys.exit(1 if bad else 0)
