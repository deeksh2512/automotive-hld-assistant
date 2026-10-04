"""Visual design system: palette, stylesheet, and presentational components.

Everything here is self-contained. No web fonts or remote assets are fetched,
because the assistant must look and behave identically on an air-gapped machine.
"""

from __future__ import annotations

from typing import Iterable, Literal

import streamlit as st

Tone = Literal["neutral", "accent", "success", "warning", "danger", "info"]

INK = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
SURFACE = "#F8FAFC"
ACCENT = "#1D4ED8"
SUCCESS = "#15803D"
WARNING = "#B45309"
DANGER = "#B91C1C"

STYLESHEET = """
<style>
:root {
    --ink: #0F172A;
    --ink-soft: #334155;
    --muted: #64748B;
    --faint: #94A3B8;
    --border: #E2E8F0;
    --border-strong: #CBD5E1;
    --surface: #F8FAFC;
    --surface-2: #F1F5F9;
    --accent: #1D4ED8;
    --accent-soft: #EFF4FF;
    --success: #15803D;
    --success-soft: #ECFDF3;
    --warning: #B45309;
    --warning-soft: #FFF8EB;
    --danger: #B91C1C;
    --danger-soft: #FEF2F2;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI",
            Roboto, "Helvetica Neue", Arial, sans-serif;
    --mono: ui-monospace, "Cascadia Mono", "Segoe UI Mono", Consolas, monospace;
    --radius: 10px;
    --shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.06);
}

html, body, [class*="st-"], button, input, textarea, select {
    font-family: var(--font);
}

/* --- Chrome ----------------------------------------------------------- */

[data-testid="stDecoration"],
[data-testid="stAppDeployButton"],
#MainMenu,
footer { display: none !important; }

[data-testid="stHeader"] { background: transparent; height: 0; }

.block-container {
    padding-top: 2.25rem;
    padding-bottom: 4rem;
    max-width: 1360px;
}

/* --- Typography ------------------------------------------------------- */

h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.015em; }
h1 { font-size: 1.65rem !important; font-weight: 650 !important; }
h2 { font-size: 1.2rem !important; font-weight: 620 !important; }
h3 { font-size: 1.02rem !important; font-weight: 600 !important; }
/* Scoped to main-area prose: a blanket rule on p/span also repaints button
   labels, which Streamlit renders as markdown. */
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li { color: var(--ink-soft); }
[data-testid^="stBaseButton-"] [data-testid="stMarkdownContainer"] p { color: inherit !important; }
small, .caption { color: var(--muted); }
code { font-family: var(--mono); font-size: 0.85em; }

/* --- Sidebar ---------------------------------------------------------- */

[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }

/* The built-in page list renders above everything; a hand-built nav below the
   brand reads better, so hide it. */
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarHeader"] { padding-bottom: 0; }

[data-testid="stSidebarUserContent"] .stPageLink a {
    border-radius: 7px;
    padding: 0.34rem 0.6rem;
    margin-bottom: 1px;
}
[data-testid="stSidebarUserContent"] .stPageLink a:hover { background: var(--surface-2); }
[data-testid="stSidebarUserContent"] .stPageLink a span {
    font-size: 0.88rem;
    color: var(--ink-soft);
}
[data-testid="stSidebarUserContent"] .stPageLink a[aria-current="page"] {
    background: var(--accent-soft);
}
[data-testid="stSidebarUserContent"] .stPageLink a[aria-current="page"] span {
    color: var(--accent);
    font-weight: 620;
}

.brand {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0 0.25rem 0.9rem 0.25rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.9rem;
}
.brand-mark { flex: 0 0 34px; line-height: 0; }
.brand-text { display: flex; flex-direction: column; gap: 1px; }
.brand-name {
    font-size: 0.93rem;
    font-weight: 650;
    color: var(--ink);
    letter-spacing: -0.01em;
}
.brand-sub {
    font-size: 0.72rem;
    color: var(--faint);
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

.side-label {
    font-size: 0.7rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--faint);
    margin: 0.35rem 0 0.3rem 0.1rem;
}

/* --- Page header ------------------------------------------------------ */

.page-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1.5rem;
    padding-bottom: 1rem;
    margin-bottom: 1.35rem;
    border-bottom: 1px solid var(--border);
}
.page-kicker {
    font-size: 0.7rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--accent);
    margin-bottom: 0.3rem;
}
.page-title {
    font-size: 1.6rem;
    font-weight: 650;
    color: var(--ink);
    letter-spacing: -0.02em;
    line-height: 1.2;
    margin: 0;
}
.page-sub {
    font-size: 0.9rem;
    color: var(--muted);
    margin: 0.4rem 0 0 0;
    max-width: 68ch;
    line-height: 1.5;
}
.page-meta { display: flex; gap: 0.4rem; flex-wrap: wrap; justify-content: flex-end; }

/* --- Section heading -------------------------------------------------- */

.section { margin: 0.4rem 0 0.9rem 0; }
.section-title {
    font-size: 1rem;
    font-weight: 620;
    color: var(--ink);
    letter-spacing: -0.01em;
}
.section-sub { font-size: 0.85rem; color: var(--muted); margin-top: 0.15rem; }

/* --- Chips and badges ------------------------------------------------- */

.chip {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.16rem 0.55rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 560;
    line-height: 1.45;
    white-space: nowrap;
    border: 1px solid transparent;
}
.chip-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.chip.neutral { background: var(--surface-2); color: var(--ink-soft); border-color: var(--border); }
.chip.accent  { background: var(--accent-soft); color: var(--accent); border-color: #DBE4FF; }
.chip.success { background: var(--success-soft); color: var(--success); border-color: #CFF3DD; }
.chip.warning { background: var(--warning-soft); color: var(--warning); border-color: #FBE7C2; }
.chip.danger  { background: var(--danger-soft);  color: var(--danger);  border-color: #FAD4D4; }
.chip.info    { background: var(--accent-soft); color: var(--accent); border-color: #DBE4FF; }

.ref {
    font-family: var(--mono);
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--ink);
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 0.08rem 0.4rem;
}

/* --- Stat cards ------------------------------------------------------- */

.stats { display: grid; gap: 0.75rem; margin-bottom: 0.25rem; }
.stat {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.85rem 1rem;
    box-shadow: var(--shadow);
}
.stat-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--faint);
}
.stat-value {
    font-size: 1.55rem;
    font-weight: 650;
    color: var(--ink);
    line-height: 1.25;
    margin-top: 0.2rem;
    letter-spacing: -0.02em;
}
.stat-hint { font-size: 0.76rem; color: var(--muted); margin-top: 0.1rem; }

/* --- Cards ------------------------------------------------------------ */

.card {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.1rem;
    box-shadow: var(--shadow);
    margin-bottom: 0.75rem;
}
.card-title { font-size: 0.95rem; font-weight: 620; color: var(--ink); }
.card-body { font-size: 0.86rem; color: var(--muted); margin-top: 0.3rem; line-height: 1.55; }

/* Streamlit containers tagged with an inline marker become cards too. */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > .card-marker) {
    background: #FFFFFF;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow);
}
.card-marker { display: none; }

/* --- Callout ---------------------------------------------------------- */

/* Block, not flex: in a narrow sidebar a flex row turns each text node into its
   own column. */
.callout {
    display: block;
    border: 1px solid var(--border);
    border-left: 3px solid var(--muted);
    border-radius: 8px;
    padding: 0.7rem 0.9rem;
    background: var(--surface);
    font-size: 0.85rem;
    line-height: 1.55;
    color: var(--ink-soft);
    margin-bottom: 0.8rem;
}
.callout.accent  { border-left-color: var(--accent);  background: var(--accent-soft); }
.callout.success { border-left-color: var(--success); background: var(--success-soft); }
.callout.warning { border-left-color: var(--warning); background: var(--warning-soft); }
.callout.danger  { border-left-color: var(--danger);  background: var(--danger-soft); }
.callout-title { font-weight: 620; color: var(--ink); margin-right: 0.25rem; }
.callout code {
    background: rgba(15, 23, 42, 0.06);
    border-radius: 4px;
    padding: 0.05rem 0.3rem;
    word-break: break-all;
}

/* --- Empty state ------------------------------------------------------ */

.empty {
    border: 1px dashed var(--border-strong);
    border-radius: var(--radius);
    background: var(--surface);
    padding: 2.1rem 1.5rem;
    text-align: center;
}
.empty-title { font-size: 0.95rem; font-weight: 620; color: var(--ink-soft); }
.empty-body {
    font-size: 0.85rem;
    color: var(--muted);
    margin-top: 0.35rem;
    line-height: 1.55;
}

/* --- Evidence --------------------------------------------------------- */

.evidence {
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    background: #FFFFFF;
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.5rem;
}
.evidence-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.35rem;
    flex-wrap: wrap;
}
.evidence-marker {
    font-family: var(--mono);
    font-size: 0.75rem;
    font-weight: 650;
    color: var(--accent);
    background: var(--accent-soft);
    border-radius: 4px;
    padding: 0.05rem 0.35rem;
}
.evidence-source { font-size: 0.82rem; font-weight: 560; color: var(--ink); }
.evidence-score { font-size: 0.74rem; color: var(--faint); margin-left: auto; }
.evidence-text {
    font-size: 0.82rem;
    color: var(--ink-soft);
    line-height: 1.6;
    white-space: pre-wrap;
    max-height: 13rem;
    overflow-y: auto;
}

/* --- Answer ----------------------------------------------------------- */

.answer {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.1rem 1.25rem;
    box-shadow: var(--shadow);
}
.answer-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.7rem;
    margin-bottom: 0.8rem;
    border-bottom: 1px solid var(--border);
}
.answer-label {
    font-size: 0.7rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--faint);
}
.answer-meta { margin-left: auto; display: flex; gap: 0.4rem; align-items: center; }
.answer-body { font-size: 0.92rem; color: var(--ink); line-height: 1.65; }
.answer-body p:last-child { margin-bottom: 0; }

/* --- Tabs ------------------------------------------------------------- */

.stTabs [data-baseweb="tab-list"] {
    gap: 0.15rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.1rem;
}
.stTabs [data-baseweb="tab"] {
    height: 2.5rem;
    padding: 0 0.85rem;
    background: transparent;
    color: var(--muted);
    font-size: 0.88rem;
    font-weight: 540;
    border-radius: 7px 7px 0 0;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--surface-2); color: var(--ink-soft); }
.stTabs [aria-selected="true"] { color: var(--ink) !important; font-weight: 620; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--accent); height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* --- Controls --------------------------------------------------------- */

/* Streamlit exposes the button variant through the test id, not a kind attribute. */
[data-testid^="stBaseButton-"] {
    border-radius: 7px !important;
    font-weight: 560 !important;
    font-size: 0.86rem !important;
    padding: 0.38rem 0.9rem;
    transition: background 120ms ease, border-color 120ms ease;
}
[data-testid^="stBaseButton-secondary"] {
    background: #FFFFFF;
    border: 1px solid var(--border-strong);
    color: var(--ink-soft);
}
[data-testid^="stBaseButton-secondary"]:hover {
    background: var(--surface-2);
    border-color: var(--muted);
    color: var(--ink);
}
[data-testid^="stBaseButton-primary"] {
    background: var(--accent);
    border: 1px solid var(--accent);
    color: #FFFFFF !important;
}
[data-testid^="stBaseButton-primary"] p { color: #FFFFFF !important; }
[data-testid^="stBaseButton-primary"]:hover {
    background: #1A43B8;
    border-color: #1A43B8;
    color: #FFFFFF !important;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: var(--accent-soft) !important;
    border: 1px solid #DBE4FF;
    border-radius: 6px;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] span { color: var(--accent) !important; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg { fill: var(--accent); }

[data-testid="stMain"] .stPageLink a {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--border-strong);
    border-radius: 7px;
    padding: 0.38rem 0.9rem;
    background: #FFFFFF;
}
[data-testid="stMain"] .stPageLink a:hover { background: var(--surface-2); }
[data-testid="stMain"] .stPageLink a span {
    color: var(--accent) !important;
    font-weight: 560;
    font-size: 0.86rem;
}

[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
    border-radius: 7px !important;
    border-color: var(--border-strong) !important;
}
.stTextInput label, .stTextArea label, .stSelectbox label,
.stMultiSelect label, .stSlider label, .stFileUploader label, .stCheckbox label {
    font-size: 0.82rem !important;
    font-weight: 560 !important;
    color: var(--ink-soft) !important;
}

[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 8px;
    background: #FFFFFF;
    overflow: hidden;
}
[data-testid="stExpander"] summary { font-size: 0.86rem; font-weight: 560; }
[data-testid="stExpander"] summary:hover { background: var(--surface); }

[data-testid="stFileUploaderDropzone"] {
    background: var(--surface);
    border: 1px dashed var(--border-strong);
    border-radius: 8px;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
}

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 0.8rem 1rem;
    box-shadow: var(--shadow);
}
[data-testid="stMetricLabel"] p {
    font-size: 0.72rem !important;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--faint) !important;
}
[data-testid="stMetricValue"] { font-size: 1.5rem; font-weight: 650; color: var(--ink); }

hr { border-color: var(--border); margin: 1.4rem 0; }
</style>
"""

