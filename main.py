from flask import Flask, request, render_template
import fitz  # PyMuPDF
import re
import spacy
import json

app = Flask(__name__)
nlp = spacy.load("en_core_web_sm")

# Load skill list
with open("skills.json") as f:
    SKILL_LIST = json.load(f)

def extract_text(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    return " ".join(page.get_text() for page in doc)

def extract_email(text):
    return re.findall(r"[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)

def extract_phone(text):
    text = text.replace('\n', ' ').replace('\r', '')
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?){1}\d{3}[-.\s]?\d{4}\b'
    phones = re.findall(phone_pattern, text)
    clean_phones = list(set(p for p in phones if len(re.sub(r'\D', '', p)) >= 10))
    return clean_phones

def extract_name(text):
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return ent.text
    return "Name not found"

def extract_skills(text):
    return [s for s in SKILL_LIST if s.lower() in text.lower()]

def extract_experience(text):
    experiences = []
    lines = text.split("\n")
    job_title_keywords = ['engineer', 'developer', 'intern', 'manager', 'consultant', 'analyst', 'lead']
    date_pattern = re.compile(
        r'((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s?\d{4})\s*[-\u2013\u2014–]\s*((Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s?\d{4}|Present)',
        re.IGNORECASE)

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        date_match = date_pattern.search(line)
        if date_match:
            exp = {"dates": date_match.group(0)}

            # Look backwards for job title
            for j in range(i - 1, max(i - 3, -1), -1):
                prev_line = lines[j].strip()
                if any(kw in prev_line.lower() for kw in job_title_keywords):
                    exp["title"] = prev_line
                    break
            else:
                exp["title"] = "Title not found"

            # Forward for company and description
            exp["company"] = "Company not found"
            exp["description"] = ""
            for k in range(i + 1, min(i + 6, len(lines))):
                next_line = lines[k].strip()
                if len(next_line.split()) <= 5 and not date_pattern.search(next_line):
                    exp["company"] = next_line
                elif next_line:
                    exp["description"] += next_line + " "
            experiences.append(exp)
            i += 5
        else:
            i += 1
    return experiences

@app.route('/', methods=["GET", "POST"])
def index():
    data = {}
    if request.method == "POST":
        uploaded_file = request.files["resume"]
        if uploaded_file:
            text = extract_text(uploaded_file)
            data = {
                "name": extract_name(text),
                "email": extract_email(text),
                "phone": extract_phone(text),
                "skills": extract_skills(text),
                "experience": extract_experience(text)
            }
    return render_template("index.html", data=data)

if __name__ == "__main__":
    app.run(debug=True)
