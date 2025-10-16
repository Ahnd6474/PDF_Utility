# textlayer_or_ocr_to_pdf.py
# 실행하면 경로를 물어보고, 텍스트 전용/검색가능 PDF를 생성
# pip install pymupdf pdf2image pytesseract pillow

import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract

def pick_standard_font(raw_font_name: str):
    name = (raw_font_name or "").lower()
    is_bold = any(k in name for k in ["bold", "black", "heavy"])
    is_italic = any(k in name for k in ["italic", "oblique", "it"])
    is_mono = any(k in name for k in ["mono", "courier", "code"])
    if is_mono:
        if is_bold and is_italic: return "courbi"
        if is_bold: return "courbd"
        if is_italic: return "couri"
        return "cour"
    else:
        if is_bold and is_italic: return "helvbi"
        if is_bold: return "helvb"
        if is_italic: return "helvi"
        return "helv"

def draw_from_rawdict(dst_page, page):
    raw = page.get_text("rawdict")
    count = 0
    if not raw: return 0
    for block in raw.get("blocks", []):
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text or not text.strip():
                    continue
                origin = span.get("origin", (None, None))
                if not isinstance(origin, (list, tuple)) or len(origin) != 2:
                    continue
                x, y = origin
                size = float(span.get("size", 10) or 10.0)
                font_std = pick_standard_font(span.get("font", ""))
                dst_page.insert_text((x, y), text, fontsize=size,
                                     fontname=font_std, fill=(0, 0, 0), render_mode=0)
                count += len(text)
    return count

def draw_from_words(dst_page, page):
    words = page.get_text("words") or []
    if not words: return 0
    words.sort(key=lambda w: (round(w[1], 1), w[0]))
    count = 0
    for (x0, y0, x1, y1, text, *_rest) in words:
        if not text or not text.strip(): continue
        h = max(1.0, y1 - y0)
        fontsize = max(6.0, min(48.0, h * 0.8))
        dst_page.insert_textbox(fitz.Rect(x0, y0, x1, y1), text,
                                fontsize=fontsize, fontname="helv",
                                align=0, fill=(0, 0, 0), render_mode=0)
        count += len(text)
    return count

def ocr_hidden_text(dst_page, page_rect, pil_img, lang="kor+eng"):
    """
    OCR 단어 박스를 PDF 좌표에 매핑해서 '보이지 않는 텍스트'(render_mode=3)로 깔기.
    """
    data = pytesseract.image_to_data(pil_img, lang=lang, output_type=pytesseract.Output.DICT)
    img_w, img_h = pil_img.size
    W, H = page_rect.width, page_rect.height

    sx = W / img_w
    sy = H / img_h

    placed = 0
    n = len(data["text"])
    for i in range(n):
        txt = data["text"][i]
        conf = int(data["conf"][i]) if data["conf"][i].isdigit() else -1
        if not txt or not txt.strip(): continue
        if conf < 40:  # 너무 낮은 신뢰도는 스킵(조절 가능)
            continue
        x = data["left"][i] * sx
        y = data["top"][i] * sy
        w = data["width"][i] * sx
        h = data["height"][i] * sy
        if w <= 0 or h <= 0: continue

        # 박스 크기로 폰트 크기 근사, 텍스트는 '보이지 않게' (render_mode=3)
        fontsize = max(6.0, min(48.0, h * 0.9))
        dst_page.insert_textbox(
            fitz.Rect(x, y, x + w, y + h),
            txt,
            fontsize=fontsize,
            fontname="helv",
            align=0,
            fill=(0, 0, 0),
            render_mode=3  # invisible text (paint 안 함, 하지만 검색/선택 가능)
        )
        placed += len(txt)
    return placed

def build_text_only_pdf(src_pdf_path: str, dst_pdf_path: str, ocr_lang="kor+eng", ocr_dpi=300):
    src = fitz.open(src_pdf_path)
    dst = fitz.open()

    # OCR용 이미지 미리 렌더 (필요시만 참조)
    ocr_images = None

    pages_missing_text = []

    for i, page in enumerate(src, start=1):
        rect = page.rect
        dst_page = dst.new_page(width=rect.width, height=rect.height)

        n1 = draw_from_rawdict(dst_page, page)
        if n1 == 0:
            n2 = draw_from_words(dst_page, page)
        else:
            n2 = 0

        if (n1 + n2) == 0:
            # 이 페이지는 텍스트 레이어가 없으므로 OCR 필요
            if ocr_images is None:
                ocr_images = convert_from_path(src_pdf_path, dpi=ocr_dpi)
            pil_img = ocr_images[i - 1]
            n3 = ocr_hidden_text(dst_page, rect, pil_img, lang=ocr_lang)
            if n3 == 0:
                pages_missing_text.append(i)

    dst.save(dst_pdf_path, deflate=True, clean=True)
    dst.close()
    src.close()

    if pages_missing_text:
        print("[WARN] OCR로도 텍스트 배치가 거의 되지 않은 페이지:", pages_missing_text)
        print("       스캔 품질/언어 패키지/해상도를 점검하세요.")

def main():
    print("=== 텍스트 레이어 복원 + 필요시 OCR로 숨김 텍스트 추가 ===")
    in_path = input("입력 PDF 경로 (기본: input.pdf): ").strip() or "input.pdf"
    out_path = input("출력 PDF 경로 (기본: output_searchable_textonly.pdf): ").strip() or "output_searchable_textonly.pdf"
    lang = input("OCR 언어 (기본: kor+eng): ").strip() or "kor+eng"
    try:
        build_text_only_pdf(in_path, out_path, ocr_lang=lang, ocr_dpi=300)
        print(f"[OK] 생성 완료 → {out_path}")
    except Exception as e:
        print(f"[ERROR] 처리 중 오류: {e}")

if __name__ == "__main__":
    main()
