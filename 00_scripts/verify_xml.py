# -*- coding: utf-8 -*-
"""위키에서 온 수치를 게임 XML 과 맞대고, 어디서 온 값인지까지 적는다.

백과사전 숫자는 대부분 **위키에서 온 것**이다. 위키는 사람이 손으로 적는 곳이라
패치를 놓치거나 칸을 헷갈릴 수 있다. 게임 XML 은 게임 그 자체라 틀릴 수 없다.

리포트에는 "다르다" 만 적지 않고 **XML 의 어느 정의, 어느 태그, 어느 파일**에서
읽은 값인지 함께 적는다. 그래야 받아 든 사람이 직접 열어 확인할 수 있다.

맞대는 칸:
  재사용 대기시간   게임이 띄우는 값(HDP 툴팁) ← Cost/Cooldown@TimeUse 를 추적용으로 첨부
  자원 소모        게임이 띄우는 값(HDP 툴팁) ← Cost/Vital@value 를 추적용으로 첨부
  레벨당 성장률     게임 툴팁의 "(+4% per level)"
  범위 그림 치수     스킬 이름으로 시작하는 정의들의 길이·각도
  시전 시간        CastIntroTime + CastOutroTime
  틱 주기          PeriodicPeriodArray 의 역수
  투사체 속도       Speed / SpeedMax
  소환물·무기 스탯   CUnit(Radius·SightRadius·LifeMax·Speed) / CWeapon(Range·Period)
  영웅 반지름       CUnit/Radius, CUnit/InnerRadius

스킬을 XML 에서 찾을 때 이펙트 그래프는 따라가지 않는다. 능력의 Range 가 500 이고
실제 사거리는 미사일 쪽에 있거나, nameId 가 XML 에는 CButton 으로만 있어 그래프가
곧잘 끊긴다. 대신 **이름이 그 스킬로 시작하는 정의**를 본다. HotS 데이터는
AnaHealingDartSearchArea 처럼 스킬 이름을 접두사로 붙이는 규칙이 일관돼 있다.

  python 00_scripts/verify_xml.py            리포트 생성
  python 00_scripts/verify_xml.py --strict   '확인 필요' 가 있으면 오류로 끝낸다

출력: 07_auto_localized/xml_check.md
"""
import argparse
import bisect
import collections
import glob
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

OUT = os.path.join(paths.LOCALIZED, "xml_check.md")
TOLERANCE = 0.011      # 위키가 소수 셋째 자리에서 반올림해 적는 경우가 있다
ROUNDING = 0.05        # 이보다 작은 차이는 위키가 잘라 적은 것
CASTER = 1.6           # 시전자 반지름만큼 어긋난 것 (중심 기준 vs 가장자리 기준)
SENTINEL = 100.0       # 500·360 처럼 '제한 없음'을 뜻하는 값은 비교 대상이 아니다

# 길이·각도를 담는 태그. 여기 값들이 곧 "XML 이 말하는 이 스킬의 치수" 다.
SIZE_TAGS = {"Radius", "InnerRadius", "RectangleWidth", "RectangleHeight",
             "Range", "MinimumRange", "Length", "Width", "Height", "Arc",
             "ArcSlop", "MaxDistance", "Distance"}
SIZE_ATTRS = ("Arc", "Radius", "RectangleWidth", "RectangleHeight",
              "X", "Y", "Length", "Width")

Found = collections.namedtuple("Found", "value defn tag file")


# --------------------------------------------------------------------------
# XML 읽기
# --------------------------------------------------------------------------
def load_catalog():
    """XML 정의를 어느 파일에서 왔는지와 함께 읽는다."""
    catalog, consts, files = collections.defaultdict(list), {}, 0
    root_dir = os.path.dirname(paths.ANALYSIS)
    for pattern in paths.XML_SOURCES:
        for path in sorted(glob.glob(pattern)):
            try:
                tree = ET.parse(path).getroot()
            except ET.ParseError:
                continue
            files += 1
            where = os.path.relpath(path, root_dir).replace("\\", "/")
            for element in tree:
                if element.tag == "const" and element.get("id"):
                    consts[element.get("id")] = element.get("value")
                elif element.get("id"):
                    catalog[element.get("id")].append((element, where))
    if not files:
        raise SystemExit("게임 XML 을 찾지 못했습니다. analysis 단계를 먼저 돌리세요.")
    return catalog, consts, files


NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


