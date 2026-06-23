"""Static UI/UX bug scanner — deterministic pass for the UI skills.

Vendored and trimmed from the author's own ui-ux-doctor
(github.com/rahulcommercial/ui-ux-doctor), pure standard library, no npm/pip/network.

Philosophy match: the UI skills (internal-ui-taste, ui-design-review,
ui-accessibility-audit) should NOT eyeball mechanical bugs the way a human can't
reliably — they should run this scanner first to get exact findings (rule, line,
severity, fix), then spend their judgement on taste and context. Same split as the
investigation engine: code does the boring exact work; the model reasons.

Heuristic by design: each finding is a strong candidate for a human/agent to
confirm in context, not a sound proof. React (.jsx/.tsx/.js/.ts) + FastAPI (.py).

Usage:
    python -m engine.ui_scan <path> [<path> ...]      # scan files/dirs
    python -m engine.ui_scan --list-rules             # print the rule catalogue
"""
from __future__ import annotations

import bisect
import os
import re
import sys
from collections import namedtuple

SEVERITY_ORDER = {"critical": 3, "warning": 2, "info": 1}
Finding = namedtuple("Finding", "rule_id severity category line message snippet fix")

# --------------------------------------------------------------------------- #
# Rule catalogue
# --------------------------------------------------------------------------- #
RULES = {
    "clickable-nonbutton": {"category": "interaction", "severity": "warning",
        "summary": "onClick on a non-interactive element (div/span/li/...).",
        "fix": "Use <button> (or <a> for nav). To keep the tag: role=\"button\", tabIndex={0}, onKeyDown."},
    "icon-button-no-label": {"category": "accessibility", "severity": "warning",
        "summary": "Icon-only <button> with no accessible name.",
        "fix": "Add aria-label to the button and aria-hidden=\"true\" on the icon."},
    "missing-key": {"category": "rendering", "severity": "warning",
        "summary": ".map() renders an element without a key prop.",
        "fix": "Add a stable key={item.id} to the top-level element returned by .map()."},
    "index-as-key": {"category": "rendering", "severity": "warning",
        "summary": "Array index used as React key.",
        "fix": "Use a stable unique id; index keys corrupt inputs/animations on reorder."},
    "length-and-leak": {"category": "rendering", "severity": "warning",
        "summary": "`x.length && <JSX>` can render a literal 0.",
        "fix": "Use {x.length > 0 && <JSX>} or {!!x.length && <JSX>}."},
    "img-no-alt": {"category": "accessibility", "severity": "warning",
        "summary": "<img> without an alt attribute.",
        "fix": "alt=\"description\" for meaningful images, alt=\"\" for decorative."},
    "dangerous-html": {"category": "rendering", "severity": "warning",
        "summary": "dangerouslySetInnerHTML used.",
        "fix": "Render text/JSX directly; if HTML required, sanitize server-side first."},
    "hardcoded-localhost": {"category": "integration", "severity": "warning",
        "summary": "Hardcoded http://localhost / 127.0.0.1 URL.",
        "fix": "Read the API base from env/config (import.meta.env / os.environ)."},
    "button-no-type": {"category": "interaction", "severity": "info",
        "summary": "<button> without an explicit type.",
        "fix": "type=\"button\" (or \"submit\" when it really submits a form)."},
    "positive-tabindex": {"category": "accessibility", "severity": "info",
        "summary": "Positive tabIndex breaks natural tab order.",
        "fix": "Use tabIndex={0} or tabIndex={-1}; never > 0."},
    "autofocus": {"category": "accessibility", "severity": "info",
        "summary": "autoFocus can disorient users and screen readers.",
        "fix": "Avoid on routed pages / modals that manage focus; confirm it's intentional."},
    "console-log": {"category": "cleanliness", "severity": "info",
        "summary": "Leftover console.log / console.debug.",
        "fix": "Remove before shipping or gate behind a debug flag."},
    "useeffect-no-deps": {"category": "rendering", "severity": "info",
        "summary": "useEffect without a dependency array.",
        "fix": "Add deps; [] for mount-only. No array => runs every render (fetch loops)."},
    "inline-style-object": {"category": "performance", "severity": "info",
        "summary": "Inline style={{...}} object literal.",
        "fix": "Move static styles to a class/token; memoize dynamic ones."},
    "modal-no-a11y": {"category": "component", "severity": "warning",
        "summary": "Modal/dialog element without role=\"dialog\" + aria-modal.",
        "fix": "role=\"dialog\" aria-modal=\"true\" + aria-labelledby; trap focus, restore on close."},
    "dialog-no-label": {"category": "accessibility", "severity": "warning",
        "summary": "role=\"dialog\" without an accessible name.",
        "fix": "aria-labelledby pointing at the title, or aria-label."},
    "modal-no-escape": {"category": "component", "severity": "info",
        "summary": "Modal/dialog in this file with no Escape-to-close handler.",
        "fix": "keydown listener closing on key === 'Escape' (and backdrop click)."},
    "sidebar-no-landmark": {"category": "component", "severity": "info",
        "summary": "Sidebar/drawer that isn't a <nav>/<aside> landmark.",
        "fix": "Use <nav>/<aside> or add a matching role."},
    "nested-interactive": {"category": "accessibility", "severity": "warning",
        "summary": "Interactive element nested inside another (button in a/button).",
        "fix": "Use one interactive element, or restructure."},
    "input-no-label": {"category": "forms", "severity": "warning",
        "summary": "Form control (input/select) with no associated label.",
        "fix": "<label htmlFor> tied to id, wrap in <label>, or aria-label. Placeholder is NOT a label."},
    "textarea-no-label": {"category": "forms", "severity": "warning",
        "summary": "<textarea> with no associated label.",
        "fix": "<label htmlFor> tied to its id, wrap in <label>, or aria-label."},
    "password-no-autocomplete": {"category": "forms", "severity": "info",
        "summary": "Password input without an autocomplete hint.",
        "fix": "autocomplete=\"current-password\" (login) or \"new-password\" (signup)."},
    "form-no-onsubmit": {"category": "forms", "severity": "info",
        "summary": "<form> without an onSubmit handler.",
        "fix": "Handle onSubmit and call e.preventDefault() so Enter-submit doesn't reload."},
    "no-dark-variant": {"category": "theming", "severity": "info",
        "summary": "Light-mode color utility with no dark: variant.",
        "fix": "Pair them: bg-white dark:bg-slate-900, text-black dark:text-white."},
    "hardcoded-theme-color": {"category": "theming", "severity": "info",
        "summary": "Hardcoded black/white color in an inline style.",
        "fix": "Use theme tokens / CSS variables (tokens.css) instead of literal #fff/#000."},
    # Dashboard-specific (incident cockpit) -----------------------------------
    "status-color-only": {"category": "accessibility", "severity": "warning",
        "summary": "Empty status/severity indicator conveyed by color alone (no text/label).",
        "fix": "Pair the color with a text label or aria-label (e.g. aria-label=\"critical\"), "
               "so colorblind/screen-reader users can read the status. Reuse the tokens.css palette."},
    "list-no-pagination": {"category": "performance", "severity": "info",
        "summary": "Table/list renders mapped rows with no visible pagination/windowing.",
        "fix": "For large datasets (query results, logs) paginate via FastAPI (?offset=&limit=) "
               "or window the visible range. See the react-performance skill. (Fine for small fixed lists.)"},
    "cors-wildcard-credentials": {"category": "integration", "severity": "critical",
        "summary": "CORS allow_origins=['*'] together with allow_credentials=True.",
        "fix": "List explicit origins; browser rejects '*' + credentials so authed calls fail."},
    "cors-wildcard": {"category": "integration", "severity": "info",
        "summary": "CORS allow_origins=['*'].",
        "fix": "Restrict to the real frontend origin(s) beyond local dev."},
    "print-debug": {"category": "cleanliness", "severity": "info",
        "summary": "print() left in server code.",
        "fix": "Use logging (logger.info/debug) instead of print in handlers."},
}

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT = re.compile(r"(?<!:)//.*$", re.MULTILINE)
_PY_COMMENT = re.compile(r"(?<!:)#.*$", re.MULTILINE)


