import tracemalloc
import os
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address
import openai

tracemalloc.start()
limiter = Limiter(key_func=get_remote_address)

log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_errors.log')
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_file,
    filemode="a"
)
logger = logging.getLogger("FleetOpsLogger")
logger.setLevel(logging.DEBUG)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import Config
from slowapi.middleware import SlowAPIMiddleware

from app.services.chatbot_service import ChatbotService
from app.services.rag_service import RAGPipeline
from app.services.web_search_service import WebSearchService


def create_app() -> FastAPI:
    app = FastAPI(title="FleetOps API", description="Fleet Operations Assistant API", version="1.0.0")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure this based on your frontend domain in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SlowAPIMiddleware)

    # Validate required environment variables
    if not Config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY environment variable is not set")
        raise ValueError("OPENAI_API_KEY environment variable is required")

    if not Config.SERP_API_KEY:
        logger.error("SERP_API_KEY environment variable is not set")
        raise ValueError("SERP_API_KEY environment variable is required")

    openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    chatbot_service = ChatbotService(Config.OPENAI_API_KEY)
    rag_pipeline = RAGPipeline(
        data_dir="app/source_files/",
        index_dir="app/index_storage"
    )
    web_search_service = WebSearchService(openai_client, Config.SERP_API_KEY)

    from app.routes.chatbot_routes import init_chatbot_routes
    init_chatbot_routes(app, chatbot_service, rag_pipeline, web_search_service)

    return app


__all__ = ["create_app", "logger", "limiter", "tracemalloc"]
