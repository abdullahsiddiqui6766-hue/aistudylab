import streamlit as st

from services import vector_store
from services.question_generator import generate_additional_questions
from utils.helpers import format_source


def render():
    st.header("❓ Additional Questions")

    if not st.session_state.get("pdf_processed"):
        st.warning("Please upload a textbook first in **📚 My Textbook**.")
        return

    chapters = st.session_state.get("chapters", [])
    if not chapters:
        st.info("No chapters were detected — questions will be generated from the whole textbook.")
        chapters = [None]

    with st.form("additional_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            chapter = st.selectbox("Chapter", chapters)
        with col2:
            q_type = st.selectbox("Question type", ["Short Questions", "Long Questions", "Conceptual Questions"])
        with col3:
            num_q = st.number_input("Number of questions", min_value=1, max_value=15, value=5)
        submitted = st.form_submit_button("Generate Questions", use_container_width=True)

    if submitted:
        chapter_val = chapter if chapter in chapters else None
        with st.spinner("Generating questions..."):
            chunks = vector_store.get_all_chunks_for_chapter(
                st.session_state["pdf_hash"], chapter_val, limit=40
            )
            items, warnings = generate_additional_questions(
                chunks, q_type, int(num_q), chapter_label=chapter_val
            )
        st.session_state["last_additional"] = items
        for w in warnings:
            st.warning(w)
        if items:
            st.success(f"Generated {len(items)} questions.")

    items = st.session_state.get("last_additional", [])
    if items:
        st.caption("Try answering each question yourself before revealing the model answer.")
        for i, item in enumerate(items, 1):
            with st.container(border=True):
                st.markdown(f"**Q{i}. {item.question}**")
                with st.expander("Reveal answer"):
                    st.write(item.answer)
                    src = format_source(item.chapter, item.page)
                    if src != "Source not available in this textbook":
                        st.caption(f"📌 {src}")
