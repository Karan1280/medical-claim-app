"""
app.py
Haryana Medical Reimbursement — EC + Working Out Sheet generator.

Clean end-user interface: upload the bill (PDF or photos), fill in four
claimant fields, click one of three generate buttons. All AI-provider /
model / NABH-tier settings are configured by the admin via Secrets and
code constants below — they are never shown to the person using the app.
"""

import json
import os
from datetime import datetime

import streamlit as st

from src.llm_extract import extract_claim, ExtractionError
from src.rate_lookup import RateLookup
from src.ec_builder import build_ec_docx
from src.workout_builder import build_workout_xlsx

# ------------------------------------------------------------------
# Admin-only configuration (not shown in the UI).
# Change PROVIDER / MODEL_NAME / NABH_LEVEL here, or override via
# Streamlit Secrets (PROVIDER, MODEL_NAME, NABH_LEVEL) without touching code.
# ------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
EC_TEMPLATE = os.path.join(DATA_DIR, "MASTER_TEMPLATE.docx")
WORKOUT_TEMPLATE = os.path.join(DATA_DIR, "Working_Out_Sheet_BASE_TEMPLATE.xlsx")
FIXED_REMARKS = os.path.join(DATA_DIR, "Fixed_Test_Remarks_REFERENCE.xlsx")
PGI_QUICK_REF = os.path.join(DATA_DIR, "PGI_Rate_Quick_Reference.xlsx")
PACKAGE_RATES = os.path.join(DATA_DIR, "haryana_package_rates.xlsx")

DEFAULT_INSTRUCTION = "Process this new claim according to the Project Instructions."


def _get_config(key: str, default: str = "") -> str:
    """Read a config value from Streamlit Secrets if available (Streamlit
    Cloud), otherwise fall back to a plain environment variable (Railway,
    Render, AWS, Docker, local shell export, etc.). Safe to call even when
    no secrets.toml exists at all - that case previously raised
    StreamlitSecretNotFoundError on non-Streamlit-Cloud hosts."""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


PROVIDER = _get_config("PROVIDER", "gemini")
MODEL_NAME = st.secrets.get("MODEL_NAME", "gemini-3.1-pro-preview" if PROVIDER == "gemini" else "claude-sonnet-4-6")

NABH_LEVEL = _get_config("NABH_LEVEL", "FULL")  # "FULL" or "ENTRY"
SECRET_KEY_NAME = "GEMINI_API_KEY" if PROVIDER == "gemini" else "ANTHROPIC_API_KEY"
API_KEY = _get_config(SECRET_KEY_NAME, "")

st.set_page_config(page_title="Medical Claim Generator", page_icon="🏥", layout="centered")

st.title("🏥 Medical Claim Generator")
st.caption("Bill upload karo, details bharo, aur EC / Workout Sheet download karo.")

if not API_KEY:
    st.error(
        "⚠️ App abhi configure nahi hai — admin ko Streamlit Secrets mein "
        f"`{SECRET_KEY_NAME}` add karni hai. (Is baare mein end-user ko kuch "
        "karne ki zaroorat nahi.)"
    )
    st.stop()


# ------------------------------------------------------------------
# Upload
# ------------------------------------------------------------------
uploaded_files = st.file_uploader(
    "Hospital bill upload karo (PDF ya photo)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Ek se zyada photos ho to sab ek saath select kar sakte ho (multi-page bill).",
)

# ------------------------------------------------------------------
# Claimant details
# ------------------------------------------------------------------
st.subheader("Claimant details")

claimant_name = st.text_input("Claimant:")
designation = st.text_input("Designation:")
department = st.text_input("Department:")

leave_basic_pay_blank = st.checkbox("Basic Pay abhi nahi pata — blank chhodo")
basic_pay = "" if leave_basic_pay_blank else st.text_input("Basic Pay (Rs.):")

with st.expander("Advanced (optional)"):
    room_type = st.selectbox("Room type on bill, agar pata ho", ["", "GENERAL", "SEMI-PRIVATE", "PRIVATE"])

st.divider()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _mime_for(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".png"):
        return "image/png"
    return "image/jpeg"


def _read_files(files):
    return [{"bytes": f.getvalue(), "mime_type": _mime_for(f)} for f in files]


def _claimant_info():
    return {
        "claimant_name": claimant_name.strip(),
        "designation": designation.strip(),
        "department": department.strip(),
        "basic_pay": basic_pay.strip(),
    }


