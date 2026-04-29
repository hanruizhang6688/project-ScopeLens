from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from src.evaluator import DEFAULT_TEST_SET, run_evaluation
from src.feature_extractor import extract_features, features_as_text
from src.policy_engine import triage_submission

APP_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="ScopeLens",
    page_icon="🔎",
    layout="wide",
)

st.title("ScopeLens: Editorial Scope Triage Memo Generator")
st.caption(
    "Advisory first-pass scope triage for thermal-radiation manuscript submissions."
)

with st.sidebar:
    st.header("Mode")
    mode_label = st.selectbox(
        "Triage mode",
        [
            "ScopeLens policy engine (no API key)",
            "ScopeLens structured LLM (requires OPENAI_API_KEY)",
            "Keyword baseline",
        ],
    )
    mode_map = {
        "ScopeLens policy engine (no API key)": "offline_policy",
        "ScopeLens structured LLM (requires OPENAI_API_KEY)": "llm",
        "Keyword baseline": "baseline",
    }
    mode = mode_map[mode_label]
    model = st.text_input("OpenAI model (optional)", value=os.getenv("SCOPELENS_MODEL", "gpt-4o-mini"))

    st.divider()
    st.write("Governance boundary")
    st.info(
        "The tool is advisory only. It must not make automated desk-reject, accept, or reviewer-assignment decisions."
    )


def load_cases() -> pd.DataFrame:
    return pd.read_csv(DEFAULT_TEST_SET)


def display_output(output):
    col1, col2, col3 = st.columns(3)
    col1.metric("Decision label", output.decision_label)
    col2.metric("Confidence", output.confidence)
    col3.metric("Human action", output.recommended_human_action)

    st.subheader("Editor memo")
    st.write(output.editor_memo)

    st.subheader("Reasoning summary")
    st.write(output.reasoning_summary)

    st.subheader("Supporting evidence")
    if output.supporting_evidence:
        st.dataframe(
            pd.DataFrame([ev.model_dump() for ev in output.supporting_evidence]),
            use_container_width=True,
        )
    else:
        st.warning("No supporting evidence returned.")

    st.subheader("Uncertainty / failure flags")
    if output.uncertainty_flags:
        for flag in output.uncertainty_flags:
            st.write(f"- {flag}")
    else:
        st.write("No specific uncertainty flags returned.")

    if output.should_not_automate:
        st.info("Automation boundary enforced: human editor review is required.")
    else:
        st.error("Automation boundary violation: output did not preserve advisory-only status.")


tab1, tab2 = st.tabs([
    "Single triage",
    "Built-in evaluation",
])

with tab1:
    st.header("Single-submission triage")
    cases = load_cases()
    sample_options = ["Blank input"] + [f"{r.case_id} — {r.title[:70]}" for r in cases.itertuples()]
    sample_choice = st.selectbox("Load a sample case", sample_options)

    if sample_choice == "Blank input":
        default_title = ""
        default_abstract = ""
        default_keywords = ""
    else:
        case_id = sample_choice.split(" — ")[0]
        selected = cases[cases["case_id"] == case_id].iloc[0]
        default_title = selected["title"]
        default_abstract = selected["abstract"]
        default_keywords = selected["keywords"]

    title = st.text_input("Title", value=default_title)
    abstract = st.text_area("Abstract", value=default_abstract, height=220)
    keywords = st.text_input("Keywords", value=default_keywords)

    with st.expander("Show deterministic feature summary"):
        features = extract_features(title, abstract, keywords)
        st.code(features_as_text(features))

    if st.button("Generate triage memo", type="primary"):
        if not title.strip() and not abstract.strip():
            st.error("Enter at least a title and abstract, or load a sample case.")
        else:
            output = triage_submission(title, abstract, keywords, mode=mode, model=model)
            display_output(output)

with tab2:
    st.header("Evaluation on built-in synthetic/public-style test set")
    st.write(
        "The test set contains 36 cases: 12 in-scope, 12 out-of-scope, 6 borderline, and 6 insufficient-information cases."
    )

    eval_mode_label = st.selectbox(
        "Evaluation mode",
        [
            "ScopeLens policy engine (no API key)",
            "Keyword baseline",
            "ScopeLens structured LLM (requires OPENAI_API_KEY)",
        ],
        key="eval_mode",
    )
    eval_mode = mode_map[eval_mode_label]

    if st.button("Run evaluation"):
        result_df, metrics, cm = run_evaluation(mode=eval_mode, model=model)
        m1, m2, m3 = st.columns(3)
        m1.metric("N", int(metrics["n"]))
        m2.metric("Accuracy", f"{metrics['accuracy']:.3f}")
        m3.metric("Macro-F1", f"{metrics['macro_f1']:.3f}")

        st.subheader("Per-label F1")
        per_label = {k: v for k, v in metrics.items() if k.startswith("f1_")}
        st.dataframe(pd.DataFrame([per_label]), use_container_width=True)

        st.subheader("Confusion matrix")
        st.dataframe(cm, use_container_width=True)

        st.subheader("Case-level outputs")
        st.dataframe(result_df, use_container_width=True)

        st.download_button(
            "Download evaluation CSV",
            data=result_df.to_csv(index=False).encode("utf-8"),
            file_name=f"scopelens_eval_{eval_mode}.csv",
            mime="text/csv",
        )

    with st.expander("Inspect test set"):
        st.dataframe(load_cases(), use_container_width=True)