def strip_comments(text, python=False):
    if python:
        return _PY_COMMENT.sub("", text)
    text = _BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _LINE_COMMENT.sub("", text)


def _line_starts(text):
    starts = [0]
    for m in re.finditer(r"\n", text):
        starts.append(m.end())
    return starts


def _lineno(starts, index):
    return bisect.bisect_right(starts, index)


def _snippet(lines, lineno):
    return lines[lineno - 1].strip()[:160] if 1 <= lineno <= len(lines) else ""


_ATTRS = r"(?:\{(?:[^{}]|\{[^{}]*\})*\}|[^<>{])*?"
_OPEN_TAG = re.compile(r"<([A-Za-z][\w.]*)(" + _ATTRS + r")(/?)>", re.DOTALL)
_NON_INTERACTIVE = {"div", "span", "li", "p", "td", "tr", "ul", "ol", "section",
                    "article", "header", "footer", "aside", "main", "figure",
                    "label", "img", "h1", "h2", "h3", "h4", "h5", "h6"}
_LIGHT_UTILS = ("bg-white", "bg-black", "text-white", "text-black",
                "bg-gray-50", "bg-gray-100", "bg-slate-50", "bg-slate-100")
_INPUT_SKIP_TYPES = {"hidden", "submit", "button", "reset", "image", "checkbox", "radio"}
# className tokens that signal a status/severity indicator drawn as a colored swatch.
_STATUS_CLS = re.compile(
    r"\b(status|severity|sev[-_]?[123]|badge|dot|indicator|critical|warning|danger|"
    r"success|healthy|bg-(?:red|green|amber|yellow|emerald|rose)|"
    r"text-(?:red|green|amber|yellow|emerald|rose))", re.I)
