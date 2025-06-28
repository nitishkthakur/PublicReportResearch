from typing import List, Iterable, Optional, Dict
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

class RAG:
    """Retrieval-Augmented Generation with hybrid BM25 + dense retrieval (RRF ensemble)."""
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
        use_hybrid: bool = True,  # default hybrid ensemble (both BM25 and dense)
    ):
        # Chunking
        self.chunker = chunker
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # Retrieval & ranking
        self.n_results = n_results
        self.use_hybrid = use_hybrid
        self.bm25_k = bm25_k
        self.bm25_params = bm25_params or {"k1": 1.2, "b": 0.75}
        # Models
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.llm = ChatOllama(model=llm_model)
        # Indexes
        self.vector_store: Optional[FAISS] = None
        self.bm25_retriever: Optional[BM25Retriever] = None

    def _load_pdf(self, path: str) -> List[Document]:
        docs: List[Document] = []
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                tables_html = []
                for tbl in page.extract_tables(
                    table_settings={"vertical_strategy":"text","horizontal_strategy":"text"}
                ):
                    rows = ["".join(f"<td>{cell or ''}</td>" for cell in row) for row in tbl]
                    tables_html.append(f"<table border=1><tr>{''.join(rows)}</tr></table>")
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
        # dense index
        self._split_and_index(docs)
        self.vector_store.save_local(INDEX_DIR)
        # BM25 index
        self.bm25_retriever = BM25Retriever.from_documents(
            docs, k=self.bm25_k, bm25_params=self.bm25_params
        )

    def load_vector_store(self, path: str = INDEX_DIR) -> None:
        self.vector_store = FAISS.load_local(path, self.embeddings)
        docs = self.vector_store.documents
        self.bm25_retriever = BM25Retriever.from_documents(
            docs, k=self.bm25_k, bm25_params=self.bm25_params
        )

    def _get_retriever(self):
        # ensemble sparse + dense via RRF (Reciprocal Rank Fusion) using LangChain's EnsembleRetriever ([python.langchain.com](https://python.langchain.com/docs/how_to/ensemble_retriever/?utm_source=chatgpt.com))
        if self.use_hybrid:
            vec_r = self.vector_store.as_retriever(search_kwargs={"k": self.n_results})
            sparse_r = self.bm25_retriever
            return EnsembleRetriever(retrievers=[vec_r, sparse_r])
        # fallback dense-only
        base = self.vector_store.as_retriever(search_kwargs={"k": self.n_results})
        return MultiQueryRetriever.from_llm(base, self.llm)

    def invoke(self, question: str) -> str:
        retr = self._get_retriever()
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Format output as valid HTML only."),
            MessagesPlaceholder(variable_name="context"),
            ("human", "{input}"),
        ])
        doc_chain = create_stuff_documents_chain(self.llm, prompt)
        chain = create_retrieval_chain(retr, doc_chain)
        res = chain.invoke({"input": question})
        return res.get("answer") if isinstance(res, dict) else res

    def evaluate_queries(self, queries: List[str], top_n: int = 3) -> None:
        retr = self._get_retriever()
        rows = []
        for q in queries:
            docs = retr.get_relevant_documents(q)[:top_n]
            for i, d in enumerate(docs, 1):
                rows.append({
                    "query": q,
                    "rank": i,
                    "file": d.metadata.get("filename"),
                    "page": d.metadata.get("page"),
                    "snippet": d.page_content[:150].replace("\n"," ")
                })
        if not rows:
            print("No results.")
            return
        cols = list(rows[0].keys())
        html = ["<table border=1><tr>" + "".join(f"<th>{c}</th>" for c in cols) + "</tr>"]
        for r in rows:
            html.append("<tr>" + "".join(f"<td>{r[c]}</td>" for c in cols) + "</tr>")
        html.append("</table>")
        display(HTML(''.join(html)))

    def save_vector_store(self, path: str = INDEX_DIR) -> None:
        if self.vector_store is None:
            raise ValueError("Vector store is not built yet. Call build_vector_store() first.")
        self.vector_store.save_local(path)
        print(f"Vector store saved to {path}")

    def load_documents_store(self, path: str = INDEX_DIR) -> None:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Vector store not found at {path}")
        self.load_vector_store(path)
        print(f"Vector store loaded from {path}")

    @property
    def documents_store(self) -> List[Document]:
        if self.vector_store is None:
            raise ValueError("Vector store is not built yet. Call build_vector_store() first.")
        return self.vector_store.documents

    def __repr__(self):
        return f"RAG(chunker={self.chunker}, chunk_size={self.chunk_size}, " \
               f"chunk_overlap={self.chunk_overlap}, n_results={self.n_results}, " \
               f"embedding_model={self.embeddings.model_name}, llm_model={self.llm.model_name})"

    def __str__(self):
        return self.__repr__()

    def __len__(self):
        return len(self.documents_store)