def number(text, consts, depth=0):
    """수치를 읽는다. $상수 면 풀어서 읽는다."""
    if not text or depth > 4:
        return None
    text = text.strip()
    if text.startswith("$"):
        return number(consts.get(text), consts, depth + 1)
    return float(text) if NUMBER.match(text) else None


def wiki_number(text):
    """위키 칸에서 숫자를 읽는다.

    '- Cast: 7.5 - Active: 11' 처럼 여러 값을 한 칸에 적은 것은 어느 쪽과 맞대야
    할지 알 수 없으므로 건너뛴다. 억지로 첫 숫자를 집으면 오탐만 늘어난다.
    """
    if text is None:
        return None
    found = re.match(r"^(-?\d+(?:\.\d+)?)\s*$", str(text).strip())
    return float(found.group(1)) if found else None


def matching_ids(keys, prefix):
    """prefix 로 시작하는 id 들. 70000개를 매번 훑지 않으려고 이분탐색을 쓴다."""
    start = bisect.bisect_left(keys, prefix)
    out = []
    for index in range(start, len(keys)):
        if not keys[index].startswith(prefix):
            break
        out.append(keys[index])
    return out


def sizes_of(catalog, consts, keys, prefix):
    """그 스킬 이름으로 시작하는 정의들이 들고 있는 길이·각도를 전부 모은다."""
    out = []
    for defn in matching_ids(keys, prefix):
        for element, where in catalog.get(defn, []):
            for child in element.iter():
                if child.tag in SIZE_TAGS:
                    value = number(child.get("value"), consts)
                    if value is not None:
                        out.append(Found(round(value, 4), defn, child.tag, where))
                for attr in SIZE_ATTRS:
                    value = number(child.get(attr), consts)
                    if value is not None:
                        out.append(Found(round(abs(value), 4), defn,
                                         "%s@%s" % (child.tag, attr), where))
    return out


def ability_node(catalog, keys, *names):
    """능력 정의를 찾는다. 정확한 이름 -> 그 이름으로 시작하는 첫 CAbil 순으로 본다."""
    for name in names:
        for element, where in catalog.get(name or "", []):
            if element.tag.startswith("CAbil"):
                return element, where, name
    for name in names:
        if not name:
            continue
        for defn in matching_ids(keys, name):
            for element, where in catalog.get(defn, []):
                if element.tag.startswith("CAbil"):
                    return element, where, defn
    return None, None, None


# --------------------------------------------------------------------------
# 판정
# --------------------------------------------------------------------------
WHY = {
    "확인 필요": "XML 에 비슷한 값조차 없다. 패치로 바뀌었는데 위키가 아직 안 고쳤거나, "
                 "위키가 칸을 헷갈렸거나, 내 해석이 틀렸을 수 있다.",
    "사거리 기준 차이": "위키는 시전자 가장자리, XML 은 중심에서 재는 경우가 있다 "
                        "(RangeUseCasterRadius). 차이가 영웅 반지름만 하면 이쪽이다.",
    "반올림 차이": "위키가 소수를 잘라 적은 것이다. 고칠 것 없다.",
    "위키 칸 헷갈림": "위키가 적어 둔 대기시간이 게임의 **마나 소모량**과 똑같다. "
                       "위키 페이지가 자원 값을 대기시간 칸에 넣은 것이라 백과사전에도 "
                       "그대로 잘못 나간다. 게임 값으로 바꿔야 한다.",
    "충전형 표기 차이": "충전을 쌓는 스킬이다. 위키는 전체 대기시간을, 게임은 충전 "
                         "하나가 차는 시간을 적어 어긋난다. 둘 다 맞는 값이다.",
    "대조 불가": "그 스킬 이름으로 시작하는 정의에 견줄 값이 없다. 미사일이나 공용 "
                 "이펙트가 값을 들고 있는 경우라 이 방식으로는 확인할 수 없다.",
}
ORDER = ["확인 필요", "위키 칸 헷갈림", "충전형 표기 차이", "사거리 기준 차이",
         "반올림 차이", "대조 불가"]


def judge(label, value, pool):
    """(분류, 가까운 Found 들). pool 은 Found 목록이다."""
    real = [f for f in pool if f.value < SENTINEL and f.value != 360.0]
    if not real:
        return "대조 불가", []
    near = sorted(real, key=lambda f: abs(f.value - value))[:3]
    gap = abs(near[0].value - value)
    if gap <= TOLERANCE:
        return "일치", near[:1]
    if gap <= ROUNDING:
        return "반올림 차이", near
    if label == "range" and gap <= CASTER:
        return "사거리 기준 차이", near
    return "확인 필요", near


