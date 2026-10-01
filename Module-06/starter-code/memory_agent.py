"""
Module 6 Lab — STARTER
Personal Knowledge Assistant: short-term (summarized) + long-term (persistent vector) memory.

Part 1: conversation buffer + summarization.
Part 2: vector write/read paths, persistence across restart, citations.

Fill in the TODOs. Each TODO names the worksheet step it belongs to.

Install (into the SAME venv as Modules 1-5, Python 3.12):
    Module-02\\.venv\\Scripts\\python.exe -m pip install -r Module-06\\requirements.txt
Check:
    Module-02\\.venv\\Scripts\\python.exe Module-06\\m6_preflight.py
Run (two SEPARATE processes — that is the whole point of Part 2):
    python memory_agent.py --run1
    python memory_agent.py --run2

Your key lives in the repo-root .env (OPENROUTER_API_KEY=sk-or-...), same as M1-M5.
"""

import argparse
import datetime
import hashlib
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import chromadb   # PersistentClient + BUILT-IN embeddings (all-MiniLM-L6-v2 via ONNX): no key, no torch

# Windows consoles default to cp1252 and turn every em-dash into mojibake.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")      # repo-root .env

SUMMARIZE_AFTER_TURNS = 6
KEEP_LAST = 4
TOP_K = 3
DB_DIR = HERE / "memory_store"   # MUST persist to disk for cross-restart recall.
                                 # Next to THIS FILE, not the current directory — a cwd-relative
                                 # path is the #1 cause of "it forgot everything after restart".

llm = ChatOpenAI(
    model=os.getenv("MODEL", "openai/gpt-4o-mini"), temperature=0,
    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.environ["OPENROUTER_API_KEY"],
)
client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_or_create_collection("memories", metadata={"hnsw:space": "cosine"})
# No embedding_function argument means Chroma uses its built-in local model.
# Cosine space means similarity = 1 - distance (0 = unrelated, 1 = identical).


# ---------------------------------------------------------------------------
# SHORT-TERM MEMORY
# ---------------------------------------------------------------------------
class ShortTermMemory:
    def __init__(self):
        self.buffer = []      # recent turns, verbatim
        self.summary = ""     # rolling summary of older turns

    def add(self, role: str, text: str):
        self.buffer.append({"role": role, "text": text})
        # TODO (Steps 2-3): if len(self.buffer) > SUMMARIZE_AFTER_TURNS -> summarize the OLDER
        # turns with one LLM call, fold them into self.summary, keep only the last KEEP_LAST verbatim.
        # Print a one-line receipt when it fires, so you can SEE it in Step 5.
        if len(self.buffer) > SUMMARIZE_AFTER_TURNS:
            older = self.buffer[:-KEEP_LAST]
            self.buffer = self.buffer[-KEEP_LAST:]
            transcript = "\n".join(f"{turn['role']}: {turn['text']}" for turn in older)
            response = llm.invoke([("user", "Update the running summary; keep durable facts and open questions; max 80 words.\n"
                                     f"CURRENT SUMMARY:\n{self.summary or '(none)'}\n\nNEW TURNS:\n{transcript}")])
            self.summary = response.content.strip()
            print(f"[trigger fired] summary: {self.summary}")

    def context(self) -> str:
        # TODO (Step 4): return summary + recent turns as ONE bounded context string.
        parts = []
        if self.summary:
            parts.append("SUMMARY: " + self.summary)
        recent = "\n".join(f"{turn['role']}: {turn['text']}" for turn in self.buffer)
        if recent:
            parts.append("RECENT:\n" + recent)
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# LONG-TERM MEMORY (persistent vector store)
# ---------------------------------------------------------------------------
def should_remember(text: str) -> str | None:
    # TODO (Step 6, WRITE policy): store durable preferences/facts about the user, not every line.
    # A few regexes are enough ("I prefer", "I'm researching", "my project" ...).
    if re.search(r"^\s*(I prefer|I like)\b", text, re.I):
        return "preference"
    if re.search(r"^\s*(I'm researching|I am researching|my project)\b", text, re.I):
        return "fact"
    return None


