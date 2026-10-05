"""Visual design system: palette, stylesheet, and presentational components.

A dark navy instrument panel rather than a document: flat surfaces, hairline
rules instead of cards, and tabular data as the primary element.

Self-contained by design. No web fonts, icon packs, or remote assets are
fetched, because the assistant must render identically on an air-gapped machine.
"""

from __future__ import annotations

import html
from typing import Any, Iterable, Literal, Mapping, Sequence

import streamlit as st

Tone = Literal["neutral", "accent", "success", "warning", "danger", "info"]

BG = "#0B1322"
PANEL = "#101A2B"
ACCENT = "#3B82F6"

STYLESHEET = """
<style>
:root {
    --bg: #0B1322;
    --bg-side: #080F1C;
    --panel: #101A2B;
    --panel-head: #16233A;
    --field: #0E1A2D;
    --row-hover: #16233A;
    --line: #1C2940;
    --line-soft: #16213350;
    --line-strong: #2A3A57;
    --text: #E6EDF7;
    --text-soft: #C2CEE0;
    --muted: #8296B3;
    --faint: #607391;
    --accent: #3B82F6;
    --accent-bright: #60A5FA;
    --accent-dim: #1E3A6B;
    --accent-wash: #132648;
    --success: #34D399;
    --success-wash: #0E2B23;
    --warning: #FBBF24;
    --warning-wash: #2E2411;
    --danger: #F87171;
    --danger-wash: #2E1618;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI",
            Roboto, "Helvetica Neue", Arial, sans-serif;
    --mono: ui-monospace, "Cascadia Mono", "Segoe UI Mono", Consolas, monospace;
}

html, body, [class*="st-"], button, input, textarea, select { font-family: var(--font); }

/* --- Chrome ----------------------------------------------------------- */

[data-testid="stDecoration"], [data-testid="stAppDeployButton"],
#MainMenu, footer { display: none !important; }
[data-testid="stHeader"] { background: transparent; height: 0; }
[data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--bg); }

.block-container {
    padding: 1.05rem 1.6rem 2rem 1.6rem;
    max-width: 100%;
}

[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: 0.5rem; }
[data-testid="stMain"] [data-testid="stHorizontalBlock"] { gap: 0.6rem; }
[data-testid="stElementContainer"]:has(> .stMarkdown > [data-testid="stMarkdownContainer"]:empty) {
    display: none;
}
/* Streamlit pulls the following element up by 1rem to cancel a trailing
   paragraph margin. Custom markup has no such margin, so the next element
   overlapped it. Paragraph spacing is set explicitly below instead. */
[data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }

/* --- Typography ------------------------------------------------------- */

h1, h2, h3, h4 { color: var(--text); letter-spacing: -0.01em; }
h1 { font-size: 1.18rem !important; font-weight: 620 !important; }
h2 { font-size: 0.98rem !important; font-weight: 620 !important; }
h3 { font-size: 0.88rem !important; font-weight: 620 !important; }
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li {
    color: var(--text-soft);
    font-size: 0.82rem;
    line-height: 1.45;
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p { margin-bottom: 0.3rem; }
[data-testid^="stBaseButton-"] [data-testid="stMarkdownContainer"] p {
    color: inherit !important;
    font-size: 0.8rem;
    margin: 0;
}
[data-testid="stCaptionContainer"] p { font-size: 0.73rem !important; color: var(--muted) !important; }
code { font-family: var(--mono); font-size: 0.82em; color: var(--accent-bright); }

/* --- Sidebar ----------------------------------------------------------- */

[data-testid="stSidebar"] {
    background: var(--bg-side);
    border-right: 1px solid var(--line);
    width: 216px !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0.7rem; }
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarHeader"] { padding-bottom: 0; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.22rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: var(--muted) !important;
    font-size: 0.72rem !important;
}
[data-testid="stSidebar"] hr { border-color: var(--line); margin: 0.6rem 0; }
[data-testid="stSidebar"] label p {
    color: var(--faint) !important;
    font-size: 0.62rem !important;
    font-weight: 650 !important;
    text-transform: uppercase;
    letter-spacing: 0.11em;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] { margin-bottom: 0.1rem; }

.brand {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0 0.1rem 0.7rem 0.1rem;
    border-bottom: 1px solid var(--line);
    margin-bottom: 0.6rem;
}
.brand-mark { flex: 0 0 26px; line-height: 0; }
.brand-name { font-size: 0.83rem; font-weight: 640; color: var(--text); }
.brand-sub {
    font-size: 0.61rem;
    color: var(--faint);
    text-transform: uppercase;
    letter-spacing: 0.11em;
    margin-top: 1px;
}

.side-label {
    font-size: 0.62rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.11em;
    color: var(--faint);
    margin: 0.45rem 0 0.25rem 0.1rem;
}
.side-foot { font-size: 0.665rem; line-height: 1.5; color: var(--faint); padding: 0 0.1rem; }
.chiprow { display: flex; gap: 0.25rem; flex-wrap: wrap; margin-bottom: 0.25rem; }

[data-testid="stSidebarUserContent"] .stPageLink a {
    border-radius: 3px;
    padding: 0.3rem 0.5rem;
    border-left: 2px solid transparent;
}
[data-testid="stSidebarUserContent"] .stPageLink a:hover { background: #0F1A2C; }
[data-testid="stSidebarUserContent"] .stPageLink a span {
    font-size: 0.825rem;
    color: var(--text-soft) !important;
    font-weight: 500;
}
[data-testid="stSidebarUserContent"] .stPageLink a[aria-current="page"] {
    background: var(--accent-wash);
    border-left-color: var(--accent);
}
[data-testid="stSidebarUserContent"] .stPageLink a[aria-current="page"] span {
    color: #FFFFFF !important;
    font-weight: 600;
}

/* --- Page header ------------------------------------------------------- */

.page-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    padding: 0 0 0.5rem 0;
    margin-bottom: 0.7rem;
    border-bottom: 1px solid var(--line);
}
.page-title-row { display: flex; align-items: baseline; gap: 0.6rem; }
.page-title {
    font-size: 1.05rem;
    font-weight: 630;
    color: var(--text);
    letter-spacing: -0.01em;
    margin: 0;
}
.page-kicker {
    font-size: 0.63rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--faint);
    border-left: 1px solid var(--line-strong);
    padding-left: 0.6rem;
}
.page-sub { font-size: 0.78rem; color: var(--muted); margin: 0.2rem 0 0 0; }
.page-meta { display: flex; gap: 0.3rem; flex-wrap: wrap; justify-content: flex-end; }

/* --- Section ----------------------------------------------------------- */

.section { display: flex; align-items: baseline; gap: 0.5rem; margin: 0.35rem 0 0.35rem 0; }
.section-title {
    font-size: 0.7rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-soft);
}
.section-sub { font-size: 0.74rem; color: var(--muted); }

/* --- Chips -------------------------------------------------------------- */

.chip {
    display: inline-flex;
    align-items: center;
    gap: 0.28rem;
    padding: 0.08rem 0.4rem;
    border-radius: 3px;
    font-size: 0.69rem;
    font-weight: 580;
    line-height: 1.55;
    white-space: nowrap;
    border: 1px solid transparent;
}
.chip-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.chip.neutral { background: #17243A; color: var(--muted); border-color: var(--line-strong); }
.chip.accent, .chip.info {
    background: var(--accent-wash); color: var(--accent-bright); border-color: var(--accent-dim);
}
.chip.success { background: var(--success-wash); color: var(--success); border-color: #1B4C3C; }
.chip.warning { background: var(--warning-wash); color: var(--warning); border-color: #4D3A12; }
.chip.danger  { background: var(--danger-wash);  color: var(--danger);  border-color: #4F2124; }

.ref {
    font-family: var(--mono);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--accent-bright);
    background: var(--accent-wash);
    border: 1px solid var(--accent-dim);
    border-radius: 3px;
    padding: 0.02rem 0.3rem;
}

/* --- Readout strip ------------------------------------------------------ */

.kpis {
    display: grid;
    gap: 1px;
    background: var(--line);
    border: 1px solid var(--line);
    border-radius: 3px;
    overflow: hidden;
}
.kpi { padding: 0.5rem 0.75rem; background: var(--panel); }
.kpi-label {
    font-size: 0.62rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--faint);
}
.kpi-value {
    font-family: var(--mono);
    font-size: 1.22rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.25;
    margin-top: 0.1rem;
}
.kpi-value.accent  { color: var(--accent-bright); }
.kpi-value.warning { color: var(--warning); }
.kpi-value.danger  { color: var(--danger); }
.kpi-value.success { color: var(--success); }
.kpi-hint { font-size: 0.675rem; color: var(--muted); }

/* --- Panels ------------------------------------------------------------- */

/* Streamlit containers tagged with a marker become panels. The depth of the
   marker under the border wrapper varies with Streamlit's internal wrappers. */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > .panel-marker),
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > div > .panel-marker),
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > div > div > .panel-marker),
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > div > div > div > .panel-marker) {
    background: var(--panel);
    border: 1px solid var(--line) !important;
    border-radius: 3px !important;
    padding: 0.6rem 0.7rem !important;
}
.panel-marker { display: none; }

.panel-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: -0.6rem -0.7rem 0.5rem -0.7rem;
    padding: 0.36rem 0.7rem;
    border-bottom: 1px solid var(--line);
    background: var(--panel-head);
}
.panel-title {
    font-size: 0.705rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--text-soft);
}
.panel-meta { margin-left: auto; display: flex; gap: 0.28rem; align-items: center; }

/* --- Data table --------------------------------------------------------- */

.tbl-wrap { border: 1px solid var(--line); border-radius: 3px; overflow: auto; background: var(--panel); }
table.tbl { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.775rem; }
table.tbl thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--panel-head);
    color: var(--muted);
    font-size: 0.645rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    text-align: left;
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid var(--line-strong);
    white-space: nowrap;
}
table.tbl tbody td {
    padding: 0.3rem 0.6rem;
    border-bottom: 1px solid var(--line);
    color: var(--text-soft);
    vertical-align: top;
    line-height: 1.4;
}
table.tbl tbody tr:last-child td { border-bottom: none; }
table.tbl tbody tr:hover td { background: var(--row-hover); }
/* Streamlit's markdown turns bare emails and URLs in cell text into links. */
table.tbl a, table.tbl a:visited, table.tbl a:hover {
    color: inherit !important;
    text-decoration: none !important;
    pointer-events: none;
}
table.tbl td.num, table.tbl th.num {
    text-align: right;
    font-family: var(--mono);
    font-variant-numeric: tabular-nums;
}
/* Mono cells hold identifiers and timestamps, which must never wrap. */
table.tbl td.mono {
    font-family: var(--mono);
    font-size: 0.735rem;
    color: var(--text);
    white-space: nowrap;
}
table.tbl td.strong { font-weight: 560; color: var(--text); }
table.tbl td.muted { color: var(--muted); }
table.tbl td.nowrap { white-space: nowrap; }
/* Long free text would otherwise make rows many lines tall and destroy density.
   The full value stays available as the cell tooltip. */
table.tbl td.clamp span {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.tbl-foot {
    font-size: 0.695rem;
    color: var(--faint);
    font-family: var(--mono);
    padding: 0.35rem 0 0.1rem 0.1rem;
    line-height: 1.3;
}

/* --- Callout and empty state -------------------------------------------- */

.callout {
    display: block;
    border: 1px solid var(--line);
    border-left: 2px solid var(--muted);
    border-radius: 3px;
    padding: 0.45rem 0.65rem;
    background: var(--panel);
    font-size: 0.775rem;
    line-height: 1.45;
    color: var(--text-soft);
    margin-bottom: 0.45rem;
}
.callout.accent  { border-left-color: var(--accent);  background: var(--accent-wash); }
.callout.success { border-left-color: var(--success); background: var(--success-wash); }
.callout.warning { border-left-color: var(--warning); background: var(--warning-wash); }
.callout.danger  { border-left-color: var(--danger);  background: var(--danger-wash); }
.callout-title { font-weight: 640; color: var(--text); margin-right: 0.22rem; }
.callout code { background: #0A1220; border-radius: 2px; padding: 0.02rem 0.26rem; }

.empty {
    border: 1px dashed var(--line-strong);
    border-radius: 3px;
    background: var(--panel);
    padding: 1.15rem 1rem;
    text-align: center;
}
.empty-title { font-size: 0.8rem; font-weight: 600; color: var(--text-soft); }
.empty-body { font-size: 0.755rem; color: var(--muted); margin-top: 0.2rem; }

.card {
    border: 1px solid var(--line);
    border-radius: 3px;
    background: var(--panel);
    padding: 0.55rem 0.7rem;
    height: 100%;
}
.card-title { font-size: 0.79rem; font-weight: 600; color: var(--text); margin-bottom: 0.15rem; }
.card-body { font-size: 0.755rem; color: var(--muted); line-height: 1.45; }

/* --- Answer and evidence ------------------------------------------------ */

.answer { background: var(--panel); border: 1px solid var(--line); border-radius: 3px; }
.answer-head {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.36rem 0.7rem;
    background: var(--panel-head);
    border-bottom: 1px solid var(--line);
}
.answer-label {
    font-size: 0.645rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--faint);
}
.answer-meta { margin-left: auto; display: flex; gap: 0.28rem; align-items: center; }
.answer-body { padding: 0.65rem 0.75rem; font-size: 0.85rem; color: var(--text); line-height: 1.55; }
.answer-body .ref-mark { color: var(--accent-bright); font-family: var(--mono); font-size: 0.78rem; }

.evidence {
    border: 1px solid var(--line);
    border-left: 2px solid var(--accent-dim);
    border-radius: 3px;
    background: var(--panel);
    padding: 0.4rem 0.6rem;
    margin-bottom: 0.3rem;
}
.evidence-head { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.evidence-marker {
    font-family: var(--mono);
    font-size: 0.68rem;
    font-weight: 650;
    color: var(--accent-bright);
    background: var(--accent-wash);
    border-radius: 2px;
    padding: 0.02rem 0.26rem;
}
.evidence-source { font-size: 0.755rem; font-weight: 540; color: var(--text-soft); }
.evidence-score { font-size: 0.68rem; color: var(--faint); margin-left: auto; font-family: var(--mono); }
.evidence-text {
    font-size: 0.74rem;
    color: var(--muted);
    line-height: 1.45;
    white-space: pre-wrap;
    margin-top: 0.22rem;
    max-height: 5.5rem;
    overflow-y: auto;
}

/* --- Tabs --------------------------------------------------------------- */

.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--line);
    margin-bottom: 0.65rem;
    background: transparent;
}
.stTabs [data-baseweb="tab"] {
    height: 2rem;
    padding: 0 0.75rem;
    background: transparent;
    color: var(--muted);
    font-size: 0.795rem;
    font-weight: 520;
    border-radius: 0;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--panel); color: var(--text-soft); }
.stTabs [aria-selected="true"] { color: var(--text) !important; font-weight: 620; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--accent); height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* --- Controls ------------------------------------------------------------ */

[data-testid^="stBaseButton-"] {
    border-radius: 3px !important;
    font-weight: 560 !important;
    font-size: 0.805rem !important;
    padding: 0.28rem 0.8rem !important;
    min-height: 2rem;
    transition: background 110ms ease, border-color 110ms ease;
}
[data-testid^="stBaseButton-secondary"] {
    background: #16233A;
    border: 1px solid var(--line-strong);
    color: var(--text-soft);
}
[data-testid^="stBaseButton-secondary"]:hover {
    background: #1D2D49;
    border-color: #3A4D70;
    color: var(--text);
}
[data-testid^="stBaseButton-primary"] {
    background: var(--accent);
    border: 1px solid var(--accent);
    color: #FFFFFF !important;
}
[data-testid^="stBaseButton-primary"] p { color: #FFFFFF !important; }
[data-testid^="stBaseButton-primary"]:hover { background: #2E6FD9; border-color: #2E6FD9; }

[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"],
[data-testid="stMain"] [data-baseweb="textarea"],
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] {
    background: var(--field) !important;
    border-radius: 3px !important;
    border-color: var(--line-strong) !important;
    min-height: 2rem;
}
[data-testid="stMain"] [data-baseweb="select"] div, [data-testid="stMain"] input,
[data-testid="stMain"] textarea { font-size: 0.82rem !important; color: var(--text) !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] div {
    font-size: 0.8rem !important;
    color: var(--text) !important;
}

[data-testid="stMain"] [data-testid="stWidgetLabel"] p {
    font-size: 0.645rem !important;
    font-weight: 660 !important;
    color: var(--faint) !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[data-testid="stMain"] .stCheckbox [data-testid="stWidgetLabel"] p {
    text-transform: none;
    letter-spacing: 0;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    color: var(--text-soft) !important;
}

[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: var(--accent-wash) !important;
    border: 1px solid var(--accent-dim);
    border-radius: 2px;
    height: 1.35rem;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] span {
    color: var(--accent-bright) !important;
    font-size: 0.72rem;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg { fill: var(--accent-bright); }

[data-testid="stExpander"] {
    border: 1px solid var(--line);
    border-radius: 3px;
    background: var(--panel);
}
[data-testid="stExpander"] summary {
    font-size: 0.785rem;
    font-weight: 540;
    padding: 0.35rem 0.65rem;
    color: var(--text-soft);
}
[data-testid="stExpander"] summary:hover { background: var(--panel-head); color: var(--text); }

[data-testid="stFileUploaderDropzone"] {
    background: var(--field);
    border: 1px dashed var(--line-strong);
    border-radius: 3px;
    padding: 0.6rem 0.8rem;
}
[data-testid="stForm"] { border: 1px solid var(--line); border-radius: 3px; background: var(--panel); }

[data-testid="stMain"] hr { border-color: var(--line); margin: 0.8rem 0; }
[data-testid="stMain"] .stPageLink a {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--line-strong);
    border-radius: 3px;
    padding: 0.26rem 0.65rem;
    background: #16233A;
}
[data-testid="stMain"] .stPageLink a:hover { background: #1D2D49; }
[data-testid="stMain"] .stPageLink a span {
    color: var(--accent-bright) !important;
    font-weight: 540;
    font-size: 0.785rem;
}

[data-testid="stJson"] { background: var(--field) !important; border-radius: 3px; }
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] { background: var(--accent); }
</style>
"""

