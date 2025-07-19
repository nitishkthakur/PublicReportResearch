import os
import re
import faiss
import numpy as np
import PyPDF2
from typing import List, Dict, Tuple, Callable, Any, Optional
from dataclasses import dataclass

@dataclass
class Document:
    """Document class to store text and metadata."""
    text: str
    metadata: Dict[str, Any]

@dataclass
class Chunk:
    """Chunk class to store chunk text and metadata."""
    text: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None

class RecursiveCharacterSplitter:
    """
    Custom recursive character splitter that splits text into chunks.
    """
    
    def __init__(self, 
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 separators: List[str] = ["\n\n", "\n", ". ", ", ", " "]):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators
    
    def split_text(self, text: str) -> List[str]:
        """
        Recursively split text into chunks based on separators.
        """
        # If text is already smaller than chunk_size, return it as is
        if len(text) <= self.chunk_size:
            return [text]
        
        # Try each separator in order
        for separator in self.separators:
            if separator in text:
                # Split by this separator
                splits = text.split(separator)
                
                # Merge splits that are too small
                merged_splits = []
                current_chunk = ""
                
                for split in splits:
                    if len(current_chunk) + len(split) + len(separator) <= self.chunk_size:
                        # Add separator only if current_chunk is not empty
                        if current_chunk:
                            current_chunk += separator
                        current_chunk += split
                    else:
                        # If current chunk is not empty, add it to the list
                        if current_chunk:
                            merged_splits.append(current_chunk)
                        
                        # Start a new chunk
                        current_chunk = split
                
                # Add the last chunk if not empty
                if current_chunk:
                    merged_splits.append(current_chunk)
                
                # Apply overlapping
                result = []
                for i in range(len(merged_splits)):
                    # Get the current chunk
                    chunk = merged_splits[i]
                    
                    # If not the first chunk, include overlap from previous chunk
                    if i > 0:
                        prev_chunk = merged_splits[i-1]
                        overlap_text = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) > self.chunk_overlap else prev_chunk
                        chunk = overlap_text + separator + chunk
                    
                    # If not the last chunk, include overlap into next chunk
                    if i < len(merged_splits) - 1:
                        next_chunk = merged_splits[i+1]
                        overlap_text = next_chunk[:self.chunk_overlap] if len(next_chunk) > self.chunk_overlap else next_chunk
                        chunk = chunk + separator + overlap_text
                    
                    result.append(chunk)
                
                # If we have valid chunks, return them
                if result:
                    return result
        
        # If no separator was found, force split by chunk size
        result = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk:
                result.append(chunk)
        
        return result

