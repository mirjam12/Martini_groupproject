# Martini_groupproject
# Document Timeliness Scoring Pipeline

## Overview

This project demonstrates a document governance pipeline designed to evaluate whether a document is suitable for inclusion in the Martini Hospital AI chatbot (**Betsy**).

The prototype automatically:

1. Accepts a document upload from a user.
2. Extracts text from the document using OCR.
3. Detects the most recent year referenced in the document.
4. Calculates a timeliness score based on predefined governance rules.
5. Routes the document either:

   * **Sent to Betsy**
   * **Sent for Human Review**

The goal is to demonstrate how AI-assisted document governance can help reduce the risk of outdated information entering a Retrieval-Augmented Generation (RAG) system.

---

## Architecture

```text
User Upload
     │
     ▼
OCR Text Extraction
     │
     ▼
Date Detection
     │
     ▼
Timeliness Scoring
     │
     ▼
Decision Engine
     │
     ├── Sent to Betsy
     │
     └── Sent for Human Review
```

---

## Technologies Used

* Python 3.x
* Streamlit
* Tesseract OCR
* Pillow (PIL)
* Regular Expressions (Regex)

---

## Timeliness Scoring Rules

| Last Updated | Timeliness Score | Interpretation              |
| ------------ | ---------------- | --------------------------- |
| 2024–2025    | 40 / 40          | Current                     |
| 2023         | 32 / 40          | Likely Current              |
| 2022         | 24 / 40          | Possibly Outdated           |
| 2018–2021    | 12 / 40          | Probably Outdated           |
| Before 2018  | 0 / 40           | High Risk of Being Outdated |

---

## Routing Logic

### Sent to Betsy

A document is automatically approved if:

```text
Timeliness Score ≥ 32
```

Example:

```text
Last Updated: 2024
Score: 40/40
Result: Sent to Betsy
```

---

### Sent for Human Review

A document is flagged for manual validation if:

```text
Timeliness Score < 32
```

Example:

```text
Last Updated: 2020
Score: 12/40
Result: Sent for Human Review
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/your-repository/document-scoring-pipeline.git
cd document-scoring-pipeline
```

### Install Dependencies

```bash
pip install streamlit
pip install pytesseract
pip install pillow
pip install pdf2image
```

### Install Tesseract OCR

#### Ubuntu / Linux

```bash
sudo apt-get install tesseract-ocr
```

#### Google Colab

```bash
!apt-get install -y tesseract-ocr
```

---

## Running the Application

Start the Streamlit application:

```bash
streamlit run app.py
```

The application will open in your browser.

---

## User Workflow

### Step 1 – Upload Document

The user uploads a document using the Streamlit file uploader.

Supported formats:

* PNG
* JPG
* JPEG

### Step 2 – Text Extraction

OCR extracts text from the uploaded document.

### Step 3 – Date Detection

The system searches for years within the extracted text.

Example:

```text
Last Updated: March 2024
```

### Step 4 – Timeliness Scoring

The most recent year is mapped to a timeliness score.

### Step 5 – Decision

The document is routed according to the score:

```text
Score ≥ 32  → Sent to Betsy
Score < 32  → Sent for Human Review
```

---

## Example Output

```text
Detected Status: Current

Timeliness Score: 40/40

Final Decision:
Sent to Betsy
```

---

## Known Limitations

This prototype evaluates only **document timeliness**.

It does not currently evaluate:

* Document completeness
* Ownership information
* Duplicate content
* Contradictions between documents
* Instruction clarity
* Clinical accuracy
* Relevance for chatbot use

---

## Future Improvements

Future versions could include additional governance dimensions:

| Dimension    | Purpose                           |
| ------------ | --------------------------------- |
| Timeliness   | Detect outdated documents         |
| Completeness | Check for missing sections        |
| Ownership    | Verify document owner exists      |
| Duplication  | Detect duplicate procedures       |
| Consistency  | Identify conflicting instructions |
| Relevance    | Determine suitability for Betsy   |

These dimensions could be combined into a single **Document Quality Score** before a document is approved for inclusion in Betsy's knowledge base.

---

## Academic Context

This prototype was developed as part of research into AI-assisted document governance for Retrieval-Augmented Generation (RAG) systems.

The central premise is that scaling an enterprise chatbot is primarily a document quality challenge rather than a chatbot challenge. By automatically evaluating document quality before ingestion, organizations can reduce the risk of outdated or unreliable information being retrieved by AI systems.

---

## Author

Mirjam Reino, Jenze Sijens, Jourit Holvast, Jesse-Jorn de Haan

Hanze University Groningen
