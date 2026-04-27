"""
Configuration file for the Data Scraping & Trust Scoring pipeline.
Contains URLs to scrape, scoring weights, and domain authority lists.
"""

# ============================================================
# SOURCES TO SCRAPE
# ============================================================

BLOG_URLS = [
    "https://www.technologyreview.com/2025/01/08/1109188/whats-next-for-ai-in-2025/",
    "https://www.healthline.com/nutrition/how-to-start-exercising",
    "https://blog.google/technology/ai/google-gemini-ai/",
]

YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=aircAruvnKk",  # 3Blue1Brown - Neural Networks
    "https://www.youtube.com/watch?v=WXuK6gekU1Y",  # Kurzgesagt - Immune System
]

PUBMED_IDS = [
    "37286606",  # AI in healthcare - recent article
]

# ============================================================
# TRUST SCORE WEIGHTS (must sum to 1.0)
# ============================================================

TRUST_WEIGHTS = {
    "author_credibility": 0.25,
    "citation_count": 0.20,
    "domain_authority": 0.25,
    "recency": 0.15,
    "medical_disclaimer": 0.15,
}

# ============================================================
# DOMAIN AUTHORITY LISTS
# ============================================================

HIGH_AUTHORITY_DOMAINS = [
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "nature.com",
    "who.int",
    "cdc.gov",
    "nih.gov",
    "mayoclinic.org",
    "nejm.org",
    "thelancet.com",
    "bmj.com",
    "openai.com",
    "deepmind.com",
    "arxiv.org",
    "ieee.org",
    "acm.org",
    "sciencedirect.com",
    "springer.com",
]

MEDIUM_AUTHORITY_DOMAINS = [
    "medium.com",
    "towardsdatascience.com",
    "healthline.com",
    "webmd.com",
    "youtube.com",
    "blog.google",
    "microsoft.com",
    "aws.amazon.com",
    "techcrunch.com",
    "wired.com",
    "theverge.com",
    "arstechnica.com",
    "technologyreview.com",
    "youtu.be",
]

LOW_AUTHORITY_DOMAINS = [
    "blogspot.com",
    "wordpress.com",
    "tumblr.com",
    "reddit.com",
    "quora.com",
]

# ============================================================
# KNOWN AUTHORS / ORGANIZATIONS
# ============================================================

KNOWN_ORGANIZATIONS = [
    "WHO", "CDC", "NIH", "Mayo Clinic", "Harvard",
    "Stanford", "MIT", "Oxford", "Cambridge",
    "OpenAI", "Google", "DeepMind", "Microsoft Research", "IBM",
    "Nature", "The Lancet", "NEJM", "BMJ",
]

KNOWN_AUTHORS = [
    "Andrew Ng", "Yoshua Bengio", "Geoffrey Hinton",
    "Yann LeCun", "Andrej Karpathy", "Fei-Fei Li",
]

# ============================================================
# MEDICAL DISCLAIMER KEYWORDS
# ============================================================

MEDICAL_DISCLAIMER_KEYWORDS = [
    "not medical advice",
    "consult your doctor",
    "consult a healthcare",
    "consult your healthcare",
    "disclaimer",
    "for informational purposes",
    "does not constitute medical advice",
    "seek professional medical",
    "talk to your doctor",
    "medical professional",
    "peer-reviewed",
    "clinical trial",
]

# ============================================================
# CHUNKING & TAGGING CONFIG
# ============================================================

MAX_CHUNK_SIZE = 500  # characters per chunk
TOP_N_TOPICS = 8      # number of topic tags to extract

# ============================================================
# GENERIC MESH TERMS TO FILTER (too broad to be useful tags)
# ============================================================

GENERIC_MESH_TERMS = [
    "Humans", "Animals", "Male", "Female", "Adult", "Aged",
    "Middle Aged", "Young Adult", "Child", "Infant", "Adolescent",
    "Child, Preschool", "Infant, Newborn",
    "Mice", "Rats", "Dogs", "Cats", "Rabbits",
    "Prospective Studies", "Retrospective Studies",
    "Treatment Outcome", "Risk Factors",
    "Time Factors", "Age Factors", "Sex Factors",
    "Follow-Up Studies", "Cross-Sectional Studies",
    "United States",
]

# ============================================================
# KNOWN RESEARCH INSTITUTIONS (for affiliation-based scoring)
# ============================================================

KNOWN_INSTITUTIONS = [
    "Harvard", "Stanford", "MIT", "Oxford", "Cambridge",
    "Johns Hopkins", "Mayo Clinic", "Yale", "Princeton",
    "Columbia University", "University of California", "UCLA", "UCSF",
    "University of Toronto", "University of Alberta",
    "University of Michigan", "University of Pennsylvania",
    "Duke University", "Northwestern University",
    "Karolinska", "Max Planck", "ETH Zurich",
    "NIH", "CDC", "WHO", "FDA",
    "Memorial Sloan Kettering", "MD Anderson",
    "Cleveland Clinic", "Mass General",
    "Imperial College", "University College London",
    "Charité", "Heidelberg University",
    "University of Tokyo", "Peking University",
    "National University of Singapore",
    "Faculty of Medicine", "School of Medicine",
    "Medical School", "Medical Center",
    "Institute of Technology", "Research Institute",
    "National Institute", "Research Center",
]

# ============================================================
# ENTREZ CONFIG (PubMed)
# ============================================================

ENTREZ_EMAIL = "abhigupta@example.com"  # Required by NCBI