BRAND_MARK = """
<svg width="26" height="26" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect x="0.5" y="0.5" width="33" height="33" rx="3" fill="#101A2B" stroke="#2A3A57"/>
  <path d="M11 11.5 L11 22.5 M23 11.5 L23 22.5 M11 17 L23 17"
        stroke="#3B82F6" stroke-width="1.5" stroke-linecap="round"/>
  <circle cx="11" cy="11.5" r="2.4" fill="#E6EDF7"/>
  <circle cx="23" cy="11.5" r="2.4" fill="#3B82F6"/>
  <circle cx="11" cy="22.5" r="2.4" fill="#3B82F6"/>
  <circle cx="23" cy="22.5" r="2.4" fill="#E6EDF7"/>
</svg>
"""


def inject() -> None:
    st.markdown(STYLESHEET, unsafe_allow_html=True)


def _html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def chip(label: str, tone: Tone = "neutral", dot: bool = False) -> str:
    marker = '<span class="chip-dot"></span>' if dot else ""
    return f'<span class="chip {tone}">{marker}{esc(label)}</span>'


def ref(value: str) -> str:
    return f'<span class="ref">{esc(value)}</span>'


def brand(name: str, subtitle: str) -> None:
    _html(
        f'<div class="brand"><div class="brand-mark">{BRAND_MARK}</div><div>'
        f'<div class="brand-name">{esc(name)}</div>'
        f'<div class="brand-sub">{esc(subtitle)}</div></div></div>'
    )


