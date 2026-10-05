import os

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

RSS_FEEDS = [
    {
        "name": "OpenAI News",
        "url": "https://openai.com/news/rss.xml",
        "max_items": 8,
    },
    {
        "name": "Google AI",
        "url": "https://blog.google/technology/ai/rss/",
        "max_items": 8,
    },
    {
        "name": "Hugging Face Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "max_items": 8,
    },
    {
        "name": "Microsoft Research",
        "url": "https://www.microsoft.com/en-us/research/feed/",
        "max_items": 8,
    },
    {
        "name": "arXiv cs.AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "max_items": 8,
    },
    {
        "name": "arXiv cs.LG",
        "url": "https://rss.arxiv.org/rss/cs.LG",
        "max_items": 8,
    },
    {
        "name": "arXiv cs.CL",
        "url": "https://rss.arxiv.org/rss/cs.CL",
        "max_items": 8,
    },
]

TECH_KEYWORDS = [
    "ai",
    "artificial intelligence",
    "llm",
    "language model",
    "agent",
    "agents",
    "coding",
    "developer",
    "programming",
    "github",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "deepmind",
    "hugging face",
    "transformer",
    "machine learning",
    "deep learning",
    "inference",
    "training",
    "gpu",
    "nvidia",
    "database",
    "postgres",
    "redis",
    "docker",
    "kubernetes",
    "devops",
    "cloud",
    "security",
    "cybersecurity",
    "compiler",
    "linux",
    "rust",
    "go",
    "python",
    "javascript",
    "typescript",
    "webassembly",
    "mcp",
    "model context protocol",
    "cursor",
    "codex",
]

MAX_HN_STORIES = 35