BRAND_MARK = """
<svg width="34" height="34" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="34" height="34" rx="8" fill="#0F172A"/>
  <path d="M11 11.5 L11 22.5 M23 11.5 L23 22.5 M11 17 L23 17"
        stroke="#1D4ED8" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="11" cy="11.5" r="2.6" fill="#FFFFFF"/>
  <circle cx="23" cy="11.5" r="2.6" fill="#60A5FA"/>
  <circle cx="11" cy="22.5" r="2.6" fill="#60A5FA"/>
  <circle cx="23" cy="22.5" r="2.6" fill="#FFFFFF"/>
</svg>
"""


def inject() -> None:
    st.markdown(STYLESHEET, unsafe_allow_html=True)


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def chip(label: str, tone: Tone = "neutral", dot: bool = False) -> str:
    marker = '<span class="chip-dot"></span>' if dot else ""
    return f'<span class="chip {tone}">{marker}{label}</span>'


def ref(value: str) -> str:
    return f'<span class="ref">{value}</span>'


def brand(name: str, subtitle: str) -> None:
    _html(
        f'<div class="brand"><div class="brand-mark">{BRAND_MARK}</div>'
        f'<div class="brand-text"><div class="brand-name">{name}</div>'
        f'<div class="brand-sub">{subtitle}</div></div></div>'
    )


