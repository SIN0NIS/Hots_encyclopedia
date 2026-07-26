# -*- coding: utf-8 -*-
"""위키가 주는 데이터를 전부 세어 목록으로 만든다.

검증을 설계하려면 "무엇을 검증할 수 있는가" 부터 알아야 한다. 이 스크립트는
위키에서 긁어 온 필드를 하나도 빼지 않고 세고, 각 숫자를 **게임 쪽 어디서 찾을 수
있는가** 로 나눈다. 그 분류가 곧 verify_xml.py 가 무엇을 대조할지 정하는 근거다.

  A 게임이 직접 주는 값   HDP 가 XML 을 풀어 놓은 값. 대조가 거의 공짜다.
  B 유닛·무기 스탯       CUnit/CWeapon 정의에 1:1 로 있다.
  C 범위 치수            스킬 이름으로 시작하는 CEffectEnumArea 에 있다.
  D 짝짓기 불확실        XML 에 있긴 한데 어느 값이 그 값인지 정하기 어렵다.
  E 글 속 숫자           비고 문장이나 렌더링 플래그. 대조 대상이 아니다.

  python 00_scripts/wiki_inventory.py

출력: 07_auto_localized/wiki_inventory.md
"""
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

OUT = os.path.join(paths.LOCALIZED, "wiki_inventory.md")

PROP = re.compile(r"^prop(\d+)$")
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
ONLY_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")
LABELLED = re.compile(r"^-\s*\w[^:]*:")
SIZE_PAIR = re.compile(r"^-?[\d.]+\s*[x×]\s*[\d.]+$")

# 위키 편집자가 오타를 낸 필드. 이름이 안 맞으니 지금은 조용히 버려진다.
KNOWN_TYPOS = {"typer": "type", "taget": "target", "tartget": "target",
               "afects": "affects", "pro1": "prop1", "properties": "props",
               "nohr2": "nohr"}

# prop 이름표를 어디서 찾을지 가르는 규칙
UNIT_STAT = re.compile(r"^(unit|sight|vision|attack|leash|movement|basic attack|"
                       r"health|mana|armor|acquisition|chase)\b", re.I)
AREA = re.compile(r"(radius|width|height|arc)$", re.I)

GAME_FIELDS = ("cooldown", "cost")
AREA_FIELDS = ("radius", "width", "height", "arc", "hitbox", "range")
SOFT_FIELDS = ("scaling", "cast", "tickrate", "missile", "notes", "speed",
               "cast range", "channel range")

TIERS = ["A 게임이 직접 주는 값", "B 유닛·무기 스탯", "C 범위 치수",
         "D 짝짓기 불확실", "E 글 속 숫자"]


def value_shape(text):
    text = str(text).strip()
    if ONLY_NUMBER.match(text):
        return "숫자"
    if LABELLED.match(text):
        return "이름표 목록"
    if SIZE_PAIR.match(text):
        return "폭x길이"
    if re.match(r"^-?[\d.]+\s*\S", text):
        return "숫자+단위"
    return "글"


def tier_of(field, label):
    """이 숫자를 게임 쪽 어디서 찾을 수 있는가."""
    if label is not None:
        if UNIT_STAT.match(label):
            return "B 유닛·무기 스탯"
        if AREA.search(label):
            return "C 범위 치수"
        return "D 짝짓기 불확실"
    if field in GAME_FIELDS:
        return "A 게임이 직접 주는 값"
    if field in AREA_FIELDS:
        return "C 범위 치수"
    if field in SOFT_FIELDS:
        return "D 짝짓기 불확실"
    return "E 글 속 숫자"


