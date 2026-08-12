"""Shared CSS injected once at app start for a clean, premium student-facing look."""

import streamlit as st

CUSTOM_CSS = """
<style>
:root {
    --sa-primary: #4F46E5;
    --sa-primary-light: #EEF2FF;
    --sa-success: #16A34A;
    --sa-danger: #DC2626;
    --sa-bg-card: #FFFFFF;
}

.sa-hero {
    background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
    padding: 2.2rem 2rem;
    border-radius: 18px;
    color: white;
    margin-bottom: 1.5rem;
}
.sa-hero h1 { margin: 0 0 0.4rem 0; font-size: 2rem; }
.sa-hero p { margin: 0; opacity: 0.92; font-size: 1.02rem; }

.sa-card {
    background: var(--sa-bg-card);
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    padding: 1.3rem 1.4rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.sa-badge {
    display: inline-block;
    background: var(--sa-primary-light);
    color: var(--sa-primary);
    padding: 0.15rem 0.65rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-right: 0.4rem;
}

.sa-source {
    font-size: 0.82rem;
    color: #6B7280;
    border-left: 3px solid var(--sa-primary);
    padding-left: 0.6rem;
    margin-top: 0.6rem;
}

.sa-correct { color: var(--sa-success); font-weight: 600; }
.sa-incorrect { color: var(--sa-danger); font-weight: 600; }

.sa-feature-grid .sa-feature {
    background: white;
    border: 1px solid #E5E7EB;
    border-radius: 14px;
    padding: 1.1rem;
    height: 100%;
}
</style>
"""


def inject_css():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str):
    st.markdown(
        f"""<div class="sa-hero"><h1>{title}</h1><p>{subtitle}</p></div>""",
        unsafe_allow_html=True,
    )