def sidebar_label(text: str) -> None:
    _html(f'<div class="side-label">{text}</div>')


def page_header(
    title: str,
    subtitle: str = "",
    kicker: str = "",
    chips: Iterable[str] = (),
) -> None:
    kicker_html = f'<div class="page-kicker">{kicker}</div>' if kicker else ""
    sub_html = f'<p class="page-sub">{subtitle}</p>' if subtitle else ""
    chips_html = "".join(chips)
    _html(
        f'<div class="page-head"><div class="page-head-main">{kicker_html}'
        f'<h1 class="page-title">{title}</h1>{sub_html}</div>'
        f'<div class="page-meta">{chips_html}</div></div>'
    )


def section(title: str, subtitle: str = "") -> None:
    sub = f'<div class="section-sub">{subtitle}</div>' if subtitle else ""
    _html(f'<div class="section"><div class="section-title">{title}</div>{sub}</div>')


def stats(items: list[tuple[str, object, str]]) -> None:
    """Render a responsive row of statistic cards: (label, value, hint)."""
    cards = "".join(
        f'<div class="stat"><div class="stat-label">{label}</div>'
        f'<div class="stat-value">{value}</div>'
        f'<div class="stat-hint">{hint}</div></div>'
        for label, value, hint in items
    )
    columns = f"repeat({len(items)}, minmax(0, 1fr))"
    _html(f'<div class="stats" style="grid-template-columns:{columns}">{cards}</div>')


def callout(body: str, title: str = "", tone: Tone = "neutral") -> None:
    heading = f'<span class="callout-title">{title}</span> ' if title else ""
    _html(f'<div class="callout {tone}">{heading}{body}</div>')


def empty_state(title: str, body: str = "") -> None:
    body_html = f'<div class="empty-body">{body}</div>' if body else ""
    _html(f'<div class="empty"><div class="empty-title">{title}</div>{body_html}</div>')


def card(title: str, body: str = "") -> None:
    body_html = f'<div class="card-body">{body}</div>' if body else ""
    _html(f'<div class="card"><div class="card-title">{title}</div>{body_html}</div>')


def card_marker() -> None:
    """Tag the enclosing st.container(border=True) so the stylesheet restyles it."""
    _html('<span class="card-marker"></span>')
