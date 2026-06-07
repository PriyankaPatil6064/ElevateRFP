import os
import faiss
import numpy as np
from dotenv import load_dotenv
from config import PRODUCTS
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

index = None
product_texts = []
product_vectors = None


def product_to_text(p):
    return f"{p['name']} capacity {p['capacity']} kg floors {p['max_floors']} speed {p['speed']} m/s"


def embed(text):
    res = genai.embed_content(model="models/embedding-001", content=text)
    return np.array(res["embedding"], dtype="float32")


def build_index():
    global index, product_vectors, product_texts

    if index is not None:
        return

    product_texts = [product_to_text(p) for p in PRODUCTS]
    product_vectors = np.array([embed(t) for t in product_texts])

    index = faiss.IndexFlatL2(product_vectors.shape[1])
    index.add(product_vectors)


def retrieve_products(query, k=3):
    try:
        build_index()
        q_vec = embed(query).reshape(1, -1)
        _, indices = index.search(q_vec, k)
        return [PRODUCTS[i] for i in indices[0]]
    except Exception as e:
        print("RAG fallback:", e)
        return PRODUCTS[:k]
