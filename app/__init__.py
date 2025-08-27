import logging
import os
import tracemalloc

import openai
from slowapi import Limiter
from slowapi.util import get_remote_address

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
from slowapi.middleware import SlowAPIMiddleware

from app.config import Config
from app.services.chatbot_service import ChatbotService
from app.services.rag_service import RAGPipeline
from app.services.web_search_service import WebSearchService


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(SlowAPIMiddleware)

    # Validate required environment variables (with deployment-friendly defaults)
    if not Config.OPENAI_API_KEY or Config.OPENAI_API_KEY == "placeholder_key_set_in_dashboard":
        logger.warning("OPENAI_API_KEY environment variable is not properly set - using placeholder")
        # Don't raise error to allow app to start for health checks
        
    if not Config.SERP_API_KEY or Config.SERP_API_KEY == "placeholder_key_set_in_dashboard":
        logger.warning("SERP_API_KEY environment variable is not properly set - using placeholder")
        # Don't raise error to allow app to start for health checks

    openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    chatbot_service = ChatbotService(Config.OPENAI_API_KEY)
    rag_pipeline = RAGPipeline(
        data_dir="app/source_files/",
        index_dir="app/index_storage"
    )
    web_search_service = WebSearchService(openai_client, Config.SERP_API_KEY)

    # Add health check endpoint
    @app.get("/")
    async def health_check():
        return {"status": "healthy", "app": "FleetOps"}
    
    @app.get("/health")
    async def detailed_health():
        return {
            "status": "healthy", 
            "app": "FleetOps",
            "openai_configured": bool(Config.OPENAI_API_KEY and Config.OPENAI_API_KEY != "placeholder_key_set_in_dashboard"),
            "serp_configured": bool(Config.SERP_API_KEY and Config.SERP_API_KEY != "placeholder_key_set_in_dashboard")
        }

    from app.routes.chatbot_routes import init_chatbot_routes
    init_chatbot_routes(app, chatbot_service, rag_pipeline, web_search_service)

    return app


__all__ = ["create_app", "logger", "limiter", "tracemalloc"]