def sidebar_label(text: str) -> None:
    _html(f'<div class="side-label">{esc(text)}</div>')


def sidebar_note(text: str) -> None:
    _html(f'<div class="side-foot">{text}</div>')


def page_header(
    title: str, subtitle: str = "", kicker: str = "", chips: Iterable[str] = ()
) -> None:
    kicker_html = f'<span class="page-kicker">{esc(kicker)}</span>' if kicker else ""
    sub_html = f'<p class="page-sub">{esc(subtitle)}</p>' if subtitle else ""
    _html(
        f'<div class="page-head"><div><div class="page-title-row">'
        f'<h1 class="page-title">{esc(title)}</h1>{kicker_html}</div>{sub_html}</div>'
        f'<div class="page-meta">{"".join(chips)}</div></div>'
    )


def section(title: str, subtitle: str = "") -> None:
    sub = f'<span class="section-sub">{esc(subtitle)}</span>' if subtitle else ""
    _html(f'<div class="section"><span class="section-title">{esc(title)}</span>{sub}</div>')


def kpis(items: Sequence[tuple[str, Any, str]], tones: Sequence[str] = ()) -> None:
    """A single strip of readouts: (label, value, hint)."""
    cells = []
    for index, (label, value, hint) in enumerate(items):
        tone = tones[index] if index < len(tones) else ""
        hint_html = f'<div class="kpi-hint">{esc(hint)}</div>' if hint else ""
        cells.append(
            f'<div class="kpi"><div class="kpi-label">{esc(label)}</div>'
            f'<div class="kpi-value {tone}">{esc(value)}</div>{hint_html}</div>'
        )
    columns = f"repeat({len(items)}, minmax(0, 1fr))"
    _html(f'<div class="kpis" style="grid-template-columns:{columns}">{"".join(cells)}</div>')


