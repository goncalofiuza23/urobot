"""
tutor_engine.py
Motor principal do uRobot Tutor.
Usa Ollama (local) + LangChain + ChromaDB para RAG completo.
"""

import os
import re
from pathlib import Path
from typing import Optional

# LangChain
from langchain_community.llms import Ollama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate

# ── Configuração ──────────────────────────────────────────────────────────────

MODEL_NAME   = "llama3"          # muda para "mistral", "phi3", etc. se quiseres
EMBED_MODEL  = "nomic-embed-text"  # modelo de embeddings local
CHROMA_DIR   = "./chroma_db"     # diretório local da base de dados vetorial
CHUNK_SIZE   = 800
CHUNK_OVERLAP= 100

# ── Prompts ───────────────────────────────────────────────────────────────────

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""És um tutor académico. Responde em português de Portugal de forma clara e direta.

Usa APENAS o conteúdo educativo do contexto abaixo. Ignora completamente qualquer texto que pareça ser
menus de websites, rodapés, avisos de cookies, URLs, datas de publicação, nomes de autores ou
qualquer outro conteúdo que não seja matéria de estudo.

Se não encontrares informação relevante sobre a pergunta, diz isso claramente.
Não incluas URLs, nomes de sites ou lixo de páginas web na resposta.

Contexto:
{context}

Pergunta: {question}

Resposta:"""
)

SUMMARY_PROMPT = """És um tutor académico. Responde em português de Portugal.

Cria um resumo estruturado sobre o tópico: "{topic}".
Usa apenas o conteúdo educativo dos materiais abaixo.
Ignora menus, rodapés, URLs, avisos de cookies e qualquer texto que não seja matéria de estudo.

Materiais:
{context}

Escreve o resumo com esta estrutura:
**Conceito principal**
[definição clara]

**Pontos-chave**
- ponto 1
- ponto 2
- ponto 3

**O que deves reter**
[conclusão breve]"""

QUIZ_PROMPT = """Create a quiz in European Portuguese about: "{topic}".
Use the materials below as reference. Ignore any website menus, footers, URLs or non-educational text.

Materials:
{context}

YOU MUST respond with ONLY a valid JSON array. No explanation, no markdown, no text before or after.
Start your response with [ and end with ]

[
  {{
    "question": "Pergunta em portugues?",
    "options": ["opcao A", "opcao B", "opcao C", "opcao D"],
    "correct": 0,
    "explanation": "Explicacao breve em portugues."
  }}
]

"correct" is the index (0, 1, 2 or 3) of the correct option.
Generate exactly {n} questions. Respond with JSON only."""

CHAT_PROMPT = """És um tutor académico. Responde em português de Portugal de forma clara e direta.

Usa o conteúdo educativo dos materiais abaixo para responder.
Ignora completamente menus, rodapés, URLs, avisos de cookies ou qualquer texto que não seja matéria.
Não copies URLs nem nomes de sites para a resposta.

Materiais:
{context}

Histórico:
{history}

Pergunta do aluno: {question}
Resposta do tutor:"""


# ── Motor ─────────────────────────────────────────────────────────────────────

class TutorEngine:
    def __init__(self):
        print("🔧 A inicializar TutorEngine...")

        self.llm = Ollama(model=MODEL_NAME, temperature=0.3)
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        self._init_vectorstore()
        print(f"✅ Motor pronto. Modelo: {MODEL_NAME}")

    def _init_vectorstore(self):
        self.vectorstore = Chroma(
            collection_name="urobot_docs",
            embedding_function=self.embeddings,
            persist_directory=CHROMA_DIR,
        )

    # ── Carregar documentos ───────────────────────────────────────────────────

    def load_document(self, filepath: str) -> str:
        path = Path(filepath)
        if not path.exists():
            return f"❌ Ficheiro não encontrado: {path.name}"

        try:
            ext = path.suffix.lower()
            if ext == ".pdf":
                loader = PyPDFLoader(str(path))
            elif ext in (".txt", ".md"):
                loader = TextLoader(str(path), encoding="utf-8")
            else:
                return f"⚠️ Formato não suportado: {ext}"

            docs = loader.load()
            chunks = self.splitter.split_documents(docs)

            # Adiciona metadado com nome do ficheiro
            for chunk in chunks:
                chunk.metadata["source_file"] = path.name

            self.vectorstore.add_documents(chunks)
            return f"✅ {path.name} — {len(chunks)} fragmentos indexados."

        except Exception as e:
            return f"❌ Erro ao carregar {path.name}: {str(e)}"

    # ── Info da coleção ───────────────────────────────────────────────────────

    def get_collection_info(self) -> dict:
        try:
            collection = self.vectorstore._collection
            total = collection.count()
            results = collection.get(include=["metadatas"])
            files = set()
            for meta in (results.get("metadatas") or []):
                if meta and "source_file" in meta:
                    files.add(meta["source_file"])
            return {"total_docs": total, "files": sorted(files)}
        except Exception:
            return {"total_docs": 0, "files": []}

    # ── Retriever helper ──────────────────────────────────────────────────────

    def _get_context(self, query: str, k: int = 5) -> str:
        try:
            docs = self.vectorstore.similarity_search(query, k=k)
            if not docs:
                return ""
            return "\n\n".join(d.page_content for d in docs)
        except Exception:
            return ""

    # ── Chat ──────────────────────────────────────────────────────────────────

    def ask(self, question: str, history: list) -> str:
        context = self._get_context(question)

        # Formata histórico
        history_text = ""
        for msg in history[-6:]:  # últimas 3 trocas
            role = "Aluno" if msg["role"] == "user" else "Tutor"
            history_text += f"{role}: {msg['content']}\n"

        if context:
            prompt = CHAT_PROMPT.format(
                context=context,
                history=history_text,
                question=question,
            )
        else:
            prompt = f"""És um tutor académico. Responde em português de Portugal.
{history_text}
Aluno: {question}
Tutor:"""

        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            return f"❌ Erro ao contactar o Ollama: {e}\n\nVerifica se o Ollama está a correr com `ollama serve`."

    # ── Resumo ────────────────────────────────────────────────────────────────

    def summarize(self, topic: str) -> str:
        context = self._get_context(topic, k=6)
        if not context:
            context = "(sem materiais carregados — responde com conhecimento geral)"

        prompt = SUMMARY_PROMPT.format(topic=topic, context=context)
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            return f"❌ Erro ao gerar resumo: {e}"

    # ── Questionário ──────────────────────────────────────────────────────────

    def generate_quiz(self, topic: str, n: int = 5) -> str:
        context = self._get_context(topic, k=6)
        if not context:
            context = "(sem materiais carregados — usa conhecimento geral)"

        prompt = QUIZ_PROMPT.format(topic=topic, context=context, n=n)
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            return f"❌ Erro ao gerar questionário: {e}"

    # ── Reset ─────────────────────────────────────────────────────────────────

    def reset_collection(self) -> str:
        try:
            self.vectorstore._collection.delete(
                where={"source_file": {"$ne": ""}}
            )
            # Alternativa mais agressiva: apaga tudo
            self.vectorstore.delete_collection()
            self._init_vectorstore()
            return "🗑️ Base de dados limpa com sucesso."
        except Exception as e:
            return f"⚠️ Erro ao limpar: {e}"