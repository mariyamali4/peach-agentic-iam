from backend.config.rag_config import load_rag_resources
from backend.rag_core.retriever import retrieve_chunks
from backend.rag_core.generator import generate_answer

# Cached load: only runs once when app starts
model, index, metadata = load_rag_resources()

def query_rag(query):
    """Run the RAG pipeline: retrieve → generate → return answer"""
    results = retrieve_chunks(query, model, index, metadata, k=10, for_rag=True)
    texts = [text for text in results["body"]]
    docs = "\n\n".join(texts)
    docTitles = list(set(results['docTitle']))
    result = generate_answer(query, docs, docTitles)
   # return result
    return {
        "answer": result["answer"],
        "output_file": result.get("output_file")  # <-- pass along sheet if produced
    }

