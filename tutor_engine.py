"""
tutor_engine.py
Motor principal do uRobot Tutor.
"""

from pathlib import Path
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate

MODEL_NAME    = "llama3"
EMBED_MODEL   = "nomic-embed-text"
CHROMA_DIR    = "./chroma_db"
CHUNK_SIZE    = 800
CHUNK_OVERLAP = 100

QA_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""Es um tutor academico. Responde em portugues de Portugal de forma clara e direta.

REGRA IMPORTANTE: Usa APENAS o conteudo educativo do contexto abaixo para responder.
Se a informacao nao estiver no contexto, responde exatamente com:
"Nao encontrei informacao sobre este tema nos materiais carregados."
Nao uses conhecimento proprio. Nao inventes. Nao copies URLs, menus ou rodapes de websites.

Contexto dos materiais:
{context}

Pergunta: {question}

Resposta:"""
)

SUMMARY_PROMPT = """Es um tutor academico. Responde em portugues de Portugal.

Cria um resumo DETALHADO e COMPLETO sobre o topico: "{topic}".
Usa apenas o conteudo educativo dos materiais abaixo.
Ignora menus, rodapes, URLs, avisos de cookies e qualquer texto que nao seja materia.
Se nao houver informacao suficiente nos materiais, diz isso claramente.

Materiais:
{context}

Escreve um resumo longo e detalhado com esta estrutura:

## Conceito principal
Explicacao clara e completa do conceito, com pelo menos 3-4 paragrafos.

## Contexto e enquadramento
Onde se insere este tema, origem, importancia.

## Pontos-chave
- Ponto detalhado 1 com explicacao
- Ponto detalhado 2 com explicacao
- Ponto detalhado 3 com explicacao
- Ponto detalhado 4 com explicacao
- Ponto detalhado 5 com explicacao

## Detalhes importantes
Explicacao aprofundada dos aspectos mais relevantes, exemplos concretos, casos de uso.

## Relacao com outros conceitos
Como este tema se relaciona com outras ideias ou areas.

## O que deves reter
Conclusao clara com os pontos mais importantes para memorizar."""

QUIZ_PROMPT = """You are creating a multiple choice quiz in European Portuguese about: "{topic}".

Reference materials:
{context}

CRITICAL INSTRUCTION: You MUST respond with ONLY a JSON array.
Do NOT write any text before or after the JSON.
Do NOT use markdown code blocks.
Do NOT explain anything.
Your entire response must start with [ and end with ]

Required format:
[
  {{
    "question": "Pergunta completa em portugues de Portugal?",
    "options": ["Opcao A completa", "Opcao B completa", "Opcao C completa", "Opcao D completa"],
    "correct": 0,
    "explanation": "Explicacao detalhada de porque esta opcao e a correta."
  }}
]

Rules:
- "correct" is the integer index (0, 1, 2 or 3) of the correct answer in "options"
- All text must be in European Portuguese
- Questions must be based ONLY on the reference materials
- Generate exactly {n} questions
- Make wrong options plausible but clearly incorrect

Respond with the JSON array only:"""

CHAT_PROMPT = """Es um tutor academico. Responde em portugues de Portugal de forma clara e direta.

REGRA IMPORTANTE: Usa APENAS o conteudo educativo dos materiais abaixo para responder.
Se a informacao nao estiver nos materiais, responde:
"Nao encontrei informacao sobre este tema nos materiais carregados."
Nao uses conhecimento proprio. Nao inventes. Nao copies URLs, menus ou rodapes.

Materiais:
{context}

Historico da conversa:
{history}

