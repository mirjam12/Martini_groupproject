
import streamlit as st


import re
from datetime import datetime
import pdfplumber
from dateutil import parser

# ----------------------------
# 1. Extract text from PDF
# ----------------------------
def extract_text(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


# ----------------------------
# 2. Timeliness score (0–40)
# ----------------------------
def timeliness_score(last_updated_year):
    if last_updated_year in [2024, 2025, 2026]:
        return 40
    elif last_updated_year == 2023:
        return 32
    elif last_updated_year == 2022:
        return 24
    elif 2018 <= last_updated_year <= 2021:
        return 12
    else:
        return 0


# simple helper: extract year from text (you'll replace later with metadata if available)
def extract_last_updated_year(text):
    # tries to find something like "2023", "updated 2022", etc.
    years = re.findall(r"(20\d{2})", text)
    if years:
        return max(int(y) for y in years)
    return 2010  # fallback = old


# ----------------------------
# 3. Structural score (0–25)
# ----------------------------
def structural_score(text):
    score = 0
    issues = []

    # 1. Headings
    headings = bool(re.search(r"\n[A-Z][A-Za-z0-9 \-]{3,}\n", text))
    if headings:
        score += 8
    else:
        issues.append("Missing clear headings")

    # 2. Length
    word_count = len(text.split())
    if word_count > 150:
        score += 7
    else:
        issues.append("Document too short (<150 words)")

    # 3. Follow-up steps (simple heuristic)
    if re.search(r"(step \d|1\.|2\.|3\.)", text.lower()):
        score += 5
    else:
        issues.append("No explicit follow-up steps")

    # 4. Abbreviations check (very naive heuristic)
    if not re.search(r"\b[A-Z]{3,}\b", text):
        score += 5
    else:
        issues.append("Possible undefined abbreviations")

    return score, issues

# ----------------------------
# 4. Duplication logic
# ----------------------------



# ----------------------------
# 5. Owner validation logic
# ----------------------------



# ----------------------------
# 6. Decision logic
# ----------------------------
def decision(total_score):
    if total_score >= 60:
        return "sent to betsy"
    else:
        return "sent for human review"


# -------------------------------
# 5. Streamlit app
# -------------------------------

st.title("Document Quality Scoring Pipeline")

uploaded_file = st.file_uploader("Upload PDF document", type="pdf")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    # Extract text
    text = extract_text(uploaded_file)

    # --- Timeliness ---
    year = extract_last_updated_year(text)
    t_score = timeliness_score(year)

    # --- Structural ---
    s_score, issues = structural_score(text)

    total = t_score + s_score

    st.subheader("Results")
    st.write(f"Last updated year detected: {year}")
    st.write(f"Timeliness score: {t_score}/40")
    st.write(f"Structural score: {s_score}/25")
    st.write(f"Total score: {total}/65 (raw system)")

    st.subheader("Structural Issues")
    if issues:
        for i in issues:
            st.warning(i)
    else:
        st.success("No structural issues detected")

    st.subheader("Final Decision")

    result = decision(total)

    if result == "sent to betsy":
        st.success("✅ SENT TO BETSY")
    else:
        st.error("❌ SENT FOR HUMAN REVIEW")
