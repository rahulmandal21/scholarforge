"""
backend/vector_store/chroma_store.py

ScholarForge — Phase 5: Vector Store

Stores past ML component implementations in ChromaDB so that when a new
paper comes in, the Codegen Agent (Phase 6) can retrieve similar prior
code as reference context.

Uses ChromaDB's built-in SentenceTransformerEmbeddingFunction
(all-MiniLM-L6-v2) — runs locally, no API key needed.
"""

import os
import uuid

import chromadb
from chromadb.utils import embedding_functions

PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "scholarforge_implementations"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


class ScholarForgeVectorStore:
    """Wraps a ChromaDB collection of ML component implementations."""

    def __init__(self, persist_dir: str = PERSIST_DIR, collection_name: str = COLLECTION_NAME):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
        )

    def add_implementation(self, component_name: str, code: str, description: str) -> str:
        """
        Store a component implementation. The description is what gets embedded
        and searched against; the code is kept as metadata and returned on match.

        Returns the generated record id.
        """
        record_id = str(uuid.uuid4())
        self.collection.add(
            ids=[record_id],
            documents=[description],
            metadatas=[{"component_name": component_name, "code": code}],
        )
        return record_id

    def search_similar(self, query: str, top_k: int = 3, component_type: str = None) -> list:
        """
        Search for the top_k most similar prior implementations to a query string
        (e.g. a new component's description).

        If component_type is given, this first tries to find matches tagged
        with that exact component_name (e.g. "model_architecture") so the
        AST-similarity comparison in eval_agent compares like-for-like
        structures. Falls back to pure semantic search if no exact-type
        match exists, so retrieval still works for component types not
        present in the seed/training data.

        Returns a list of dicts: {component_name, description, code, distance}
        """
        if self.collection.count() == 0:
            return []

        top_k = min(top_k, self.collection.count())

        if component_type:
            typed_results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where={"component_name": component_type},
                include=["documents", "metadatas", "distances"],
            )
            if typed_results.get("documents", [[]])[0]:
                return self._format_results(typed_results)

        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        return self._format_results(results)

    @staticmethod
    def _format_results(results: dict) -> list:
        matches = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            matches.append({
                "component_name": meta.get("component_name", "unknown"),
                "description": doc,
                "code": meta.get("code", ""),
                "distance": dist,
            })
        return matches

    def reset(self) -> None:
        """Delete all records in the collection (useful for re-seeding during testing)."""
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_fn,
        )


