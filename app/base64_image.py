import glob 
import os 
import json 
from typing import List, Any 
from llama_index.embeddings.huggingface import HuggingFaceEmbedding 
from llama_index.core import VectorStoreIndex, Document, StorageContext, load_index_from_storage 
from transformers import AutoModelForCausalLM, AutoTokenizer 
import requests

os.environ["HUGGINGFACE_HUB_TOKEN"] = "xxxx" 
token = os.environ["HUGGINGFACE_HUB_TOKEN"] 

class OfflineModel: 
    def __init__(self, data_dir="asource_files/", index_dir="inde_storage/"): 
        self.index = None 
        self.data_dir = data_dir 
        self.index_dir = index_dir 
        self.model_name = "meta-llama/Llama-3.1-8B-Instruct" 
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name,token=token) 
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, token=token, device_map="cpu", load_in_8bit=True) 
        self._build_or_load_index() 
    
    def flatten_pages(self, page, parent_title=""): 
        docs = [] 
        title = page.get("title", "") 
        content = page.get("content", "").strip() 
        full_title = f"{parent_title} > {title}" if parent_title else title 
        docs.append(Document(text=content, metadata={"title": full_title, "id": page["id"]})) 
        for child in page.get("children", []): 
            docs.extend(self.flatten_pages(child, full_title)) 
            return docs 
        
    def _build_or_load_index(self): 
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-en-v1.5") 
        if os.path.exists(self.index_dir) and os.listdir(self.index_dir): #Load index if it exists 
            storage_context = StorageContext.from_defaults(persist_dir=self.index_dir) 
            self.index = load_index_from_storage(storage_context, embed_model=embed_model) 
        else: 
            documents = [] 
            for file in glob.glob(os.path.join(self.data_dir, "*.json")): 
                with open(file, "r", encoding="utf-8") as f: 
                    data = json.load(f) 
                    flattened = self.flatten_pages(data) 
                    documents.extend(flattened) 
                    self.index = VectorStoreIndex.from_documents(documents, embed_model=embed_model) 
                    self.index.storage_context.persist(persist_dir=self.index_dir) 
    
    def retrieve(self, query: str, top_k: int = 2) -> list: 
        module_names = [os.path.splitext(f)[0].replace('_', ' ').title() for f in os.listdir(self.data_dir) if f.endswith('.json')] 
        question_context = f"{query}, Company System: MIPS, Modules: {', '.join(module_names)}" 
        try: 
            nodes = self.index.as_retriever(similarity_top_k=top_k).retrieve(question_context) 
            context_chunks = [node.get_content() for node in nodes] 
            return context_chunks 
        except Exception as e: print(f"Error: {e}") 
    
    def ask_llama(self, query: str) -> str: 
        context_docs = self.retrieve(query, top_k=2) 
        context = "\n".join(context_docs) 
        url = "http://localhost:11434/api/generate"

        prompt = f""" 
        ROLE & PURPOSE  
        You are a professional, helpful AI assistant who communicates with clarity, precision, and empathy. Your goal is to deliver structured, visually clear, and engaging answers. 
        
        CONTEXT USAGE  
        - You will receive the users conversation context and chat history.  
        - Always use them internally to understand the user’s needs.  
        - Never mention, quote, or hint that they exist.  
        - Rephrase or summarize relevant details naturally into your answer without revealing their source.

        '''
        CONTEXT
        {context}
        '''

        OUTPUT STRUCTURE  
        Every answer must be visually rich, easy to scan, and engaging:  
        1. **Related Questions** — End with 2–3 natural, relevant next questions (never label them as “follow-ups”).  

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

        payload = {
        "model": self.model_name,   # you can change this to "llama2:8b", "mistral:7b", etc.
        "prompt": prompt,
        "stream": True   # set True if you want streaming responses
        }
        
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device) 
        outputs = self.model.generate(**inputs, max_new_tokens=1000, temperature=0.3) 
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True) 

if __name__ == '__main__': 
    bot = OfflineModel() 
    while True: 
        query = input("Ask anything (or 'quit'): ") 
        if query.lower() in ["quit", "exit"]: 
            break 
        answer = bot.ask_llama(query) 
        print("🤖:", answer) 
