"""Utilities for building a simple RAG pipeline with LangChain."""

from __future__ import annotations
from IPython.display import HTML, display, Markdown
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
from langchain.prompts import PromptTemplate
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain.chains import RetrievalQA
from langchain.schema import SystemMessage, HumanMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

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
        system_instructions: Optional[str] = "",
    ) -> None:
        self.chunker = chunker
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.n_results = n_results
        self.embedding_model_name = embedding_model
        self.llm_model_name = llm_model
        self.system_instructions = system_instructions

        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.llm = ChatOllama(model=llm_model)

        self.vector_store: Optional[FAISS] = None

    # ------------------------------------------------------------------
    # Document Loading utilities
    # ------------------------------------------------------------------
    def _load_pdf(self, path: str) -> List[Document]:
        """Load PDF, extract text-only pages, and store tables as raw, HTML, and Markdown."""
        docs: List[Document] = []
        for name, page in pdfplumber.open(path).pages.items() if False else []:
            # This dummy loop to satisfy static code before opening real loop below
            pass
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                # Extract page text
                text = page.extract_text() or ""
                # Prepare table formats
                tables_raw, tables_html, tables_md = [], [], []
                for tbl in page.extract_tables():
                    # Raw text representation
                    rows = ["\t".join(cell or "" for cell in row) for row in tbl]
                    raw = "\n".join(rows)
                    tables_raw.append(raw)
                    # HTML table
                    html_rows = []
                    for row in tbl:
                        cells = [f"<td>{cell or ''}</td>" for cell in row]
                        html_rows.append(f"<tr>{''.join(cells)}</tr>")
                    html = f"<table>{''.join(html_rows)}</table>"
                    tables_html.append(html)
                    # Markdown table (assume first row is header)
                    header = tbl[0]
                    sep = ["---" for _ in header]
                    md = ["| " + " | ".join(cell or "" for cell in header) + " |"]
                    md.append("| " + " | ".join(sep) + " |")
                    for body in tbl[1:]:
                        md.append("| " + " | ".join(cell or "" for cell in body) + " |")
                    tables_md.append("\n".join(md))
                metadata = {
                    "filename": os.path.basename(path),
                    "page": i,
                    "tables_raw": tables_raw,
                    "tables_html": tables_html,
                    "tables_md": tables_md,
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
                min_chunk_size=self.chunk_size
            )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        return splitter.split_documents(documents)

    def build_vector_store(self, folder: str) -> None:
        """Read all PDFs from *folder* and build the FAISS vector store."""
        self.documents_store = documents = self.load_documents(folder)
        self.chunk_store = chunks = self._split_documents(documents)
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
        return MultiQueryRetriever.from_llm(base, self.llm)

    # ------------------------------------------------------------------
    # User facing methods
    # ------------------------------------------------------------------
    def invoke(self, question: str) -> str:
        """Return the answer to ``question`` using retrieval augmented generation."""
        retriever = self._get_retriever()
        # Use raw question for retrieval; instruct the LLM with the pre_prompt
        '''prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=self.system_instructions + "\n\nContext:\n{context}\n\nQuestion: {question}",
        )'''

        '''prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_instructions),
            MessagesPlaceholder(variable_name="context"),
            ("human", "{question}"),
        ])'''

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Use context to answer. Context: {context}"),
            ("human", "{input}"),
        ])
        '''chain = RetrievalQA.from_chain_type(
            self.llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt},
        )'''
        doc_chain = create_stuff_documents_chain(self.llm, prompt)
        chain = create_retrieval_chain(retriever, doc_chain)
        result = chain.invoke({"input": question})

        print(result)
        #return result["result"] if isinstance(result, dict) else result
        return result, result.get("answer") or result.get("result") or result.get("text")

    def stream(self, question: str) -> Iterable[str]:
        """Yield the answer tokens for ``question`` as they are produced."""
        retriever = self._get_retriever()
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=self.pre_prompt + "\n\nContext:\n{context}\n\nQuestion: {question}",
        )
        chain = RetrievalQA.from_chain_type(
            self.llm,
            retriever=retriever,
            chain_type="stuff",
            chain_type_kwargs={"prompt": prompt_template},
            streaming=True,
        )
        for chunk in chain.stream({"query": question}):
            if isinstance(chunk, dict):
                yield chunk.get("result", "")
            else:
                yield chunk


    def evaluate_queries(self, queries: List[str], top_n: int = 3) -> None:
        """Run multiple queries and display top-n chunks for each in HTML, including file info."""
        html = ["<html><body>"]
        for q in queries:
            html.append(f"<h2>Query: {q}</h2>")
            retriever = self._get_retriever()
            docs = retriever.get_relevant_documents(q)[:top_n]
            for idx, doc in enumerate(docs, start=1):
                filename = doc.metadata.get("filename", "<unknown file>")
                page = doc.metadata.get("page", "<unknown page>")
                html.append(f"<h3>Result {idx} — {filename}, page {page}</h3>")
                html.append(f"<p>{doc.page_content[:200]}...</p>")
                # show tables if present
                for tbl_html in doc.metadata.get("tables_html", []):
                    html.append(tbl_html)
                html.append("<hr>")
        html.append("</body></html>")
        display(HTML(''.join(html)))
        return ''.join(html)