def table(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[Mapping[str, Any]],
    max_height: str = "25rem",
    empty: str = "No rows.",
    note: str = "",
) -> None:
    """A dense, sticky-header table.

    Each column spec takes: key, label, and optionally style (text, strong,
    mono, num, muted, clamp, clamp-muted, chip), width, and tones for chips.
    """
    if not rows:
        empty_state(empty)
        return

    head_cells = []
    for column in columns:
        css = "num" if column.get("style") == "num" else ""
        width = column.get("width")
        style_attr = f' style="width:{width}"' if width else ""
        label = column.get("label", column["key"])
        head_cells.append(f'<th class="{css}"{style_attr}>{esc(label)}</th>')
    head = "".join(head_cells)

    body_rows = []
    for row in rows:
        cells = []
        for column in columns:
            style = column.get("style", "text")
            value = row.get(column["key"], "")
            if style == "chip":
                tone = column.get("tones", {}).get(str(value), "neutral")
                content = chip(str(value), tone) if value != "" else ""
                cells.append(f'<td class="nowrap">{content}</td>')
                continue
            if style == "num":
                cells.append(f'<td class="num">{esc(value)}</td>')
                continue
            if style in ("clamp", "clamp-muted"):
                css = "clamp muted" if style == "clamp-muted" else "clamp"
                cells.append(
                    f'<td class="{css}" title="{esc(value)}"><span>{esc(value)}</span></td>'
                )
                continue
            cells.append(f'<td class="{style}">{esc(value)}</td>')
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    height = f"max-height:{max_height}" if max_height != "none" else ""
    # The note is emitted inside the same markdown block as the table: as its
    # own element it rendered on top of whatever Streamlit laid out next.
    note_html = f'<div class="tbl-foot">{esc(note)}</div>' if note else ""
    _html(
        f'<div class="tbl-wrap" style="{height}">'
        f'<table class="tbl"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>{note_html}'
    )