def trace(found):
    """XML 위치를 사람이 읽을 한 줄로."""
    return " / ".join("`%s`·%s (%s)" % (f.defn, f.tag, f.file) for f in found) or "—"


# --------------------------------------------------------------------------
# 대조 항목
# --------------------------------------------------------------------------
def drawn_numbers(geom):
    """범위 그림이 실제로 쓰는 길이·각도. (칸 이름, 값) 목록."""
    out = []
    for part in (geom.get("parts") or [geom]):
        for key in ("radius", "inner", "outer", "width", "height", "depth",
                    "side", "arc", "flat"):
            if isinstance(part.get(key), (int, float)):
                out.append((key, float(part[key])))
    for key in ("range", "bounce", "search"):
        if isinstance(geom.get(key), (int, float)):
            out.append((key, float(geom[key])))
    return out


# prop 이름표 -> XML 어디를 볼지. 대부분 소환물 스탯이라 CUnit/CWeapon 에 있다.
# 마지막 칸은 값을 뒤집어야 하는지 - 위키 공격 속도는 초당 횟수, XML 은 주기다.
UNIT_STATS = {
    "unit radius": ("unit", "Radius", False),
    "inner radius": ("unit", "InnerRadius", False),
    "sight radius": ("unit", "SightRadius", False),
    "vision radius": ("unit", "SightRadius", False),
    "health": ("unit", "LifeMax", False),
    "movement speed": ("unit", "Speed", False),
    "attack range": ("weapon", "Range", False),
    "attack speed": ("weapon", "Period", True),
}


def unit_of(catalog, keys, prefix):
    """그 스킬이 소환하는 유닛 정의. 이름이 스킬 이름으로 시작하는 첫 CUnit."""
    for defn in matching_ids(keys, prefix):
        for element, where in catalog.get(defn, []):
            if element.tag.startswith("CUnit"):
                return element, where, defn
    return None, None, None


def weapon_of(catalog, unit):
    """유닛이 드는 무기 정의. WeaponArray 의 Link 를 따라간다."""
    if unit is None:
        return None, None, None
    array = unit.find("WeaponArray")
    link = array.get("Link") if array is not None else None
    for element, where in catalog.get(link or "", []):
        if element.tag.startswith("CWeapon"):
            return element, where, link
    return None, None, None


def stat_reads(catalog, consts, keys, prefix):
    """소환물·무기 스탯을 {이름표: [Found]} 로 모은다."""
    unit, unit_where, unit_id = unit_of(catalog, keys, prefix)
    if unit is None:
        return {}
    weapon, weapon_where, weapon_id = weapon_of(catalog, unit)
    out = {}
    for label, (owner, tag, invert) in UNIT_STATS.items():
        node, where, defn = ((unit, unit_where, unit_id) if owner == "unit"
                             else (weapon, weapon_where, weapon_id))
        if node is None:
            continue
        child = node.find(tag)
        value = number(child.get("value"), consts) if child is not None else None
        if value is None:
            continue
        if invert and value:
            value = round(1.0 / value, 4)     # 주기 1.05초 -> 초당 0.9524회
        out[label] = [Found(value, defn, "%s/%s" % (node.tag, tag), where)]
    return out


CAST_TIP = re.compile(r"\(\+([\d.]+)%\s*per level\)", re.I)
CAST_PAIR = re.compile(r"^([\d.]+)\s*\+\s*([\d.]+)\s*seconds?$", re.I)
TICKRATE = re.compile(r"^([\d.]+)\s*per second", re.I)
SPEED_TAGS = {"Speed", "SpeedMax", "MissileSpeed"}


def timing_reads(catalog, consts, keys, prefix, node):
    """시전 시간·틱 주기·투사체 속도를 모은다."""
    out = collections.defaultdict(list)
    if node is not None:
        for tag in ("CastIntroTime", "CastOutroTime", "CastFinishTime"):
            child = node.find(tag)
            value = number(child.get("value"), consts) if child is not None else None
            if value is not None:
                out["cast"].append(Found(value, prefix, tag, "-"))
    for defn in matching_ids(keys, prefix):
        for element, where in catalog.get(defn, []):
            for child in element.iter():
                if child.tag == "PeriodicPeriodArray":
                    value = number(child.get("value"), consts)
                    if value:
                        out["tickrate"].append(
                            Found(round(1.0 / value, 4), defn, child.tag, where))
                if child.tag in SPEED_TAGS:
                    value = number(child.get("value"), consts)
                    if value is not None:
                        out["missile"].append(Found(value, defn, child.tag, where))
    return out


