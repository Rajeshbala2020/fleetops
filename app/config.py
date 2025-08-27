from dotenv import load_dotenv
import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(base_dir, ".env")

# Load .env from the root project directory
load_dotenv(dotenv_path=env_path)


class Config:

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SERP_API_KEY = os.getenv("SERP_API_KEY")