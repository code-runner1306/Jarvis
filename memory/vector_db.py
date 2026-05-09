import chromadb
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from utils.config import settings

class MemoryDB:
    def __init__(self):
        # We will use Ollama's nomic-embed-text for local embeddings.
        # Make sure you have run `ollama pull nomic-embed-text`
        self.embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=settings.OLLAMA_BASE_URL
        )
        
        # Initialize persistent ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Collections for different types of memory
        self.semantic_collection = "semantic_memory"
        self.learning_collection = "learning_content"
        
        self.semantic_store = Chroma(
            client=self.chroma_client,
            collection_name=self.semantic_collection,
            embedding_function=self.embeddings
        )
        
        self.learning_store = Chroma(
            client=self.chroma_client,
            collection_name=self.learning_collection,
            embedding_function=self.embeddings
        )

    def add_semantic_memory(self, text: str, metadata: dict = None):
        """Store facts about the user or important context."""
        doc = Document(page_content=text, metadata=metadata or {})
        self.semantic_store.add_documents([doc])
        return f"Stored semantic memory: '{text[:50]}...'"

    def search_semantic_memory(self, query: str, top_k: int = 3):
        """Retrieve relevant semantic memories based on a query."""
        results = self.semantic_store.similarity_search(query, k=top_k)
        return [doc.page_content for doc in results]
        
    def add_learning_content(self, text: str, metadata: dict = None):
        """Store notes, quiz material, or study context."""
        doc = Document(page_content=text, metadata=metadata or {})
        self.learning_store.add_documents([doc])
        return f"Stored learning content."

    def search_learning_content(self, query: str, top_k: int = 3):
        """Retrieve relevant learning materials based on a query."""
        results = self.learning_store.similarity_search(query, k=top_k)
        return [doc.page_content for doc in results]

# Global instance
memory_db = MemoryDB()
