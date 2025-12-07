import os
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader
    

def load_pdf(path: str) -> List[Document]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return PyPDFLoader(path).load()


def load_txt(path: str) -> List[Document]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    return TextLoader(path).load()


def load_documents_from_paths(paths: list[str]) -> List[Document]:
    docs = []
    for path in paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".pdf":
            docs.extend(load_pdf(path))
        elif ext in [".txt", ".md"]:
            docs.extend(load_txt(path))
        else:
            raise ValueError(f"Unsupported file: {path}")
    return docs