def write_memory(text: str, mem_type: str = "fact"):
    # TODO (Step 6): collection.upsert(...) with metadata {text, source, timestamp, type}.
    # chromadb embeds the text for you. It is on disk the moment upsert returns.
    timestamp = datetime.date.today().isoformat()
    memory_id = hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()[:24]
    collection.upsert(
        ids=[memory_id],
        documents=[text],
        metadatas=[{"text": text, "source": "conversation", "timestamp": timestamp,
                    "type": mem_type, "ts": time.time()}],
    )
    print(f"[stored {mem_type}] {text}")


def recall(query: str, k: int = TOP_K) -> list:
    # TODO (Step 7): collection.query(query_texts=[query], n_results=k, include=[...])
    # -> return the top-k memories WITH their metadata (you need type + timestamp to cite).
    if collection.count() == 0:
        return []
    hits = collection.query(
        query_texts=[query],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    memories = []
    for text, metadata, distance in zip(hits["documents"][0], hits["metadatas"][0], hits["distances"][0]):
        similarity = 1 - distance
        if similarity >= 0.2:
            memories.append({"text": text, "type": metadata["type"],
                             "timestamp": metadata["timestamp"], "similarity": similarity})
    return memories


# ---------------------------------------------------------------------------
# AGENT TURN
# ---------------------------------------------------------------------------
def answer(user_text: str, stm: ShortTermMemory) -> str:
    # TODO: (a) write policy -> maybe write_memory;  (b) recall long-term memories;
    #       (c) build the context IN THIS ORDER: system rules -> recalled memories -> summary
    #           -> recent turns -> the question;
    #       (d) one LLM call; tell the model to CITE any memory it used as
    #           "(from your stored <type>, <YYYY-MM-DD>)"  (Step 9);
    #       (e) print a receipt: prompt size, how many memories were recalled;
    #       (f) stm.add(...) the user turn and the answer.
    for part in re.split(r";\s*|\s+and\s+(?=I\b)", user_text, flags=re.I):
        part = part.strip()
        mem_type = should_remember(part)
        if mem_type:
            write_memory(part, mem_type)

    memories = recall(user_text)
    recalled = "RECALLED MEMORIES:\n" + "\n".join(
        f"{index}. [{memory['type']}, {memory['timestamp']}, sim {memory['similarity']:.3f}] {memory['text']}"
        for index, memory in enumerate(memories, 1)
    )
    rules = ("You are a personal knowledge assistant. Be concise (max 80 words). "
             "Treat every preference in RECALLED MEMORIES as an instruction. "
             "Cite each memory you apply exactly as (from your stored <type>, <date>).")
    messages = [("system", rules)]
    if memories:
        messages.append(("system", recalled))
    if stm.summary:
        messages.append(("system", "SUMMARY OF EARLIER CONVERSATION:\n" + stm.summary))
    messages.extend((turn["role"], turn["text"]) for turn in stm.buffer)
    messages.append(("user", user_text))

    response = llm.invoke(messages)
    prompt_size = (response.usage_metadata or {}).get("input_tokens", "?")
    print(f"[receipt] prompt size: {prompt_size}; recalled: {len(memories)}")
    answer_text = response.content.strip()
    stm.add("user", user_text)
    stm.add("assistant", answer_text)
    return answer_text


# ---------------------------------------------------------------------------
# CLI — do not change; the worksheet's commands depend on these flags
# ---------------------------------------------------------------------------
RUN1 = "I prefer metric units and I'm researching renewable energy."
RUN2 = "Give me a quick figure for solar capacity."

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run1", action="store_true", help=f'send "{RUN1}"')
    ap.add_argument("--run2", action="store_true", help=f'send "{RUN2}" — in a NEW process')
    ap.add_argument("--chat", action="store_true", help="interactive; type quit to leave")
    args = ap.parse_args()

    stm = ShortTermMemory()
    print(f"[store: {DB_DIR}  pid: {os.getpid()}]")
    print(f"[memories on disk: {collection.count()}]")

    if args.run1:
        print(answer(RUN1, stm))
    elif args.run2:
        print(answer(RUN2, stm))
    elif args.chat:
        while (user := input("\nyou > ").strip().lower()) not in {"quit", "exit", "q"}:
            if user:
                print("\nassistant > " + answer(user, stm))
    else:
        ap.print_help()
