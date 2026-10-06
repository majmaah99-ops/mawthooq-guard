"""
موثوق 2.0 — محرك OCR
Qwen2-VL للصور عالية الجودة (يحتاج GPU)
Tesseract كـ fallback فوري (يعمل على CPU)
"""
import re
import json
from dataclasses import dataclass, asdict
from typing import Optional
from PIL import Image

from config import OCR_MODEL_ID, USE_GPU


@dataclass
class InvoiceData:
    vat_seller: Optional[str] = None
    vat_buyer: Optional[str] = None
    invoice_date: Optional[str] = None
    total_with_vat: Optional[str] = None
    qr_present: bool = False
    qr_data: Optional[str] = None
    raw_text: str = ""
    engine: str = "unknown"

    def to_dict(self):
        return asdict(self)


PROMPT = """أنت محلل فواتير ضريبية سعودية. استخرج من الصورة الحقول التالية بصيغة JSON فقط:

{
  "vat_seller": "الرقم الضريبي للبائع (15 رقماً)",
  "vat_buyer": "الرقم الضريبي للمشتري أو null",
  "invoice_date": "التاريخ بصيغة ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)",
  "total_with_vat": "الإجمالي شامل الضريبة",
  "qr_present": true/false
}

إن لم تجد حقلاً، اكتب null. أعد JSON فقط بدون أي شرح."""


class OCREngine:
    def __init__(self):
        self._model = None
        self._processor = None
        self._qwen_available = False

    def _try_load_qwen(self):
        if self._model is not None:
            return self._qwen_available
        if not USE_GPU:
            self._qwen_available = False
            return False
        try:
            import torch
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = Qwen2VLForConditionalGeneration.from_pretrained(
                OCR_MODEL_ID,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map=device,
            )
            self._processor = AutoProcessor.from_pretrained(OCR_MODEL_ID)
            self._qwen_available = True
            return True
        except Exception as e:
            print(f"[OCR] Qwen2-VL غير متوفر: {e}. استخدام Tesseract.")
            self._qwen_available = False
            return False

    def extract(self, image: Image.Image) -> InvoiceData:
        if self._try_load_qwen():
            try:
                return self._extract_qwen(image)
            except Exception as e:
                print(f"[OCR] فشل Qwen: {e}. الرجوع إلى Tesseract.")
        return self._extract_tesseract(image)

    # ── Qwen2-VL ─────────────────────────────────
    def _extract_qwen(self, image: Image.Image) -> InvoiceData:
        import torch
        from qwen_vl_utils import process_vision_info

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": PROMPT},
            ],
        }]
        text = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, _ = process_vision_info(messages)
        inputs = self._processor(
            text=[text], images=image_inputs, return_tensors="pt"
        ).to(self._model.device)

        with torch.no_grad():
            out = self._model.generate(**inputs, max_new_tokens=512)
        generated = out[:, inputs.input_ids.shape[1]:]
        response = self._processor.batch_decode(
            generated, skip_special_tokens=True
        )[0]

        data = self._parse_json(response)
        return InvoiceData(
            vat_seller=data.get("vat_seller"),
            vat_buyer=data.get("vat_buyer"),
            invoice_date=data.get("invoice_date"),
            total_with_vat=str(data.get("total_with_vat") or ""),
            qr_present=bool(data.get("qr_present", False)),
            raw_text=response,
            engine="Qwen2-VL",
        )

    # ── Tesseract fallback ───────────────────────
    def _extract_tesseract(self, image: Image.Image) -> InvoiceData:
        import pytesseract
        text = pytesseract.image_to_string(image, lang="ara+eng")

        vat = re.search(r"\b3\d{13}3\b", text)
        date = re.search(
            r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}Z?)?", text
        )
        total = re.search(r"[\d,]+\.?\d*\s*(?:ر\.?س|SAR)?", text)

        return InvoiceData(
            vat_seller=vat.group(0) if vat else None,
            vat_buyer=None,
            invoice_date=date.group(0) if date else None,
            total_with_vat=total.group(0).strip() if total else None,
            qr_present="QR" in text.upper() or "فاتورة" in text,
            raw_text=text,
            engine="Tesseract",
        )

    @staticmethod
    def _parse_json(text: str) -> dict:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
