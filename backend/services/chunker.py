from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List


def chunk_text(text: str, doc_id: str, filename: str) -> List[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024,       # increased from 512 — keeps professor sections together
        chunk_overlap=200,     # increased from 50 — more context shared between chunks
        length_function=len,
        separators=[
            "\n\n",            # paragraph breaks first
            "\n",              # then line breaks
            ". ",              # then sentences
            " ",               # then words
            "",                # last resort character split
        ],
    )
    chunks = splitter.split_text(text)
    return [
        {
            "text": chunk,
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": i,
        }
        for i, chunk in enumerate(chunks)
    ]