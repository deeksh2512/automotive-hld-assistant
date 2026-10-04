"""Render every Streamlit page and assert no uncaught exception.

Requires the backend to be running; skipped otherwise so the unit suite stays
offline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.api_client import backend_online

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

UI_DIR = Path(__file__).resolve().parent.parent / "ui"

PAGES = [
    UI_DIR / "Home.py",
    UI_DIR / "pages" / "0_Documents.py",
    UI_DIR / "pages" / "1_HLD_Analysis.py",
    UI_DIR / "pages" / "2_Review_Queue.py",
    UI_DIR / "pages" / "3_Audit_Trail.py",
]

pytestmark = pytest.mark.skipif(
    not backend_online(), reason="backend is not running on API_BASE_URL"
)


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.stem)
def test_page_renders_without_exception(page: Path):
    app = AppTest.from_file(str(page), default_timeout=180)
    app.run()
    assert not app.exception, [str(e) for e in app.exception]
    assert not app.error, [str(e.value) for e in app.error]