Pergunta do aluno: {question}
Resposta do tutor:"""


class TutorEngine:
    def __init__(self):
        print("A inicializar TutorEngine...")
        self.llm = OllamaLLM(model=MODEL_NAME, temperature=0.2)
        self.embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        self._init_vectorstore()
        print(f"Motor pronto. Modelo: {MODEL_NAME}")

    def _init_vectorstore(self):
        self.vectorstore = Chroma(
            collection_name="urobot_docs",
            embedding_function=self.embeddings,
            persist_directory=CHROMA_DIR,
        )

    def load_document(self, filepath: str) -> str:
        path = Path(filepath)
        if not path.exists():
            return f"Ficheiro nao encontrado: {path.name}"
        try:
            ext = path.suffix.lower()
            if ext == ".pdf":
                loader = PyPDFLoader(str(path))
            elif ext in (".txt", ".md"):
                loader = TextLoader(str(path), encoding="utf-8")
            else:
                return f"Formato nao suportado: {ext}"
            docs = loader.load()
            chunks = self.splitter.split_documents(docs)
            for chunk in chunks:
                chunk.metadata["source_file"] = path.name
            self.vectorstore.add_documents(chunks)
            return f"{path.name} — {len(chunks)} fragmentos indexados."
        except Exception as e:
            return f"Erro ao carregar {path.name}: {str(e)}"

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

    def _has_docs(self) -> bool:
        try:
            return self.vectorstore._collection.count() > 0
        except Exception:
            return False

    def _get_context(self, query: str, k: int = 5) -> str:
        try:
            docs = self.vectorstore.similarity_search(query, k=k)
            if not docs:
                return ""
            return "\n\n".join(d.page_content for d in docs)
        except Exception:
            return ""

    def _is_relevant(self, query: str, context: str) -> bool:
        """
        Verifica se a query tem relacao com o contexto recuperado
        comparando palavras-chave. Bloqueia topicos sem qualquer
        sobreposicao com os documentos (ex: Benfica num PDF de LLMs).
        """
        if not context:
            return False
        # Palavras com mais de 3 letras (ignora artigos, preposicoes)
        query_words = set(w.lower().strip(".,?!") for w in query.split() if len(w) > 3)
        context_words = set(w.lower().strip(".,?!") for w in context.split() if len(w) > 3)
        if not query_words:
            return True
        overlap = query_words & context_words
        return len(overlap) >= 1

    def ask(self, question: str, history: list) -> str:
        if not self._has_docs():
            return "Nao ha materiais carregados. Carrega um PDF ou ficheiro de texto na barra lateral."

        context = self._get_context(question, k=5)
        if not context or not self._is_relevant(question, context):
            return "Nao encontrei informacao sobre este tema nos materiais carregados."

        history_text = ""
        for msg in history[-6:]:
            role = "Aluno" if msg["role"] == "user" else "Tutor"
            history_text += f"{role}: {msg['content']}\n"

        prompt = CHAT_PROMPT.format(
            context=context,
            history=history_text,
            question=question,
        )
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            return f"Erro ao contactar o Ollama: {e}"

    def summarize(self, topic: str) -> str:
        if not self._has_docs():
            return "Nao ha materiais carregados. Carrega um PDF ou ficheiro de texto primeiro."

        context = self._get_context(topic, k=8)
        if not context or not self._is_relevant(topic, context):
            return "Nao encontrei informacao sobre este topico nos materiais carregados."

        prompt = SUMMARY_PROMPT.format(topic=topic, context=context)
        try:
            return self.llm.invoke(prompt)
        except Exception as e:
            return f"Erro ao gerar resumo: {e}"

    def generate_quiz(self, topic: str, n: int = 5) -> str:
        if not self._has_docs():
            return '[]'

        context = self._get_context(topic, k=8)
        if not context:
            return '[]'

        prompt = QUIZ_PROMPT.format(topic=topic, context=context, n=n)
        try:
            raw = self.llm.invoke(prompt)
            raw = raw.strip().replace("```json", "").replace("```", "").strip()
            start = raw.find("[")
            end = raw.rfind("]")
            if start != -1 and end != -1:
                return raw[start:end+1]
            return '[]'
        except Exception:
            return '[]'

    def reset_collection(self) -> str:
        try:
            self.vectorstore.delete_collection()
            self._init_vectorstore()
            return "Base de dados limpa."
        except Exception as e:
            return f"Erro ao limpar: {e}"