def _ensure_claim_extracted():
    """Run extraction once per uploaded file-set, cache in session_state."""
    file_key = tuple((f.name, f.size) for f in uploaded_files)
    if st.session_state.get("_file_key") == file_key and "claim" in st.session_state:
        return st.session_state["claim"]

    with st.spinner("Bill padh raha hoon…"):
        files = _read_files(uploaded_files)
        claim = extract_claim(files, _claimant_info(), DEFAULT_INSTRUCTION,
                               PROVIDER, API_KEY, MODEL_NAME)
    st.session_state["claim"] = claim
    st.session_state["_file_key"] = file_key
    return claim


def _base_filename(claim: dict) -> str:
    patient_name = (claim.get("patient", {}).get("name") or "patient").strip().lower().replace(" ", "")
    admit_date_raw = claim.get("admission", {}).get("admission_date")
    try:
        admit_dt = datetime.strptime(admit_date_raw, "%d-%m-%Y")
        admit_str = admit_dt.strftime("%d%B%Y").lower()
    except Exception:
        admit_str = "date"
    return f"{patient_name}_{admit_str}"


def _generate(make_ec: bool, make_workout: bool):
    if not uploaded_files:
        st.error("Pehle bill upload karo (PDF ya photo).")
        return
    try:
        claim = _ensure_claim_extracted()
    except ExtractionError as e:
        st.error(f"Extraction fail ho gaya: {e}")
        return
    except Exception as e:
        st.error(f"Kuch galat ho gaya: {e}")
        return

    claimant_info = _claimant_info()
    base_name = _base_filename(claim)
    notes = claim.get("extraction_notes") or []

    result_ec, result_workout, flagged = None, None, []
    try:
        if make_ec:
            with st.spinner("Essentiality Certificate bana raha hoon…"):
                result_ec = build_ec_docx(EC_TEMPLATE, claim, claimant_info)
        if make_workout:
            with st.spinner("Working Out Sheet bana raha hoon…"):
                rl = RateLookup(FIXED_REMARKS, PGI_QUICK_REF, PACKAGE_RATES)
                result_workout, flagged = build_workout_xlsx(
                    WORKOUT_TEMPLATE, claim, claimant_info, rl,
                    nabh_level=NABH_LEVEL, room_type=room_type)
    except Exception as e:
        st.error(f"Document banate waqt error aaya: {e}")
        st.exception(e)
        return

    st.success("✅ Ready!")

    if result_ec is not None and result_workout is not None:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Download EC (.docx)", data=result_ec,
                                file_name=f"EC_{base_name}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True)
        with c2:
            st.download_button("⬇️ Download Workout Sheet (.xlsx)", data=result_workout,
                                file_name=f"Work_{base_name}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True)
    elif result_ec is not None:
        st.download_button("⬇️ Download EC (.docx)", data=result_ec,
                            file_name=f"EC_{base_name}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            use_container_width=True)
    elif result_workout is not None:
        st.download_button("⬇️ Download Workout Sheet (.xlsx)", data=result_workout,
                            file_name=f"Work_{base_name}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True)

    if notes:
        st.warning("Bill mein kuch cheezein unclear thi:\n\n" + "\n".join(f"- {n}" for n in notes))
    if flagged:
        st.warning("Yeh rows PGI rate schedule mein match nahi hui — manually verify karo:\n\n" +
                   "\n".join(f"- {f}" for f in flagged))
    if leave_basic_pay_blank:
        st.info("Basic Pay blank rakha gaya tha — Room Rent rows Workout Sheet mein pending honge, baad mein Excel mein bhar dena.")

    with st.expander("🔍 Extracted data dekho (advanced)"):
        st.json(claim)


# ------------------------------------------------------------------
# Three generate buttons
# ------------------------------------------------------------------
b1, b2, b3 = st.columns(3)
with b1:
    go_both = st.button("EC + WORKOUT", type="primary", use_container_width=True)
with b2:
    go_ec = st.button("EC", use_container_width=True)
with b3:
    go_workout = st.button("WORKOUT", use_container_width=True)

if go_both:
    _generate(make_ec=True, make_workout=True)
elif go_ec:
    _generate(make_ec=True, make_workout=False)
elif go_workout:
    _generate(make_ec=False, make_workout=True)

st.divider()
st.caption("Generate hone ke baad bhi original bills se cross-check zaroor kar lo submission se pehle.")
