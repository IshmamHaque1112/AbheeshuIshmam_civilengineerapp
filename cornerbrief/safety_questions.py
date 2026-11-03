"""Questions for a professional. This is not a safety plan or a final PPE list."""
OSHA = "https://www.osha.gov/Publications/OSHA3681.pdf"
DOB = "https://www.nyc.gov/assets/buildings/pdf/LL196_OnePager.pdf"


def build_questions() -> list[dict]:
    return [
        {"topic": "Silica", "question": "Which saw and removal tasks fall under OSHA's Table 1, and which controls do their location and duration require?", "url": OSHA},
        {"topic": "Silica", "question": "Who is the competent person, and what does the written exposure control plan say?", "url": OSHA},
        {"topic": "Training", "question": "Does this site and each worker's role require NYC Site Safety Training? If the site type is unclear, the answer is unknown until a professional confirms it.", "url": DOB},
        {"topic": "Traffic and access", "question": "How will vehicles and pedestrians, including people with disabilities, be kept safe and routed during the work?", "url": None},
    ]