def cost_values(node, consts):
    """능력 정의의 Cost 에서 대기시간·자원을 읽는다.

    충전형 스킬은 Cooldown 이 내부용 짧은 값이고 사람이 보는 것은 Charge/TimeUse 다
    (아바투르 독성 둥지: Cooldown 0.0625 / Charge 10). 둘 다 후보로 넣는다.
    """
    out = {"cooldown": [], "cost": []}
    cost = node.find("Cost")
    if cost is None:
        return out
    cooldown = cost.find("Cooldown")
    if cooldown is not None:
        value = number(cooldown.get("TimeUse"), consts)
        if value is not None:
            out["cooldown"].append(("Cost/Cooldown@TimeUse", value))
    charge = cost.find("Charge")
    if charge is not None:
        child = charge.find("TimeUse")
        value = number(child.get("value"), consts) if child is not None else None
        if value is not None:
            out["cooldown"].append(("Cost/Charge/TimeUse", value))
    for vital in cost.findall("Vital"):
        value = number(vital.get("value"), consts)
        if value is not None:
            out["cost"].append(("Cost/Vital@%s" % (vital.get("index") or "?"), value))
    return out


SCALING_TIP = re.compile(r"\(\+([\d.]+)%\s*per level\)", re.I)
COOLDOWN_TIP = re.compile(r"(?:Cooldown|Recharge)\s*:\s*([\d.]+)", re.I)
COST_TIP = re.compile(r":\s*([\d.]+)\s*$")


def game_tooltips(data):
    """게임이 실제로 띄우는 대기시간·자원. HDP 가 XML+게임스트링에서 뽑아 둔 값이다."""
    out = {}
    for hero in data.values():
        groups = list((hero.get("abilities") or {}).values())
        groups += list((hero.get("talents") or {}).values())
        for group in groups:
            for item in group:
                button = item.get("buttonId")
                if not button:
                    continue
                plain = lambda t: re.sub(r"<[^>]+>", "", t or "")
                cooldown = COOLDOWN_TIP.search(plain(item.get("cooldownTooltip")))
                cost = COST_TIP.search(plain(item.get("energyTooltip")).strip())
                scaling = SCALING_TIP.search(plain(item.get("fullTooltip")))
                out[button] = {
                    "cooldown": float(cooldown.group(1)) if cooldown else None,
                    "cost": float(cost.group(1)) if cost else None,
                    "scaling": float(scaling.group(1)) if scaling else None,
                }
    return out


