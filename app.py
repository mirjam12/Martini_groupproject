import streamlit as st
import re
from datetime import datetime
import pdfplumber
from dateutil import parser

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

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


def extract_last_updated_year(text):
    years = re.findall(r"(20\d{2})", text)
    if years:
        return max(int(y) for y in years)
    return 2010


# ----------------------------
# 3. Structural score (0–25)
# ----------------------------
def structural_score(text):
    score = 0
    issues = []

    # Headings
    headings = bool(re.search(r"\n[A-Z][A-Za-z0-9 \-]{3,}\n", text))
    if headings:
        score += 8
    else:
        issues.append("Missing clear headings")

    # Length
    word_count = len(text.split())
    if word_count > 150:
        score += 7
    else:
        issues.append("Document too short (<150 words)")

    # Steps
    if re.search(r"(step \d|1\.|2\.|3\.)", text.lower()):
        score += 5
    else:
        issues.append("No explicit follow-up steps")

    # Abbreviations
    if not re.search(r"\b[A-Z]{3,}\b", text):
        score += 5
    else:
        issues.append("Possible undefined abbreviations")

    return score, issues


# ----------------------------
# 4. Duplication logic (0–20)
# ----------------------------
@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource
def get_qdrant():
    return QdrantClient(url="http://localhost:6333", api_key=None)

def duplication_score(text, collection_name="documents"):
    model = load_model()
    qdrant = get_qdrant()

    vector = model.encode(text).tolist()

    try:
        results = qdrant.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=5
        )
    except Exception:
        return 10, 0.0, "Qdrant unavailable — default minor overlap"

    if not results:
        return 20, 0.0, "No matches found — unique"

    max_similarity = max(hit.score for hit in results)
    similarity_pct = max_similarity * 100

    if similarity_pct < 30:
        return 20, similarity_pct, "Unique (<30% similarity)"
    elif 30 <= similarity_pct <= 60:
        return 10, similarity_pct, "Minor overlap (30–60%)"
    else:
        return 0, similarity_pct, "Substantial overlap (>60%)"


# ----------------------------
# 5. Owner validation (0–15)
# ----------------------------
VALID_OWNERS = {
    "HR", "ICT", "Finance", "Quality & Safety",
    "Medical Affairs", "Communications", "Operations"
}

def extract_owner(text):
    patterns = [
        r"owner[:\-]\s*([A-Za-z &]+)",
        r"document owner[:\-]\s*([A-Za-z &]+)",
        r"published by[:\-]\s*([A-Za-z &]+)",
        r"author[:\-]\s*([A-Za-z &]+)"
    ]

    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()

    return None


def owner_validation_score(text):
    owner = extract_owner(text)

    if owner is None:
        return 5, None, "Owner missing — requires manual validation"

    if owner in VALID_OWNERS:
        return 15, owner, f"Valid owner: {owner}"

    return 0, owner, f"Unrecognized owner: {owner} — flagged for review"


# ----------------------------
# 6. Composite score (0–100)
# ----------------------------
def composite_score(t, s, d, o):
    return t + s + d + o


# ----------------------------
# 7. Decision logic (4 categories)
# ----------------------------
def decision(composite):
    if composite >= 80:
        return "High quality – auto include"
    elif composite >= 60:
        return "Acceptable – include with note"
    elif composite >= 40:
        return "Needs attention – human review"
    else:
        return "Insufficient – exclude"

# ----------------------------
#  Kill switch for script tabs
# ----------------------------
def contains_script_tags(text):
    patterns = [
        r"<script.*?>",
        r"</script>",
        r"javascript:",
        r"onload=",
        r"onclick="
    ]

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )
# ----------------------------
#  Kill switch for SQL injection
# ----------------------------
def contains_sql_injection(text):

    patterns = [
        r"union\s+select",
        r"drop\s+table",
        r"delete\s+from",
        r"insert\s+into",
        r"or\s+1\s*=\s*1",
        r"--",
        r";\s*drop",
    ]

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )

# ----------------------------
#  Kill switch for suspicious URL-s
# ----------------------------

def suspicious_urls(text):

    urls = re.findall(
        r"https?://[^\s]+",
        text,
        re.IGNORECASE
    )

    suspicious_keywords = [
        "bit.ly",
        "tinyurl",
      #  ".ru",
        ".xyz",
        ".tk",
        "pastebin"
    ]

    found = []

    for url in urls:
        if any(k in url.lower() for k in suspicious_keywords):
            found.append(url)

    return found


