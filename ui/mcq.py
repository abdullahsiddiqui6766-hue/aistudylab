import streamlit as st

from services import vector_store
from services.mcq_generator import generate_mcqs
from utils.helpers import format_source


def render():
    st.header("📝 Generate MCQs")

    if not st.session_state.get("pdf_processed"):
        st.warning("Please upload a textbook first in **📚 My Textbook**.")
        return

    chapters = st.session_state.get("chapters", [])
    if not chapters:
        st.info("No chapters were detected — MCQs will be generated from the whole textbook.")
        chapters = [None]

    with st.form("mcq_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            chapter = st.selectbox("Chapter", chapters if chapters else ["Whole book"])
        with col2:
            num_mcqs = st.number_input("Number of MCQs", min_value=1, max_value=25, value=5)
        with col3:
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
        submitted = st.form_submit_button("Generate MCQs", use_container_width=True)

    if submitted:
        chapter_val = chapter if chapter in chapters else None
        with st.spinner("Generating MCQs from your textbook..."):
            chunks = vector_store.get_all_chunks_for_chapter(
                st.session_state["pdf_hash"], chapter_val, limit=40
            )
            items, warnings = generate_mcqs(chunks, int(num_mcqs), difficulty, chapter_label=chapter_val)

        st.session_state["last_mcqs"] = items

        for w in warnings:
            st.warning(w)

        if items:
            st.success(f"Generated {len(items)} MCQs.")

    items = st.session_state.get("last_mcqs", [])
    if items:
        for i, item in enumerate(items, 1):
            with st.container(border=True):
                st.markdown(f"**Q{i}. {item.question}**")
                for opt in item.options:
                    st.write(f"- {opt}")
                with st.expander("Show answer & explanation"):
                    st.markdown(f"✅ **Correct answer:** {item.normalized_correct_answer()}")
                    st.write(item.explanation)
                    src = format_source(item.chapter, item.page)
                    if src != "Source not available in this textbook":
                        st.caption(f"📌 {src}")
