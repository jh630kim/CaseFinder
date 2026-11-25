"""책자형 소청결정사례집 PDF를 목차 기준으로 사건별 쪽 범위로 나눈다.

실행: python -m casefinder.case_splitter <PDF 경로> <출력 JSON 경로>
"""
import json
import re
import subprocess
import sys

TOC_SCAN_PAGES = 25          # 목차를 찾아볼 앞쪽 PDF 쪽 수
ENTRY_START = re.compile(r"^\s*(\d{1,3})\.\s+(.*)$")      # '12. 제목' 줄
ENTRY_END = re.compile(r"^(.*?)\s*·{2,}\s*(\d+)\s*$")      # '··· 83' 줄
PART_LINE = re.compile(r"^\s*(제\d편)\s*(\S.*)$")      # '제2편 기타 불이익 처분' 줄
VERIFY_LEN = 10              # 본문 확인에 쓰는 제목 앞 글자 수


class CaseSplitter:
    """목차를 읽어 사건 목록과 PDF 쪽 범위를 만드는 클래스."""

    def __init__(self, pdf_path):
        """pdf_path(str): 분리할 PDF 파일 경로."""
        self.pdf_path = pdf_path
        self.pages = []

    def load_pages(self):
        """pdftotext로 쪽별 텍스트를 읽어 self.pages에 저장한다. 반환: 쪽 수(int)."""
        out = subprocess.run(["pdftotext", "-layout", self.pdf_path, "-"],
                             capture_output=True, text=True, check=True).stdout
        self.pages = out.split("\f")[:-1]    # 마지막 \f 뒤 빈 조각 제거
        return len(self.pages)

    def parse_toc(self):
        """앞쪽 목차에서 사건 항목을 읽는다. 반환: [{no, title, printed_page}]."""
        entries, pending, part = [], None, ""
        for page in self.pages[:TOC_SCAN_PAGES]:
            for line in page.splitlines():
                head = PART_LINE.match(line)
                if head:                            # 편이 바뀌면 사건 번호가 다시 1부터 시작
                    part, pending = head.group(1), None
                    continue
                before = len(entries)
                pending = self._feed_line(line, pending, entries)
                if len(entries) > before:
                    entries[-1]["part"] = part
        return entries

    def _feed_line(self, line, pending, entries):
        """목차 한 줄을 처리한다. 제목이 여러 줄이면 pending에 이어 붙인다.

        매개변수: line(str) 한 줄, pending([번호, 제목]|None) 진행 중 항목,
        entries(list) 완성 항목 누적. 반환: 갱신된 pending.
        """
        start = ENTRY_START.match(line)
        if start:                                   # 새 항목 시작
            pending = [int(start.group(1)), start.group(2).strip()]
        elif pending and line.strip():              # 제목의 다음 줄
            pending[1] += " " + line.strip()
        if not pending:
            return None
        end = ENTRY_END.match(pending[1])
        if end:                                     # 점선과 쪽 번호가 나오면 완성
            title = re.sub(r"\s+", " ", end.group(1)).strip()
            entries.append({"no": pending[0], "title": title,
                            "printed_page": int(end.group(2))})
            return None
        return pending

    @staticmethod
    def _norm(text):
        """공백·기호를 없애 비교용 문자열로 만든다. 반환: str."""
        return re.sub(r"[^0-9A-Za-z가-힣]", "", text)

    def _key(self, title):
        """본문 확인용 키: 결과 괄호는 목차와 본문 표기가 다를 수 있어 괄호 앞 제목만 쓴다."""
        return self._norm(title.split("(")[0])[:VERIFY_LEN]

    def find_offset(self, entries):
        """인쇄 쪽 번호에 더하면 PDF 쪽 번호가 되는 값을 찾는다. 반환: int|None."""
        first = entries[0]
        key = self._key(first["title"])
        # 점선이 있는 마지막 쪽까지는 목차이므로 그 다음 쪽부터 본문을 찾는다
        toc_last = max(i for i, p in enumerate(self.pages[:TOC_SCAN_PAGES]) if "····" in p)
        for idx in range(toc_last + 1, len(self.pages)):
            if key in self._norm(self.pages[idx]):
                return idx + 1 - first["printed_page"]
        return None

    def _last_part_page(self, part):
        """part(str) 머리글이 있는 마지막 PDF 쪽 번호(1부터)를 반환한다. 판권 쪽을 제외하려는 것."""
        return max(i for i, p in enumerate(self.pages, 1) if part in p[:80])

    def split(self):
        """사건별 PDF 쪽 범위(1부터)와 본문 제목 확인 결과를 만든다. 반환: list[dict]."""
        entries = self.parse_toc()
        offset = self.find_offset(entries) if entries else None
        if offset is None:
            return []
        for i, e in enumerate(entries):
            e["pdf_start"] = e["printed_page"] + offset
            nxt = entries[i + 1]["printed_page"] + offset if i + 1 < len(entries) else None
            e["pdf_end"] = max(e["pdf_start"], nxt - 1) if nxt else self._last_part_page(e["part"])
            body = self._norm(self.pages[e["pdf_start"] - 1])
            e["title_found"] = self._key(e["title"]) in body
        return entries


def main(pdf_path, out_path):
    """PDF를 분리해 JSON으로 저장하고 요약을 출력한다. 매개변수: 입력 PDF, 출력 JSON 경로."""
    splitter = CaseSplitter(pdf_path)
    total = splitter.load_pages()
    cases = splitter.split()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cases, f, ensure_ascii=False, indent=1)
    bad = [c["no"] for c in cases if not c["title_found"]]
    print(f"PDF {total}쪽, 사건 {len(cases)}건, 본문 제목 미확인 {len(bad)}건 {bad}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
