import json
import os
from io import BytesIO
from tempfile import NamedTemporaryFile

import pandas as pd
import streamlit as st

from batch import evaluate_batch
from db import delete_all_answer_keys, delete_all_student_results, delete_answer_key, get_all_results, get_answer_key, get_answer_key_info, init_db, save_answer_key, save_student_result
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


def _student_input_key(name: str) -> str:
    return f"{name}_{_upload_generation('student_input_generation')}"


def _show_delete_set_dialog() -> None:
    set_name = st.session_state.get("pending_delete_set")
    if not set_name:
        return
    st.write(f"Delete the saved answer key for Set {set_name}? This cannot be undone.")
    confirm, cancel = st.columns(2)
    if confirm.button("Confirm", type="primary", key="confirm_delete_set"):
        if delete_answer_key(set_name):
            st.session_state["key_delete_success_message"] = f"Set {set_name} answer key deleted."
        st.session_state.pop("pending_delete_set", None)
        st.rerun()
    if cancel.button("Cancel", key="cancel_delete_set"):
        st.session_state.pop("pending_delete_set", None)
        st.rerun()


def _show_delete_all_dialog() -> None:
    saved_sets = st.session_state.get("pending_delete_all_sets", [])
    if not saved_sets:
        return
    set_list = ", ".join(saved_sets)
    st.write(f"Delete ALL saved answer keys for Sets {set_list}? This cannot be undone.")
    confirm, cancel = st.columns(2)
    if confirm.button("Confirm", type="primary", key="confirm_delete_all"):
        count = delete_all_answer_keys()
        st.session_state["key_delete_success_message"] = f"All answer keys deleted ({count} removed). Student results were not changed."
        st.session_state.pop("pending_delete_all_sets", None)
        st.rerun()
    if cancel.button("Cancel", key="cancel_delete_all"):
        st.session_state.pop("pending_delete_all_sets", None)
        st.rerun()


def _show_clear_results_dialog() -> None:
    if not st.session_state.get("pending_clear_results"):
        return
    st.write("Clear ALL saved student results? Answer keys will not be changed. This cannot be undone.")
    confirm, cancel = st.columns(2)
    if confirm.button("Confirm", type="primary", key="confirm_clear_results"):
        count = delete_all_student_results()
        st.session_state["results_clear_success_message"] = f"Cleared {count} student results. Answer keys were not changed."
        st.session_state.pop("pending_clear_results", None)
        st.rerun()
    if cancel.button("Cancel", key="cancel_clear_results"):
        st.session_state.pop("pending_clear_results", None)
        st.rerun()


if hasattr(st, "dialog"):
    _show_delete_set_dialog = st.dialog("Confirm answer-key deletion")(_show_delete_set_dialog)
    _show_delete_all_dialog = st.dialog("Confirm all answer-key deletion")(_show_delete_all_dialog)
    _show_clear_results_dialog = st.dialog("Confirm student-results deletion")(_show_clear_results_dialog)


