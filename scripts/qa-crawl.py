#!/usr/bin/env python3
"""Reusable QA crawler for the oem-ui showcase.

Usage:
  python3 scripts/qa-crawl.py [BASE_URL] [--out PATH] [--engines chromium,webkit]
  [--viewports 1440x900,768x1024,390x844] [--themes dark,light]
  [--screenshots-dir DIR] [--screenshots-only]

Defaults: base URL https://ui.mrx.sh, all engines/viewports/themes.
Writes a JSON report to --out (default /tmp/oem-ui-qa-report.json).
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

PAGES = [
    ("/", "home"),
    ("/f/foundation/", "foundation"),
    ("/f/surfaces/", "surfaces"),
    ("/f/tables/", "tables"),
    ("/f/panels/", "panels"),
    ("/f/content/", "content"),
    ("/f/prose/", "prose"),
    ("/f/layout/", "layout"),
    ("/f/composed/", "composed"),
    ("/f/reference/", "reference"),
    ("/testing/", "testing"),
]

URL_CHECK_CACHE = {}


def check_url(url):
    if url in URL_CHECK_CACHE:
        return URL_CHECK_CACHE[url]
    status = None
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "oem-ui-qa/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            status = r.status
    except urllib.error.HTTPError as he:
        status = he.code
    except Exception:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "oem-ui-qa/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                status = r.status
        except urllib.error.HTTPError as he:
            status = he.code
        except Exception as e:
            status = "ERR:" + str(e)[:80]
    URL_CHECK_CACHE[url] = status
    return status


JS_DETECT = r"""
(mobile) => {
  function sel(el){
    if(!el) return '';
    if(el.id) return '#'+el.id;
    const tag = el.tagName.toLowerCase();
    const cls = (typeof el.className === 'string') ? el.className.trim().split(/\s+/).filter(Boolean).slice(0,2) : [];
    if(cls.length) return tag+'.'+cls.join('.');
    return tag;
  }
  function sectionOf(el){ const s = el && el.closest ? el.closest('section[id]') : null; return s ? s.id : null; }
  const all = Array.from(document.querySelectorAll('*'));
  const pageOverflowPx = document.documentElement.scrollWidth - window.innerWidth;
  const voSet = new Set();
  const viewportOffenders = [];
  for(const el of all){
    if(el === document.documentElement || el === document.body) continue;
    const r = el.getBoundingClientRect();
    if(r.width===0 && r.height===0) continue;
    const st = getComputedStyle(el);
    if(st.display==='none' || st.visibility==='hidden') continue;
    if(r.right > window.innerWidth + 2 || r.left < -2){
      const key = sel(el)+'|'+sectionOf(el);
      if(voSet.has(key)) continue;
      voSet.add(key);
      viewportOffenders.push({selector:sel(el), section:sectionOf(el), right:Math.round(r.right), left:Math.round(r.left)});
    }
  }
  const tcSet = new Set();
  const textClipped = [];
  for(const el of all){
    if(el.scrollWidth > el.clientWidth + 1){
      const st = getComputedStyle(el);
      if(/auto|scroll/.test(st.overflowX)) continue;
      if(st.textOverflow === 'ellipsis') continue;
      if(!el.textContent || !el.textContent.trim()) continue;
      const key = sel(el)+'|'+sectionOf(el);
      if(tcSet.has(key)) continue;
      tcSet.add(key);
      textClipped.push({selector:sel(el), section:sectionOf(el), scrollWidth:el.scrollWidth, clientWidth:el.clientWidth});
    }
  }
  const ovSet = new Set();
  const overlaps = [];
  const sections = Array.from(document.querySelectorAll('section[id]'));
  for(const sec of sections){
    const elems = [sec].concat(Array.from(sec.querySelectorAll('*')));
    for(const parent of elems){
      const kids = Array.from(parent.children);
      if(kids.length < 2) continue;
      const rects = kids.map(k=>({el:k, r:k.getBoundingClientRect()}));
      for(let i=0;i<rects.length;i++){
        for(let j=i+1;j<rects.length;j++){
          const a=rects[i].r, b=rects[j].r;
          const iw = Math.min(a.right,b.right)-Math.max(a.left,b.left);
          const ih = Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
          if(iw > 4 && ih > 4){
            const key = sec.id+'|'+sel(parent);
            if(ovSet.has(key)) continue;
            ovSet.add(key);
            overlaps.push({section:sec.id, parent:sel(parent), a:sel(rects[i].el), b:sel(rects[j].el)});
            if(overlaps.length > 100) break;
          }
        }
        if(overlaps.length > 100) break;
      }
      if(overlaps.length > 100) break;
    }
    if(overlaps.length > 100) break;
  }
  const targets = [];
  const clickables = document.querySelectorAll('button, a, input, select, textarea, summary, [role="button"], [tabindex]:not([tabindex="-1"]), [data-cm-copy], [data-cm-theme-toggle]');
  for(const el of clickables){
    const r = el.getBoundingClientRect();
    if(r.width===0 || r.height===0) continue;
    const st = getComputedStyle(el);
    if(st.display==='none' || st.visibility==='hidden') continue;
    const minDim = Math.min(r.width, r.height);
    const issue = (minDim < 24) || (mobile && minDim < 44);
    if(issue){
      targets.push({selector:sel(el), section:sectionOf(el), width:Math.round(r.width), height:Math.round(r.height), text:(el.textContent||'').trim().slice(0,40), mobileThreshold: mobile});
    }
  }
  const media = [];
  for(const el of document.querySelectorAll('img, video, audio, svg')){
    const r = el.getBoundingClientRect();
    let broken=false, missingDims=false;
    if(el.tagName==='IMG'){
      if(!el.complete || el.naturalWidth===0) broken=true;
      if(!el.hasAttribute('width') || !el.hasAttribute('height')) missingDims=true;
    } else if(el.tagName==='VIDEO' || el.tagName==='AUDIO'){
      if(el.error) broken=true;
      if(el.tagName==='VIDEO' && (!el.hasAttribute('width') || !el.hasAttribute('height'))) missingDims=true;
      if(r.width===0 || r.height===0) missingDims=true;
    } else if(el.tagName==='SVG'){
      if(!el.hasAttribute('width') && !el.hasAttribute('height') && (r.width===0||r.height===0)) missingDims=true;
    }
    if(broken || missingDims){
      media.push({selector:sel(el), section:sectionOf(el), broken, missingDims, width:Math.round(r.width), height:Math.round(r.height)});
    }
  }
  const brokenAnchors = [];
  const anchorLinks = Array.from(document.querySelectorAll('a[href^="#"]'));
  for(const a of anchorLinks){
    const href = a.getAttribute('href');
    if(!href || href==='#') continue;
    let target=null;
    try { target = document.querySelector(href); } catch(e){}
    if(!target && href.length>1){ try{ target = document.getElementById(href.slice(1)); }catch(e){} }
    if(!target){ brokenAnchors.push({href, selector:sel(a), section:sectionOf(a)}); }
  }
  const coveredAnchors = [];
  const header = document.querySelector('header') || document.querySelector('[data-cm-header]') || document.querySelector('.cm-header');
  const prevScroll = window.scrollY;
  for(const a of anchorLinks){
    const href = a.getAttribute('href');
    if(!href || href==='#') continue;
    let target=null;
    try { target = document.querySelector(href); } catch(e){}
    if(!target && href.length>1){ try{ target = document.getElementById(href.slice(1)); }catch(e){} }
    if(!target) continue;
    try { target.scrollIntoView({block:'start', behavior:'instant'}); } catch(e){}
    const tr = target.getBoundingClientRect();
    const hr = header ? header.getBoundingClientRect() : null;
    if(hr && tr.top < hr.bottom + 4){
      coveredAnchors.push({href, target:sel(target), section:sectionOf(target), targetTop:Math.round(tr.top), headerBottom:Math.round(hr.bottom)});
    }
  }
  try { window.scrollTo(0, prevScroll); } catch(e){}
  function parseColor(str){
    const m = String(str).match(/rgba?\(([^)]+)\)/);
    if(!m) return null;
    const parts = m[1].split(',').map(x=>x.trim());
    const r=parseFloat(parts[0]), g=parseFloat(parts[1]), b=parseFloat(parts[2]);
    const a = parts[3]!==undefined ? parseFloat(parts[3]) : 1;
    return {r,g,b,a};
  }
  function lum(c){
    const chan = [c.r,c.g,c.b].map(v=>{
      v/=255;
      return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4);
    });
    return 0.2126*chan[0]+0.7152*chan[1]+0.0722*chan[2];
  }
  function contrastRatio(fg,bg){
    const L1=lum(fg), L2=lum(bg);
    const light=Math.max(L1,L2), dark=Math.min(L1,L2);
    return (light+0.05)/(dark+0.05);
  }
  function effectiveBg(el){
    let cur = el;
    while(cur && cur !== document.documentElement){
      const st = getComputedStyle(cur);
      const c = parseColor(st.backgroundColor);
      if(c && c.a >= 0.95) return c;
      cur = cur.parentElement;
    }
    const root = parseColor(getComputedStyle(document.body).backgroundColor) || parseColor(getComputedStyle(document.documentElement).backgroundColor);
    return root || {r:10,g:10,b:10,a:1};
  }
  const contrastIssues = [];
  const cSet = new Set();
  for(const el of all){
    const hasDirectText = Array.from(el.childNodes).some(n=>n.nodeType===3 && n.textContent.trim().length>0);
    if(!hasDirectText) continue;
    const st = getComputedStyle(el);
    if(st.display==='none' || st.visibility==='hidden') continue;
    const fg = parseColor(st.color);
    if(!fg) continue;
    const bg = effectiveBg(el);
    if(!bg) continue;
    const ratio = contrastRatio(fg,bg);
    const fontSize = parseFloat(st.fontSize);
    const bold = parseInt(st.fontWeight) >= 700;
    const large = fontSize >= 18 || (fontSize >= 14 && bold);
    const threshold = large ? 3.0 : 4.5;
    if(ratio < threshold - 0.02){
      const key = sel(el)+'|'+st.color+'|'+bg.r+','+bg.g+','+bg.b;
      if(cSet.has(key)) continue;
      cSet.add(key);
      contrastIssues.push({selector:sel(el), section:sectionOf(el), fg:st.color, bg:`rgb(${bg.r},${bg.g},${bg.b})`, ratio:Math.round(ratio*100)/100, threshold, fontSize:Math.round(fontSize)});
      if(contrastIssues.length > 120) break;
    }
  }
  function tops(){
    const out = {};
    for(const sec of sections){ const r=sec.getBoundingClientRect(); out[sec.id]=Math.round(r.top + window.scrollY); }
    return out;
  }
  const tops1 = tops();
  return {
    pageOverflow: pageOverflowPx > 1,
    pageOverflowPx,
    viewportOffenders,
    textClipped,
    overlaps,
    smallTargets: targets,
    media,
    brokenAnchors,
    coveredAnchors,
    contrastIssues,
    tops1,
  };
}
"""


def run_one(page, url, engine, viewport, theme, shot_dir, screenshots_only):
    result = {
        "page": url,
        "engine": engine,
        "viewport": viewport,
        "theme": theme,
        "console": [],
        "pageerrors": [],
        "failedRequests": [],
        "httpErrors": [],
        "findings": {},
    }
    console_msgs = []
    page_errors = []
    failed_reqs = []
    http_errors = []

    def on_console(msg):
        if msg.type in ("error", "warning"):
            console_msgs.append({"type": msg.type, "text": msg.text[:500]})

    def on_pageerror(err):
        page_errors.append(str(err)[:500])

    def on_requestfailed(req):
        failed_reqs.append({"url": req.url, "failure": str(req.failure)})

    def on_response(resp):
        try:
            if resp.status >= 400:
                http_errors.append({"url": resp.url, "status": resp.status})
        except Exception:
            pass

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("requestfailed", on_requestfailed)
    page.on("response", on_response)

    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=5000)
    except Exception:
        pass
    page.wait_for_timeout(1200)
    try:
        page.evaluate("(t)=>{ if(window.cliMono && window.cliMono.applyTheme) window.cliMono.applyTheme(t); }", theme)
    except Exception:
        pass
    page.wait_for_timeout(800)

    if shot_dir:
        os.makedirs(shot_dir, exist_ok=True)
        slug = url.rstrip("/").split("/")[-1] or "home"
        fname = f"{slug}-{viewport}-{theme}-{engine}.png"
        fpath = os.path.join(shot_dir, fname)
        try:
            page.screenshot(path=fpath, full_page=True)
            result["screenshot"] = fpath
        except Exception as e:
            result["screenshot_error"] = str(e)

    if screenshots_only:
        result["console"] = console_msgs
        result["pageerrors"] = page_errors
        result["failedRequests"] = failed_reqs
        result["httpErrors"] = http_errors
        return result

    w, h = [int(x) for x in viewport.split("x")]
    mobile = w <= 768
    try:
        data = page.evaluate(JS_DETECT, mobile)
    except Exception as e:
        data = {"error": str(e)}

    tops2 = {}
    try:
        page.wait_for_timeout(1500)
        tops2 = page.evaluate("() => { const out={}; document.querySelectorAll('section[id]').forEach(s=>{const r=s.getBoundingClientRect(); out[s.id]=Math.round(r.top+window.scrollY);}); return out; }")
    except Exception:
        tops2 = {}
    shifted = []
    if isinstance(data, dict) and "tops1" in data:
        for sid, t1 in data["tops1"].items():
            t2 = tops2.get(sid)
            if t2 is not None and abs(t2 - t1) > 2:
                shifted.append({"section": sid, "from": t1, "to": t2, "delta": t2 - t1})
    if isinstance(data, dict):
        data["shiftedSections"] = shifted

    try:
        cls = page.evaluate("""() => {
          try {
            let s=0;
            const entries = performance.getEntriesByType('layout-shift') || [];
            for (const e of entries) { if(!e.hadRecentInput) s += e.value; }
            return s;
          } catch(e){ return null; }
        }""")
        if isinstance(data, dict):
            data["cls"] = cls
    except Exception:
        pass

    try:
        links = page.evaluate("""() => Array.from(document.querySelectorAll('a[href]')).map(a=>a.getAttribute('href'))""")
    except Exception:
        links = []
    broken_links = []
    seen = set()
    for href in links or []:
        if not href:
            continue
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:") or href.startswith("javascript:"):
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        seen.add(full)
        if not full.startswith("http"):
            continue
        parsed = urllib.parse.urlparse(full)
        base_host = urllib.parse.urlparse(url).netloc
        if parsed.netloc != base_host and 'github.com' not in parsed.netloc:
            continue
        status = check_url(full)
        if (isinstance(status, int) and status >= 400) or (isinstance(status, str) and status.startswith("ERR")):
            broken_links.append({"href": href, "resolved": full, "status": status})
    if isinstance(data, dict):
        data["brokenLinks"] = broken_links

    result["console"] = console_msgs
    result["pageerrors"] = page_errors
    result["failedRequests"] = failed_reqs
    result["httpErrors"] = http_errors
    result["findings"] = data if isinstance(data, dict) else {"error": str(data)}
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default="https://ui.mrx.sh")
    ap.add_argument("--out", default="/tmp/oem-ui-qa-report.json")
    ap.add_argument("--engines", default="chromium,webkit")
    ap.add_argument("--viewports", default="1440x900,768x1024,390x844")
    ap.add_argument("--themes", default="dark,light")
    ap.add_argument("--screenshots-dir", default=None)
    ap.add_argument("--screenshots-only", action="store_true")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    viewports = [v.strip() for v in args.viewports.split(",") if v.strip()]
    themes = [t.strip() for t in args.themes.split(",") if t.strip()]

    all_results = []
    with sync_playwright() as p:
        for engine in engines:
            browser = getattr(p, engine).launch(headless=True)
            for viewport in viewports:
                w, h = [int(x) for x in viewport.split("x")]
                for theme in themes:
                    context = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
                    context.add_init_script(f"try{{localStorage.setItem('cm-theme','{theme}');}}catch(e){{}}")
                    page = context.new_page()
                    for path, fam in PAGES:
                        url = base + path
                        print(f"[{engine} {viewport} {theme}] {url}", file=sys.stderr, flush=True)
                        try:
                            r = run_one(page, url, engine, viewport, theme, args.screenshots_dir, args.screenshots_only)
                            r["family"] = fam
                            all_results.append(r)
                        except Exception as e:
                            all_results.append({"page": url, "family": fam, "engine": engine, "viewport": viewport, "theme": theme, "error": str(e)})
                    page.close()
                    context.close()
            browser.close()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({"base": base, "results": all_results}, f, indent=2)
    print(f"Wrote {len(all_results)} runs to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