class ManualRAG:
    """
    RAG implementation without using LangChain.
    Uses FAISS for vector storage and a custom recursive character splitter.
    """
    
    def __init__(self, 
                 embedding_func: Callable[[str], np.ndarray],
                 llm: Any,
                 chunk_size: int = 1000,
                 chunk_overlap: int = 200,
                 k: int = 5):
        """
        Initialize the RAG system.
        
        Args:
            embedding_func: Function that takes a string and returns an embedding vector
            llm: LLM model with a chat() method
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
            k: Default number of chunks to retrieve
        """
        self.embedding_func = embedding_func
        self.llm = llm
        self.chunks = []
        self.splitter = RecursiveCharacterSplitter(chunk_size, chunk_overlap)
        self.index = None
        self.k = k
    
    def extract_metadata_from_filename(self, filename: str) -> Dict[str, str]:
        """
        Split the filename on '_' and use the result as metadata.
        
        Args:
            filename: Name of the file
            
        Returns:
            Dictionary containing metadata extracted from filename
        """
        # Get the base filename without extension or path
        base_name = os.path.basename(filename)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # Split by underscore
        parts = name_without_ext.split('_')
        
        # Create metadata dict
        metadata = {
            "filename": base_name,
            "full_path": filename
        }
        
        # Add numbered parts
        for i, part in enumerate(parts):
            metadata[f"part_{i}"] = part
            
        return metadata
    
    def load_documents_from_pdfs(self, directory: str) -> List[Document]:
        """
        Load documents from PDF files in the specified directory.
        
        Args:
            directory: Directory containing PDF files
            
        Returns:
            List of Document objects
        """
        documents = []
        
        for filename in os.listdir(directory):
            if filename.lower().endswith('.pdf'):
                filepath = os.path.join(directory, filename)
                metadata = self.extract_metadata_from_filename(filepath)
                
                # Extract text from PDF
                with open(filepath, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        text += page.extract_text() + "\n\n"
                
                documents.append(Document(text=text, metadata=metadata))
        
        return documents
    
    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """
        Chunk documents and add metadata to each chunk.
        
        Args:
            documents: List of Document objects
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        for doc in documents:
            # Split the document text into chunks
            text_chunks = self.splitter.split_text(doc.text)
            
            # Create chunk objects with metadata
            for text_chunk in text_chunks:
                # Enclose the chunk in metadata tags
                metadata_str = ", ".join([f"{k}={v}" for k, v in doc.metadata.items()])
                chunk_text = f"<metadata={metadata_str}>{text_chunk}</metadata>"
                
                chunks.append(Chunk(text=chunk_text, metadata=doc.metadata))
        
        return chunks
    
    def index_chunks(self, chunks: List[Chunk]) -> None:
        """
        Compute embeddings and index chunks with FAISS.
        
        Args:
            chunks: List of Chunk objects
        """
        self.chunks = chunks
        
        # Compute embeddings for all chunks
        embeddings = []
        for i, chunk in enumerate(chunks):
            embedding = self.embedding_func(chunk.text)
            chunks[i].embedding = embedding
            embeddings.append(embedding)
        
        # Convert to numpy array
        embeddings_array = np.array(embeddings).astype('float32')
        
        # Create FAISS index
        vector_dimension = embeddings_array.shape[1]
        self.index = faiss.IndexFlatL2(vector_dimension)
        self.index.add(embeddings_array)
    
    def retrieve_chunks(self, query: str, n: int = None) -> List[Chunk]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Query string
            n: Number of chunks to retrieve (defaults to self.k)
            
        Returns:
            List of relevant chunks
        """
        if n is None:
            n = self.k
            
        # Compute query embedding
        query_embedding = self.embedding_func(query)
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search in FAISS index
        distances, indices = self.index.search(query_embedding, n)
        
        # Get the chunks
        retrieved_chunks = [self.chunks[idx] for idx in indices[0]]
        
        return retrieved_chunks
    
    def process_documents(self, directory: str) -> None:
        """
        Process all documents in a directory.
        
        Args:
            directory: Directory containing PDF files
        """
        # Load documents
        documents = self.load_documents_from_pdfs(directory)
        
        # Chunk documents
        chunks = self.chunk_documents(documents)
        
        # Index chunks
        self.index_chunks(chunks)
    
    def answer_question(self, query: str, n: int = None) -> str:
        """
        Answer a question using RAG.
        
        Args:
            query: Question to answer
            n: Number of chunks to retrieve
            
        Returns:
            Answer from the LLM
        """
        # Retrieve relevant chunks
        chunks = self.retrieve_chunks(query, n)
        
        # Prepare context for LLM
        context = "\n\n".join([chunk.text for chunk in chunks])
        
        # Prepare prompt for LLM
        prompt = f"Based on the following context, please answer the question:\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        
        # Get answer from LLM
        response = self.llm.chat(prompt)
        
        return response

# Example usage
if __name__ == "__main__":
    # Mock embedding function for demonstration
    def mock_embedding(text):
        # In a real scenario, this would be a call to an embedding model
        return np.random.rand(768)  # Assuming 768-dimensional embeddings
    
    # Mock LLM for demonstration
    class MockLLM:
        def chat(self, prompt):
            return f"This is a mock response to: {prompt[:100]}..."
    
    # Initialize RAG system
    rag = ManualRAG(
        embedding_func=mock_embedding,
        llm=MockLLM()
    )
    
    # Process documents (assuming there are PDFs in the 'documents' directory)
    # rag.process_documents("documents")
    
    # Answer a question
    # answer = rag.answer_question("What is RAG?")
    # print(answer)
