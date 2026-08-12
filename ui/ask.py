import streamlit as st

from services.rag import ask_textbook
from utils.helpers import format_source


def render():
    st.header("💬 Ask My Textbook")

    if not st.session_state.get("pdf_processed"):
        st.warning("Please upload a textbook first in **📚 My Textbook**.")
        return

    chapters = ["All chapters"] + st.session_state.get("chapters", [])
    chapter_choice = st.selectbox("Limit search to a chapter (optional)", chapters)
    chapter_filter = None if chapter_choice == "All chapters" else chapter_choice

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for turn in st.session_state["chat_history"]:
        with st.chat_message("user"):
            st.write(turn["question"])
        with st.chat_message("assistant"):
            st.write(turn["answer"])
            if turn["sources"]:
                src_lines = "  \n".join(
                    f"📌 {format_source(s['chapter'], s['page'])}" for s in turn["sources"]
                )
                st.markdown(f'<div class="sa-source">{src_lines}</div>', unsafe_allow_html=True)

    question = st.chat_input("Ask anything from your textbook...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Searching your textbook..."):
                result = ask_textbook(
                    st.session_state["pdf_hash"], question, chapter_filter=chapter_filter
                )
            st.write(result.answer)
            if result.sources:
                src_lines = "  \n".join(
                    f"📌 {format_source(s['chapter'], s['page'])}" for s in result.sources
                )
                st.markdown(f'<div class="sa-source">{src_lines}</div>', unsafe_allow_html=True)

        st.session_state["chat_history"].append(
            {"question": question, "answer": result.answer, "sources": result.sources}
        )