def inject_styles() -> None:
    st.markdown("""
    <style>
    /* OMR Evaluate visual system: energetic ocean tones with readable status contrast. */
    :root { --omr-ink: #16324F; --omr-blue: #0B3954; --omr-teal: #087E8B; --omr-coral: #EF476F; --omr-gold: #F4A261; --omr-line: #9BC5D1; }
    .stApp { background: linear-gradient(135deg, #F7FAFC 0%, #EEF8F7 54%, #FFF7EF 100%); }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #073B4C 0%, #0B3954 58%, #087E8B 100%); }
    [data-testid="stSidebar"] * { color: #F5FAFC; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.22); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #DDECF0; }
    .omr-hero { padding: 1.2rem 1.45rem; border: 2px solid var(--omr-teal); border-radius: 14px; background: linear-gradient(110deg, #FFFFFF 0%, #E8F7F4 100%); box-shadow: 0 10px 26px rgba(8,126,139,.15); margin-bottom: 1.2rem; }
    .omr-hero h1 { color: var(--omr-blue); letter-spacing: 0; margin: 0; text-shadow: 1px 1px 0 #BEEBE4; }
    .omr-card { padding: 1rem 1.15rem; border: 2px solid var(--omr-line); border-radius: 10px; background: rgba(255,255,255,.94); box-shadow: 0 6px 18px rgba(11,57,84,.1); margin: .6rem 0 1rem; }
    .omr-table-header { padding: .7rem .85rem; border: 2px solid var(--omr-blue); border-radius: 9px 9px 0 0; color: white; background: var(--omr-blue); }
    .omr-table-row { padding: .35rem .25rem; border: 1px solid var(--omr-line); border-top: 0; background: rgba(255,255,255,.92); }
    .omr-table-row:last-of-type { border-radius: 0 0 9px 9px; }
    .omr-step { padding: .5rem 0; border-bottom: 1px solid rgba(255,255,255,.16); }
    .omr-step:last-child { border-bottom: 0; }
    .omr-status { display: flex; justify-content: space-between; padding: .35rem .55rem; margin: .2rem 0; border-radius: 6px; background: rgba(255,255,255,.09); }
    .omr-badge { display: inline-block; padding: .52rem 1rem; border-radius: 999px; font-size: 1.1rem; font-weight: 700; letter-spacing: .04em; }
    .omr-pass { color: #064E3B; background: #B7F7D8; border: 2px solid #16A36A; box-shadow: 0 3px 10px rgba(22,163,106,.2); }
    .omr-fail { color: #8F1025; background: #FFD0D9; border: 2px solid var(--omr-coral); box-shadow: 0 3px 10px rgba(239,71,111,.2); }
    .omr-score { font-size: 2.4rem; font-weight: 750; color: var(--omr-blue); line-height: 1.1; margin: .35rem 0 .7rem; }
    div.stButton > button { border-radius: 8px; border-width: 2px; font-weight: 650; }
    div.stButton > button[kind="primary"] { background: var(--omr-teal); border-color: var(--omr-teal); color: white; box-shadow: 0 5px 12px rgba(8,126,139,.25); }
    div.stButton > button[kind="primary"]:hover { background: var(--omr-coral); border-color: var(--omr-coral); transform: translateY(-1px); }
    div.stButton > button[kind="secondary"]:hover { color: var(--omr-blue); border-color: var(--omr-gold); background: #FFF4E7; }
    [data-testid="stProgressBar"] > div > div { background: linear-gradient(90deg, var(--omr-teal), var(--omr-coral)); }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## :material/assignment_turned_in: OMR Evaluate")
        st.caption("Digital answer-sheet control room")
        st.markdown("### How to use this app")
        st.markdown('<div class="omr-step"><strong>1</strong> &nbsp; Upload an answer key for each set</div><div class="omr-step"><strong>2</strong> &nbsp; Evaluate students one-by-one or in batch</div><div class="omr-step"><strong>3</strong> &nbsp; Download the results</div>', unsafe_allow_html=True)


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
    inject_styles()
    render_sidebar()
    st.markdown('<div class="omr-hero"><h1>OMR Evaluate</h1><p>Digital answer-sheet evaluation for exam sets A-D</p></div>', unsafe_allow_html=True)
    setup_tab, evaluate_tab, batch_tab, results_tab, debug_tab = st.tabs(["🔑 Setup keys", "✓ Evaluate student", "⇢ Batch evaluate", "▦ All results", "⚙ Calibration / debug"])

    with setup_tab:
        st.subheader("🔑 Master answer keys")
        st.caption("Upload one complete 50-question master answer key for each exam set. Saved keys unlock evaluation.")
        st.caption("Manage saved keys below. Deleting a key never deletes student results.")
        with st.container(border=True):
            headers = st.columns([1, 2, 2, 1])
            for header, label in zip(headers, ["Set", "Status", "Uploaded at", "Delete"]):
                header.markdown(f"**{label}**")
        saved_sets = []
        for set_name in SETS:
            key_info = get_answer_key_info(set_name)
            if key_info:
                saved_sets.append(set_name)
            with st.container(border=True):
                row = st.columns([1, 2, 2, 1])
                row[0].write(set_name)
                row[1].write("Saved" if key_info else "Not Saved")
                row[2].write(key_info["uploaded_at"] if key_info else "")
                if key_info:
                    if row[3].button("", key=f"delete_key_{set_name}", icon=":material/delete:", help=f"Delete Set {set_name} answer key"):
                        st.session_state["pending_delete_set"] = set_name
                        _show_delete_set_dialog()
        if saved_sets:
            if st.button("Delete All Answer Keys", key="delete_all_keys", icon=":material/delete_sweep:"):
                st.session_state["pending_delete_all_sets"] = saved_sets
                _show_delete_all_dialog()
            st.caption("This deletes answer keys only. Student results are preserved.")
        if st.session_state.get("key_delete_success_message"):
            st.success(st.session_state["key_delete_success_message"], icon=":material/check_circle:")
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
        st.info("Preferred: `Student_Name_RollNo_SetX.pdf` such as `Ananya_Sharma_007_SetA.pdf` extracts name, roll number, and set. Older: `Student_Name_SetX.pdf` such as `Ananya_Sharma_SetA.pdf` extracts name and set, leaving roll number blank. Files without a recognizable `_SetX` marker use the fallback dropdown.", icon=":material/info:")
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
            if st.button("Clear All Student Results", key="clear_all_student_results", icon=":material/delete_forever:"):
                st.session_state["pending_clear_results"] = True
                _show_clear_results_dialog()
        if st.session_state.get("results_clear_success_message"):
            st.success(st.session_state["results_clear_success_message"], icon=":material/check_circle:")

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