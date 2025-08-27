import json
import logging
import openai
from openai.types.chat import ChatCompletionChunk
from app import logger
import asyncio
from typing import Optional, AsyncGenerator 
from typing import Callable
from io import StringIO
import os

class ChatbotService:
    def __init__(self, openai_api_key: str):
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.response_buffer = StringIO()
        self.argument_buffer = StringIO()
        self.directory = "app/source_files/"
        self.json_files = [os.path.join(self.directory, f) for f in os.listdir(self.directory) if f.endswith('.json')]
        self.sent_tokens = []
        self.chat_history = []
        self.research_functions = {}
        self.current_module_file = None
        self.system_message = "System initializing."
        self.fallback_responses = {
            'greeting': "Hello! I'm having trouble connecting to my main system, please try again later.",
            'help': "I'm currently operating in limited mode. Please try asking your question again in a few minutes.",
            'default': "I apologize, but I'm currently experiencing technical difficulties. Please try again in a few minutes."
        }
        self.functions = [
            {
                "name": "research_wrapper",
                "description": "Rephrase the user's question to do a web search to find relevant information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The user's question to to be rephrased and web searched."
                        }
                    },
                    "required": ["question"]
                }
            }
        ]
        self.messages = [{"role": "system", "content": self.system_message}]
    
    def set_function(self, name: str, func: Callable):
        self.research_functions[name] = func
    
    def update_system_message(self):
        # Handle sent_tokens properly - ensure it's always a list
        if isinstance(self.sent_tokens, list):
            context_str = '\n\n'.join(self.sent_tokens)
        else:
            context_str = str(self.sent_tokens) if self.sent_tokens else ""
    
        self.system_message = f""" 
        ROLE & PURPOSE  
        You are a professional, helpful AI assistant who communicates with clarity, precision, and empathy. Your goal is to deliver structured, visually clear, and engaging answers. 
        
        FUNCTION CALLING  
        You can call the `research_wrapper` tool for **company information** or detailed background data. Trigger it when the user: 
        - Asks about companies, products, services, or topics not in your internal knowledge  
        - Uses trigger words: “search”, “find”, “look up”, “check”, “investigate”, “explore”  
        - Requests information that requires web search or external data retrieval.

        CONTEXT USAGE  
        - You will receive the users conversation context and chat history.  
        - Always use them internally to understand the user’s needs.  
        - Never mention, quote, or hint that they exist.  
        - Rephrase or summarize relevant details naturally into your answer without revealing their source.

        '''
        CONTEXT
        {context_str}
        '''

        OUTPUT STRUCTURE  
        Every answer must be visually rich, easy to scan, and engaging:  
        1. **Main Answer** — Use bold, italics, bullet points, numbered lists, and emojis.  
        2. **Steps or Process** — Present in ordered lists when explaining actions.  
        3. **Tables** — Use valid Markdown table syntax (header + separator row).  
        4. **Code or Formulas** — Wrap in triple backticks (```) with language tag. Keep formulas on a single line.  
        5. **Related Questions** — End with 2–3 natural, relevant next questions (never label them as “follow-ups”).  

        STRICT RULES  
        - Always answer using the provided context & history; use outside knowledge only when calling `research_wrapper`.  
        - Focus entirely on the query; keep responses free of references to yourself, your capabilities, or the system.  
        - Format tables in Markdown or HTML, never using plain-text “pipes”.  
        - When something is unclear, ask a concise and polite clarifying question.  
        - For sensitive data, respond respectfully and decline to proceed if it cannot be shared.

        
        STYLE & TONE  
        - Warm and approachable greeting if the user greets you  
        - Calm and supportive for confusion/frustration  
        - Concise and energetic for curiosity  
        - Empathetic and insightful at all times  
        - Stay entirely on the user’s task
        """
        self.messages[0] = {"role": "system", "content": self.system_message}

    def get_fallback_response(self, query: str) -> str:
        """Provide fallback responses when OpenAI is down"""
        query = query.lower()

        if any(word in query for word in ['hello', 'hi', 'hey', 'greetings']):
            return self.fallback_responses['greeting']

        if 'help' in query or 'what can you do' in query:
            return self.fallback_responses['help']

        return self.fallback_responses['default']

    async def gpt_engine(self, max_retries=3, delay=2) -> Optional[AsyncGenerator[ChatCompletionChunk, None]]:
        retries = 0
        models = ["gpt-4.1-mini", "gpt-5-mini"]  # Model fallback mechanism

        for model in models:
            while True:
                try:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=self.messages,
                        functions=self.functions,  # Add function calling capability
                        function_call="auto",  # Let GPT decide when to call a function
                        max_completion_tokens=1000,  # Increased max tokens for more detailed responses
                        temperature=0.3,
                        stream=True
                    )
                    logging.info(f"Successfully used {model} for response")
                    return response
                except Exception as e:
                    logging.error(f"Error with {model}: {str(e)}")
                    if retries < max_retries:
                        retries += 1
                        await asyncio.sleep(delay * retries)
                        continue
                    # If all retries failed for this model, try the next model
                    break
        # If all models failed, use fallback
        logger.warning("All GPT models failed, using fallback response")
        return None

    async def generate_response(self, query: str) -> AsyncGenerator[str, None]:
        import app.routes.chatbot_routes as chatbot_routes 
        """Generate a streaming response."""
        try:
            # Add user message to chat history
            self.messages.append({"role": "user", "content": query})

            # Get the stream from gpt_engine
            stream = await self.gpt_engine()
            if stream is None:
                fallback_text = self.get_fallback_response(query)
                for chunk in fallback_text.splitlines():
                    yield chunk
                return

            function_call = None
          
            # Reset buffers for each new query - use fresh instances to prevent memory fragmentation
            if hasattr(self, 'response_buffer'):
                self.response_buffer.close()
            if hasattr(self, 'argument_buffer'):
                self.argument_buffer.close()
            
            self.response_buffer = StringIO()
            self.argument_buffer = StringIO()
            
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if hasattr(delta, "function_call") and delta.function_call:
                    if delta.function_call.name:
                        function_call = delta.function_call.name
                    if delta.function_call.arguments:
                        self.argument_buffer.write(delta.function_call.arguments)
                    continue

                if hasattr(delta, "content") and delta.content:
                    content = delta.content
                    self.response_buffer.write(content)
                    yield f"data: {json.dumps({'content': content})}\n\n"

            # Get function arguments after the loop ends
            function_args_str = self.argument_buffer.getvalue()
            self.argument_buffer.close()

            if function_call == "research_wrapper":
                logging.info(f"Web search triggered for query: {query}")
                try:
                    # More robust JSON parsing with better error handling
                    if function_args_str and function_args_str.strip():
                        args_dict = json.loads(function_args_str)
                    else:
                        args_dict = {"question": query}
                except (json.JSONDecodeError, ValueError) as e:
                    logging.warning(f"Failed to parse function arguments: {e}, using fallback")
                    args_dict = {"question": query}

                question_arg = args_dict.get("question", query)  # fallback to original query
                
                # Check if research_wrapper function exists
                if "research_wrapper" not in self.research_functions:
                    logging.error("research_wrapper function not found")
                    yield f"data: {json.dumps({'error': 'Research function not available'})}\n\n"
                    return
                    
                context = self.research_functions["research_wrapper"](question_arg)
                self.messages.append({
                    "role": "function",
                    "name": function_call,
                    "content": context if function_call == "research_wrapper" else ""
                })

                followup_stream = await self.gpt_engine()
                
                if followup_stream is None:
                    yield f"data: {json.dumps({'error': 'Failed to generate followup response'})}\n\n"
                    return
                
                # Use StringIO for followup stream too
                followup_buffer = StringIO()
                try:
                    async for chunk in followup_stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            followup_buffer.write(content)
                            yield f"data: {json.dumps({'content': content})}\n\n"
                    
                    # Get the followup response
                    followup_response = followup_buffer.getvalue()
                finally:
                    followup_buffer.close()
                
                # Combine with main response
                full_response = self.response_buffer.getvalue() + followup_response

            # Get the final response from the buffer
            full_response = self.response_buffer.getvalue()
            
            # Handle sent_tokens properly - it could be a string or list
            context_reference = ""
            if self.sent_tokens:
                if isinstance(self.sent_tokens, list):
                    context_reference = "\n".join(self.sent_tokens)
                else:
                    context_reference = str(self.sent_tokens)

            
            self.response_buffer.write("\n\n")
            self.response_buffer.write(context_reference)

            assistant_message = self.response_buffer.getvalue()
            self.response_buffer.close()

            self.messages.append({"role": "assistant", "content": assistant_message})
            self.add_to_history(user_message=query, bot_response=full_response)

            yield f"data: {json.dumps({'end': True})}\n\n"

        except Exception as e:
            logging.error(f"Error in generate_response: {e}", exc_info=True)
            error_message = f"An error occurred while processing your request. Please try again."
            yield f"data: {json.dumps({'error': error_message})}\n\n"

    def add_to_history(self, user_message: str, bot_response: str) -> None:
        """Add a conversation exchange to the chat history."""
        self.chat_history.append({
            'user': user_message,
            'bot': bot_response
        })
    
    
