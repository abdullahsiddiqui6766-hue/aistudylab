import streamlit as st

from services.test_engine import build_test, score_test


def _reset_test_state():
    for key in ["test_questions", "test_answers", "test_submitted", "test_idx", "test_result"]:
        st.session_state.pop(key, None)


def render():
    st.header("🎯 Test Preparation Mode")

    if not st.session_state.get("pdf_processed"):
        st.warning("Please upload a textbook first in **📚 My Textbook**.")
        return

    chapters = st.session_state.get("chapters", [])
    has_active_test = bool(st.session_state.get("test_questions")) and not st.session_state.get(
        "test_submitted"
    )

    if not has_active_test:
        st.subheader("Set up your test")
        if not chapters:
            st.info("No chapters were detected — the test will be built from the whole textbook.")

        with st.form("test_setup_form"):
            selected_chapters = st.multiselect(
                "Chapters to include", chapters, default=chapters[:1] if chapters else []
            )
            col1, col2 = st.columns(2)
            with col1:
                num_questions = st.number_input("Number of questions", min_value=2, max_value=40, value=10)
            with col2:
                difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
            start = st.form_submit_button("Start Test", use_container_width=True)

        if start:
            chapters_for_test = selected_chapters if selected_chapters else (chapters[:1] if chapters else [None])
            with st.spinner("Building your test from the textbook..."):
                questions, warnings = build_test(
                    st.session_state["pdf_hash"], chapters_for_test, int(num_questions), difficulty
                )
            for w in warnings:
                st.warning(w)

            if questions:
                _reset_test_state()
                st.session_state["test_questions"] = questions
                st.session_state["test_answers"] = {}
                st.session_state["test_submitted"] = False
                st.session_state["test_idx"] = 0
                st.rerun()
        return

    # --- Active test in progress ---
    questions = st.session_state["test_questions"]
    total = len(questions)
    idx = st.session_state.get("test_idx", 0)
    idx = max(0, min(idx, total - 1))
    answers = st.session_state.setdefault("test_answers", {})

    st.progress((idx + 1) / total, text=f"Question {idx + 1} of {total}")

    q = questions[idx]
    st.markdown(f"### {q.question}")

    current_answer = answers.get(idx)
    choice = st.radio(
        "Select your answer:",
        q.options,
        index=q.options.index(current_answer) if current_answer in q.options else None,
        key=f"test_q_{idx}",
    )
    if choice is not None:
        answers[idx] = choice

    nav1, nav2, nav3 = st.columns([1, 1, 1])
    with nav1:
        if st.button("⬅️ Previous", disabled=idx == 0, use_container_width=True):
            st.session_state["test_idx"] = idx - 1
            st.rerun()
    with nav2:
        if st.button("Next ➡️", disabled=idx == total - 1, use_container_width=True):
            st.session_state["test_idx"] = idx + 1
            st.rerun()
    with nav3:
        if st.button("✅ Submit Test", type="primary", use_container_width=True):
            result = score_test(questions, answers)
            st.session_state["test_result"] = result
            st.session_state["test_submitted"] = True
            st.rerun()

    answered = len(answers)
    st.caption(f"Answered {answered} of {total} questions. You can submit anytime — unanswered questions count as incorrect.")

    with st.expander("Jump to question"):
        jump_cols = st.columns(10)
        for i in range(total):
            with jump_cols[i % 10]:
                label = f"{i + 1}" + ("✓" if i in answers else "")
                if st.button(label, key=f"jump_{i}"):
                    st.session_state["test_idx"] = i
                    st.rerun()

    if st.session_state.get("test_submitted"):
        st.success("Test submitted! Go to **📊 Test Results** to see your score and review.")
