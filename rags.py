from typing import List, Iterable, Optional, Dict, Set
import os
import pdfplumber
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain.embeddings import OllamaEmbeddings
from langchain.vectorstores import FAISS
from langchain.chat_models import ChatOllama
from langchain.retrievers import MultiQueryRetriever, EnsembleRetriever
from langchain_community.retrievers.bm25 import BM25Retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from IPython.display import HTML, display

INDEX_DIR = "./faiss_index"

class FilteredRetriever:
    """Wrap a retriever and filter docs by metadata filename."""
    def __init__(self, retriever, filenames: List[str]):
        self.retriever = retriever
        self.filenames: Set[str] = set(filenames)

    def get_relevant_documents(self, query: str, **kwargs) -> List[Document]:
        docs = self.retriever.get_relevant_documents(query, **kwargs)
        return [d for d in docs if d.metadata.get("filename") in self.filenames]

class RAG:
    """Retrieval-Augmented Generation with hybrid retrieval and filename-based filtering."""

    def __init__(
        self,
        chunker: str = "recursive",
        chunk_size: int = 3000,
        chunk_overlap: int = 500,
        n_results: int = 10,
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "qwen2.5:7b",
        bm25_k: int = 5,
        bm25_params: Optional[Dict[str, float]] = None,
        use_hybrid: bool = True,
    ):
        # Chunking
        self.chunker = chunker
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Retrieval parameters
        self.n_results = n_results
        self.use_hybrid = use_hybrid
        self.bm25_k = bm25_k
        self.bm25_params = bm25_params or {"k1": 1.2, "b": 0.75}
        # Models
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.llm = ChatOllama(model=llm_model)
        # Index placeholders
        self.vector_store: Optional[FAISS] = None
        self.bm25_retriever: Optional[BM25Retriever] = None

    def _load_pdf(self, path: str) -> List[Document]:
        docs: List[Document] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                tables_html = []
                for tbl in page.extract_tables(table_settings={"vertical_strategy":"text","horizontal_strategy":"text"}):
                    html_rows = ["".join(f"<td>{cell or ''}</td>" for cell in row) for row in tbl]
                    tables_html.append(f"<table border=1><tr>{''.join(html_rows)}</tr></table>")
                meta = {"filename": os.path.basename(path), "page": i, "tables_html": tables_html}
                docs.append(Document(page_content=text, metadata=meta))
        return docs

    def load_documents(self, folder: str) -> List[Document]:
        documents: List[Document] = []
        for fname in os.listdir(folder):
            if fname.lower().endswith('.pdf'):
                documents.extend(self._load_pdf(os.path.join(folder, fname)))
        return documents

    def _split_and_index(self, documents: List[Document]) -> None:
        if self.chunker == "semantic":
            splitter = SemanticChunker(embeddings=self.embeddings)
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
        chunks = splitter.split_documents(documents)
        self.vector_store = FAISS.from_documents(chunks, self.embeddings)

    def build_vector_store(self, folder: str) -> None:
        docs = self.load_documents(folder)
        # Dense index
        self._split_and_index(docs)
        self.vector_store.save_local(INDEX_DIR)
        # Sparse BM25 index
        self.bm25_retriever = BM25Retriever.from_documents(
            docs, k=self.bm25_k, bm25_params=self.bm25_params
        )

    def load_vector_store(self, path: str = INDEX_DIR) -> None:
        """Load existing FAISS index and rebuild BM25 retriever from saved docs."""
        self.vector_store = FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization = True)
        docs = self.vector_store.documents
        self.bm25_retriever = BM25Retriever.from_documents(
            docs, k=self.bm25_k, bm25_params=self.bm25_params
        )

    def save_vector_store(self, path: str = INDEX_DIR) -> None:
        """Save the FAISS index to disk at the given path."""
        if self.vector_store is None:
            raise ValueError("Vector store not initialized. Call build_vector_store or load_vector_store first.")
        self.vector_store.save_local(path)

    def _get_retriever(self):
        # Hybrid ensemble with RRF via LangChain's EnsembleRetriever
        if self.use_hybrid and self.bm25_retriever:
            vec_r = self.vector_store.as_retriever(search_kwargs={"k": self.n_results})
            sparse_r = self.bm25_retriever
            return EnsembleRetriever(retrievers=[vec_r, sparse_r])
        
        # Dense-only fallback
        base = self.vector_store.as_retriever(search_kwargs={"k": self.n_results})
        return MultiQueryRetriever.from_llm(base, self.llm)

    def invoke(
        self,
        question: str,
        filenames: Optional[List[str]] = None
    ) -> str:
        """
        Retrieve and generate an HTML-formatted answer.
        If `filenames` is provided, only considers chunks from those source files.
        """
        retr = self._get_retriever()
        # Apply filename filter if specified
        if filenames:
            retr = FilteredRetriever(retr, filenames)

        prompt = ChatPromptTemplate.from_messages([
            ("system", "Format output as valid HTML only."),
            MessagesPlaceholder(variable_name="context"),
            ("human", "{input}"),
        ])
        doc_chain = create_stuff_documents_chain(self.llm, prompt)
        chain = create_retrieval_chain(retr, doc_chain)
        res = chain.invoke({"input": question})
        return res.get("answer") if isinstance(res, dict) else res

    def evaluate_queries(
        self,
        queries: List[str],
        filters: Optional[List[List[str]]] = None,
        top_n: int = 3) -> None:
        """
        Run multiple queries and display top-n docs in HTML.
        If `filters` is provided, it should be a list of filename-lists, one per query,
        to restrict retrieval by file for each individual query.
        """
        retr_base = self._get_retriever()
        rows = []
        for idx, q in enumerate(queries):
            # Determine filename filter for this query
            filenames = None
            if filters and idx < len(filters):
                filenames = filters[idx]
            # Apply filtering if needed
            retr = retr_base
            if filenames:
                retr = FilteredRetriever(retr, filenames)
            # Retrieve top_n documents
            docs = retr.get_relevant_documents(q)[:top_n]
            for rank, d in enumerate(docs, start=1):
                rows.append({
                    "query": q,
                    "rank": rank,
                    "file": d.metadata.get("filename"),
                    "page": d.metadata.get("page"),
                    "snippet": d.page_content[:].replace("\n", " ")
                })
        # Display results in HTML table
        if not rows:
            print("No results to display.")
            return
        cols = list(rows[0].keys())
        html = ["<table border=1><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"]
        for r in rows:
            html.append("<tr>" + "".join(f"<td>{r[c]}</td>" for c in cols) + "</tr>")
        html.append("</table>")
        display(HTML(''.join(html)))
