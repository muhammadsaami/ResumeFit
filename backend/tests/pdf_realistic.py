"""Realistic, privacy-safe regression fixtures.

These reproduce the failure modes reported against real PDFs rather than the
idealised fixtures in :mod:`tests.synthetic`:

* a single header line carrying name + all contact details;
* sections and entries packed together with no blank lines (as most PDF text
  layers extract them);
* bullet glyphs that PDF extraction turns into ``(cid:127)`` escapes;
* bullet text that wraps onto a continuation line;
* certifications, which had no model field before the fix.

All names, employers, projects and certifications are fictional placeholders.
"""

from __future__ import annotations

import io

# The canonical resume. Each logical line is a separate physical line and no
# blank lines separate entries - matching how reportlab/pdfplumber recovers a
# real PDF text layer.
REALISTIC_RESUME_LINES = [
    "Jordan Rivera | +44 7000 123456 | jordan.rivera@example.com | "
    "linkedin.com/in/jordanrivera | github.com/jrivera",
    "Senior Software Engineer | London, UK | 2016 - Present",
    "PROFESSIONAL SUMMARY",
    "Backend engineer who builds reliable distributed systems and mentors",
    "teammates across product teams.",
    "TECHNICAL SKILLS",
    "Languages: Python, TypeScript, Java, SQL",
    "Frameworks: FastAPI, React, Node.js, Django",
    "Tools: Docker, Kubernetes, PostgreSQL, AWS, Git",
    "PROFESSIONAL EXPERIENCE",
    "Senior Software Engineer, Riverstone Labs | 2019 - Present",
    "- Built a payments platform serving millions of requests each day.",
    "- Designed a queue-based ingestion pipeline handling events daily.",
    "- Mentored engineers across the organisation.",
    "Software Engineer, Northwind Systems Ltd | 2016 - 2019",
    "- Built REST APIs and internal tooling for the data team.",
    "- Cut deployment time by forty percent using CI/CD automation.",
    "PROJECTS",
    "SupportPilot | FastAPI, Docker, PostgreSQL",
    "- Automated support ticket triage using rule-based classification.",
    "- Cut average first response time by fifty percent.",
    "trustlens | Python, React, GraphQL",
    "- Reviewed claims and flagged high-risk cases.",
    "DocuMind | PyTorch, FastAPI, Selenium",
    "- Built a document ingestion pipeline so files are extracted reliably.",
    "EDUCATION",
    "M.Sc. Computer Science, University College London | 2014 - 2016",
    "B.E. Software Engineering, University of Oxford | 2011 - 2014",
    "CERTIFICATIONS",
    "AWS Certified Solutions Architect - Associate",
    "Certified Kubernetes Administrator",
]

REALISTIC_RESUME = "\n".join(REALISTIC_RESUME_LINES) + "\n"

# A bullet that wraps onto a lowercase continuation line must merge into one
# bullet instead of being mistaken for a new section or entry.
WRAPPED_BULLET_RESUME = (
    "Jordan Rivera\n"
    "jordan.rivera@example.com\n"
    "PROFESSIONAL EXPERIENCE\n"
    "Senior Software Engineer, Riverstone Labs | 2019 - Present\n"
    "- Built a payments platform serving millions of requests each day\n"
    "across multiple regions and currencies.\n"
    "- Mentored engineers across the organisation.\n"
)

# Skills spread over several labelled lines. A regroup change must replace the
# whole block, not just its first line, or the remaining labels duplicate it.
MULTILINE_SKILLS_RESUME = (
    "Jordan Rivera\n"
    "jordan.rivera@example.com\n"
    "TECHNICAL SKILLS\n"
    "Languages: Python, SQL\n"
    "Tools: Docker\n"
    "Frameworks: Django, React\n"
    "PROFESSIONAL EXPERIENCE\n"
    "Engineer, Acme Ltd | 2020 - Present\n"
    "- Built internal tools.\n"
    "EDUCATION\n"
    "B.Sc. Computer Science, Example University | 2016 - 2020\n"
)

# Headings present but with no extractable content: they must not earn full
# section credit (no double-counting an empty heading as a complete section).
EMPTY_SECTION_RESUME = (
    "Jordan Rivera\n"
    "jordan.rivera@example.com\n"
    "PROJECTS\n"
    "SKILLS\n"
    "Python, SQL, Docker\n"
)

# Contact fields deliberately absent so an uncertain-extraction warning can flip
# the "missing" conclusion from failed to warning.
NO_PHONE_RESUME = (
    "Jordan Rivera\n"
    "jordan.rivera@example.com\n"
    "SKILLS\n"
    "Python, SQL, Docker\n"
)

