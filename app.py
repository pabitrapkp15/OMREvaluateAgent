import json
import os
from io import BytesIO
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from batch import evaluate_batch
from db import clear_all_data, get_all_results, get_answer_key, init_db, save_answer_key, save_student_result
from evaluator import evaluate
from models import AnswerKey, StudentResult
from pdf_parser import debug_extract, extract_answers

SETS = ["A", "B", "C", "D"]
EXPECTED_QUESTIONS = set(range(1, 51))


def is_complete_master_key(answers: dict[int, str]) -> bool:
    return set(answers) == EXPECTED_QUESTIONS


def _upload_generation(name: str) -> int:
    if name not in st.session_state:
        st.session_state[name] = 0
    return st.session_state[name]


def _reset_checkbox_key() -> str:
    return f"reset_acknowledged_{_upload_generation('reset_acknowledged_generation')}"


def _student_input_key(name: str) -> str:
    return f"{name}_{_upload_generation('student_input_generation')}"


def inject_styles() -> None:
    st.markdown("""
    <style>
    /* OMR Evaluate visual system: ocean blue structure, teal action, clear result states. */
    :root { --omr-ink: #16324F; --omr-blue: #0B3954; --omr-teal: #087E8B; --omr-line: #C9D8E0; }
    .stApp { background: #F7FAFC; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #0B3954 0%, #123F59 58%, #0E5360 100%); }
    [data-testid="stSidebar"] * { color: #F5FAFC; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.22); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #DDECF0; }
    .omr-hero { padding: 1.2rem 1.45rem; border: 1px solid var(--omr-line); border-radius: 14px; background: white; box-shadow: 0 8px 24px rgba(11,57,84,.08); margin-bottom: 1.2rem; }
    .omr-hero h1 { color: var(--omr-blue); letter-spacing: 0; margin: 0; }
    .omr-card { padding: 1rem 1.15rem; border: 1px solid var(--omr-line); border-radius: 10px; background: white; box-shadow: 0 4px 14px rgba(11,57,84,.06); margin: .6rem 0 1rem; }
    .omr-step { padding: .5rem 0; border-bottom: 1px solid rgba(255,255,255,.16); }
    .omr-step:last-child { border-bottom: 0; }
    .omr-status { display: flex; justify-content: space-between; padding: .35rem .55rem; margin: .2rem 0; border-radius: 6px; background: rgba(255,255,255,.09); }
    .omr-badge { display: inline-block; padding: .52rem 1rem; border-radius: 999px; font-size: 1.1rem; font-weight: 700; letter-spacing: .04em; }
    .omr-pass { color: #0B5D3B; background: #DDF7E9; border: 1px solid #9ADBB8; }
    .omr-fail { color: #9F1C16; background: #FDE4E2; border: 1px solid #F1AAA5; }
    .omr-score { font-size: 2.4rem; font-weight: 750; color: var(--omr-blue); line-height: 1.1; margin: .35rem 0 .7rem; }
    div.stButton > button[kind="primary"] { background: var(--omr-teal); border-color: var(--omr-teal); color: white; box-shadow: 0 4px 10px rgba(8,126,139,.2); }
    div.stButton > button[kind="primary"]:hover { background: var(--omr-blue); border-color: var(--omr-blue); }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar(saved_sets: list[str]) -> None:
    with st.sidebar:
        st.markdown("## :material/assignment_turned_in: OMR Evaluate")
        st.caption("Digital answer-sheet control room")
        st.markdown("### How to use this app")
        st.markdown('<div class="omr-step"><strong>1</strong> &nbsp; Upload an answer key for each set</div><div class="omr-step"><strong>2</strong> &nbsp; Evaluate students one-by-one or in batch</div><div class="omr-step"><strong>3</strong> &nbsp; Download the results</div>', unsafe_allow_html=True)
        st.markdown("### Key setup")
        for set_name in SETS:
            icon = ":material/check_circle:" if set_name in saved_sets else ":material/radio_button_unchecked:"
            label = "Saved" if set_name in saved_sets else "Missing"
            st.markdown(f'<div class="omr-status"><span>Set {set_name}</span><span>{icon} {label}</span></div>', unsafe_allow_html=True)
        st.caption(f"{len(saved_sets)}/4 answer keys ready")
        with st.expander("Danger zone", icon=":material/warning:"):
            st.caption("Resetting permanently deletes every saved answer key and student result.")
            reset_message = st.session_state.get("reset_success_message")
            if reset_message:
                st.success(reset_message, icon=":material/check_circle:")
            acknowledged = st.checkbox("I understand this deletes all saved keys and results", key=_reset_checkbox_key())
            if st.button("Reset everything", type="secondary", disabled=not acknowledged, key="reset_everything", icon=":material/delete_forever:"):
                key_count, result_count = clear_all_data()
                st.session_state["reset_success_message"] = f"Cleared {key_count} answer keys and {result_count} student results."
                st.session_state["reset_acknowledged_generation"] += 1
                st.rerun()


def render_result_badge(passed: bool) -> None:
    label = "PASS" if passed else "FAIL"
    style = "omr-pass" if passed else "omr-fail"
    icon = "✓" if passed else "!"
    st.markdown(f'<div class="omr-badge {style}">{icon} {label}</div>', unsafe_allow_html=True)


def render_student_result(result: dict) -> None:
    score = result.get("score", result["total_score"])
    st.markdown(f'<div class="omr-card"><div class="omr-score">{score}/50</div>', unsafe_allow_html=True)
    render_result_badge(result["passed"])
    st.progress(score / 50, text=f"{score} of 50 points")
    st.markdown("</div>", unsafe_allow_html=True)
    wrong = [item for item in result["questions"] if not item["correct"]]
    st.dataframe(pd.DataFrame(wrong, columns=["question_number", "student_answer", "correct_answer", "correct"]), hide_index=True, width="stretch")
    if result.get("anomalies"):
        st.warning("; ".join(result["anomalies"]))
    if result.get("partial_submission"):
        st.warning(f"Score: {score}/50 - marked FAIL: submission incomplete. Only {result.get('detected_answers', 0)}/50 answers were detected; remaining questions scored as blank/incorrect.", icon=":material/warning:")


def _write_uploaded_pdf(uploaded_file) -> str:
    temporary_file = NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        temporary_file.write(uploaded_file.getbuffer())
        return temporary_file.name
    finally:
        temporary_file.close()


def _remove_temp_pdf(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def parse_uploaded(uploaded_file):
    temporary_path = _write_uploaded_pdf(uploaded_file)
    try:
        return extract_answers(temporary_path)
    finally:
        _remove_temp_pdf(temporary_path)


def debug_uploaded(uploaded_file):
    temporary_path = _write_uploaded_pdf(uploaded_file)
    try:
        return debug_extract(temporary_path)
    finally:
        _remove_temp_pdf(temporary_path)


def main() -> None:
    init_db()
    st.set_page_config(page_title="OMR Evaluate", page_icon=":material/assignment_turned_in:", layout="wide")
    saved_sets = [item for item in SETS if get_answer_key(item)]
    inject_styles()
    render_sidebar(saved_sets)
    st.markdown('<div class="omr-hero"><h1>OMR Evaluate</h1><p>Digital answer-sheet evaluation for exam sets A-D</p></div>', unsafe_allow_html=True)
    setup_tab, evaluate_tab, batch_tab, results_tab, debug_tab = st.tabs(["🔑 Setup keys", "✓ Evaluate student", "⇢ Batch evaluate", "▦ All results", "⚙ Calibration / debug"])

    with setup_tab:
        st.subheader("🔑 Master answer keys")
        st.caption("Upload one complete 50-question master answer key for each exam set. Saved keys unlock evaluation.")
        status = pd.DataFrame({"Set": SETS, "Status": ["Saved" if get_answer_key(item) else "Missing" for item in SETS]})
        st.dataframe(status, hide_index=True, width="stretch")
        selected_set = st.selectbox("Answer-key set", SETS, key="key_set")
        previous_set = st.session_state.get("key_upload_selected_set")
        if previous_set is not None and previous_set != selected_set:
            st.session_state.pop("save_success_set", None)
            st.session_state.pop("save_success_message", None)
        st.session_state["key_upload_selected_set"] = selected_set
        key_file = st.file_uploader("Upload master answer-key PDF", type="pdf", key=f"key_upload_{selected_set}_{_upload_generation('key_upload_generation')}")
        if key_file and st.session_state.get("save_success_set") == selected_set:
            st.session_state.pop("save_success_set", None)
            st.session_state.pop("save_success_message", None)
        if st.session_state.get("save_success_set") == selected_set:
            st.success(st.session_state["save_success_message"], icon=":material/check_circle:")
        if st.button("Save key", type="primary", disabled=not key_file, icon=":material/save:"):
            if not key_file:
                st.error("Upload a PDF before saving the key.")
            else:
                answers, warnings = parse_uploaded(key_file)
                if not is_complete_master_key(answers):
                    st.error(f"Only {len(answers)}/50 answers were parsed. Key was not saved.")
                    st.warning("; ".join(warnings))
                else:
                    key = AnswerKey(selected_set, answers)
                    save_answer_key(key.set_name, key.answers, key.uploaded_at)
                    st.session_state["save_success_set"] = selected_set
                    st.session_state["save_success_message"] = f"Set {selected_set} answer key saved."
                    st.session_state["key_upload_generation"] += 1
                    st.rerun()
                    if warnings:
                        st.warning("; ".join(warnings))

    with evaluate_tab:
        available_sets = [item for item in SETS if get_answer_key(item)]
        st.subheader("✓ Evaluate one student")
        st.caption("Choose a configured set, identify the student, and upload one answer-sheet PDF.")
        student_name = st.text_input("Student name", key=_student_input_key("student_name"))
        roll_no = st.text_input("Roll number", key=_student_input_key("roll_no"))
        chosen_set = st.selectbox("Exam set", available_sets or SETS, disabled=not available_sets, key="student_set")
        if not available_sets:
            st.warning("Upload an answer key for Set A first in the Setup keys tab.", icon=":material/warning:")
        elif not get_answer_key(chosen_set):
            st.warning(f"Upload an answer key for Set {chosen_set} first in the Setup keys tab.", icon=":material/warning:")
        student_file = st.file_uploader("Upload student answer PDF", type="pdf", key=_student_input_key(f"student_upload_{chosen_set}"))
        if st.button("Evaluate", type="primary"):
            if not available_sets:
                st.error("Save at least one answer key first.")
            elif not student_name.strip() or not student_file:
                st.error("Student name and a PDF are required. Roll number is optional; blank roll numbers are saved separately.")
            else:
                answers, warnings = parse_uploaded(student_file)
                if not answers:
                    st.error("No answers could be extracted from this PDF. Nothing was submitted.")
                    if warnings:
                        st.warning("; ".join(warnings))
                else:
                    outcome = evaluate(answers, get_answer_key(chosen_set))
                    comment = outcome["comment"]
                    result = StudentResult(student_name.strip(), roll_no.strip(), chosen_set, answers, outcome["total_score"], passed=outcome["passed"], comment=comment)
                    save_student_result(result)
                    st.session_state["last_student_result"] = {
                        "student_name": result.student_name,
                        "set_name": result.set_name,
                        "outcome": {**outcome, "score": result.score, "comment": comment, "detected_answers": len(answers)},
                    }
        last_result = st.session_state.get("last_student_result")
        if last_result:
            st.caption(f"Last evaluated: {last_result['student_name']} · Set {last_result['set_name']}")
            render_student_result(last_result["outcome"])
            if st.button("Reset for next student", type="secondary", icon=":material/person_add:"):
                st.session_state.pop("last_student_result", None)
                st.session_state["student_input_generation"] += 1
                st.rerun()

    with batch_tab:
        st.subheader("⇢ Evaluate multiple students")
        st.info("Name files like `Student_Name_SetA.pdf` to detect the set automatically. Files without `_SetX` use the fallback dropdown.", icon=":material/info:")
        batch_set = st.selectbox("Fallback exam set", SETS, key="batch_set")
        batch_files = st.file_uploader("Upload student answer PDFs", type="pdf", accept_multiple_files=True, key=f"batch_upload_{batch_set}_{_upload_generation('batch_upload_generation')}")
        if st.button("Evaluate batch", type="primary"):
            if not batch_files:
                st.error("Upload at least one student PDF.")
            else:
                temporary_paths = []
                try:
                    file_pairs = []
                    for uploaded_file in batch_files:
                        temporary_path = _write_uploaded_pdf(uploaded_file)
                        temporary_paths.append(temporary_path)
                        file_pairs.append((uploaded_file.name, temporary_path))
                    rows = evaluate_batch(file_pairs, batch_set, {item: get_answer_key(item) for item in SETS}, extract_answers, save_student_result)
                finally:
                    for temporary_path in temporary_paths:
                        _remove_temp_pdf(temporary_path)
                batch_results = pd.DataFrame(rows)
                st.dataframe(batch_results, hide_index=True, width="stretch")
                excel_buffer = BytesIO()
                batch_results.to_excel(excel_buffer, index=False, engine="openpyxl")
                st.download_button("Download batch results as Excel", excel_buffer.getvalue(), "omr-batch-results.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="batch_download")

    with results_tab:
        st.subheader("▦ Evaluation history")
        st.caption("Review every saved evaluation and export the full history as an Excel workbook.")
        results = get_all_results()
        if results.empty:
            st.info("No results yet. Evaluate a student to start building your results history.", icon=":material/inbox:")
        else:
            st.dataframe(results, hide_index=True, width="stretch")
            excel_buffer = BytesIO()
            results.to_excel(excel_buffer, index=False, engine="openpyxl")
            st.download_button("Download as Excel", excel_buffer.getvalue(), "omr-results.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/download:")

    with debug_tab:
        st.subheader("⚙ Verify a real PDF before evaluation")
        st.caption("Inspect extracted text and form fields here before trusting a new PDF format with student data.")
        debug_file = st.file_uploader("Upload any sample PDF", type="pdf", key="debug_file")
        if debug_file:
            debug = debug_uploaded(debug_file)
            st.text_area("Raw extracted text", debug["raw_text"], height=300)
            st.code(json.dumps(debug["raw_form_fields"], indent=2, default=str), language="json")
        else:
            st.info("No PDF loaded. Upload a sample to inspect its extracted content.", icon=":material/search:")


if __name__ == "__main__":
    main()