"""Generate realistic synthetic Set A PDFs for parser/evaluator calibration."""

import json
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "tests" / "samples"

MASTER_KEY = {
    1: "B", 2: "D", 3: "A", 4: "C", 5: "B", 6: "A", 7: "D", 8: "C", 9: "A", 10: "D",
    11: "C", 12: "B", 13: "D", 14: "A", 15: "C", 16: "B", 17: "A", 18: "D", 19: "C", 20: "B",
    21: "A", 22: "C", 23: "B", 24: "D", 25: "A", 26: "D", 27: "C", 28: "B", 29: "D", 30: "A",
    31: "B", 32: "C", 33: "A", 34: "D", 35: "C", 36: "B", 37: "D", 38: "A", 39: "B", 40: "C",
    41: "D", 42: "A", 43: "C", 44: "B", 45: "A", 46: "C", 47: "D", 48: "B", 49: "C", 50: "A",
}

QUESTIONS = [
    ("Which city is the capital of India?", "New Delhi", "Mumbai", "Kolkata", "Chennai"),
    ("Who wrote the Indian national anthem?", "Bankim Chandra Chattopadhyay", "Sarojini Naidu", "Rabindranath Tagore", "Subhas Chandra Bose"),
    ("The Taj Mahal is located in which city?", "Agra", "Jaipur", "Delhi", "Lucknow"),
    ("Which is the largest ocean on Earth?", "Atlantic", "Indian", "Pacific", "Arctic"),
    ("What is the chemical symbol for gold?", "Ag", "Au", "Gd", "Go"),
    ("Which planet is known as the Red Planet?", "Mars", "Venus", "Jupiter", "Mercury"),
    ("Who was the first Prime Minister of India?", "Mahatma Gandhi", "Sardar Patel", "Rajendra Prasad", "Jawaharlal Nehru"),
    ("The currency of Japan is the:", "Won", "Yuan", "Yen", "Ringgit"),
    ("Which gas do plants absorb during photosynthesis?", "Carbon dioxide", "Oxygen", "Nitrogen", "Hydrogen"),
    ("The Great Barrier Reef is off the coast of:", "India", "Australia", "Brazil", "South Africa"),
    ("In which year did India gain independence?", "1942", "1945", "1947", "1950"),
    ("What is the hardest natural substance?", "Iron", "Diamond", "Quartz", "Graphite"),
    ("Which river is often called the lifeline of Egypt?", "Nile", "Amazon", "Ganga", "Danube"),
    ("Who developed the theory of relativity?", "Isaac Newton", "Galileo Galilei", "Albert Einstein", "Niels Bohr"),
    ("The headquarters of the United Nations is in:", "Geneva", "Paris", "New York City", "Vienna"),
    ("Which Indian state has the longest coastline?", "Tamil Nadu", "Gujarat", "Maharashtra", "Kerala"),
    ("What is the SI unit of electric current?", "Ampere", "Volt", "Watt", "Ohm"),
    ("Mount Everest lies in which mountain range?", "Andes", "Alps", "Rockies", "Himalayas"),
    ("Which organ pumps blood through the human body?", "Liver", "Heart", "Lung", "Kidney"),
    ("The Quit India Movement began in:", "1930", "1935", "1942", "1947"),
    ("Which is the smallest continent by land area?", "Europe", "Australia", "Antarctica", "South America"),
    ("What does CPU stand for?", "Central Processing Unit", "Computer Personal Unit", "Core Program Utility", "Central Power User"),
    ("Who was known as the Iron Man of India?", "B. R. Ambedkar", "Sardar Vallabhbhai Patel", "Bhagat Singh", "Lal Bahadur Shastri"),
    ("Which instrument measures atmospheric pressure?", "Thermometer", "Hygrometer", "Barometer", "Anemometer"),
    ("The 2024 Summer Olympics were held in:", "Los Angeles", "Tokyo", "Paris", "Brisbane"),
    ("Which vitamin is produced when skin is exposed to sunlight?", "Vitamin A", "Vitamin B12", "Vitamin C", "Vitamin D"),
    ("The Suez Canal connects the Mediterranean Sea with the:", "Red Sea", "Black Sea", "Arabian Sea", "Caspian Sea"),
    ("What is the approximate speed of light?", "3,000 km/s", "30,000 km/s", "300,000 km/s", "3,000,000 km/s"),
    ("Which Indian space mission soft-landed near the Moon's south polar region in 2023?", "Chandrayaan-1", "Chandrayaan-2", "Mangalyaan", "Chandrayaan-3"),
    ("Who painted the Mona Lisa?", "Vincent van Gogh", "Leonardo da Vinci", "Pablo Picasso", "Claude Monet"),
    ("Which is the largest desert in the world?", "Sahara", "Gobi", "Arabian", "Antarctic"),
    ("The Constitution of India came into effect on:", "15 August 1947", "26 January 1950", "26 November 1949", "2 October 1950"),
    ("Which blood cells help fight infection?", "Red blood cells", "Platelets", "White blood cells", "Plasma"),
    ("The World Wide Web was invented by:", "Tim Berners-Lee", "Bill Gates", "Steve Jobs", "Vint Cerf"),
    ("Which Indian festival is known as the festival of lights?", "Holi", "Eid", "Diwali", "Pongal"),
    ("What is the boiling point of water at sea level?", "90 C", "100 C", "110 C", "120 C"),
    ("Which country hosted the G20 Summit in 2023?", "Brazil", "India", "Italy", "Indonesia"),
    ("What is the national animal of India?", "Lion", "Elephant", "Bengal tiger", "Peacock"),
    ("Which layer protects Earth from most ultraviolet radiation?", "Troposphere", "Ozone layer", "Ionosphere", "Exosphere"),
    ("Who is associated with the discovery of penicillin?", "Alexander Fleming", "Louis Pasteur", "Marie Curie", "Robert Koch"),
    ("The 2025 G20 presidency was held by:", "South Africa", "India", "United States", "Canada"),
    ("Which Indian classical dance form originated in Kerala?", "Kathak", "Bharatanatyam", "Kuchipudi", "Kathakali"),
    ("What is the main gas in Earth's atmosphere?", "Oxygen", "Nitrogen", "Carbon dioxide", "Argon"),
    ("The Battle of Plassey took place in:", "1757", "1764", "1857", "1942"),
    ("Which device converts sunlight directly into electricity?", "Turbine", "Solar cell", "Generator", "Transformer"),
    ("The headquarters of the World Health Organization is in:", "Rome", "Geneva", "London", "Washington, D.C."),
    ("Which ocean surrounds the North Pole?", "Southern", "Indian", "Arctic", "Pacific"),
    ("Who was India's first woman president?", "Indira Gandhi", "Pratibha Patil", "Sarojini Naidu", "Droupadi Murmu"),
    ("What is the study of earthquakes called?", "Ecology", "Seismology", "Geology", "Meteorology"),
    ("Which metal is liquid at room temperature?", "Mercury", "Copper", "Aluminium", "Silver"),
    ("The 2025 Nobel Peace Prize was awarded to:", "Synthetic calibration item", "Synthetic calibration item", "Synthetic calibration item", "Synthetic calibration item"),
]