# A layout commonly produced by design-heavy resumes and recovered by PDF text
# extraction: two-line experience headers where the first line carries the role
# plus a month/year range and the second line carries "Company | Location"; a
# project title with a trailing year followed by a bare technology list and a
# link line; bullets whose wrapped continuation starts with a capital letter or
# punctuation ("UI."); education listed institution-first; and a certification
# wrapped across two lines. All content is fictional.
#
# This mirrors the failure modes found on a real PDF: the role being split at
# the em-dash, the company being lost, the second project being merged into the
# first, education dates bleeding between entries, wrapped certifications split
# into two, and wrapped bullet fragments ("UI.") mistaken for a heading.
EMBEDDED_DATE_RESUME = (
    "Alex Mercer\n"
    "Backend Developer (AI & Full-Stack)\n"
    "+44 7000 123456 | alex.mercer@example.com | github.com/alexmercer |\n"
    "Manchester, UK\n"
    "Summary\n"
    "Backend developer with experience building AI and full-stack applications.\n"
    "Technical Skills\n"
    "AI / ML: Large Language Models, RAG Pipelines, Prompt Engineering, LangChain, Pinecone,\n"
    "Embeddings\n"
    "Web Development: React.js, Node.js, Express.js, FastAPI, REST APIs, Tailwind CSS, JavaScript\n"
    "Languages: Python, JavaScript, SQL\n"
    "Databases: PostgreSQL, MongoDB, Pinecone\n"
    "Experience\n"
    "Senior Developer \u2014 AI Platforms Jul 2021 \u2013 May 2023\n"
    "Riverstone Labs | Manchester, UK 22 months\n"
    "- Architected and deployed LLM-powered services to deliver context-aware products;\n"
    "improved retrieval precision using better chunking.\n"
    "- Designed end-to-end agent workflows from prompt engineering and tool orchestration to\n"
    "LangChain pipelines enabling automated multi-step reasoning.\n"
    "Backend Developer (Contract) Mar 2020 \u2013 Jul 2021\n"
    "Northwind Systems | Remote\n"
    "- Built and maintained REST APIs consumed by web clients; implemented JWT authentication.\n"
    "Projects\n"
    "Full-Stack Commerce Platform 2022\n"
    "React.js, Node.js, Express.js, MongoDB, Tailwind CSS\n"
    "github.com/alexmercer/commerce\n"
    "- Designed a complete commerce platform with catalogue, cart, and order management.\n"
    "- Implemented secure authentication and a responsive mobile-first\n"
    "UI.\n"
    "Gestures Controller 2022\n"
    "Python, OpenCV, MediaPipe, Computer Vision\n"
    "github.com/alexmercer/gestures\n"
    "- Built a real-time gesture controller using landmark detection.\n"
    "Education\n"
    "Northfield University \u2014 Faculty of Engineering Aug 2021 \u2013 Aug 2023\n"
    "M.Sc. (AI) \u2014 Master of Computer Science, Artificial Intelligence | CGPA: 8.5 Leeds, UK\n"
    "Westbridge University Sep 2018 \u2013 Feb 2021\n"
    "B.Sc. (Hons) Mathematics | CGPA: 8.9 Leeds, UK\n"
    "Certifications\n"
    "Machine Learning Specialisation | Example Institute | Sep - Oct 2020 - Hands-on program "
    "covering Python and ML\n"
    "development and deployment.\n"
)

UNCERTAINTY_WARNING = (
    "Extracted text looks incomplete (12 words across 1 page); the file may be "
    "scanned or image-based."
)


def build_realistic_pdf() -> bytes:
    """Render the realistic resume to a text-based PDF (no blank lines)."""
    return build_pdf_from_lines(REALISTIC_RESUME_LINES)


def build_pdf_from_lines(lines: list[str]) -> bytes:
    """Render each logical line to its own PDF text line (no blank lines).

    This mirrors how a genuine resume export reaches the extractor: the PDF text
    layer contains the already-wrapped physical lines, including any hyphen a
    layout engine inserted when breaking a word.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter
    y = height - 60
    for line in lines:
        if line.startswith("- "):
            pdf.drawString(72, y, "\u2022 " + line[2:])
        else:
            pdf.drawString(72, y, line)
        y -= 16
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


MUST_HAVE_CONTENT = [
    "Jordan Rivera",
    "+44 7000 123456",
    "jordan.rivera@example.com",
    "Senior Software Engineer",
    "Riverstone Labs",
    "Northwind Systems Ltd",
    "SupportPilot",
    "trustlens",
    "DocuMind",
    "FastAPI",
    "Docker",
    "PostgreSQL",
    "GraphQL",
    "M.Sc.",
    "University College London",
    "B.E.",
    "University of Oxford",
    "AWS Certified Solutions Architect",
    "Certified Kubernetes Administrator",
    "Python",
    "TypeScript",
    "React",
    "Django",
    "Kubernetes",
]
