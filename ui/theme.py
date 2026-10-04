"""Visual design system: palette, stylesheet, and presentational components.

Self-contained by design. No web fonts, icon packs, or remote assets are
fetched, because the assistant must render identically on an air-gapped machine.
"""

from __future__ import annotations

import html
from typing import Any, Iterable, Literal, Mapping, Sequence

import streamlit as st

Tone = Literal["neutral", "accent", "success", "warning", "danger", "info"]

ACCENT = "#2563EB"
NAVY = "#0D1829"
INK = "#0F172A"
MUTED = "#64748B"

STYLESHEET = """
<style>
:root {
    --ink: #0F172A;
    --ink-soft: #334155;
    --muted: #64748B;
    --faint: #94A3B8;
    --border: #E3E8EF;
    --border-strong: #CBD5E1;
    --surface: #F8FAFC;
    --surface-2: #F1F5F9;
    --accent: #2563EB;
    --accent-dark: #1D4ED8;
    --accent-soft: #EFF4FF;
    --accent-line: #D8E3FF;
    --success: #15803D;
    --success-soft: #ECFDF3;
    --warning: #B45309;
    --warning-soft: #FFF8EB;
    --danger: #B91C1C;
    --danger-soft: #FEF2F2;
    --navy: #0D1829;
    --navy-2: #16233A;
    --navy-line: rgba(255, 255, 255, 0.09);
    --navy-text: #CBD5E1;
    --navy-faint: #7C8DA6;
    --font: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI",
            Roboto, "Helvetica Neue", Arial, sans-serif;
    --mono: ui-monospace, "Cascadia Mono", "Segoe UI Mono", Consolas, monospace;
    --radius: 8px;
    --shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
}

html, body, [class*="st-"], button, input, textarea, select { font-family: var(--font); }

/* --- Chrome ----------------------------------------------------------- */

[data-testid="stDecoration"], [data-testid="stAppDeployButton"],
#MainMenu, footer { display: none !important; }
[data-testid="stHeader"] { background: transparent; height: 0; }

.block-container {
    padding: 1.3rem 2.1rem 2.5rem 2.1rem;
    max-width: 1560px;
}

[data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: 0.55rem; }
[data-testid="stMain"] [data-testid="stHorizontalBlock"] { gap: 0.7rem; }
[data-testid="stElementContainer"]:has(> .stMarkdown > [data-testid="stMarkdownContainer"]:empty) {
    display: none;
}

/* --- Typography ------------------------------------------------------- */

h1, h2, h3, h4 { color: var(--ink); letter-spacing: -0.015em; }
h1 { font-size: 1.32rem !important; font-weight: 650 !important; }
h2 { font-size: 1.02rem !important; font-weight: 620 !important; }
h3 { font-size: 0.92rem !important; font-weight: 620 !important; }
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] li {
    color: var(--ink-soft);
    font-size: 0.855rem;
    line-height: 1.5;
}
[data-testid="stMain"] [data-testid="stMarkdownContainer"] p { margin-bottom: 0.35rem; }
[data-testid^="stBaseButton-"] [data-testid="stMarkdownContainer"] p {
    color: inherit !important;
    font-size: 0.82rem;
    margin: 0;
}
[data-testid="stCaptionContainer"] p { font-size: 0.76rem !important; color: var(--muted) !important; }
code { font-family: var(--mono); font-size: 0.82em; }

/* --- Sidebar: dark navy ------------------------------------------------ */

[data-testid="stSidebar"] { background: var(--navy); border-right: none; width: 244px !important; }
[data-testid="stSidebar"] > div:first-child { padding-top: 0.85rem; }
[data-testid="stSidebarNav"] { display: none !important; }
[data-testid="stSidebarHeader"] { padding-bottom: 0; }
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap: 0.3rem; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: var(--navy-faint) !important;
    font-size: 0.74rem !important;
}
[data-testid="stSidebar"] hr { border-color: var(--navy-line); margin: 0.75rem 0; }
[data-testid="stSidebar"] label p {
    color: #5D7190 !important;
    font-size: 0.64rem !important;
    font-weight: 650 !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] { margin-bottom: 0.1rem; }

.brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0 0.1rem 0.85rem 0.1rem;
    border-bottom: 1px solid var(--navy-line);
    margin-bottom: 0.7rem;
}
.brand-mark { flex: 0 0 30px; line-height: 0; }
.brand-name { font-size: 0.88rem; font-weight: 650; color: #F1F5F9; letter-spacing: -0.01em; }
.brand-sub {
    font-size: 0.65rem;
    color: var(--navy-faint);
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-top: 1px;
}

.side-label {
    font-size: 0.64rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #5D7190;
    margin: 0.55rem 0 0.3rem 0.15rem;
}

[data-testid="stSidebarUserContent"] .stPageLink a {
    border-radius: 6px;
    padding: 0.33rem 0.55rem;
    margin-bottom: 0;
    border-left: 2px solid transparent;
}
[data-testid="stSidebarUserContent"] .stPageLink a:hover { background: var(--navy-2); }
[data-testid="stSidebarUserContent"] .stPageLink a span {
    font-size: 0.845rem;
    color: var(--navy-text) !important;
    font-weight: 500;
}
[data-testid="stSidebarUserContent"] .stPageLink a[aria-current="page"] {
    background: rgba(37, 99, 235, 0.18);
    border-left-color: #60A5FA;
}
[data-testid="stSidebarUserContent"] .stPageLink a[aria-current="page"] span {
    color: #FFFFFF !important;
    font-weight: 600;
}

/* Dark form controls inside the sidebar. */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"],
[data-testid="stSidebar"] [data-baseweb="base-input"] {
    background: var(--navy-2) !important;
    border-color: var(--navy-line) !important;
    border-radius: 6px !important;
    min-height: 2rem !important;
}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"] div[value],
[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #E2E8F0 !important;
    font-size: 0.82rem !important;
}
[data-testid="stSidebar"] svg { fill: #8CA0BC; }
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: transparent;
    border: 1px solid var(--navy-line);
    border-radius: 6px;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary { color: var(--navy-text); }
[data-testid="stSidebar"] [data-testid="stExpander"] summary p {
    color: var(--navy-text) !important;
    font-size: 0.8rem !important;
}
[data-testid="stSidebar"] [data-testid^="stBaseButton-"] {
    background: var(--navy-2);
    border: 1px solid var(--navy-line);
    color: #E2E8F0;
}
[data-testid="stSidebar"] [data-testid^="stBaseButton-"] p { color: #E2E8F0 !important; }

.side-foot {
    font-size: 0.68rem;
    line-height: 1.45;
    color: #5D7190;
    padding: 0.1rem 0.15rem;
}

/* --- Page header ------------------------------------------------------- */

.page-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.2rem;
    padding-bottom: 0.65rem;
    margin-bottom: 0.9rem;
    border-bottom: 1px solid var(--border);
}
.page-kicker {
    font-size: 0.64rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
    margin-bottom: 0.18rem;
}
.page-title {
    font-size: 1.3rem;
    font-weight: 650;
    color: var(--ink);
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin: 0;
}
.page-sub { font-size: 0.8rem; color: var(--muted); margin: 0.22rem 0 0 0; max-width: 92ch; }
.page-meta { display: flex; gap: 0.35rem; flex-wrap: wrap; justify-content: flex-end; }

/* --- Section ----------------------------------------------------------- */

.section {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin: 0.5rem 0 0.45rem 0;
}
.section-title {
    font-size: 0.74rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.085em;
    color: var(--ink);
}
.section-sub { font-size: 0.76rem; color: var(--muted); }

/* --- Chips -------------------------------------------------------------- */

.chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.11rem 0.45rem;
    border-radius: 5px;
    font-size: 0.705rem;
    font-weight: 580;
    line-height: 1.5;
    white-space: nowrap;
    border: 1px solid transparent;
}
.chip-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.chip.neutral { background: var(--surface-2); color: #475569; border-color: var(--border); }
.chip.accent  { background: var(--accent-soft); color: var(--accent-dark); border-color: var(--accent-line); }
.chip.info    { background: var(--accent-soft); color: var(--accent-dark); border-color: var(--accent-line); }
.chip.success { background: var(--success-soft); color: var(--success); border-color: #CBEFD9; }
.chip.warning { background: var(--warning-soft); color: var(--warning); border-color: #F6E2BE; }
.chip.danger  { background: var(--danger-soft);  color: var(--danger);  border-color: #F7D2D2; }

.ref {
    font-family: var(--mono);
    font-size: 0.73rem;
    font-weight: 600;
    color: var(--accent-dark);
    background: var(--accent-soft);
    border: 1px solid var(--accent-line);
    border-radius: 4px;
    padding: 0.04rem 0.33rem;
}

/* --- KPI strip ---------------------------------------------------------- */

.kpis {
    display: grid;
    gap: 0;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: #FFFFFF;
    overflow: hidden;
    box-shadow: var(--shadow);
}
.kpi { padding: 0.6rem 0.85rem; border-left: 1px solid var(--border); }
.kpi:first-child { border-left: none; }
.kpi-label {
    font-size: 0.645rem;
    font-weight: 650;
    text-transform: uppercase;
    letter-spacing: 0.085em;
    color: var(--faint);
}
.kpi-value {
    font-size: 1.28rem;
    font-weight: 660;
    color: var(--ink);
    line-height: 1.2;
    margin-top: 0.12rem;
    letter-spacing: -0.02em;
}
.kpi-value.accent { color: var(--accent-dark); }
.kpi-value.warning { color: var(--warning); }
.kpi-hint { font-size: 0.695rem; color: var(--muted); margin-top: 0.05rem; }

/* --- Panels ------------------------------------------------------------- */

.panel {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: #FFFFFF;
    box-shadow: var(--shadow);
    overflow: hidden;
    margin-bottom: 0.6rem;
}
.panel-head {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
}
.panel-title {
    font-size: 0.735rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.085em;
    color: var(--ink-soft);
}
.panel-meta { margin-left: auto; display: flex; gap: 0.3rem; align-items: center; }
.panel-body { padding: 0.7rem 0.75rem; }
.panel-body.flush { padding: 0; }

/* Streamlit containers tagged with a marker become panels. The depth of the
   marker under the border wrapper varies with Streamlit's internal wrappers. */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > .panel-marker),
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > div > .panel-marker),
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > div > div > .panel-marker),
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > div > div > div > div > .panel-marker) {
    background: #FFFFFF;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow);
    padding: 0.65rem 0.8rem !important;
}
.panel-marker { display: none; }

.panel-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin: -0.65rem -0.8rem 0.55rem -0.8rem;
    padding: 0.4rem 0.8rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
    border-radius: var(--radius) var(--radius) 0 0;
}

/* --- Data table --------------------------------------------------------- */

.tbl-wrap {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: auto;
    background: #FFFFFF;
}
.tbl-wrap.flush { border: none; border-radius: 0; }
table.tbl { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.78rem; }
table.tbl thead th {
    position: sticky;
    top: 0;
    z-index: 2;
    background: var(--surface);
    color: var(--muted);
    font-size: 0.665rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    text-align: left;
    padding: 0.42rem 0.6rem;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
}
table.tbl tbody td {
    padding: 0.33rem 0.6rem;
    border-bottom: 1px solid #F1F5F9;
    color: var(--ink-soft);
    vertical-align: top;
    line-height: 1.4;
}
table.tbl tbody tr:last-child td { border-bottom: none; }
table.tbl tbody tr:hover td { background: #F8FAFF; }
/* Streamlit's markdown turns bare emails and URLs in cell text into links. */
table.tbl a { color: inherit; text-decoration: none; pointer-events: none; }
table.tbl td.num, table.tbl th.num { text-align: right; font-variant-numeric: tabular-nums; }
table.tbl td.mono { font-family: var(--mono); font-size: 0.74rem; color: var(--ink); }
table.tbl td.strong { font-weight: 580; color: var(--ink); }
table.tbl td.muted { color: var(--muted); }
table.tbl td.wrap { white-space: normal; }
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
    font-size: 0.71rem;
    color: var(--faint);
    margin: 0.3rem 0 0.1rem 0.1rem;
}

.chiprow { display: flex; gap: 0.3rem; flex-wrap: wrap; margin-bottom: 0.3rem; }

/* --- Callout and empty state -------------------------------------------- */

.callout {
    display: block;
    border: 1px solid var(--border);
    border-left: 3px solid var(--muted);
    border-radius: 6px;
    padding: 0.5rem 0.7rem;
    background: var(--surface);
    font-size: 0.79rem;
    line-height: 1.5;
    color: var(--ink-soft);
    margin-bottom: 0.55rem;
}
.callout.accent  { border-left-color: var(--accent);  background: var(--accent-soft); }
.callout.success { border-left-color: var(--success); background: var(--success-soft); }
.callout.warning { border-left-color: var(--warning); background: var(--warning-soft); }
.callout.danger  { border-left-color: var(--danger);  background: var(--danger-soft); }
.callout-title { font-weight: 650; color: var(--ink); margin-right: 0.22rem; }
.callout code {
    background: rgba(15, 23, 42, 0.07);
    border-radius: 3px;
    padding: 0.02rem 0.26rem;
    word-break: break-all;
}

.card {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: #FFFFFF;
    padding: 0.6rem 0.75rem;
    box-shadow: var(--shadow);
    height: 100%;
}
.card-title { font-size: 0.82rem; font-weight: 620; color: var(--ink); margin-bottom: 0.18rem; }
.card-body { font-size: 0.775rem; color: var(--muted); line-height: 1.5; }

.empty {
    border: 1px dashed var(--border-strong);
    border-radius: var(--radius);
    background: var(--surface);
    padding: 1.4rem 1rem;
    text-align: center;
}
.empty-title { font-size: 0.84rem; font-weight: 620; color: var(--ink-soft); }
.empty-body { font-size: 0.775rem; color: var(--muted); margin-top: 0.22rem; }

/* --- Answer and evidence ------------------------------------------------ */

.answer {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
}
.answer-head {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.45rem 0.8rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
}
.answer-label {
    font-size: 0.665rem;
    font-weight: 680;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    color: var(--faint);
}
.answer-meta { margin-left: auto; display: flex; gap: 0.3rem; align-items: center; }
.answer-body { padding: 0.75rem 0.85rem; font-size: 0.87rem; color: var(--ink); line-height: 1.58; }

.evidence {
    border: 1px solid var(--border);
    border-left: 2px solid var(--accent);
    border-radius: 6px;
    background: #FFFFFF;
    padding: 0.45rem 0.65rem;
    margin-bottom: 0.35rem;
}
.evidence-head { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.evidence-marker {
    font-family: var(--mono);
    font-size: 0.69rem;
    font-weight: 680;
    color: var(--accent-dark);
    background: var(--accent-soft);
    border-radius: 3px;
    padding: 0.02rem 0.28rem;
}
.evidence-source { font-size: 0.765rem; font-weight: 570; color: var(--ink); }
.evidence-score { font-size: 0.69rem; color: var(--faint); margin-left: auto; }
.evidence-text {
    font-size: 0.755rem;
    color: var(--muted);
    line-height: 1.5;
    white-space: pre-wrap;
    margin-top: 0.25rem;
    max-height: 6rem;
    overflow-y: auto;
}

/* --- Tabs --------------------------------------------------------------- */

.stTabs [data-baseweb="tab-list"] {
    gap: 0.1rem;
    border-bottom: 1px solid var(--border);
    margin-bottom: 0.75rem;
}
.stTabs [data-baseweb="tab"] {
    height: 2.15rem;
    padding: 0 0.7rem;
    background: transparent;
    color: var(--muted);
    font-size: 0.815rem;
    font-weight: 540;
    border-radius: 6px 6px 0 0;
}
.stTabs [data-baseweb="tab"]:hover { background: var(--surface-2); color: var(--ink-soft); }
.stTabs [aria-selected="true"] { color: var(--ink) !important; font-weight: 640; }
.stTabs [data-baseweb="tab-highlight"] { background-color: var(--accent); height: 2px; }
.stTabs [data-baseweb="tab-border"] { display: none; }

/* --- Controls ------------------------------------------------------------ */

[data-testid^="stBaseButton-"] {
    border-radius: 6px !important;
    font-weight: 560 !important;
    font-size: 0.82rem !important;
    padding: 0.3rem 0.75rem !important;
    min-height: 2.1rem;
    transition: background 110ms ease, border-color 110ms ease;
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
[data-testid^="stBaseButton-primary"]:hover { background: var(--accent-dark); border-color: var(--accent-dark); }

[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"],
[data-testid="stMain"] [data-baseweb="textarea"] {
    border-radius: 6px !important;
    border-color: var(--border-strong) !important;
    min-height: 2.1rem;
    font-size: 0.83rem;
}
[data-testid="stMain"] [data-baseweb="select"] div, [data-testid="stMain"] input {
    font-size: 0.83rem !important;
}
[data-testid="stMain"] .stTextInput label, [data-testid="stMain"] .stTextArea label,
[data-testid="stMain"] .stSelectbox label, [data-testid="stMain"] .stMultiSelect label,
[data-testid="stMain"] .stSlider label, [data-testid="stMain"] .stFileUploader label,
[data-testid="stMain"] .stCheckbox label {
    font-size: 0.735rem !important;
    font-weight: 600 !important;
    color: var(--muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMain"] .stCheckbox label { text-transform: none; letter-spacing: 0; font-weight: 500 !important; }

[data-testid="stMultiSelect"] [data-baseweb="tag"] {
    background: var(--accent-soft) !important;
    border: 1px solid var(--accent-line);
    border-radius: 4px;
    height: 1.4rem;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] span { color: var(--accent-dark) !important; font-size: 0.73rem; }
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg { fill: var(--accent-dark); }

[data-testid="stExpander"] {
    border: 1px solid var(--border);
    border-radius: 6px;
    background: #FFFFFF;
    overflow: hidden;
}
[data-testid="stExpander"] summary { font-size: 0.8rem; font-weight: 560; padding: 0.4rem 0.7rem; }
[data-testid="stExpander"] summary:hover { background: var(--surface); }

[data-testid="stFileUploaderDropzone"] {
    background: var(--surface);
    border: 1px dashed var(--border-strong);
    border-radius: 6px;
    padding: 0.7rem 0.9rem;
}

[data-testid="stMain"] hr { border-color: var(--border); margin: 0.9rem 0; }

[data-testid="stMain"] .stPageLink a {
    display: inline-flex;
    align-items: center;
    border: 1px solid var(--border-strong);
    border-radius: 6px;
    padding: 0.3rem 0.7rem;
    background: #FFFFFF;
}
[data-testid="stMain"] .stPageLink a:hover { background: var(--surface-2); }
[data-testid="stMain"] .stPageLink a span {
    color: var(--accent-dark) !important;
    font-weight: 560;
    font-size: 0.8rem;
}
</style>
"""