def table_note(text: str) -> None:
    _html(f'<div class="tbl-foot">{esc(text)}</div>')


def callout(body: str, title: str = "", tone: Tone = "neutral") -> None:
    heading = f'<span class="callout-title">{esc(title)}</span>' if title else ""
    _html(f'<div class="callout {tone}">{heading}{body}</div>')


def empty_state(title: str, body: str = "") -> None:
    body_html = f'<div class="empty-body">{body}</div>' if body else ""
    _html(f'<div class="empty"><div class="empty-title">{esc(title)}</div>{body_html}</div>')


def card(title: str, body: str) -> None:
    _html(
        f'<div class="card"><div class="card-title">{esc(title)}</div>'
        f'<div class="card-body">{esc(body)}</div></div>'
    )


def panel_marker() -> None:
    """Tag the enclosing st.container(border=True) so the stylesheet restyles it."""
    _html('<span class="panel-marker"></span>')


def panel_bar(title: str, meta: Iterable[str] = ()) -> None:
    """A header strip for the first slot of a st.container(border=True)."""
    meta_html = f'<div class="panel-meta">{"".join(meta)}</div>' if meta else ""
    _html(
        f'<span class="panel-marker"></span><div class="panel-bar">'
        f'<span class="panel-title">{esc(title)}</span>{meta_html}</div>'
    )


# Retained so older call sites keep working.
stats = kpis
card_marker = panel_marker