def scan():
    fields = collections.Counter()
    shapes = collections.defaultdict(collections.Counter)
    origin = collections.defaultdict(collections.Counter)
    props = collections.Counter()
    tiers = collections.Counter()
    inside = collections.defaultdict(collections.Counter)
    typos = collections.Counter()
    entries = 0

    for path in sorted(glob.glob(os.path.join(paths.HEROES_KR, "*.json"))):
        hero = json.load(open(path, encoding="utf-8"))
        for kind, group in (("스킬", hero["abilities"]), ("특성", hero["talents"])):
            for entry in group:
                data = entry.get("fields") or {}
                if data:
                    entries += 1
                for key, value in data.items():
                    if key.startswith("val"):
                        continue
                    if key in KNOWN_TYPOS:
                        typos[key] += 1
                    found = PROP.match(key)
                    if found:
                        label = str(value).strip()
                        props[label] += 1
                        raw = data.get("val" + found.group(1))
                    else:
                        label, raw = None, value
                        fields[key] += 1
                        shapes[key][value_shape(value)] += 1
                        origin[key][kind] += 1
                    numbers = NUMBER.findall(str(raw or ""))
                    if numbers:
                        tier = tier_of(key, label)
                        tiers[tier] += len(numbers)
                        inside[tier][label or key] += len(numbers)
    return entries, fields, shapes, origin, props, tiers, inside, typos


def main():
    entries, fields, shapes, origin, props, tiers, inside, typos = scan()
    total = sum(tiers.values())

    lines = ["# 위키 데이터 목록", "",
             "위키에서 긁어 온 것을 하나도 빼지 않고 센 결과다. 검증을 설계하려면",
             "무엇이 있는지부터 알아야 해서 만들었다.", "",
             "- 필드가 붙은 항목: **%d개** (스킬·특성)" % entries,
             "- 서로 다른 필드 이름: **%d개**" % len(fields),
             "- prop 이름표: **%d종**" % len(props),
             "- 위키가 들고 있는 숫자: **%d개**" % total, "",
             "## 필드별", "",
             "| 필드 | 전체 | 스킬 | 특성 | 값 생김새 |", "|---|---|---|---|---|"]
    for key, count in fields.most_common():
        lines.append("| `%s` | %d | %d | %d | %s |"
                     % (key, count, origin[key]["스킬"], origin[key]["특성"],
                        ", ".join("%s %d" % kv for kv in shapes[key].most_common(3))))

    if typos:
        lines += ["", "## 위키 편집자 오타", "",
                  "필드 이름이 어긋나 지금은 값이 조용히 버려진다. 읽을 때 고쳐 주면 "
                  "그만큼 데이터가 늘어난다.", "",
                  "| 적힌 이름 | 원래 이름 | 횟수 |", "|---|---|---|"]
        for key, count in typos.most_common():
            lines.append("| `%s` | `%s` | %d |" % (key, KNOWN_TYPOS[key], count))

    lines += ["", "## 숫자를 게임 쪽 어디서 찾을 수 있나", "",
              "| 갈래 | 숫자 | 비중 | 많이 차지하는 것 |", "|---|---|---|---|"]
    for tier in TIERS:
        count = tiers.get(tier, 0)
        if not count:
            continue
        top = ", ".join("%s %d" % kv for kv in inside[tier].most_common(5))
        lines.append("| %s | %d | %.1f%% | %s |"
                     % (tier, count, 100.0 * count / total, top))

    lines += ["", "## prop 이름표 (상위 30종)", "",
              "| 이름표 | 횟수 | 갈래 |", "|---|---|---|"]
    for label, count in props.most_common(30):
        lines.append("| %s | %d | %s |" % (label, count, tier_of(None, label)))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    print("  항목 %d개 / 필드 %d종 / prop 이름표 %d종 / 숫자 %d개"
          % (entries, len(fields), len(props), total))
    for tier in TIERS:
        if tiers.get(tier):
            print("    %-22s %5d (%4.1f%%)"
                  % (tier, tiers[tier], 100.0 * tiers[tier] / total))
    if typos:
        print("  위키 오타 필드 %d종: %s" % (len(typos), ", ".join(sorted(typos))))
    print("-> %s" % OUT)


if __name__ == "__main__":
    main()
