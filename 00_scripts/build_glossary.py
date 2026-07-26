"""output/ 에 용어집 페이지를 만든다.

스킬·특성 하단 필드는 게임이 번역해 준 문장이 아니라 위키 편집자가 붙인 값이라,
한글 표기를 전부 사람이 정했다. 무엇을 어떻게 옮겼는지 한 장에서 볼 수 있게 한다.
"""
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

# 백과사전 안에 심을 조각. 통째로 된 페이지가 아니라 본문만 만든다.
OUT = os.path.join(paths.LOCALIZED, "glossary_body.html")

# inject_wiki.py 의 UNITS·모양·사거리 설명과 짝을 맞춰 둔 표.
# 저쪽을 고치면 여기도 고쳐야 한다 (양쪽 다 사람이 정한 표기라 자동 추출이 어렵다).
UNIT_RULES = [
    ("seconds / second", "초", "0.125 + 0 seconds → 0.125 + 0 초"),
    ("per second", "초당", "1.0 per second → 1.0 초당"),
    ("degrees", "도", "45 degrees → 45 도"),
    ("Instant", "즉시", "시전 시간"),
    ("Global", "전역", "사거리 제한 없음"),
    ("threshold", "조건부", "레벨당 상승이 조건부일 때"),
    ("(x3)", "(3회)", "1.0 per second (x3) → 1.0 초당 (3회)"),
    ("1.0 x 1.6", "1.0 × 1.6", "판정 범위 표기"),
    ("CH", "정신집중", "0 + CH + 0 seconds"),
    ("initial / impact", "최초 / 충돌", "지연시간 종류"),
    ("primary / secondary", "주 대상 / 부 대상", ""),
    ("quest / reward", "퀘스트 / 보상", ""),
]

SHAPES = [
    ("Circle", "원형", "반경 하나로 그린다"),
    ("Radial", "부채꼴", "반경 + 각도. 꼭짓점이 시전자에 붙는다"),
    ("Rectangle", "직사각형", "너비 × 길이. 시전자에서 앞으로 뻗는다"),
    ("Ring", "고리형", "안쪽·바깥쪽 반경"),
    ("hitbox 기반", "관통 경로", "범위 형태가 없고 판정 상자만 있는 논타겟·돌진"),
]

NO_RANGE = [
    ("self", "자기 중심", "시전자를 기준으로 터진다. 부채꼴은 정의상 여기 속한다"),
    ("inherit", "부모 스킬을 따름", "다른 스킬을 강화하는 특성"),
    ("unstated", "위키에 없음", "게임 데이터에도 제한값이 없다"),
]

LEAD = """
<div class="gl-lead">
  스킬·특성 카드 아래의 <b>위키 상세</b> 필드는 게임이 번역해 준 문장이 아니다.
  위키 편집자가 영어로 붙인 값이라 대응하는 한글이 없어 표기를 직접 정했고,
  그 목록이 이 페이지다.<br>
  이름과 설명문은 사정이 다르다 - 그건 게임에 들어 있는 한글 문자열을 그대로 가져다 쓴다.
</div>
"""

TAIL = """
<div class="gl-foot">
  고치려면 <code>00_custom/glossary.json</code> 을 손보고 다시 빌드하면 된다.
  아직 옮기지 않은 표현은 <code>07_localized/report.md</code> 에 빈도순으로 쌓인다.
</div>
"""


def escape(text):
    return html.escape(str(text if text is not None else ""))


def table(rows, headers, classes=("en", "ko", "note")):
    head = "".join("<th>%s</th>" % escape(h) for h in headers)
    body = "".join(
        "<tr>%s</tr>" % "".join(
            '<td class="%s">%s</td>' % (classes[i], escape(cell))
            for i, cell in enumerate(row))
        for row in rows)
    return "<table class=\"gl-table\"><tr>%s</tr>%s</table>" % (head, body)


def section(title, count, content):
    label = ' <span class="gl-n">%d</span>' % count if count else ""
    return ('<section class="gl-sec"><h3 class="gl-h">%s%s</h3>%s</section>'
            % (escape(title), label, content))


def main():
    data = json.load(open(paths.GLOSSARY, encoding="utf-8"))
    parts = []

    parts.append(section(
        "필드 이름", len(data["_field_labels"]),
        table(sorted(data["_field_labels"].items()), ["위키 필드", "표시 이름"],
              classes=("en", "ko"))))

    groups = data["terms"]
    total = sum(len(bucket) for bucket in groups.values())
    inner = "".join(
        section(name, len(bucket),
                table(sorted(bucket.items()), ["원문", "표기"], classes=("en", "ko")))
        for name, bucket in groups.items())
    parts.append(section("필드 값 (%d개)" % total, 0,
                         '<div class="gl-cols">%s</div>' % inner))

    parts.append(section("단위·꼬리말", len(UNIT_RULES),
                         table(UNIT_RULES, ["원문", "표기", "보기"])))
    parts.append(section("범위 그림 - 모양", len(SHAPES),
                         table(SHAPES, ["원문", "표기", "설명"])))
    parts.append(section("범위 그림 - 사거리가 없을 때", len(NO_RANGE),
                         table(NO_RANGE, ["구분", "표기", "뜻"])))

    os.makedirs(paths.LOCALIZED, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(LEAD + "".join(parts) + TAIL)
    print("용어집 본문 -> %s (필드 %d개 / 값 %d개)"
          % (OUT, len(data["_field_labels"]), total))


if __name__ == "__main__":
    main()
