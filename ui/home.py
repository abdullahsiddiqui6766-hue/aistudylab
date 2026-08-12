import streamlit as st

from ui.styles import hero


def render():
    hero(
        "📚 StudyAI — AI Textbook Study Assistant",
        "Upload any textbook PDF and turn it into a personal tutor: ask questions, "
        "generate MCQs, build practice tests, and track your weak topics.",
    )

    ready = st.session_state.get("pdf_processed", False)

    if not ready:
        st.info("👉 Start by uploading your textbook in **📚 My Textbook**.")

    cols = st.columns(3)
    features = [
        ("💬 Ask My Textbook", "Ask any question and get answers grounded strictly in your uploaded book, with page references."),
        ("📝 Generate MCQs", "Pick a chapter, difficulty, and count — get instant MCQs with explanations."),
        ("❓ Additional Questions", "Short, long, or conceptual practice questions with answers kept separate."),
        ("🎯 Test Preparation", "Build a full multi-chapter test, take it, and submit for instant evaluation."),
        ("📊 Test Results", "See your score, a question-by-question review, and your weak topics to revise."),
        ("📖 Source-Aware", "Every answer and question is checked against your actual textbook content — never invented."),
    ]
    for i, (title, desc) in enumerate(features):
        with cols[i % 3]:
            st.markdown(
                f"""<div class="sa-feature"><b>{title}</b><p style="color:#6B7280;font-size:0.9rem;margin-top:0.4rem;">{desc}</p></div>""",
                unsafe_allow_html=True,
            )

    st.write("")
    if ready:
        st.success(
            f"✅ **{st.session_state.get('pdf_filename', 'Your textbook')}** is loaded "
            f"({st.session_state.get('page_count', 0)} pages, "
            f"{len(st.session_state.get('chapters', []))} chapters detected). "
            "Use the sidebar to jump into any feature."
        )