# ----------------------------
#  Kill switch for drafts
# ----------------------------

def draft_check(text):

    pattern = r"\b(DRAFT|PRELIMINARY|FOR REVIEW|NOT FOR CLINICAL USE|nog in te vullen|wordt aangevuld|in ontwikkeling|concept)\b"

    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return False, f"Document marked as '{match.group()}'"

    return True, "Passed"

# ----------------------------
#  Human review for discrimination
# ----------------------------

def discrimination_check(text):

    suspicious_terms = [
        "inferior race",
        "foreigners are",
        "women are less capable",
        "elderly people cannot",
    # nationality keywords
        "allochtonen",
        "buitenlanders",
        "vreemdelingen",
        "niet-westerse",
        "moslims zijn",
        "marokkanen zijn",
        "turken zijn",
        "asielzoekers zijn",
        "vluchtelingen zijn",
    # gender keywords
        "vrouwen zijn minder",
        "vrouwen kunnen niet",
        "mannen horen",
        "vrouwelijke medewerkers zijn",
        "mannen zijn beter",
        "zwakke vrouwen",
        "typisch vrouwengedrag",
        "typisch mannengedrag",
    # sexuality keywords
        "homoseksuelen zijn",
        "homo's zijn",
        "lesbiennes zijn",
        "transgenders zijn",
        "transpersonen zijn",
        "genderideologie",
        "afwijkende seksuele voorkeur",
    # patterns
        r"\b.*zijn altijd\b",
        r"\b.*zijn meestal\b",
        r"\b.*kunnen niet\b",
        r"\b.*horen niet\b",
        r"\b.*zijn minder\b",
        r"\b.*zijn ongeschikt\b"
    ]

    for term in suspicious_terms:
        if term.lower() in text.lower():
            return False, f"Potential discriminatory phrase: {term}"

    return True, "Passed"


# ----------------------------
#  All security checks together
# ----------------------------

def check_security_compliance(text):
    """
    Returns (is_valid, reason)
    """
    if contains_script_tags(text):
        return False, "Security violation: Script tags detected."
    
    if contains_sql_injection(text):
        return False, "Security violation: Potential SQL injection detected."
    
    suspicious = suspicious_urls(text)
    if suspicious:
        return False, f"Security violation: Suspicious URLs found: {', '.join(suspicious)}"
        
    is_draft, draft_reason = draft_check(text)
    if not is_draft:
        return False, draft_reason
        
    is_safe, disc_reason = discrimination_check(text)
    if not is_safe:
        return False, disc_reason
        
    return True, "Passed"

# ----------------------------
# 8. Streamlit UI
# ----------------------------
st.title("Document Quality Scoring Pipeline (Full Version)")

uploaded_file = st.file_uploader("Upload PDF document", type="pdf")

if uploaded_file is not None:
    st.success("File uploaded successfully!")

    text = extract_text(uploaded_file)
    
    # Compliance checks (kill switches)

    is_valid, status_msg = check_security_compliance(text)
    
    if not is_valid:
        st.error(f"❌ DOCUMENT FAILED: {status_msg}")
        # Stop further execution
        st.stop()

    # Timeliness
    year = extract_last_updated_year(text)
    t_score = timeliness_score(year)

    # Structural
    s_score, issues = structural_score(text)

    # Duplication
    d_score, d_pct, d_status = duplication_score(text)

    # Owner validation
    o_score, owner, o_status = owner_validation_score(text)

    # Composite
    composite = composite_score(t_score, s_score, d_score, o_score)

    # Display results
    st.subheader("Subscores")
    st.write(f"Timeliness: {t_score}/40 (year detected: {year})")
    st.write(f"Structural: {s_score}/25")
    st.write(f"Duplication: {d_score}/20 — {d_status} ({d_pct:.2f}%)")
    st.write(f"Owner validation: {o_score}/15 — {o_status}")

    st.subheader("Composite Score")
    st.write(f"**{composite}/100**")

    st.subheader("Structural Issues")
    if issues:
        for i in issues:
            st.warning(i)
    else:
        st.success("No structural issues detected")

    st.subheader("Final Decision")
    result = decision(composite)

    if "High quality" in result:
        st.success("✅ " + result)
    elif "Acceptable" in result:
        st.info("ℹ️ " + result)
    elif "Needs attention" in result:
        st.warning("⚠️ " + result)
    else:
        st.error("❌ " + result)
