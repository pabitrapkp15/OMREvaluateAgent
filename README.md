# OMR Evaluate

This Streamlit app evaluates digital PDF answer sheets for four exam sets (A-D), with 50 questions, four options per question, and a passing cutoff of 40/50.

## Run

From this folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The SQLite database is created at `data/omr.db` on first run. Run the tests with:

```powershell
python -m pytest
```

To manually reset production data from PowerShell, run `python scripts/reset_db.py` for a dry run showing current counts. Nothing is deleted without the explicit command `python scripts/reset_db.py --confirm`. The app also provides the same two-step action inside the **Danger zone** expander at the bottom of the sidebar; check the acknowledgment box before the reset button becomes active. There is no automatic reset on startup.

Tests use an isolated per-process SQLite path via `OMR_DB_PATH`; they never read or write the production `data/omr.db`. To inspect the unexpected synthetic Set C key without changing production data, run `python scripts/cleanup_synthetic_set_c.py`. It is a dry run by default and requires `--confirm` to delete Set C; it refuses to delete anything unless the full mapping matches the known generated key.

The `streamlit` executable is installed in Python's Scripts directory, which may not be included in PowerShell's PATH. Use `python -m streamlit run app.py` from this folder; it works without any PATH configuration. VS Code also provides a **Run OMR Evaluate app** task using the same command.

The **Batch Evaluate** tab accepts multiple PDFs. The preferred filename convention is `Student_Name_RollNo_SetX.pdf`, for example `Ananya_Sharma_007_SetA.pdf`; this extracts student name `Ananya Sharma`, roll number `007`, and Set A. The older `Student_Name_SetX.pdf` format remains accepted with a blank roll number. Set markers and numeric roll segments are detected independently; missing set markers use the fallback dropdown, while missing roll numbers remain blank. Missing keys and incomplete PDFs are reported as failed rows while the remaining files continue processing.

The additive roll-numbered calibration fixtures can be regenerated with `python tests/generate_roll_samples.py`; this preserves existing samples and merges the 20 new expected outcomes into `tests/samples/expected_results.json`.

## PDF assumptions

The parser first checks AcroForm fields using `pypdf`. Field names must end in a question number, such as `q1`, `question_1`, or `question-1`, and values must be A, B, C, or D. If 50 clean numbered fields are not found, it extracts text with `pdfplumber` and recognizes typed patterns such as `12. C`, `Q12: C`, `12) C`, and `12 - C`, regardless of case and extra whitespace.

`extract_answers` returns `(answers, warnings)`. The app refuses to save or evaluate fewer than 50 parsed answers. Duplicate, missing, invalid, and out-of-range items are included in warnings. Extra student question numbers are reported as evaluation anomalies and do not add points.

## Calibration before trust

1. Start the app and open **Calibration/Debug**.
2. Upload one real master-key PDF and one real student PDF separately.
3. Confirm the raw extracted text contains recognizable question/answer pairs, or confirm the raw form-field dump contains numbered fields and A-D values.
4. If fewer than 50 answers parse, adjust the source PDF format or parser patterns before saving any key.
5. Once a sample parses cleanly, upload each master key under **Setup Answer Keys**, then evaluate a known student sample and manually verify its score.

The app stores uploaded metadata and results locally; it does not perform OCR because the stated inputs are digital PDFs with text or AcroForm data.
