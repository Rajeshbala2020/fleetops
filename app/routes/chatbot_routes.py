# app/routes/chatbot_routes.py
import os
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.routing import APIRouter
from starlette.responses import JSONResponse, PlainTextResponse, StreamingResponse
from slowapi.errors import RateLimitExceeded
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from app import limiter, logger
from pydantic import ValidationError
from app.services.schemas import ChatRequest

chatbot_bp = APIRouter()


project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_dir = os.path.join(project_root, "app","templates")
templates = Jinja2Templates(directory=templates_dir)


def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return PlainTextResponse("Rate limit exceeded", status_code=HTTP_429_TOO_MANY_REQUESTS)


def init_chatbot_routes(app, chatbot_service, db_service, web_search_service):

    def research_wrapper(question: str) -> str:
        try:
            logger.info(f"Starting web search for: {question}")
            rephrased_query = web_search_service.rephrase_query(question, chatbot_service.chat_history)
            logger.info(f"Rephrased query: {rephrased_query}")
            context_chunks = db_service.get_corpus_data(question)
            web_context = web_search_service.do_web_search(rephrased_query)
            logger.info(f"Web search completed, found {len(web_context.split('Title:')) - 1} results")
            # Combine web context and context chunks into a list
            combined_context = [web_context] + context_chunks
            chatbot_service.sent_tokens = combined_context
            chatbot_service.update_system_message()
            return web_context + "\n".join(context_chunks)
        except Exception as e:
            logger.error(f"Error in research_wrapper: {e}")
            # Fallback to just context chunks
            context_chunks = db_service.get_corpus_data(question)
            chatbot_service.sent_tokens = context_chunks
            chatbot_service.update_system_message()
            return "\n".join(context_chunks)
        
        
    
    chatbot_service.set_function("research_wrapper", research_wrapper)

    @chatbot_bp.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        return templates.TemplateResponse("index.html",
                                          {"request": request, "chat_history": chatbot_service.chat_history})

    @chatbot_bp.post('/get-bot-response', response_class=StreamingResponse)
    @limiter.limit("5/minute")
    async def get_bot_response(request: Request):
        try:

            data = await request.json()

            validated = ChatRequest(**data)
            question = validated.question

            context_chunks = db_service.get_corpus_data(question)
            chatbot_service.sent_tokens = context_chunks  # Keep as list
            chatbot_service.update_system_message()

            async def event_stream():
                async for chunk in chatbot_service.generate_response(question):
                    yield chunk

            return StreamingResponse(event_stream(), media_type='text/event-stream')

        except ValidationError as ve:
            return JSONResponse(content={"error": ve.errors()}, status_code=400)
        except KeyError as ke:
            logger.error(f"KeyError: {ke}")
            return JSONResponse(content={"error": f"Missing key in request: {str(ke)}"}, status_code=400)
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            return JSONResponse(content={"error": f"Invalid data: {str(ve)}"}, status_code=400)
        except Exception as e:
            logger.exception("Unexpected error:")
            return JSONResponse(content={"error": "An unexpected error occurred. Please try again later."},
                                status_code=500)

    app.include_router(chatbot_bp)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
