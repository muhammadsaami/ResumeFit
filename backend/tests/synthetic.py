"""Synthetic resume fixtures for Phase 2 tests.

All names, emails and organisations here are fictional placeholders. No real
personal information is used anywhere in the test suite.
"""

from __future__ import annotations

COMPLETE_RESUME = (
    "Jordan Rivera\n"
    "jordan.rivera@example.com | +1 555 123 4567\n"
    "Seattle, WA\n"
    "linkedin.com/in/jordanrivera | github.com/jordanrivera\n"
    "\n"
    "Summary:\n"
    "Backend developer experienced in building web services and data pipelines.\n"
    "\n"
    "Education:\n"
    "Bachelor of Science in Computer Science\n"
    "University of Example\n"
    "2018 - 2022\n"
    "GPA: 3.8\n"
    "\n"
    "Experience:\n"
    "Software Engineer at Example Corp\n"
    "2022 - Present\n"
    "- Built REST APIs in Python that serve internal tools reliably.\n"
    "- Improved database queries and reduced response time noticeably.\n"
    "- Wrote automated tests for critical backend services.\n"
    "\n"
    "Projects:\n"
    "Portfolio Tracker\n"
    "Tech: React, Node.js, PostgreSQL\n"
    "- Developed a dashboard for tracking personal investments.\n"
    "- Implemented authentication and a data export feature.\n"
    "\n"
    "Skills:\n"
    "Python, JavaScript, SQL, React, Node.js, Docker, Git, PostgreSQL\n"
)

ALIAS_RESUME = (
    "Sam Lee\n"
    "sam.lee@example.com\n"
    "555-987-6543\n"
    "\n"
    "Academic Background:\n"
    "Bachelor of Arts in Economics\n"
    "Example University, 2017 - 2021\n"
    "\n"
    "Work Experience:\n"
    "Data Analyst\n"
    "Example Analytics Inc\n"
    "2021 - Present\n"
    "- Wrote SQL queries for monthly reporting.\n"
    "- Created dashboards used by the whole team.\n"
    "\n"
    "Personal Projects:\n"
    "Budget App\n"
    "- Built a budgeting tool with Python and Flask.\n"
    "\n"
    "Technical Expertise:\n"
    "Python, SQL, Tableau, Excel\n"
)

MISSING_SECTIONS_RESUME = "Taylor Morgan\ntaylor.morgan@example.com\n"

REORDERED_RESUME = (
    "Morgan Blake\n"
    "morgan.blake@example.com\n"
    "\n"
    "Skills:\n"
    "Java, Spring Boot, MySQL, Docker\n"
    "\n"
    "Projects:\n"
    "Inventory Service\n"
    "- Built an inventory service using Java and MySQL.\n"
    "- Added caching with Redis for hot lookups.\n"
    "\n"
    "Education:\n"
    "Bachelor of Computer Science\n"
    "Example Institute of Technology\n"
    "2016 - 2020\n"
    "\n"
    "Experience:\n"
    "Junior Developer at Example Labs\n"
    "2020 - 2023\n"
    "- Implemented REST endpoints for internal services.\n"
    "- Fixed defects reported by the support team.\n"
)

DUPLICATE_SKILLS_RESUME = (
    "Casey Nguyen\n"
    "casey.nguyen@example.com\n"
    "\n"
    "Skills:\n"
    "Python, Python, SQL, sql, Docker\n"
    "\n"
    "Education:\n"
    "Bachelor of Information Systems\n"
    "Example College, 2019 - 2023\n"
    "\n"
    "Projects:\n"
    "Reporting Tool\n"
    "- Built a reporting tool with Python and SQL.\n"
)

_LONG_BULLET = (
    "Responsible for a very broad range of activities across many different teams and "
    "systems including but not limited to maintaining legacy services, writing extensive "
    "documentation, coordinating with stakeholders, preparing weekly status reports, and "
    "supporting a wide variety of unrelated operational tasks over an extended period of time."
)

LONG_BULLET_RESUME = (
    "Riley Cooper\n"
    "riley.cooper@example.com\n"
    "\n"
    "Experience:\n"
    "Operations Assistant\n"
    "Example Services Ltd\n"
    "2020 - 2023\n"
    f"- {_LONG_BULLET}\n"
    "- I was responsible for team player duties.\n"
    "\n"
    "Skills:\n"
    "Excel, Word\n"
)

INCONSISTENT_DATES_RESUME = (
    "Drew Patel\n"
    "drew.patel@example.com\n"
    "\n"
    "Experience:\n"
    "Support Analyst\n"
    "Example Systems\n"
    "2019 - 2015\n"
    "- Handled support tickets for internal users.\n"
    "\n"
    "Education:\n"
    "Bachelor of Commerce\n"
    "Example College\n"
    "2014 - 2018\n"
)

UNPARSEABLE_TEXT = "qqqq qqqq qqqq qqqq qqqq qqqq"