def check_entries(catalog, consts, keys, targets, tooltips):
    """스킬·특성마다 위키 수치를 XML 과 맞댄다."""
    tally = collections.Counter()
    problems = collections.defaultdict(list)

    for hero_ko, button, name, fields, geom in targets:
        node, where, defn = ability_node(catalog, keys, name, button)

        # 1) 대기시간·자원.
        #    맞대는 상대는 게임이 화면에 띄우는 값(HDP 가 XML+게임스트링에서 뽑은
        #    툴팁)이다. 내가 XML 을 직접 읽는 것보다 정확하다 - 충전·연동 같은
        #    복잡한 계산을 HDP 가 이미 풀어 놓았다. XML 원본값은 추적용으로 함께 적는다.
        reads = cost_values(node, consts) if node is not None else {"cooldown": [], "cost": []}
        for label in ("cooldown", "cost"):
            shown = wiki_number(fields.get(label))
            actual = tooltips.get(button, {}).get(label)
            trail = [Found(v, defn, tag, where) for tag, v in reads[label]]
            if shown is None:
                continue                 # 위키에 그 칸이 아예 없다 - 셀 일이 아니다
            if actual is None:
                tally["%s 대조 불가" % label] += 1
                continue
            if abs(shown - actual) <= TOLERANCE:
                tally["%s 일치" % label] += 1
                continue
            # 위키가 마나 값을 대기시간 칸에 적어 둔 경우가 꽤 있다. 그러면 게임
            # 값과 크게 어긋나는데 패치 때문이 아니라 칸을 헷갈린 것이다.
            mana = [v for tag, v in reads["cost"] if v is not None]
            if label == "cooldown" and any(abs(shown - v) <= TOLERANCE for v in mana):
                kind = "위키 칸 헷갈림"
            elif any(t == "Cost/Charge/TimeUse" for t, _ in reads[label]):
                # 충전형은 위키가 총량을, 게임이 충전 하나치를 적어 어긋난다
                kind = "충전형 표기 차이"
            else:
                kind = "확인 필요"
            tally["%s %s" % (label, kind)] += 1
            problems[label].append((kind, hero_ko, button, shown,
                                    [Found(actual, "게임 표시값", "HDP 툴팁", "-")] + trail))

        # 2) 범위 그림에 쓴 치수.
        #    특성이 늘려 준 범위(src=upgrade)는 기반 스킬 값에 보너스를 더한 것이라
        #    그 특성 이름의 XML 에는 있을 리가 없다. 기반 스킬 쪽에서 이미 본다.
        if geom and geom.get("src") == "upgrade":
            tally["도형 특성이 늘린 값"] += 1
        elif geom and geom.get("src") != "manual":
            pool = sizes_of(catalog, consts, keys, name or button)
            for label, value in drawn_numbers(geom):
                if value > SENTINEL:
                    tally["도형 제한 없음 값"] += 1
                    continue
                kind, near = judge(label, value, pool)
                tally["도형 %s" % kind] += 1
                if kind != "일치":
                    problems["shape"].append((kind, hero_ko, button, value, near,
                                              label))
        elif geom:
            tally["도형 손으로 넣은 값"] += 1

        # 3) 레벨당 성장률 - 게임 툴팁이 "(+4% per level)" 로 직접 말해 준다
        shown = wiki_number(str(fields.get("scaling") or "").rstrip("%"))
        actual = tooltips.get(button, {}).get("scaling")
        if shown is not None and actual is not None:
            kind = "일치" if abs(shown - actual) <= ROUNDING else "확인 필요"
            tally["성장률 %s" % kind] += 1
            if kind != "일치":
                problems["scaling"].append(
                    (kind, hero_ko, button, shown,
                     [Found(actual, "게임 표시값", "HDP 툴팁", "-")], "scaling"))

        # 4) 시전 시간·틱 주기·투사체 속도
        timing = timing_reads(catalog, consts, keys, name or button, node)
        pair = CAST_PAIR.match(str(fields.get("cast") or "").strip())
        if pair:
            # 위키는 "앞 + 뒤 초" 로 적는다. 합이 맞으면 같은 값으로 본다.
            shown = float(pair.group(1)) + float(pair.group(2))
            pool = timing["cast"]
            total = sum(f.value for f in pool)
            if not pool:
                tally["시전 시간 대조 불가"] += 1
            else:
                kind = "일치" if abs(shown - total) <= ROUNDING else "확인 필요"
                tally["시전 시간 %s" % kind] += 1
                if kind != "일치":
                    problems["cast"].append((kind, hero_ko, button, shown, pool, "cast"))
        for label, key in (("틱 주기", "tickrate"), ("투사체 속도", "missile")):
            raw = fields.get(key)
            shown = (wiki_number(raw) if key == "missile"
                     else (float(TICKRATE.match(str(raw).strip()).group(1))
                           if raw and TICKRATE.match(str(raw).strip()) else None))
            if shown is None:
                continue
            pool = timing[key]
            if not pool:
                tally["%s 대조 불가" % label] += 1
                continue
            kind, near = judge(key, shown, pool)
            # 맞는 값이 하나도 없는데 스킬 안에 주기가 여럿이면 (피해용·소리용·
            # 시야용 persistent 가 따로 있다) 위키가 어느 것을 적은 건지 알 수 없다.
            # 첸 불의 숨결은 위키가 화상 지속피해 1회/초를, XML 은 원뿔 적용
            # 0.0625초×4 를 말한다. 가릴 수 없는 것을 "다르다" 고 외치면 거짓 경보다.
            if kind != "일치" and key == "tickrate" and len({f.value for f in pool}) > 1:
                kind = "대조 불가"
                near = []
            tally["%s %s" % (label, kind)] += 1
            if kind != "일치":
                problems[key].append((kind, hero_ko, button, shown, near, key))

        # 5) 소환물·무기 스탯 (prop 짝에 적혀 있다)
        stats = stat_reads(catalog, consts, keys, name or button)
        for index, label in list(fields.items()):
            found = re.match(r"^prop(\d+)$", index)
            if not found:
                continue
            want = str(label).strip().lower()
            if want not in stats:
                continue
            shown = wiki_number(fields.get("val" + found.group(1)))
            if shown is None:
                continue
            kind, near = judge(want, shown, stats[want])
            tally["유닛 스탯 %s" % kind] += 1
            if kind != "일치":
                problems["stat"].append((kind, hero_ko, button, shown, near, label))
    return tally, problems


