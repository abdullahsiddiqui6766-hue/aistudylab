import streamlit as st

from utils.helpers import format_source


def render():
    st.header("📊 Test Results")

    result = st.session_state.get("test_result")
    if not result or not st.session_state.get("test_submitted"):
        st.info("No submitted test yet. Take a test in **🎯 Test Preparation** first.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{result.score} / {result.total}")
    c2.metric("Percentage", f"{result.percentage}%")
    c3.metric("Incorrect", result.total - result.score)

    if result.weak_topics:
        st.subheader("📌 Areas to revise")
        st.markdown("\n".join(f"- {t}" for t in result.weak_topics))
    else:
        st.success("No weak topics identified — great job! 🎉")

    st.divider()
    st.subheader("Question-by-question review")

    for i, item in enumerate(result.review, 1):
        with st.container(border=True):
            status = "✅ Correct" if item["is_correct"] else "❌ Incorrect"
            st.markdown(f"**Q{i}. {item['question']}**  \n{status}")
            for opt in item["options"]:
                if opt == item["correct_answer"]:
                    st.markdown(f"- ✅ **{opt}** (correct answer)")
                elif opt == item["selected"]:
                    st.markdown(f"- ❌ ~~{opt}~~ (your answer)")
                else:
                    st.markdown(f"- {opt}")
            if item["selected"] is None:
                st.caption("You did not answer this question.")
            st.write(f"**Explanation:** {item['explanation']}")
            src = format_source(item.get("chapter"), item.get("page"))
            if src != "Source not available in this textbook":
                st.caption(f"📌 {src}")

    if st.button("🔁 Start a new test"):
        for key in ["test_questions", "test_answers", "test_submitted", "test_idx", "test_result"]:
            st.session_state.pop(key, None)
        st.rerun()
