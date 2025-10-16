# textlayer_to_pdf_robust.py
# 실행하면 입력/출력 경로를 묻고, 텍스트 레이어만 재구성한 PDF를 생성
# pip install pymupdf

import fitz  # PyMuPDF

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
    """rawdict 스팬을 좌표대로 재그리기. 그린 글자 수 반환."""
    raw = page.get_text("rawdict")
    count = 0
    if not raw:
        return 0
    for block in raw.get("blocks", []):
        if block.get("type", 0) != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "")
                # 공란 스팬은 스킵 (ToUnicode 없는 경우 빈 문자열일 수 있음)
                if not text or not text.strip():
                    continue
                origin = span.get("origin", (None, None))
                if not isinstance(origin, (list, tuple)) or len(origin) != 2:
                    continue
                x, y = origin
                if x is None or y is None:
                    continue
                size = float(span.get("size", 10) or 10.0)
                font_std = pick_standard_font(span.get("font", ""))
                dst_page.insert_text((x, y), text, fontsize=size,
                                     fontname=font_std, fill=(0, 0, 0))
                count += len(text)
    return count

def draw_from_words(dst_page, page):
    """words 모드로 추출하여 단어 박스에 텍스트 배치. 그린 글자 수 반환."""
    # words: (x0, y0, x1, y1, "text", block_no, line_no, word_no)
    words = page.get_text("words") or []
    if not words:
        return 0
    # y(상단) → x(좌측) 순으로 안정 정렬
    words.sort(key=lambda w: (round(w[1], 1), w[0]))
    count = 0
    for (x0, y0, x1, y1, text, *_rest) in words:
        if not text or not text.strip():
            continue
        # 박스 높이로 폰트 크기 근사 (경험적 계수 0.8)
        h = max(1.0, y1 - y0)
        fontsize = max(6.0, min(48.0, h * 0.8))
        # insert_textbox로 박스 안에 재배치 (자동 줄바꿈 없음: 단어 단위라 문제 없음)
        dst_page.insert_textbox(
            fitz.Rect(x0, y0, x1, y1),
            text,
            fontsize=fontsize,
            fontname="helv",
            align=0,            # left
            fill=(0, 0, 0),
        )
        count += len(text)
    return count

def pdf_textlayer_to_pdf(src_pdf_path: str, dst_pdf_path: str):
    src = fitz.open(src_pdf_path)
    dst = fitz.open()

    empty_pages = []

    for i, page in enumerate(src, start=1):
        rect = page.rect
        dst_page = dst.new_page(width=rect.width, height=rect.height)

        n1 = draw_from_rawdict(dst_page, page)
        if n1 == 0:
            # rawdict가 비어 있거나 공란만이면 words로 폴백
            n2 = draw_from_words(dst_page, page)
            if n2 == 0:
                empty_pages.append(i)

    dst.save(dst_pdf_path, deflate=True, clean=True)
    dst.close()
    src.close()

    # 빈 페이지 보고(텍스트 레이어 자체가 없을 가능성 높음)
    if empty_pages:
        print(f"[WARN] 텍스트를 전혀 추출하지 못한 페이지: {empty_pages}")
        print("       해당 페이지는 텍스트 레이어가 없거나(ToUnicode 없음/벡터 외곽선), 완전 이미지일 수 있습니다.")
        print("       텍스트가 필요하면 OCR 파이프라인으로 별도 생성해야 합니다.")

def main():
    print("=== 텍스트 레이어만 추출 → 텍스트 전용 PDF ===")
    in_path = input("입력 PDF 경로 (기본: input.pdf): ").strip() or "input.pdf"
    out_path = input("출력 PDF 경로 (기본: output_textonly.pdf): ").strip() or "output_textonly.pdf"
    try:
        pdf_textlayer_to_pdf(in_path, out_path)
        print(f"[OK] 생성 완료 → {out_path}")
    except Exception as e:
        print(f"[ERROR] 처리 중 오류: {e}")

if __name__ == "__main__":
    main()
