"""
موثوق 2.0 — محرك RAG على دليل فاتورة (ZATCA)
يستخدم multilingual-e5-large (الأفضل للعربية) + Qdrant in-memory
"""
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
from sentence_transformers import SentenceTransformer

from config import (
    QDRANT_COLLECTION,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
)


# ── القواعد الرسمية من دليل ZATCA (مع أرقام الصفحات) ──
ZATCA_RULES = [
    {
        "text": "يجب أن يحتوي رمز QR على 5 حقول TLV إلزامية: اسم البائع، الرقم الضريبي للبائع، الطابع الزمني (ISO 8601)، الإجمالي شامل الضريبة، وقيمة ضريبة القيمة المضافة.",
        "page": 12,
        "topic": "QR",
    },
    {
        "text": "يجب أن يكون الرقم الضريبي مكوناً من 15 رقماً، يبدأ بالرقم 3 وينتهي بالرقم 3، ولا يحتوي على مسافات أو رموز.",
        "page": 8,
        "topic": "VAT",
    },
    {
        "text": "يجب أن يكون تاريخ الفاتورة بصيغة ISO 8601 بالشكل: YYYY-MM-DDTHH:MM:SSZ بتوقيت UTC أو بتحديد المنطقة الزمنية.",
        "page": 15,
        "topic": "DATE",
    },
    {
        "text": "الفاتورة الضريبية (B2B) تتطلب الرقم الضريبي للمشتري. الفاتورة المبسطة (B2C) لا تتطلبه. في حال وجوده في B2C يجب أن يكون صحيحاً.",
        "page": 9,
        "topic": "VAT_BUYER",
    },
    {
        "text": "يجب أن يكون الختم التشفيري Cryptographic Stamp مطابقاً لشهادة CSID المسجلة في منصة فاتورة. عدم التطابق يؤدي إلى رفض فوري.",
        "page": 22,
        "topic": "STAMP",
    },
    {
        "text": "في حال عدم تطابق الإجمالي مع مجموع البنود مضافاً إليها ضريبة القيمة المضافة، تُرفض الفاتورة تلقائياً من منصة فاتورة.",
        "page": 18,
        "topic": "TOTAL",
    },
    {
        "text": "يجب أن يكون حجم ملف QR قابلاً للقراءة الآلية، وأن يحتوي على بيانات Base64 صالحة. QR غير المقروء يُعاد كـ ملف مرفوض.",
        "page": 13,
        "topic": "QR",
    },
    {
        "text": "في حال تكرار المخالفات الفنية، تُفرض غرامة مالية تصل إلى 5,000 ريال سعودي، وقد يصل الأمر إلى إيقاف الخدمات الرقمية للمنشأة.",
        "page": 45,
        "topic": "PENALTY",
    },
]


class RAGEngine:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        self.client = QdrantClient(":memory:")
        self._build_index()

    def _build_index(self):
        self.client.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM, distance=Distance.COSINE
            ),
        )
        texts = [r["text"] for r in ZATCA_RULES]
        vectors = self.model.encode(texts, normalize_embeddings=True)

        points = [
            {
                "id": i,
                "vector": v.tolist(),
                "payload": {
                    "text": ZATCA_RULES[i]["text"],
                    "page": ZATCA_RULES[i]["page"],
                    "topic": ZATCA_RULES[i]["topic"],
                },
            }
            for i, v in enumerate(vectors)
        ]
        self.client.upsert(collection_name=QDRANT_COLLECTION, points=points)

    def query(self, question: str, top_k: int = 2) -> list[dict]:
        """يعيد أفضل الفقرات مطابقة مع رقم الصفحة."""
        vec = self.model.encode(
            f"query: {question}", normalize_embeddings=True
        ).tolist()

        results = self.client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vec,
            limit=top_k,
        )
        return [
            {
                "text": r.payload["text"],
                "page": r.payload["page"],
                "topic": r.payload["topic"],
                "score": round(r.score, 3),
            }
            for r in results
        ]

    def explain_failure(self, failed_label: str) -> dict:
        """يولّد شرحاً بمصدر رسمي بناءً على نوع الفشل."""
        topic_map = {
            "QR": "QR",
            "رمز": "QR",
            "الرقم الضريبي": "VAT",
            "التاريخ": "DATE",
            "ISO": "DATE",
        }
        query = failed_label
        for key, topic in topic_map.items():
            if key in failed_label:
                query = next(
                    (r["text"] for r in ZATCA_RULES if r["topic"] == topic),
                    failed_label,
                )
                break

        results = self.query(query, top_k=1)
        if not results:
            return {"text": "—", "page": "—", "source": "غير متوفر"}
        top = results[0]
        return {
            "text": top["text"],
            "page": top["page"],
            "source": f"دليل فاتورة — ص {top['page']}",
            "score": top["score"],
        }
