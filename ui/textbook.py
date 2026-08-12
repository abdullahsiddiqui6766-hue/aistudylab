import streamlit as st

from services import vector_store
from services.pdf_processor import PDFProcessingError, process_pdf
from utils.helpers import hash_bytes


def render():
    st.header("📚 My Textbook")
    st.caption(
        "Upload any textbook PDF — text-based or scanned. Scanned/image-only pages "
        "are automatically detected and read using OCR. It will be processed once "
        "and reused for every feature."
    )

    uploaded = st.file_uploader("Upload textbook PDF", type=["pdf"])

    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        pdf_hash = hash_bytes(file_bytes)

        already_done = st.session_state.get("pdf_hash") == pdf_hash and st.session_state.get("pdf_processed")

        if already_done:
            st.success(f"✅ **{uploaded.name}** is already processed and ready to use.")
        else:
            status_placeholder = st.empty()
            progress_placeholder = st.empty()
            status_placeholder.info("Extracting text and detecting chapters...")

            def progress_cb(done: int, total: int, page_number: int):
                progress_placeholder.progress(
                    done / total,
                    text=f"Running OCR on scanned page {page_number} ({done}/{total})...",
                )

            try:
                # Normal PyMuPDF extraction runs first; OCR only kicks in as a
                # fallback for pages with little/no extractable text, with a
                # progress bar shown just for that phase (it's the slow part).
                result = process_pdf(file_bytes, progress_callback=progress_cb)
                progress_placeholder.empty()
                chapters_titles = [c.title for c in result.chapters]

                if not vector_store.collection_exists(pdf_hash):
                    status_placeholder.info("Building the search index (embeddings)...")
                    vector_store.build_collection(pdf_hash, result.chunks)

                status_placeholder.empty()

                st.session_state["pdf_hash"] = pdf_hash
                st.session_state["pdf_filename"] = uploaded.name
                st.session_state["pdf_processed"] = True
                st.session_state["chapters"] = chapters_titles
                st.session_state["page_count"] = result.page_count
                st.session_state["chunk_count"] = len(result.chunks)
                st.session_state["ocr_pages_used"] = result.ocr_pages_used

                for w in result.warnings:
                    st.warning(w)

                ocr_note = (
                    f" ({result.ocr_pages_used} page(s) read via OCR)"
                    if result.ocr_pages_used
                    else ""
                )
                st.success(
                    f"✅ Processed **{uploaded.name}** — {result.page_count} pages, "
                    f"{len(result.chunks)} chunks indexed{ocr_note}."
                )
            except PDFProcessingError as exc:
                progress_placeholder.empty()
                status_placeholder.empty()
                st.error(f"❌ {exc}")
            except Exception as exc:
                progress_placeholder.empty()
                status_placeholder.empty()
                st.error(f"❌ Something went wrong while processing this PDF: {exc}")

    st.divider()

    if st.session_state.get("pdf_processed"):
        st.subheader("📖 Detected Chapters")
        chapters = st.session_state.get("chapters", [])
        if chapters:
            for ch in chapters:
                st.markdown(f"- {ch}")
        else:
            st.warning(
                "No clear chapter headings were detected in this PDF. You can still "
                "use Ask My Textbook, but chapter-based features (MCQs, Additional "
                "Questions, Test Prep) will use the whole book as one 'chapter' where needed."
            )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pages", st.session_state.get("page_count", 0))
        c2.metric("Chapters detected", len(chapters))
        c3.metric("Text chunks indexed", st.session_state.get("chunk_count", 0))
        c4.metric("Pages read via OCR", st.session_state.get("ocr_pages_used", 0))
    else:
        st.info("No textbook uploaded yet.")

