"""Deterministic skill taxonomy used to categorise extracted skills.

This is intentionally a fixed, local lookup - no external service or model is
consulted. Unknown skills are preserved in the ``other`` bucket rather than
being dropped or guessed.
"""

from __future__ import annotations

LANGUAGES = {
    "python",
    "java",
    "javascript",
    "typescript",
    "c",
    "c++",
    "c#",
    "sql",
    "pl/sql",
    "plsql",
    "html",
    "html5",
    "css",
    "css3",
    "php",
    "ruby",
    "go",
    "golang",
    "swift",
    "kotlin",
    "r",
    "scala",
    "dart",
    "matlab",
    "bash",
    "shell",
    "perl",
    "objective-c",
    "assembly",
    "rust",
    "vb",
    "vb.net",
    "visual basic",
    "powershell",
    "cobol",
    "fortran",
    "solidity",
    "elixir",
    "haskell",
    "lua",
    "groovy",
    "sass",
    "scss",
    "less",
    "xml",
    "json",
    "yaml",
    "markdown",
    "graphql",
}

FRAMEWORKS = {
    "react",
    "react.js",
    "reactjs",
    "angular",
    "angularjs",
    "vue",
    "vue.js",
    "vuejs",
    "next.js",
    "nextjs",
    "node.js",
    "nodejs",
    "express",
    "express.js",
    "django",
    "flask",
    "fastapi",
    "spring",
    "spring boot",
    "rails",
    "ruby on rails",
    "laravel",
    ".net",
    "dotnet",
    "asp.net",
    "bootstrap",
    "tailwind",
    "tailwind css",
    "jquery",
    "svelte",
    "nuxt",
    "nuxt.js",
    "flutter",
    "react native",
    "tensorflow",
    "pytorch",
    "keras",
    "pandas",
    "numpy",
    "scikit-learn",
    "sklearn",
    "opencv",
    "redux",
    "rest",
    "rest api",
    "celery",
    "hibernate",
    "jpa",
    "electron",
    "three.js",
    "ember",
    "backbone",
    "struts",
    "codeigniter",
}

TOOLS = {
    "git",
    "github",
    "gitlab",
    "bitbucket",
    "docker",
    "kubernetes",
    "k8s",
    "jenkins",
    "aws",
    "amazon web services",
    "azure",
    "gcp",
    "google cloud",
    "heroku",
    "netlify",
    "vercel",
    "linux",
    "unix",
    "windows",
    "macos",
    "mongodb",
    "mysql",
    "postgresql",
    "postgres",
    "sqlite",
    "redis",
    "oracle",
    "sql server",
    "firebase",
    "supabase",
    "jira",
    "confluence",
    "slack",
    "trello",
    "asana",
    "figma",
    "adobe xd",
    "photoshop",
    "illustrator",
    "postman",
    "vs code",
    "visual studio code",
    "visual studio",
    "eclipse",
    "intellij",
    "pycharm",
    "vim",
    "nginx",
    "apache",
    "terraform",
    "ansible",
    "grafana",
    "prometheus",
    "kafka",
    "rabbitmq",
    "spark",
    "hadoop",
    "airflow",
    "selenium",
    "jest",
    "pytest",
    "junit",
    "cypress",
    "webpack",
    "vite",
    "babel",
    "eslint",
    "prettier",
    "npm",
    "yarn",
    "pip",
    "conda",
    "anaconda",
    "unity",
    "blender",
    "tableau",
    "power bi",
    "excel",
    "word",
    "powerpoint",
    "elasticsearch",
    "solr",
    "maven",
    "gradle",
}

# AI / ML and modern LLM-stack terminology. Grouped separately so it can be
# recognised for job-description matching without forcing a storage bucket;
# individual terms fall into "other" unless they are also a known tool.
AI_ML = {
    "llm",
    "llms",
    "large language model",
    "rag",
    "retrieval augmented generation",
    "ai agent",
    "ai agents",
    "prompt engineering",
    "langchain",
    "llamaindex",
    "embeddings",
    "embedding",
    "pinecone",
    "vector database",
    "vector databases",
    "vector store",
    "vector search",
    "nlp",
    "natural language processing",
    "computer vision",
    "generative ai",
    "genai",
    "fine-tuning",
    "fine tuning",
    "hugging face",
    "transformers",
    "openai",
    "mlops",
    "deep learning",
    "machine learning",
    "artificial intelligence",
}

# Common aliases mapped to a canonical spelling for de-duplication.
_ALIASES = {
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "nextjs": "next.js",
    "vuejs": "vue",
    "vue.js": "vue",
    "angularjs": "angular",
    "express.js": "express",
    "nuxt.js": "nuxt",
    "scikit learn": "scikit-learn",
    "node js": "node.js",
    "dot net": ".net",
    "amazon web services": "aws",
    "google cloud platform": "gcp",
    "google cloud": "gcp",
    "sqlserver": "sql server",
    "postgres": "postgresql",
    "plsql": "pl/sql",
    "k8s": "kubernetes",
    "vs code": "visual studio code",
    "golang": "go",
    "rest api": "rest",
    "rest apis": "rest",
    "restful": "rest",
    "restful api": "rest",
    "restful apis": "rest",
    "tailwind css": "tailwind",
    "html5": "html",
    "css3": "css",
    "llms": "llm",
    "large language model": "llm",
    "rag pipelines": "rag",
    "rag pipeline": "rag",
    "retrieval augmented generation": "rag",
    "ai agent": "ai agents",
    "embedding": "embeddings",
    "llama-index": "llamaindex",
    "huggingface": "hugging face",
    "gen ai": "genai",
    "generative ai": "genai",
    "fine tuning": "fine-tuning",
    "vector databases": "vector database",
    "vector db": "vector database",
    "vector store": "vector database",
    "vector search": "vector database",
}


def normalize_skill(raw: str) -> str:
    """Normalise a skill token for matching (lowercase, collapsed spacing)."""
    token = raw.strip().lower()
    token = token.replace("\u2013", "-").replace("\u2014", "-")
    token = " ".join(token.split())
    return token


def canonical_skill(token: str) -> str:
    """Return the canonical display spelling used for de-duplication."""
    normalized = normalize_skill(token)
    return _ALIASES.get(normalized, normalized)


def categorize_skill(token: str) -> str:
    """Return one of ``languages``, ``frameworks``, ``tools`` or ``other``."""
    normalized = normalize_skill(token)
    canonical = _ALIASES.get(normalized, normalized)
    if normalized in LANGUAGES or canonical in LANGUAGES:
        return "languages"
    if normalized in FRAMEWORKS or canonical in FRAMEWORKS:
        return "frameworks"
    if normalized in TOOLS or canonical in TOOLS:
        return "tools"
    return "other"


def known_skill_terms() -> dict[str, str]:
    """Return ``{normalised term: canonical skill}`` for matchable skills.

    Very short tokens (fewer than three characters) are excluded so that common
    words are not mistaken for skills such as ``C`` or ``R``.
    """
    terms: dict[str, str] = {}
    for name in LANGUAGES | FRAMEWORKS | TOOLS | AI_ML:
        if len(name) >= 3:
            terms[name] = canonical_skill(name)
    for alias in _ALIASES:
        if len(alias) >= 3:
            terms[alias] = canonical_skill(alias)
    return terms