def seed_sample_data(store: "ScholarForgeVectorStore") -> None:
    """Add 5 sample ML implementations so retrieval can be tested immediately."""

    samples = [
        {
            "component_name": "model_architecture",
            "description": (
                "PyTorch implementation of multi-head self-attention, splitting "
                "queries, keys, and values into multiple heads for parallel attention."
            ),
            "code": '''
import torch
import torch.nn as nn

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model: int, num_heads: int):
        super().__init__()
        assert d_model % num_heads == 0
        self.d_k = d_model // num_heads
        self.num_heads = num_heads
        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.out_proj = nn.Linear(d_model, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size, seq_len, _ = x.shape
        q = self.q_proj(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        k = self.k_proj(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        v = self.v_proj(x).view(batch_size, seq_len, self.num_heads, self.d_k).transpose(1, 2)
        scores = torch.matmul(q, k.transpose(-2, -1)) / (self.d_k ** 0.5)
        attn = torch.softmax(scores, dim=-1)
        out = torch.matmul(attn, v).transpose(1, 2).contiguous().view(batch_size, seq_len, -1)
        return self.out_proj(out)
'''.strip(),
        },
        {
            "component_name": "loss_function",
            "description": (
                "Cross-entropy loss function with label smoothing for sequence "
                "classification or generation tasks."
            ),
            "code": '''
import torch.nn as nn

class LabelSmoothingLoss(nn.Module):
    def __init__(self, num_classes: int, smoothing: float = 0.1):
        super().__init__()
        self.criterion = nn.CrossEntropyLoss(label_smoothing=smoothing)
        self.num_classes = num_classes

    def forward(self, predictions, targets):
        return self.criterion(predictions, targets)
'''.strip(),
        },
        {
            "component_name": "training_loop",
            "description": (
                "Generic PyTorch training loop with gradient clipping and a "
                "linear warmup learning rate schedule."
            ),
            "code": '''
import torch

def train_one_epoch(model, dataloader, optimizer, loss_fn, device, max_grad_norm=1.0):
    model.train()
    total_loss = 0.0
    for batch in dataloader:
        inputs, targets = batch
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = loss_fn(outputs, targets)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(dataloader)
'''.strip(),
        },
        {
            "component_name": "data_preprocessing",
            "description": (
                "PyTorch Dataset and DataLoader setup for tokenized text "
                "sequences, with padding for variable-length batches."
            ),
            "code": '''
import torch
from torch.utils.data import Dataset, DataLoader
from torch.nn.utils.rnn import pad_sequence

class TokenizedTextDataset(Dataset):
    def __init__(self, sequences: list):
        self.sequences = [torch.tensor(seq) for seq in sequences]

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx]


def collate_fn(batch):
    return pad_sequence(batch, batch_first=True, padding_value=0)
'''.strip(),
        },
        {
            "component_name": "evaluation_metric",
            "description": (
                "BLEU score evaluation for machine translation model outputs "
                "using the sacrebleu library."
            ),
            "code": '''
import sacrebleu

def compute_bleu(predictions: list, references: list) -> float:
    bleu = sacrebleu.corpus_bleu(predictions, [references])
    return bleu.score
'''.strip(),
        },

        # --- Second samples per category, added to widen the structural ---
        # --- range AST scoring compares against (see chroma_store v2 notes) ---
        {
            "component_name": "model_architecture",
            "description": (
                "A multi-layer feedforward neural network with configurable "
                "hidden layers, batch normalization, and dropout regularization."
            ),
            "code": '''
import torch
import torch.nn as nn

class FeedForwardNet(nn.Module):
    def __init__(self, input_dim: int, hidden_dims: list, output_dim: int, dropout: float = 0.1):
        super().__init__()
        layers = []
        prev_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.BatchNorm1d(hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev_dim = hidden_dim
        layers.append(nn.Linear(prev_dim, output_dim))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)

    def count_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters() if p.requires_grad)
'''.strip(),
        },
        {
            "component_name": "loss_function",
            "description": (
                "A custom weighted multi-task loss combining classification "
                "and regression objectives with learnable task weights."
            ),
            "code": '''
import torch
import torch.nn as nn

class MultiTaskLoss(nn.Module):
    def __init__(self, num_tasks: int):
        super().__init__()
        self.log_vars = nn.Parameter(torch.zeros(num_tasks))
        self.classification_loss = nn.CrossEntropyLoss()
        self.regression_loss = nn.MSELoss()

    def forward(self, class_preds, class_targets, reg_preds, reg_targets):
        cls_loss = self.classification_loss(class_preds, class_targets)
        reg_loss = self.regression_loss(reg_preds, reg_targets)
        precision_cls = torch.exp(-self.log_vars[0])
        precision_reg = torch.exp(-self.log_vars[1])
        total = precision_cls * cls_loss + self.log_vars[0]
        total += precision_reg * reg_loss + self.log_vars[1]
        return total

    def get_task_weights(self) -> list:
        return torch.exp(-self.log_vars).tolist()
'''.strip(),
        },
        {
            "component_name": "training_loop",
            "description": (
                "A training loop class with early stopping, checkpoint saving, "
                "and validation-loss tracking across epochs."
            ),
            "code": '''
import torch

class Trainer:
    def __init__(self, model, optimizer, loss_fn, patience: int = 5):
        self.model = model
        self.optimizer = optimizer
        self.loss_fn = loss_fn
        self.patience = patience
        self.best_val_loss = float("inf")
        self.epochs_no_improve = 0

    def train_epoch(self, dataloader) -> float:
        self.model.train()
        total_loss = 0.0
        for inputs, targets in dataloader:
            self.optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = self.loss_fn(outputs, targets)
            loss.backward()
            self.optimizer.step()
            total_loss += loss.item()
        return total_loss / len(dataloader)

    def validate(self, dataloader) -> float:
        self.model.eval()
        total_loss = 0.0
        with torch.no_grad():
            for inputs, targets in dataloader:
                outputs = self.model(inputs)
                total_loss += self.loss_fn(outputs, targets).item()
        return total_loss / len(dataloader)

    def should_stop_early(self, val_loss: float) -> bool:
        if val_loss < self.best_val_loss:
            self.best_val_loss = val_loss
            self.epochs_no_improve = 0
            return False
        self.epochs_no_improve += 1
        return self.epochs_no_improve >= self.patience

    def save_checkpoint(self, path: str) -> None:
        torch.save(self.model.state_dict(), path)
'''.strip(),
        },
        {
            "component_name": "data_preprocessing",
            "description": (
                "Text preprocessing pipeline with tokenization, vocabulary "
                "building, and train/validation splitting."
            ),
            "code": '''
from collections import Counter

class TextPreprocessor:
    def __init__(self, min_freq: int = 2):
        self.min_freq = min_freq
        self.vocab = {}

    def tokenize(self, text: str) -> list:
        return text.lower().split()

    def build_vocab(self, texts: list) -> dict:
        counter = Counter()
        for text in texts:
            counter.update(self.tokenize(text))
        self.vocab = {
            word: idx + 1
            for idx, (word, count) in enumerate(counter.items())
            if count >= self.min_freq
        }
        self.vocab["<unk>"] = 0
        return self.vocab

    def encode(self, text: str) -> list:
        return [self.vocab.get(tok, 0) for tok in self.tokenize(text)]

    def train_val_split(self, data: list, val_ratio: float = 0.2) -> tuple:
        split_idx = int(len(data) * (1 - val_ratio))
        return data[:split_idx], data[split_idx:]
'''.strip(),
        },
        {
            "component_name": "evaluation_metric",
            "description": (
                "Classification metrics calculator computing precision, "
                "recall, F1 score, and a confusion matrix."
            ),
            "code": '''
import torch

class ClassificationMetrics:
    def __init__(self, num_classes: int):
        self.num_classes = num_classes
        self.reset()

    def reset(self) -> None:
        self.confusion_matrix = torch.zeros(self.num_classes, self.num_classes)

    def update(self, preds: torch.Tensor, targets: torch.Tensor) -> None:
        for p, t in zip(preds, targets):
            self.confusion_matrix[t.long(), p.long()] += 1

    def precision(self) -> torch.Tensor:
        return self.confusion_matrix.diag() / self.confusion_matrix.sum(0).clamp(min=1)

    def recall(self) -> torch.Tensor:
        return self.confusion_matrix.diag() / self.confusion_matrix.sum(1).clamp(min=1)

    def f1_score(self) -> torch.Tensor:
        p, r = self.precision(), self.recall()
        return 2 * p * r / (p + r).clamp(min=1e-8)
'''.strip(),
        },
    ]

    for sample in samples:
        store.add_implementation(
            component_name=sample["component_name"],
            code=sample["code"],
            description=sample["description"],
        )

    print(f"Seeded {len(samples)} sample implementations.")


if __name__ == "__main__":
    store = ScholarForgeVectorStore()

    if store.collection.count() == 0:
        seed_sample_data(store)
    else:
        print(f"Collection already has {store.collection.count()} records — skipping seed.")

    test_query = "self-attention mechanism for transformer model"
    print(f"\nSearching for: '{test_query}'\n")
    results = store.search_similar(test_query, top_k=3)
    for r in results:
        print(f"- {r['component_name']} (distance: {r['distance']:.4f})")
        print(f"  {r['description']}\n")
