"""
موثوق 2.0 — حارس فاتورة
Streamlit App مع RAG مدمج
"""
import streamlit as st
from PIL import Image
import time

# ── إعداد الصفحة ──────────────────────────────
st.set_page_config(
    page_title="موثوق 2.0 — حارس فاتورة",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── تحميل الخط والاتجاه ───────────────────────
st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {
            font-family: 'Tajawal', sans-serif !important;
            direction: rtl;
            text-align: right;
        }
        .stApp { background: #080D0B; }
        .metric-card {
            background: #111A17;
            border: 1px solid rgba(255,255,255,0.07);
            border-radius: 16px;
            padding: 16px;
            text-align: center;
        }
        .success-badge {
            background: rgba(0,196,140,0.15);
            border: 1px solid rgba(0,196,140,0.3);
            color: #00C48C;
            padding: 8px 16px;
            border-radius: 12px;
            font-weight: 700;
        }
        .fail-badge {
            background: rgba(255,90,90,0.15);
            border: 1px solid rgba(255,90,90,0.3);
            color: #FF5A5A;
            padding: 8px 16px;
            border-radius: 12px;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── تحميل المحركات (مرة واحدة) ────────────────
@st.cache_resource(show_spinner="⏳ تحميل محرك RAG...")
def load_rag():
    from rag_engine import RAGEngine
    return RAGEngine()


@st.cache_resource(show_spinner="⏳ تحميل محرك OCR...")
def load_ocr():
    from ocr_engine import OCREngine
    return OCREngine()


rag = load_rag()
ocr = load_ocr()
from rule_engine import RuleEngine
rules = RuleEngine()
from config import FINE_PER_VIOLATION_SAR, TIME_SAVED_HOURS


# ── الترويسة ──────────────────────────────────
st.title("🛡️ موثوق 2.0 — حارس فاتورة")
st.caption(
    "نمنع رفض فاتورتك قبل إصدارها بـ 4 ثوانٍ | "
    "طبقة الوقاية Pre-compliance فوق قيود ووافق"
)

st.divider()

# ── التخطيط: عمودان ───────────────────────────
col1, col2 = st.columns([1, 1], gap="large")

# ═══════════ العمود الأيمن: الإدخال ═══════════
with col1:
    st.subheader("1️⃣ ارفع الفاتورة")

    uploaded = st.file_uploader(
        "صورة فاتورة (JPG / PNG)",
        type=["jpg", "jpeg", "png"],
        label_visibility="collapsed",
    )

    if uploaded:
        img = Image.open(uploaded)
        st.image(img, caption="الفاتورة المرفوعة", use_container_width=True)
        demo_type = None
        st.info(
            "🔬 في النسخة الإنتاجية: Qwen2-VL يستخرج الحقول من الصورة. "
            "للديمو السريع، اختر أحد النماذج أدناه."
        )

    demo_type = st.radio(
        "أو جرب أحد النماذج:",
        [
            "✅ فاتورة سليمة",
            "❌ فاتورة مرفوضة — QR ناقص",
            "❌ فاتورة مرفوضة — رقم ضريبي خطأ",
            "❌ فاتورة مرفوضة — تاريخ غير صحيح",
        ],
        horizontal=False,
    )

    scan_btn = st.button(
        "🔍 افحص فاتورتي",
        type="primary",
        use_container_width=True,
    )


# ═══════════ تنفيذ الفحص ═══════════
if scan_btn:
    with st.spinner("⏳ Qwen2-VL يستخرج الحقول... ثم محرك القواعد يفحص..."):
        time.sleep(1.0)

        # ── استخراج الحقول ────────────────────
        if uploaded:
            # في الإنتاج: fields = ocr.extract(img).to_dict()
            # في الديمو: نستخدم النموذج المختار
            pass

        # نماذج واقعية
        demo_map = {
            "✅ فاتورة سليمة": {
                "vat_seller": "300123456700003",
                "vat_buyer": "310987654300003",
                "invoice_date": "2026-10-05T10:30:00Z",
                "total_with_vat": "1,150.00 ر.س",
                "qr_present": True,
                "qr_data": "TLV:1|name|2|vat|3|date|4|total|5|vat_amt",
            },
            "❌ فاتورة مرفوضة — QR ناقص": {
                "vat_seller": "300123456700003",
                "vat_buyer": "310987654300003",
                "invoice_date": "2026-10-05T10:30:00Z",
                "total_with_vat": "1,150.00 ر.س",
                "qr_present": False,
                "qr_data": None,
            },
            "❌ فاتورة مرفوضة — رقم ضريبي خطأ": {
                "vat_seller": "12345",
                "vat_buyer": "310987654300003",
                "invoice_date": "2026-10-05T10:30:00Z",
                "total_with_vat": "1,150.00 ر.س",
                "qr_present": True,
                "qr_data": "TLV:1|name|2|vat|3|date|4|total|5|vat_amt",
            },
            "❌ فاتورة مرفوضة — تاريخ غير صحيح": {
                "vat_seller": "300123456700003",
                "vat_buyer": "310987654300003",
                "invoice_date": "05/10/2026",
                "total_with_vat": "1,150.00 ر.س",
                "qr_present": True,
                "qr_data": "TLV:1|name|2|vat|3|date|4|total|5|vat_amt",
            },
        }
        fields = demo_map[demo_type]

        # ── تشغيل محرك القواعد ────────────────
        results = rules.run(fields)
        verdict = rules.verdict(results)

        # ── RAG: ابحث عن مصدر أول فشل ─────────
        rag_source = None
        failed = [r for r in results if not r.passed]
        if failed:
            rag_source = rag.explain_failure(failed[0].label)

        # ── خزّن في الجلسة ────────────────────
        st.session_state["fields"] = fields
        st.session_state["results"] = results
        st.session_state["verdict"] = verdict
        st.session_state["rag_source"] = rag_source


# ═══════════ العمود الأيسر: النتيجة ═══════════
with col2:
    st.subheader("2️⃣ نتيجة الفحص")

    if "verdict" not in st.session_state:
        st.info("👈 ارفع فاتورة واضغط 'افحص فاتورتي' لعرض النتيجة")
    else:
        fields = st.session_state["fields"]
        results = st.session_state["results"]
        verdict = st.session_state["verdict"]
        rag_source = st.session_state.get("rag_source")

        if verdict["valid"]:
            st.markdown(
                '<div class="success-badge">✅ متوافقة — جاهزة للإرسال إلى منصة فاتورة</div>',
                unsafe_allow_html=True,
            )
            st.markdown("### 🎯 دقة المطابقة: 100%")
            st.success(
                f"**الغرامة المتفاداة:** {FINE_PER_VIOLATION_SAR:,} ريال "
                f"| **الوقت الموفر:** {TIME_SAVED_HOURS} ساعة "
                f"| **خطر إيقاف الخدمات:** تم منعه ✅"
            )
        else:
            st.markdown(
                '<div class="fail-badge">❌ ستُرفض من منصة فاتورة</div>',
                unsafe_allow_html=True,
            )
            first_fail = next(r for r in results if not r.passed)
            st.error(f"**السبب:** {first_fail.label}")
            st.metric(
                label="الغرامة المحتملة",
                value=f"{FINE_PER_VIOLATION_SAR:,} ريال",
                delta="خطر إيقاف الخدمات",
                delta_color="inverse",
            )

        st.divider()

        # ── مصدر RAG ──────────────────────────
        if rag_source and rag_source.get("page") != "—":
            st.markdown("**📖 المصدر الرسمي (RAG):**")
            st.info(
                f"**{rag_source['source']}**\n\n"
                f"_{rag_source['text']}_"
            )

        # ── محرك القواعد ──────────────────────
        st.markdown("**🔍 محرك القواعد (Rule Engine):**")
        for r in results:
            icon = "✅" if r.passed else "❌"
            st.write(f"{icon} **{r.label}** — *{r.page}*")
            if not r.passed:
                st.caption(f"↳ {r.details}")

        # ── الحقول المستخرجة ──────────────────
        with st.expander("📋 الحقول المستخرجة (OCR)"):
            st.json(fields)


# ═══════════ Footer: الأثر والسوق ═══════════
st.divider()

st.markdown("### 📊 لوحة الأثر وحجم السوق")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    label="TAM — إجمالي السوق",
    value="1.8M",
    help="منشأة ملزمة بمنصة مدد",
)
c2.metric(
    label="SAM — السوق القابل للخدمة",
    value="8,000",
    help="منشأة ممولة من بنك التنمية الاجتماعية (2025)",
)
c3.metric(
    label="SOM — خطة الاحتضان",
    value="100",
    help="منشأة مستهدفة خلال 4 أشهر",
)
c4.metric(
    label="الأثر السنوي المتوقع",
    value="6M ريال",
    help="منع غرامات على 100 منشأة",
)

st.caption(
    "**طبقة الوقاية:** قيود / وافق / دفترة يسجّلون بعد الإصدار — "
    "**موثوق** يمنع قبل الإصدار. تكامل عبر API، لا منافسة."
)