def check_heroes(catalog, consts, data):
    """영웅 충돌·피격 반지름. 모든 범위 그림이 이 값으로 시전자를 그린다."""
    tally, problems = collections.Counter(), []
    for hero in data.values():
        unit = hero.get("unitId") or hero.get("hyperlinkId")
        node = next(((e, w) for e, w in catalog.get(unit, [])
                     if e.tag.startswith("CUnit")), None)
        if node is None:
            tally["유닛 못 찾음"] += 1
            continue
        element, where = node
        for key, tag in (("radius", "Radius"), ("innerRadius", "InnerRadius")):
            shown, child = hero.get(key), element.find(tag)
            actual = number(child.get("value"), consts) if child is not None else None
            if shown is None or actual is None:
                continue
            if abs(float(shown) - actual) <= TOLERANCE:
                tally["일치"] += 1
            else:
                tally["다름"] += 1
                problems.append((hero["hyperlinkId"], key, float(shown),
                                 Found(actual, unit, tag, where)))
    return tally, problems


# --------------------------------------------------------------------------
def encyclopedia():
    with open(paths.ENCYCLOPEDIA, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("const dataEN = "):
                return json.loads(line[len("const dataEN = "):].strip().rstrip(";"))
    return {}


def gather(data, rows):
    """(영웅 한글명, buttonId, nameId, 위키 필드, geom) 목록. 스킬과 특성 모두."""
    names = {}
    for hero in data.values():
        groups = list((hero.get("abilities") or {}).values())
        groups += list((hero.get("talents") or {}).values())
        for group in groups:
            for item in group:
                if item.get("buttonId"):
                    names[item["buttonId"]] = item.get("nameId")

    out = []
    for path in sorted(glob.glob(os.path.join(paths.HEROES_KR, "*.json"))):
        hero = json.load(open(path, encoding="utf-8"))
        for entry in hero["abilities"] + hero["talents"]:
            key = (entry["_match"].get("key") or "").split("/")[-1]
            if key:
                out.append((hero["hero_kr"], key, names.get(key),
                            entry.get("fields") or {},
                            (rows.get(key) or {}).get("geom")))
    return out


def section(lines, title, tally, prefix):
    picked = [(k[len(prefix):].strip(), v) for k, v in tally.most_common()
              if k.startswith(prefix)]
    if not picked:
        return
    lines += ["", "## %s" % title, ""]
    for key, count in picked:
        lines.append("- %s: **%d**" % (key, count))


def table(lines, title, rows, with_field=False):
    for kind in ORDER:
        picked = [r for r in rows if r[0] == kind]
        if not picked:
            continue
        lines += ["", "### %s — %s (%d건)" % (title, kind, len(picked)), "",
                  WHY.get(kind, ""), ""]
        if with_field:
            lines += ["| 영웅 | 스킬 | 칸 | 위키 | XML | XML 위치 |",
                      "|---|---|---|---|---|---|"]
        else:
            lines += ["| 영웅 | 스킬 | 위키 | XML | XML 위치 |", "|---|---|---|---|---|"]
        for row in picked:
            near = row[4]
            values = ", ".join(str(f.value) for f in near) or "—"
            if with_field:
                lines.append("| %s | `%s` | %s | %s | %s | %s |"
                             % (row[1], row[2], row[5], row[3], values, trace(near)))
            else:
                lines.append("| %s | `%s` | %s | %s | %s |"
                             % (row[1], row[2], row[3], values, trace(near)))


def main():
    parser = argparse.ArgumentParser(description="위키 수치를 게임 XML 과 대조")
    parser.add_argument("--strict", action="store_true",
                        help="'확인 필요' 가 있으면 오류로 끝낸다")
    args = parser.parse_args()

    catalog, consts, files = load_catalog()
    keys = sorted(catalog)
    print("  XML %d개 / 정의 %d개 / 상수 %d개" % (files, len(catalog), len(consts)))

    data = encyclopedia()
    rows = json.load(open(paths.WIKI_FIELDS, encoding="utf-8"))["rows"]
    targets = gather(data, rows)

    tally, problems = check_entries(catalog, consts, keys, targets,
                                    game_tooltips(data))
    hero_tally, hero_problems = check_heroes(catalog, consts, data)

    matched = sum(v for k, v in tally.items() if k.endswith("일치"))
    serious = sum(v for k, v in tally.items() if k.endswith("확인 필요"))
    undecidable = sum(v for k, v in tally.items() if k.endswith("대조 불가"))
    explained = sum(tally.values()) - matched - serious - undecidable

    lines = ["# 게임 XML 대조", "",
             "위키에서 온 수치를 게임 XML 과 맞대 본 결과다. 위키는 사람이 손으로 적는",
             "곳이라 패치를 놓치거나 칸을 헷갈릴 수 있고, XML 은 게임 그 자체라 틀릴 수",
             "없다. **여기 걸린 값은 틀렸다는 뜻이 아니라 사람이 한 번 봐야 한다는 뜻**이다.",
             "",
             "각 줄에 XML 의 어느 정의·태그·파일에서 읽었는지 적어 두었으니 직접 열어",
             "확인할 수 있다.", "",
             "대조 대상 **%d개** (스킬·특성)" % len(targets), "",
             "## 한눈에", "",
             "| | 값 |", "|---|---|",
             "| 맞대 본 수치 | **%d개** |" % sum(tally.values()),
             "| 게임과 일치 | **%d개** (%.1f%%) |"
             % (matched, 100.0 * matched / max(sum(tally.values()), 1)),
             "| 사람이 봐야 할 것 | **%d개** |" % serious,
             "| 이유가 밝혀진 차이 | **%d개** |" % explained,
             "| 이 방식으로는 못 보는 것 | **%d개** |" % undecidable]
    section(lines, "재사용 대기시간", tally, "cooldown")
    section(lines, "자원 소모", tally, "cost")
    section(lines, "범위 그림 치수", tally, "도형")
    section(lines, "레벨당 성장률", tally, "성장률")
    section(lines, "시전 시간", tally, "시전 시간")
    section(lines, "틱 주기", tally, "틱 주기")
    section(lines, "투사체 속도", tally, "투사체 속도")
    section(lines, "소환물·무기 스탯", tally, "유닛 스탯")
    lines += ["", "## 영웅 충돌·피격 반지름", ""]
    for key, count in hero_tally.most_common():
        lines.append("- %s: **%d**" % (key, count))

    table(lines, "재사용 대기시간", problems["cooldown"])
    table(lines, "자원 소모", problems["cost"])
    table(lines, "범위 그림 치수", problems["shape"], with_field=True)
    table(lines, "레벨당 성장률", problems["scaling"], with_field=True)
    table(lines, "시전 시간", problems["cast"], with_field=True)
    table(lines, "틱 주기", problems["tickrate"], with_field=True)
    table(lines, "투사체 속도", problems["missile"], with_field=True)
    table(lines, "소환물·무기 스탯", problems["stat"], with_field=True)
    if hero_problems:
        lines += ["", "### 영웅 반지름 — 다름", "",
                  "| 영웅 | 칸 | 백과사전 | XML | XML 위치 |", "|---|---|---|---|---|"]
        for hero, key, shown, found in hero_problems:
            lines.append("| %s | %s | %s | %s | %s |"
                         % (hero, key, shown, found.value, trace([found])))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")

    for prefix, title in (("cooldown", "대기시간"), ("cost", "자원"), ("도형", "도형"),
                          ("성장률", "성장률"), ("시전 시간", "시전"),
                          ("틱 주기", "틱"), ("투사체 속도", "투사체"),
                          ("유닛 스탯", "유닛")):
        picked = ["%s %d" % (k[len(prefix):].strip(), v)
                  for k, v in tally.most_common() if k.startswith(prefix)]
        if picked:
            print("  %s: %s" % (title, "  ".join(picked)))
    print("  영웅 반지름: " + "  ".join("%s %d" % kv for kv in hero_tally.most_common()))
    print("-> %s" % OUT)

    serious = sum(1 for group in problems.values() for row in group
                  if row[0] == "확인 필요")
    if args.strict and (serious or hero_problems):
        raise SystemExit("사람이 봐야 할 값이 %d건 있습니다."
                         % (serious + len(hero_problems)))


if __name__ == "__main__":
    main()
