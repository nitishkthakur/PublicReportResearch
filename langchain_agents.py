"""Utilities for building a simple RAG pipeline with LangChain."""

from __future__ import annotations

import os
from typing import List, Iterable, Optional

import pdfplumber
from langchain.docstore.document import Document
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter
)
from langchain_experimental.text_splitter import SemanticChunker
from langchain.embeddings import OllamaEmbeddings
from langchain.vectorstores import FAISS
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOllama



class RAG:
    """Simple Retrieval-Augmented Generation helper."""

    def __init__(
        self,
        chunker: str = "recursive",
        chunk_size: int = 3000,
        chunk_overlap: int = 500,
        n_results: int = 10,
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "qwen2.5:7b",
    ) -> None:
        self.chunker = chunker
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.n_results = n_results
        self.embedding_model_name = embedding_model
        self.llm_model_name = llm_model

        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.llm = ChatOllama(model=llm_model)

        self.vector_store: Optional[FAISS] = None

    # ------------------------------------------------------------------
    # Document Loading utilities
    # ------------------------------------------------------------------
    def _load_pdf(self, path: str) -> List["Document"]:
        docs: List[Document] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                tables = []
                for tbl in page.extract_tables():
                    rows = ["\t".join(cell or "" for cell in row) for row in tbl]
                    tables.append("\n".join(rows))

                metadata = {
                    "filename": os.path.basename(path),
                    "page": i,
                    "tables": tables,
                }
                docs.append(Document(page_content=text, metadata=metadata))
        return docs

    def load_documents(self, folder: str) -> List["Document"]:
        """Load all PDF documents from *folder*."""
        documents: List[Document] = []
        for name in os.listdir(folder):
            if name.lower().endswith(".pdf"):
                documents.extend(self._load_pdf(os.path.join(folder, name)))
        return documents

    # ------------------------------------------------------------------
    # Vector store helpers
    # ------------------------------------------------------------------
    def _split_documents(self, documents: List["Document"]) -> List["Document"]:
        if self.embeddings is None:
            raise ImportError("LangChain embeddings are required")

        if self.chunker == "semantic":
            splitter = SemanticChunker(
                embeddings=self.embeddings,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        return splitter.split_documents(documents)

    def build_vector_store(self, folder: str) -> None:
        """Read all PDFs from *folder* and build the FAISS vector store."""
        documents = self.load_documents(folder)
        chunks = self._split_documents(documents)
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)

    def save_vector_store(self, path: str) -> None:
        if self.vector_store is None:
            raise ValueError("Vector store has not been built")
        self.vector_store.save_local(path)

    def load_vector_store(self, path: str) -> None:
        if self.embeddings is None:
            raise ImportError("LangChain embeddings are required")
        self.vector_store = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization = True)

    def _get_retriever(self) -> "MultiQueryRetriever":
        if self.vector_store is None:
            raise ValueError("Vector store is not initialized")
        base = self.vector_store.as_retriever(search_kwargs={"k": self.n_results})
        return MultiQueryRetriever.from_llm(self.llm, base)

    # ------------------------------------------------------------------
    # User facing methods
    # ------------------------------------------------------------------
    def invoke(self, question: str) -> str:
        """Return the answer to ``question`` using retrieval augmented generation."""
        retriever = self._get_retriever()
        chain = RetrievalQA.from_chain_type(self.llm, retriever=retriever)
        result = chain.invoke({"query": question})
        return result["result"] if isinstance(result, dict) else result

    def stream(self, question: str) -> Iterable[str]:
        """Yield the answer tokens for ``question`` as they are produced."""
        retriever = self._get_retriever()
        chain = RetrievalQA.from_chain_type(self.llm, retriever=retriever, streaming=True)
        for chunk in chain.stream({"query": question}):
            if isinstance(chunk, dict):
                yield chunk.get("result", "")
            else:
                yield chunk

