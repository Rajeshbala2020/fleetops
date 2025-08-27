import glob
import json
import os
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Document, VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.embeddings.openai import OpenAIEmbedding
import app


class RAGPipeline:
    def __init__(self, data_dir="app/source_files/", index_dir="app/index_storage"):
        self.data_dir = data_dir
        self.index_dir = index_dir
        self.index = None
        self._build_or_load_index()

    def get_corpus_data(self, question: str, top_k: int = 2) -> list:
        """
        Retrieve top-k relevant context chunks for a question using LlamaIndex.
        """
        module_names = [os.path.splitext(f)[0].replace('_', ' ').title()
                        for f in os.listdir(self.data_dir) if f.endswith('.json')]
        question_context = f"{question}, Company System: MIPS, Modules: {', '.join(module_names)}"
        try:
            nodes = self.index.as_retriever(similarity_top_k=top_k).retrieve(question_context)
            context_chunks = [node.get_content() for node in nodes]
            return context_chunks
        except Exception as e:
            app.logger.error(f"Error retrieving corpus data: {e}", exc_info=True)
            raise

    def flatten_pages(self, page, parent_title=""):
        docs = []
        title = page["title"]
        content = page.get("content", "").strip()
        full_title = f"{parent_title} > {title}" if parent_title else title
        docs.append(Document(text=content, metadata={"title": full_title, "id": page["id"]}))
        for child in page.get("children", []):
            docs.extend(self.flatten_pages(child, full_title))
        return docs

    def _build_or_load_index(self):
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-large-en-v1.5")

        if os.path.exists(self.index_dir) and os.listdir(self.index_dir):
            # Load index if it exists
            storage_context = StorageContext.from_defaults(persist_dir=self.index_dir)
            self.index = load_index_from_storage(storage_context, embed_model=embed_model)
        else:
            # Build new index from JSON documents
            documents = []
            for file in glob.glob(os.path.join(self.data_dir, "*.json")):
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    flattened = self.flatten_pages(data)
                    documents.extend(flattened)
            self.index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
            self.index.storage_context.persist(persist_dir=self.index_dir)
