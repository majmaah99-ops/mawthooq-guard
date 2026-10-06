"""
إعدادات مشروع موثوق 2.0 — حارس فاتورة
"""
import os

# ── Qdrant ─────────────────────────────────────
QDRANT_COLLECTION = "zatca_fatoora"

# ── Embeddings ─────────────────────────────────
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_DIM = 1024

# ── OCR ────────────────────────────────────────
OCR_MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"
USE_GPU = os.getenv("USE_GPU", "false").lower() == "true"

# ── قواعد هيئة الزكاة والضريبة (مختصرة للهاكاثون) ──
VAT_LENGTH = 15
VAT_PREFIX = "3"
VAT_SUFFIX = "3"
MAX_INVOICE_AGE_HOURS = 24

# ── الأثر المالي ───────────────────────────────
FINE_PER_VIOLATION_SAR = 5000
TIME_SAVED_HOURS = 2.8