# Empty span/div/i (self-closing, or open immediately closed with only whitespace).
_EMPTY_EL = re.compile(r"<(span|div|i)\b(" + _ATTRS + r")(?:/>|>\s*</\1>)", re.DOTALL)
# Signs that a list/table already limits what it renders.
_PAGINATION_HINTS = re.compile(
    r"\b(slice\(|paginat|pageSize|page\b|\blimit\b|offset|virtual|useVirtual|"
    r"windowed|loadMore|infinite|take\(|\.slice|rowsPerPage)", re.I)


def _within_label(clean, pos):
    before = clean[:pos]
    return before.rfind("<label") > before.rfind("</label>")


def _has(attrs, *names):
    return any(re.search(r"\b" + re.escape(n) + r"\s*=", attrs) for n in names)


def _classname_literal(attrs):
    m = re.search(r"""className\s*=\s*["']([^"']*)["']""", attrs)
    return m.group(1) if m else ""


def _mk(rule_id, lineno, lines):
    meta = RULES[rule_id]
    return Finding(rule_id, meta["severity"], meta["category"], lineno,
                   meta["summary"], _snippet(lines, lineno), meta["fix"])


# --------------------------------------------------------------------------- #
# React / JSX
# --------------------------------------------------------------------------- #
def scan_jsx(text):
    findings = []
    clean = strip_comments(text)
    raw = text.splitlines()
    starts = _line_starts(clean)

    for m in _OPEN_TAG.finditer(clean):
        tag, attrs = m.group(1), (m.group(2) or "")
        ln = _lineno(starts, m.start())
        if tag in _NON_INTERACTIVE and re.search(r"\bonClick\s*=", attrs):
            kb = re.search(r"\brole\s*=", attrs) and re.search(r"\bonKey(Down|Press|Up)\s*=", attrs)
            if not kb:
                findings.append(_mk("clickable-nonbutton", ln, raw))
        if tag == "img" and not re.search(r"\balt\s*=", attrs):
            findings.append(_mk("img-no-alt", ln, raw))
        if tag == "button" and not re.search(r"\btype\s*=", attrs):
            findings.append(_mk("button-no-type", ln, raw))
        if "dangerouslySetInnerHTML" in attrs:
            findings.append(_mk("dangerous-html", ln, raw))
        if re.search(r"\bstyle\s*=\s*\{\{", attrs):
            findings.append(_mk("inline-style-object", ln, raw))
        if re.search(r"\bautoFocus\b", attrs):
            findings.append(_mk("autofocus", ln, raw))
        tab = re.search(r"\btabIndex\s*=\s*\{?\s*['\"]?(\d+)", attrs)
        if tab and int(tab.group(1)) > 0:
            findings.append(_mk("positive-tabindex", ln, raw))

    btn_re = re.compile(r"<button\b(" + _ATTRS + r")>(.*?)</button>", re.DOTALL)
    for m in btn_re.finditer(clean):
        attrs, inner = m.group(1), m.group(2)
        has_label = re.search(r"\b(aria-label|aria-labelledby|title)\s*=", attrs)
        text_only = re.sub(r"\{[^{}]*\}", "", re.sub(r"<[^>]*>", "", inner)).strip()
        looks_icon = ("<svg" in inner or "Icon" in inner or re.search(r"<i\b", inner))
        if looks_icon and not has_label and not text_only:
            findings.append(_mk("icon-button-no-label", _lineno(starts, m.start()), raw))

    map_re = re.compile(
        r"\.map\(\s*(?:async\s*)?\(?[^()=]*\)?\s*=>\s*\(?\s*<([A-Za-z][\w.]*)((?:[^<>]|\{[^{}]*\})*?)/?>",
        re.DOTALL)
    for m in map_re.finditer(clean):
        if not re.search(r"\bkey\s*=", m.group(2) or ""):
            findings.append(_mk("missing-key", _lineno(starts, m.start()), raw))

    for m in re.finditer(r"\bkey\s*=\s*\{\s*([A-Za-z_]\w*)\s*\}", clean):
        if m.group(1) in {"i", "idx", "index", "_i", "n", "ix"}:
            findings.append(_mk("index-as-key", _lineno(starts, m.start()), raw))

    for m in re.finditer(r"\{\s*[\w.$]*\.length\s*&&", clean):
        findings.append(_mk("length-and-leak", _lineno(starts, m.start()), raw))

    for m in re.finditer(r"useEffect\s*\(\s*(?:async\s*)?\(\s*\)\s*=>\s*\{", clean):
        depth, i, n = 0, m.end() - 1, len(clean)
        while i < n:
            c = clean[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if not re.match(r"\s*,\s*\[", clean[i + 1:i + 40]):
            findings.append(_mk("useeffect-no-deps", _lineno(starts, m.start()), raw))

    for m in _OPEN_TAG.finditer(clean):
        tag, attrs = m.group(1), (m.group(2) or "")
        ln = _lineno(starts, m.start())
        cls_lit = _classname_literal(attrs)
        cls_modalish = re.search(r"\b(modal|dialog)\b", attrs, re.I)
        is_dialog_role = re.search(r"role\s*=\s*['\"]dialog['\"]", attrs)
        if (cls_modalish or is_dialog_role) and tag != "img":
            if not is_dialog_role and not _has(attrs, "role"):
                findings.append(_mk("modal-no-a11y", ln, raw))
            if is_dialog_role and not _has(attrs, "aria-label", "aria-labelledby"):
                findings.append(_mk("dialog-no-label", ln, raw))
        if re.search(r"\b(sidebar|drawer)\b", attrs, re.I) and tag not in ("nav", "aside") and not _has(attrs, "role"):
            findings.append(_mk("sidebar-no-landmark", ln, raw))
        if tag in ("input", "select", "textarea"):
            typ = re.search(r"type\s*=\s*['\"]?(\w+)", attrs)
            typ = typ.group(1).lower() if typ else "text"
            labelled = _has(attrs, "aria-label", "aria-labelledby", "id") or _within_label(clean, m.start())
            if tag in ("input", "select"):
                if typ not in _INPUT_SKIP_TYPES and not labelled:
                    findings.append(_mk("input-no-label", ln, raw))
                if typ == "password" and not _has(attrs, "autocomplete"):
                    findings.append(_mk("password-no-autocomplete", ln, raw))
            elif tag == "textarea" and not labelled:
                findings.append(_mk("textarea-no-label", ln, raw))
        if tag == "form" and not _has(attrs, "onSubmit"):
            findings.append(_mk("form-no-onsubmit", ln, raw))
        if cls_lit and any(u in cls_lit for u in _LIGHT_UTILS) and "dark:" not in cls_lit:
            findings.append(_mk("no-dark-variant", ln, raw))
        if re.search(r"(?:color|background|backgroundColor)\s*:\s*['\"]?#?"
                     r"(?:fff(?:fff)?|000(?:000)?|white|black)\b", attrs, re.I):
            findings.append(_mk("hardcoded-theme-color", ln, raw))

    for pat in (r"<a\b" + _ATTRS + r">(?:(?!</a>).)*?<(?:button|a)\b",
                r"<button\b" + _ATTRS + r">(?:(?!</button>).)*?<(?:button|a)\b"):
        for m in re.finditer(pat, clean, re.DOTALL):
            findings.append(_mk("nested-interactive", _lineno(starts, m.start()), raw))

    if re.search(r"\b(modal|dialog)\b", clean, re.I) or "role=\"dialog\"" in clean:
        if not re.search(r"['\"]Esc(?:ape)?['\"]|keyCode\s*===?\s*27|which\s*===?\s*27", clean):
            mm = re.search(r"\b(modal|dialog)\b", clean, re.I)
            if mm:
                findings.append(_mk("modal-no-escape", _lineno(starts, mm.start()), raw))

    # --- status conveyed by color alone (empty colored badge/dot) ----------- #
    for m in _EMPTY_EL.finditer(clean):
        attrs = m.group(2) or ""
        cls = _classname_literal(attrs)
        if cls and _STATUS_CLS.search(cls) and not _has(attrs, "aria-label", "aria-labelledby", "title") \
                and not re.search(r"role\s*=\s*['\"]img['\"]", attrs):
            findings.append(_mk("status-color-only", _lineno(starts, m.start()), raw))

    # --- table/list with no pagination or windowing (file-level, once) ------ #
    has_table = "<table" in clean.lower()
    has_row_map = re.search(r"\.map\([^)]*\)?\s*=>\s*\(?\s*<(?:tr\b|li\b|[A-Z]\w*Row\b)", clean)
    if (has_table or has_row_map) and not _PAGINATION_HINTS.search(clean):
        anchor = re.search(r"<table", clean, re.I) or has_row_map
        findings.append(_mk("list-no-pagination", _lineno(starts, anchor.start()), raw))

    for n, line in enumerate(clean.splitlines(), 1):
        if re.search(r"\bconsole\.(log|debug)\s*\(", line):
            findings.append(_mk("console-log", n, raw))
        if re.search(r"https?://(localhost|127\.0\.0\.1)(:\d+)?", line):
            findings.append(_mk("hardcoded-localhost", n, raw))
    return findings


# --------------------------------------------------------------------------- #
# FastAPI / Python
# --------------------------------------------------------------------------- #
def scan_python(text):
    findings = []
    clean = strip_comments(text, python=True)
    raw = text.splitlines()
    wildcard = re.search(r"allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]", clean)
    credentials = re.search(r"allow_credentials\s*=\s*True", clean)
    if wildcard:
        ln = _lineno(_line_starts(clean), wildcard.start())
        findings.append(_mk("cors-wildcard-credentials" if credentials else "cors-wildcard", ln, raw))
    for n, line in enumerate(clean.splitlines(), 1):
        if re.search(r"https?://(localhost|127\.0\.0\.1)(:\d+)?", line):
            findings.append(_mk("hardcoded-localhost", n, raw))
        if re.match(r"\s*print\s*\(", line):
            findings.append(_mk("print-debug", n, raw))
    return findings


JSX_EXT = {".jsx", ".tsx", ".js", ".ts", ".mjs"}
PY_EXT = {".py"}
_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", "venv", ".venv"}


def scan_text(text, ext):
    if ext in JSX_EXT:
        return scan_jsx(text)
    if ext in PY_EXT:
        return scan_python(text)
    return []


def iter_files(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        elif os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
                for f in files:
                    if os.path.splitext(f)[1] in JSX_EXT | PY_EXT:
                        yield os.path.join(root, f)


def scan_paths(paths):
    """Return {filepath: [Finding, ...]} for all scannable files under paths."""
    out = {}
    for fp in iter_files(paths):
        try:
            with open(fp, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        fs = scan_text(text, os.path.splitext(fp)[1])
        if fs:
            out[fp] = sorted(fs, key=lambda f: (-SEVERITY_ORDER[f.severity], f.line))
    return out


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _list_rules():
    for rid, m in sorted(RULES.items(), key=lambda kv: -SEVERITY_ORDER[kv[1]["severity"]]):
        print(f"  {m['severity']:8} {m['category']:13} {rid:26} {m['summary']}")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--list-rules":
        _list_rules()
        return 0
    results = scan_paths(argv)
    if not results:
        print("No UI/UX issues found (static heuristics). Apply judgement for taste/context.")
        return 0
    total = sum(len(v) for v in results.values())
    counts = {"critical": 0, "warning": 0, "info": 0}
    for fs in results.values():
        for f in fs:
            counts[f.severity] += 1
    for fp, fs in sorted(results.items()):
        print(f"\n{fp}")
        for f in fs:
            print(f"  L{f.line:<4} {f.severity:8} {f.rule_id:24} {f.message}")
            print(f"        ↳ {f.fix}")
    print(f"\n{total} findings  "
          f"({counts['critical']} critical, {counts['warning']} warning, {counts['info']} info)")
    print("Heuristic — confirm each in context before fixing. Pair with the UI skills' judgement passes.")
    return 1 if counts["critical"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
