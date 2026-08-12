"""
app.py — StudyAI entrypoint.

This file only wires up navigation + session-state defaults. All feature
logic lives in services/, and all page rendering lives in ui/.
"""

import streamlit as st

from ui import additional, ask, home, mcq, test_prep, test_results, textbook
from ui.styles import inject_css

st.set_page_config(
    page_title="StudyAI — AI Textbook Study Assistant",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

DEFAULTS = {
    "pdf_processed": False,
    "pdf_hash": None,
    "pdf_filename": None,
    "chapters": [],
    "page_count": 0,
    "chunk_count": 0,
    "ocr_pages_used": 0,
    "chat_history": [],
}
for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

PAGES = {
    "🏠 Home": home,
    "📚 My Textbook": textbook,
    "💬 Ask My Textbook": ask,
    "📝 Generate MCQs": mcq,
    "❓ Additional Questions": additional,
    "🎯 Test Preparation": test_prep,
    "📊 Test Results": test_results,
}

with st.sidebar:
    st.markdown("## 📚 StudyAI")
    st.caption("AI Textbook Study Assistant")
    choice = st.radio("Navigate", list(PAGES.keys()), label_visibility="collapsed")

    st.divider()
    if st.session_state.get("pdf_processed"):
        st.success(f"📖 {st.session_state.get('pdf_filename')}")
    else:
        st.info("No textbook uploaded yet")

PAGES[choice].render()
