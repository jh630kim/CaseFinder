"""CaseSplitter 목차 파싱 단위 테스트(PDF 없이 합성 텍스트 사용)."""
import unittest

from casefinder.case_splitter import CaseSplitter

TOC = [
    "                   제1편 징계처분",
    "Ⅰ. 복무규정 위반 ················3",
    "     1. 초과근무 미제외(정직1월 → 감봉2월) ·········5",
    "     2. 제목이 두 줄인 사건",
    "         (견책 → 기각) ·········· 12",
    "            제2편 기타 불이익 처분",
    "1. 호봉 인정 청구(기타 → 기각) ·· 294",
]


class CaseSplitterTest(unittest.TestCase):
    """목차 파싱 규칙(여러 줄 제목, 점 2개, 편별 번호 재시작)을 검증한다."""

    def _splitter(self):
        """합성 목차를 가진 CaseSplitter를 만든다. 반환: CaseSplitter."""
        s = CaseSplitter("없음.pdf")
        s.pages = ["\n".join(TOC)]
        return s

    def test_toc_entries(self):
        """항목 3건이 번호·쪽·편과 함께 읽히는지 확인한다."""
        got = self._splitter().parse_toc()
        self.assertEqual([(e["part"], e["no"], e["printed_page"]) for e in got],
                         [("제1편", 1, 5), ("제1편", 2, 12), ("제2편", 1, 294)])

    def test_multiline_title(self):
        """두 줄 제목이 한 제목으로 합쳐지는지 확인한다."""
        got = self._splitter().parse_toc()
        self.assertEqual(got[1]["title"], "제목이 두 줄인 사건 (견책 → 기각)")


if __name__ == "__main__":
    unittest.main()