MASTER_KEYS = {
    "A": MASTER_KEY,
    "B": {number: answer for number, answer in enumerate("CADBCDABDCADBCADBC DAB CABC DABCDABCDABCDABCDABCDABCDABCDABCDABCD".replace(" ", "")[:50], 1)},
    "C": {number: answer for number, answer in enumerate("DBCADCBACBDACBDACBDABDCABDACBABDCABDACBDACDBACDBACDBACDBACDBAC"[:50], 1)},
    "D": {number: answer for number, answer in enumerate("ACBDABCDBACDABCDABCDABCDABCDABCDABCDABCDABCDABCDABCDABCDABCD"[:50], 1)},
}

SET_QUESTIONS = {
    "A": QUESTIONS[:50],
    "B": [(f"Which fact is associated with {topic}?", "Option Alpha", "Option Beta", "Option Gamma", "Option Delta") for topic in ["the largest planet", "Hamlet", "the Amazon River", "the SI unit of force", "the first battle of Panipat", "UNESCO", "transpiration", "Canada's capital", "adult human bones", "the telephone", "the Mariana Trench", "helium balloons", "the Ajanta caves", "the smallest prime", "Italy's shape", "Aryabhata", "wind speed", "the Indian Constitution's Preamble", "haemoglobin", "the Equator", "the International Court of Justice", "weather science", "India's Green Revolution", "the blue whale", "liquid evaporation", "the 2022 FIFA World Cup", "India's national flower", "frequency", "Saturn", "Buddha", "Kuchipudi", "the Moon", "copper wiring", "Marie Curie", "the savanna", "GDP", "the monsoon", "sound", "Nalanda", "a capacitor", "ozone", "Jawaharlal Nehru's book", "democracy", "gravity", "India's 2024 election", "heredity", "Kerala", "solar energy", "quantum science", "oxygen"]],
    "C": [(f"Which institution, place, or discovery is linked with {topic}?", "Answer One", "Answer Two", "Answer Three", "Answer Four") for topic in ["the Mauryan Empire", "the Himalayas", "the periodic table", "the United Nations", "the Harappan civilisation", "the Indian Parliament", "the Pacific Ocean", "the microscope", "the Green Revolution", "the Nobel Prize", "the Sundarbans", "the decimal system", "the Red Fort", "the World Bank", "the monsoon climate", "the Indian Space Research Organisation", "the French Revolution", "the human genome", "the Deccan Plateau", "the printing press", "the Arctic Circle", "the Supreme Court", "the water cycle", "the Olympic Games", "the Indian rupee", "the DNA double helix", "the Silk Road", "the Western Ghats", "the decimal number zero", "the World Health Organization", "the Gupta period", "the Grand Canyon", "the transistor", "the Nobel Chemistry Prize", "the Ganga basin", "the United States Constitution", "the greenhouse effect", "the Red Planet", "the Konark temple", "the International Monetary Fund", "the semiconductor", "the Bhakti movement", "the Indian tiger", "the Richter scale", "the 2025 space programme", "the vaccine", "the Thar Desert", "the Earth's core", "the Commonwealth", "the library", "the carbon cycle"][:50]],
    "D": [(f"In general knowledge, which answer best matches {topic}?", "Choice A", "Choice B", "Choice C", "Choice D") for topic in ["the rule of law", "the Indian Constitution", "the Atlantic Ocean", "the periodic table", "the freedom movement", "the capital of Australia", "the human heart", "the internet", "the World Trade Organization", "the monsoon winds", "the Prime Meridian", "the solar system", "the Mughal period", "the biosphere", "the national flag", "the Indian Railways", "the theory of evolution", "the United Nations Charter", "the Himalayan rivers", "the 2024 Olympics", "the legislative branch", "the computer processor", "the Indian national song", "the water cycle", "the European Union", "the Chandrayaan programme", "the Earth's atmosphere", "the Supreme Court of India", "the census", "the Pacific Rim", "the electric motor", "the medieval Bhakti saints", "the human kidney", "the World Wide Web", "the ozone layer", "the Lok Sabha", "the global climate", "the Indian Ocean", "the periodic motion", "the 2025 G20 presidency", "the national emblem", "the science of earthquakes", "the blue economy", "the ancient trade routes", "the public sector", "the renewable energy transition", "the Indian judiciary", "the Nobel Peace Prize", "the Arctic", "the basic unit of life"]],
}


