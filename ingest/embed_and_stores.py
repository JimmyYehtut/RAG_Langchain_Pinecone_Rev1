import sys
from pathlib import Path
from dotenv import load_dotenv
from ingest.load_documents import load_documents_from_paths
from ingest.chunk_documents import chunk_documents
from rag.vectorstore import create_or_load_vectorstore

load_dotenv()

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m ingest.embed_and_store <file1> <file2>")
        return

    paths = [str(Path(p)) for p in sys.argv[1:]]

    docs = load_documents_from_paths(paths)
    chunks = chunk_documents(docs)

    create_or_load_vectorstore(documents=chunks)
    print("✅ Ingestion completed.")

if __name__ == "__main__":
    main()