BRAND_MARK = """
<svg width="30" height="30" viewBox="0 0 34 34" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="34" height="34" rx="8" fill="#16233A"/>
  <path d="M11 11.5 L11 22.5 M23 11.5 L23 22.5 M11 17 L23 17"
        stroke="#3B82F6" stroke-width="1.6" stroke-linecap="round"/>
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
    kicker_html = f'<div class="page-kicker">{esc(kicker)}</div>' if kicker else ""
    sub_html = f'<p class="page-sub">{esc(subtitle)}</p>' if subtitle else ""
    _html(
        f'<div class="page-head"><div>{kicker_html}'
        f'<h1 class="page-title">{esc(title)}</h1>{sub_html}</div>'
        f'<div class="page-meta">{"".join(chips)}</div></div>'
    )


def section(title: str, subtitle: str = "") -> None:
    sub = f'<span class="section-sub">{esc(subtitle)}</span>' if subtitle else ""
    _html(f'<div class="section"><span class="section-title">{esc(title)}</span>{sub}</div>')


def kpis(items: Sequence[tuple[str, Any, str]], tones: Sequence[str] = ()) -> None:
    """A single bordered strip of figures: (label, value, hint)."""
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
) -> None:
    """A dense, sticky-header table.

    Each column spec takes: key, label, and optionally style (text, strong,
    mono, num, muted, wrap, chip), width, and tones for chip columns.
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
                tones = column.get("tones", {})
                tone = tones.get(str(value), "neutral")
                content = chip(str(value), tone) if value != "" else ""
                css = "nowrap"
                cells.append(f'<td class="{css}">{content}</td>')
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

    _html(
        f'<div class="tbl-wrap" style="max-height:{max_height}">'
        f'<table class="tbl"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
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


# Retained so older call sites keep working.
stats = kpis


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


card_marker = panel_marker