def make_pdf(path: Path, title: str, lines: list[str]) -> None:
    document = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=15 * mm, bottomMargin=15 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph(title, styles["Title"]), Spacer(1, 6)]
    for index, line in enumerate(lines, 1):
        story.append(Paragraph(line, styles["BodyText"]))
        story.append(Spacer(1, 5))
        if index in {25, 50}:
            story.append(PageBreak())
    document.build(story)


def answer_line(number: int, answer: str) -> str:
    separators = [f"Q{number}: {answer}", f"{number}) {answer}", f"{number} - {answer}", f"{number}. {answer}"]
    return separators[(number - 1) % len(separators)]


def flipped_answers(master_key: dict[int, str], count: int, blank_count: int = 0) -> dict[int, str | None]:
    answers: dict[int, str | None] = dict(master_key)
    for number in range(1, count + 1):
        correct = master_key[number]
        answers[number] = next(option for option in "ABCD" if option != correct)
    for number in range(count + 1, count + blank_count + 1):
        answers[number] = None
    return answers


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    scenarios = [("topper", "Ananya Sharma", 2, 0, 48, True), ("boundary_pass", "Rohan Mehta", 10, 0, 40, True), ("boundary_fail", "Ishita Nair", 11, 0, 39, False), ("low_scorer", "Vikram Singh", 30, 0, 20, False), ("partial_attempt", "Meera Iyer", 10, 5, 35, False)]
    expected = {}
    for set_name, master_key in MASTER_KEYS.items():
        question_lines = [f"{number}. {question}<br/>A. {a}<br/>B. {b}<br/>C. {c}<br/>D. {d}" for number, (question, a, b, c, d) in enumerate(SET_QUESTIONS[set_name], 1)]
        make_pdf(SAMPLES_DIR / f"question_paper_set_{set_name}.pdf", f"Set {set_name}: General Knowledge and Current Affairs", question_lines)
        make_pdf(SAMPLES_DIR / f"master_key_set_{set_name}.pdf", f"Set {set_name} Master Answer Key", [answer_line(number, answer) for number, answer in master_key.items()])
        for variant, student_name, wrong_count, blank_count, score, passed in scenarios:
            filename = f"student_{variant}_set_{set_name}.pdf"
            answers = flipped_answers(master_key, wrong_count, blank_count)
            lines = [f"Student: {student_name}", f"Set: {set_name}"] + [answer_line(number, answer) for number, answer in answers.items() if answer is not None]
            make_pdf(SAMPLES_DIR / filename, f"Set {set_name} Student Answer Sheet: {student_name}", lines)
            expected[filename] = {"student": student_name, "set": set_name, "intended_score": score, "intended_passed": passed}
    (SAMPLES_DIR / "expected_results.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(list(SAMPLES_DIR.glob('*.pdf')))} PDFs in {SAMPLES_DIR}")


if __name__ == "__main__":
    main()