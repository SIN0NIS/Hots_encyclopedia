"""heroes_kr/*.json 의 위키 메타 필드를 백과사전 HTML 이 쓸 형태로 뽑는다.

백과사전의 ability/talent 는 `buttonId` 를 들고 있고, 이는 gamestring 키의 접미사와
같다. 한글화 단계에서 이미 gamestring 키를 확정해 두었으므로 그대로 조인 키가 된다.
buttonId 로 못 찾을 때를 대비해 nameId·(영웅|이름) 별칭도 함께 싣는다.

출력: hots_kr/wiki_fields.json
  { "rows": { <buttonId>: {"en": [[label,value],...], "ko": [...],
                           "noteEn": str|null, "noteKo": str|null,
                           "descEn": str|null, "descKo": str|null} },
    "alias": { "<heroId>|<정규화한 이름>": <buttonId> } }
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
from gamestrings import normalize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = paths.HEROES_KR
AOE_OVERRIDES = paths.AOE_OVERRIDES
OUT = paths.WIKI_FIELDS
ENCYCLOPEDIA = paths.ENCYCLOPEDIA


def encyclopedia_data():
    """백과사전이 들고 있는 영웅 사전. 파일이 커서 한 번만 읽는다."""
    if not hasattr(encyclopedia_data, "cache"):
        encyclopedia_data.cache = {}
        with open(ENCYCLOPEDIA, encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("const dataEN = "):
                    encyclopedia_data.cache = json.loads(
                        line[len("const dataEN = "):].strip().rstrip(";"))
                    break
    return encyclopedia_data.cache


def hyperlink_ids():
    """백과사전의 영문 영웅명 -> hyperlinkId.

    별칭 키는 백과사전이 조회할 때 쓰는 hyperlinkId 로 맞춰야 한다. 내 hero_id 는
    게임 내부 코드명(Firebat, L90ETC …)이라 백과사전 쪽과 네임스페이스가 다르다.
    """
    return {normalize(h["name"]): h["hyperlinkId"]
            for h in encyclopedia_data().values()}


def talent_targets():
    """특성 buttonId -> 그 특성이 손보는 스킬의 buttonId.

    특성 항목의 nameId 가 대상 스킬을 가리킨다 (가압 분비선 -> 가시 폭발). 덕분에
    "반경 +1.0" 같은 값을 어느 스킬에 더해야 하는지 알 수 있다.
    """
    out = {}
    for hero in encyclopedia_data().values():
        for level in (hero.get("talents") or {}).values():
            for talent in level:
                target, button = talent.get("nameId"), talent.get("buttonId")
                if target and button and target != button:
                    out[button] = target
    return out

PROP = re.compile(r"^prop(\d+)$")
SKIP = {"nohr", "nohr2"}          # 위키 내부 렌더링 플래그

# 위키 템플릿의 필드 키를 위키가 실제로 화면에 쓰는 표기로 되돌린다.
EN_LABELS = {
    "type": "Type", "scaling": "Scaling", "affects": "Affects", "props": "Properties",
    "target": "Target", "cast": "Cast time", "range": "Range", "hitbox": "Hitbox",
    "missile": "Missile speed", "cooldown": "Cooldown", "cost": "Cost",
    "aoe": "Area shape", "radius": "Radius", "arc": "Arc", "width": "Width",
    "height": "Height", "speed": "Speed", "tickrate": "Tickrate",
    "targeting": "Targeting", "cast range": "Cast range",
    "channel range": "Channel range",
}


def en_label(key):
    return EN_LABELS.get(key, key[:1].upper() + key[1:] if key else key)


def rows_of(entry):
    """[(라벨_en, 값_en), ...] 와 [(라벨_ko, 값_ko), ...] 를 나란히 만든다.

    prop1/val1 같은 짝은 한 줄로 합친다 — prop 쪽 문구가 곧 라벨이기 때문이다.
    """
    fields = entry.get("fields") or {}
    fields_kr = entry.get("fields_kr") or {}
    # fields_kr 은 fields 를 순서대로 옮긴 것이라 위치가 1:1 로 대응한다
    pairs = list(zip(fields.items(), fields_kr.items()))
    if len(pairs) != len(fields):
        pairs = [((k, v), (k, v)) for k, v in fields.items()]

    en, ko, note_en, note_ko, skip = [], [], None, None, set()
    for index, ((key_en, val_en), (key_ko, val_ko)) in enumerate(pairs):
        if key_en in SKIP or index in skip:
            continue
        if key_en == "notes":
            note_en, note_ko = val_en, val_ko
            continue
        prop = PROP.match(key_en)
        if prop:
            mate = "val" + prop.group(1)
            found = next((i for i, p in enumerate(pairs) if p[0][0] == mate), None)
            if found is not None:
                skip.add(found)
                en.append([val_en, pairs[found][0][1]])
                ko.append([val_ko, pairs[found][1][1]])
                continue
        en.append([en_label(key_en), val_en])
        ko.append([key_ko, val_ko])
    return en, ko, note_en, note_ko


NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
INNER = re.compile(r"inner\s*:?\s*(\d+(?:\.\d+)?)", re.I)
OUTER = re.compile(r"outer\s*:?\s*(\d+(?:\.\d+)?)", re.I)


# 위키 각주. 원문이 <sup>(1)</sup> 라 태그를 걷어내면 "(1" 만 남는다.
FOOTNOTE = re.compile(r"\s*\(\d+\s*$")


def clean(text):
    return FOOTNOTE.sub("", (text or "").strip())


def number(text):
    """'45 degrees' -> 45.0, '- Base: 2.0 - Verdant Spheres: 3.0' -> 2.0"""
    if not text:
        return None
    found = NUMBER.search(text)
    return float(found.group()) if found else None


# 복합 값. 두 가지 적는 방식이 섞여 있다.
#   "- Slam: Circle - Shockwave: Rectangle"   앞에 이름표를 달아 나열
#   "2.5 (slam)"                              값 뒤 괄호에 이름표
LABELLED_LIST = re.compile(r"-\s*([^:]+?)\s*:\s*([^-]+)")
LABELLED_ONE = re.compile(r"^(.*?)\s*\(([^)]+)\)\s*$")


def labelled(text):
    """이름표가 붙은 값들을 {이름표: 값} 으로 편다. 이름표가 없으면 {"": 값}."""
    text = clean(text)
    if not text:
        return {}
    if text.startswith("-"):
        return {key.strip().lower(): value.strip()
                for key, value in LABELLED_LIST.findall(text)}
    single = LABELLED_ONE.match(text)
    if single and not single.group(2).replace(".", "").isdigit():
        return {single.group(2).strip().lower(): single.group(1).strip()}
    return {"": text}


def pick(values, label):
    """이름표로 값을 고른다. 이름표 없는 값은 모두가 나눠 쓴다."""
    if label in values:
        return values[label]
    for key, value in values.items():
        if key and (key.startswith(label) or label.startswith(key)):
            return value
    return values.get("")


HITBOX = re.compile(r"(\d+(?:\.\d+)?)\s*[x×]\s*(\d+(?:\.\d+)?)")
MAX_RANGE = re.compile(r"max(?:imum)?\s*:?\s*(\d+(?:\.\d+)?)", re.I)


# 이름표가 여럿일 때 어느 값을 피해 범위로 볼지. 앞쪽이 우선이다.
DAMAGE_LABELS = ("explosion", "splash", "damage", "impact", "blast", "pool",
                 "outer", "final", "maximum", "max", "area", "end")
# 피해 범위가 아닌 것들 - 날아가는 물체 크기나 탐지·획득 반경이다
NOT_DAMAGE = ("hitbox", "collision", "acquisition", "target search", "trigger",
              "drop", "pickup", "vision", "sight", "tether", "path", "launch",
              "bounce", "collect", "mineral", "deaths", "focus", "weapon",
              "cannon", "leash", "spawn")

# 다음 대상으로 튀어 가는 거리. 맞은 대상을 중심으로 재므로 피해 범위와 기준점이
# 다르다. 위키는 이를 radius 에도(카시아 번개 구체) range 에도(스랄 연쇄 번개) 적는다.
BOUNCE = re.compile(r"bounce|chain|ricochet|jump", re.I)
BOUNCE_NOTE = re.compile(r"bounce radius", re.I)


def bounce_reach(fields):
    """튕겨 갈 수 있는 거리. 없으면 None."""
    for key in ("radius", "range"):
        for label, value in labelled(fields.get(key)).items():
            if label and BOUNCE.search(label):
                found = number(value)
                if found is not None:
                    return found
    # prop 짝에 적어 둔 경우 (요한나 축복받은 방패의 Bounce search radius)
    found, _ = prop_value(fields, PROP_BOUNCE)
    if found is not None:
        return found
    # 이름표 없이 비고에만 적어 둔 경우 (카시아 번개의 일격)
    if BOUNCE_NOTE.search(fields.get("notes") or ""):
        values = labelled(fields.get("radius"))
        if len(values) == 1 and "" in values:
            return number(fields.get("radius"))
    return None


# 위키가 prop1/val1 짝으로 적어 둔 수치. aoe/radius 칸에는 안 들어가지만 실제로는
# 범위인 것들이 여기 숨어 있다 (가로쉬 파쇄추의 인식 2.25 / 착지 2.5).
PROP_AREA = re.compile(
    r"^(impact|explosion|splash|power field|blast|detonation|center|end area|"
    r"spread|pickup) radius$", re.I)
PROP_SEARCH = re.compile(r"^(?!bounce)[\w ]*?search radius$", re.I)
# 폭·길이·각도를 aoe 칸 대신 prop 짝에 적어 둔 스킬이 있다 (오르페아 어둠의 왈츠).
PROP_SIZE = {
    "width": re.compile(r"^(?!bonus)([\w ]*? )?width$", re.I),
    "height": re.compile(r"^(?!bonus)([\w ]*? )?height$", re.I),
    "arc": re.compile(r"^(?!bonus)([\w ]*? )?arc$", re.I),
}


# "Pull area width" 처럼 앞에 이름표가 붙은 폭. 이름표 없는 "Width" 는 뺀다.
PROP_ZONE_WIDTH = re.compile(r"^(?!bonus)(.+?)\s+(?:area\s+)?width$", re.I)


def rect_zones(fields, height):
    """폭이 다른 구역이 둘 이상인 직사각형. 없으면 빈 목록.

    한 스킬 안에서 끌어당기는 넓이와 피해를 주는 넓이가 다를 때 위키는 이를
    prop 짝에 따로 적는다. 넓은 것부터 그려야 좁은 쪽이 위로 올라온다.
    """
    found = []
    for label, value in props(fields).items():
        name = PROP_ZONE_WIDTH.match(label)
        width = number(value) if name else None
        if width is not None:
            found.append((width, name.group(1).strip()))
    if len(found) < 2:
        return []
    return [{"shape": "rectangle", "width": w, "height": height, "at": 0, "label": name}
            for w, name in sorted(found, reverse=True)]


def sized(fields, key):
    """치수를 fields 에서 먼저 찾고, 없으면 prop 짝에서 찾는다."""
    if fields.get(key):
        return fields[key]
    found, _ = prop_value(fields, PROP_SIZE[key])
    return None if found is None else str(found)
PROP_BOUNCE = re.compile(r"^[\w ]*?bounce[\w ]*? radius$", re.I)


# 특성이 대상 스킬의 범위를 늘려 주는 값. "Bonus radius 1.0" 처럼 적혀 있다.
BONUS_RADIUS = re.compile(r"^bonus\b.*\bradius$", re.I)
BONUS_RANGE = re.compile(r"^bonus\b.*\brange$", re.I)
# 그림에 반영할 수 없는 것들 - 시야나 평타 사거리, 유닛 크기라 범위와 무관하다
BONUS_SKIP = ("sight", "vision", "attack", "hitbox", "unit", "creep",
              "per bounce", "leash")
# 도형마다 '크기' 를 담는 칸이 다르다. 앞에서부터 있는 칸에 더한다.
# width 는 넣지 않는다 - 관통 스킬의 width 는 투사체 굵기라 여기에 더하면
# 스투코프 전력 투구가 굵기 1.0 -> 6.75 인 괴물이 된다.
SIZE_FIELDS = ("radius", "outer", "side")


def bonus_of(fields, pattern):
    """특성이 더해 주는 값. 없으면 None."""
    for label, value in props(fields).items():
        if pattern.match(label) and not any(bad in label for bad in BONUS_SKIP):
            found = damage_number(value)     # "- Center: 0.375 - Outer: 1.25" 는 바깥값
            if found is not None:
                return found
    return None


def apply_bonus(base, add_size, add_range):
    """대상 스킬의 범위에 특성 보정을 얹은 도형과, 무엇이 얼마나 변했는지를 돌려준다.

    조각이 여럿인 스킬은 어느 조각에 얹어야 할지 데이터로 알 수 없어 그림은 그대로
    두고 수치만 알린다 - 아무 조각에나 더하면 거짓 그림이 된다.
    """
    changes = []
    geom = json.loads(json.dumps(base)) if base else None

    def bump(field, amount):
        """소수점 쓰레기가 붙지 않게 자른다 (2.25 + 0.3375 -> 2.5875)."""
        was = geom[field]
        now = round(was + amount, 4)
        geom[field] = now
        changes.append((field, was, now))

    if geom and not geom.get("parts"):
        if add_size is not None:
            field = next((f for f in SIZE_FIELDS
                          if isinstance(geom.get(f), (int, float))), None)
            # 크기를 담는 칸이 없는 도형에 "반경 +N" 이 붙었다면 위키가 사거리를
            # radius 라 적은 것이다 (스투코프 전력 투구: 툴팁은 "range by 50%").
            if field is None and isinstance(geom.get("range"), (int, float)):
                field, add_range = "range", None
            if field:
                bump(field, add_size)
        if add_range is not None and isinstance(geom.get("range"), (int, float)):
            bump("range", add_range)
    if not changes:
        geom = None                          # 그릴 수 없으면 도형을 만들지 않는다
    return geom, changes


SIZE_KO = {"radius": "반경", "outer": "바깥 반경", "side": "한 변",
           "width": "폭", "range": "사거리"}
SIZE_EN = {"radius": "radius", "outer": "outer radius", "side": "side",
           "width": "width", "range": "range"}


def upgrade_rows(ability_ko, ability_en, changes, add_size, add_range):
    """스킬·특성 카드 하단의 위키 상세 표에 넣을 '범위 변화' 줄."""
    if changes:
        ko = " · ".join("%s %s → %s" % (SIZE_KO.get(f, f), a, b) for f, a, b in changes)
        en = " · ".join("%s %s → %s" % (SIZE_EN.get(f, f), a, b) for f, a, b in changes)
    else:
        # 대상 스킬의 도형을 못 찾았거나 조각이 여럿이라 더할 자리가 없는 경우
        parts_ko, parts_en = [], []
        if add_size is not None:
            parts_ko.append("반경 +%s" % add_size)
            parts_en.append("radius +%s" % add_size)
        if add_range is not None:
            parts_ko.append("사거리 +%s" % add_range)
            parts_en.append("range +%s" % add_range)
        ko, en = " · ".join(parts_ko), " · ".join(parts_en)
    return (["Area change", "%s — %s" % (ability_en, en)],
            ["범위 변화", "%s — %s" % (ability_ko, ko)])


def props(fields):
    """{prop 이름(소문자): 값} 으로 편다."""
    out = {}
    for key, label in fields.items():
        found = PROP.match(key)
        if found:
            value = fields.get("val" + found.group(1))
            if value is not None:
                out[clean(label).lower()] = value
    return out


def prop_value(fields, pattern):
    """prop 이름이 규칙에 맞는 첫 값을 숫자로. 특성이 더해 주는 값(bonus)은 뺀다."""
    for label, value in props(fields).items():
        if label.startswith("bonus"):
            continue
        if pattern.match(label):
            found = number(value)
            if found is not None:
                return found, label
    return None, None


def damage_radius(text):
    """피해가 들어가는 반경만 돌려준다. 획득·감지·판정 반경이면 None.

    "5.5 (bounce)" 는 튕겨 나가는 거리, "1.5 (pickup)" 은 줍는 거리다. 이런 값을
    피해 원으로 그리면 그만큼 넓게 맞는 것처럼 보인다.
    """
    values = labelled(text)
    if len(values) == 1 and "" in values:
        return number(text)                       # 이름표 없는 순수한 반경
    for label, value in values.items():
        if any(bad in label for bad in NOT_DAMAGE):
            continue
        found = number(value)
        if found is not None:
            return found
    return None


def damage_number(text):
    """이름표가 붙은 수치에서 '피해가 들어가는' 값을 고른다.

    "- Hitbox: 0.5 - Explosion: 2.0" 에서 앞의 0.5 를 집으면 투사체 크기를
    피해 범위로 그리게 된다. 실제로 맞는 넓이는 2.0 이다.
    """
    values = labelled(text)
    if len(values) <= 1:
        return number(text)
    for want in DAMAGE_LABELS:
        for label, value in values.items():
            if want in label:
                return number(value)
    # 이름표를 모르겠으면 피해와 무관한 것만 걸러내고 남은 첫 값을 쓴다
    for label, value in values.items():
        if not any(bad in label for bad in NOT_DAMAGE):
            return number(value)
    return number(text)


def cast_range(text):
    """사거리 문자열에서 실제로 날아가는 거리를 뽑는다.

    '- Min: 3 - Max: 18.25' 처럼 최소·최대가 같이 적힌 경우 최대를 쓴다.
    첫 숫자를 집으면 최소치가 잡혀 경로가 실제보다 훨씬 짧게 그려진다.
    """
    if not text:
        return None
    largest = MAX_RANGE.search(text)
    return float(largest.group(1)) if largest else number(text)


# "Shuriken at the edges are aligned 10 degrees to both sides from the target point."
SPREAD_ANGLE = re.compile(
    r"(\d+(?:\.\d+)?)\s*degrees?\s*(?:to\s+)?(?:both sides|each side)", re.I)
SPREAD_COUNT = re.compile(r"\b(?:throw|fire|launch|shoot|release)s?\s+(\d+)\b", re.I)


def spread_of(fields, description):
    """한 번에 여러 갈래로 나가는 스킬인지 본다.

    위키가 비고에 각도를 적어 두는 경우에만 잡는다 (겐지 수리검). 문구가 없으면
    갈래 수를 알 길이 없으므로 한 갈래로 그린다 - 지어내지 않는다.
    """
    text = "%s %s" % (fields.get("notes") or "", description or "")
    angle = SPREAD_ANGLE.search(text)
    if not angle:
        # "Wave spacing = 20 degrees" 처럼 항목으로 적힌 경우
        for key, value in fields.items():
            if key.startswith("prop") and "spacing" in (value or "").lower():
                raw = fields.get("val" + key[4:]) or ""
                if "degree" in raw.lower():
                    angle = re.match(r"\s*(\d+(?:\.\d+)?)", raw)
                break
    if not angle:
        return None
    count = SPREAD_COUNT.search(text) or WAVE_COUNT.search(text)
    # "양옆으로" 라면 가운데 한 갈래에 좌우가 붙어 최소 3갈래다
    return {"angle": float(angle.group(1)),
            "count": int(count.group(1)) if count else 3}


HITBOX_RADIUS = re.compile(r"(\d+(?:\.\d+)?)\s*\(\s*hitbox\s*\)", re.I)
LABELLED_HITBOX = re.compile(r"hitbox\s*:\s*(\d+(?:\.\d+)?)", re.I)


def hitbox_width(fields):
    """반경 칸에 적힌 투사체 굵기를 꺼낸다.

    "0.65 (hitbox)" 나 "- Hitbox: 0.5 - Vision: 7.0" 처럼 적힌 값은 피해 반경이
    아니라 날아가는 물체의 굵기다. 원으로 그리면 그만큼 넓게 맞는 것처럼 보인다.
    """
    text = clean(fields.get("radius"))
    found = HITBOX_RADIUS.search(text) or LABELLED_HITBOX.search(text)
    return float(found.group(1)) if found else None


# "Sends 5 waves." 처럼 비고에 갈래 수가 적힌 경우
WAVE_COUNT = re.compile(r"\bsends?\s+(\d+)\s+waves?", re.I)


def skillshot_geometry(fields, description=None):
    """aoe 는 없고 hitbox 만 있는 논타겟 스킬. 지나간 자리를 경로로 그린다.

    hitbox 는 "폭 x 두께" 다. 데스윙 대격변이 aoe=Rectangle·width=9.0 인데
    hitbox=9.0 x 3.0 인 것이 근거 - 앞 수치가 진행 방향에 수직인 폭이고,
    뒤 수치는 투사체 자체의 앞뒤 두께다.
    """
    matched = HITBOX.search(fields.get("hitbox") or "")
    if matched:
        width, depth = float(matched.group(1)), float(matched.group(2))
    else:
        # hitbox 칸이 없고 반경 칸에 굵기가 적힌 경우 (갈 어둠의 화살 등)
        width = hitbox_width(fields)
        if width is None:
            return None
        depth = width
    distance = cast_range(fields.get("range"))
    geom = {"shape": "skillshot", "label": "Skillshot (hitbox)",
            "width": width, "depth": depth}
    spread = spread_of(fields, description)
    if spread:
        geom["spread"] = spread
    if distance is not None:
        geom["range"] = distance
    elif (fields.get("range") or "").strip().lower() == "global":
        geom["global"] = True
    else:
        geom["noRange"] = "unstated"
    return geom


# "Call forth three bursts", "Launch 3 blasts into the air"
BLAST_COUNT = re.compile(
    r"\b(two|three|four|five|2|3|4|5)\s+"
    r"(?:bursts?|blasts?|waves?|explosions?|missiles?|projectiles?|bolts?|orbs?)", re.I)
AOE_TIMES = re.compile(r"\(x(\d+)\)")
WORD_TO_NUMBER = {"two": 2, "three": 3, "four": 4, "five": 5}


def repeat_of(fields, shape_raw, description):
    """한 번 시전에 같은 범위가 여러 번, 일렬로 떨어지는 스킬.

    굴단 부패(3연발)·크로미 용의 숨결(3연발)이 이에 해당한다. 개수는 aoe 의
    "(x3)" 이나 설명문의 "three bursts" 에서, 간격은 "* spacing" 항목에서 읽는다.
    둘 다 있어야만 인정한다 - 간격을 모르면 어디에 그릴지 알 수 없다.
    """
    spacing = None
    for key, value in fields.items():
        if not key.startswith("prop") or "spacing" not in (value or "").lower():
            continue
        raw = fields.get("val" + key[4:]) or ""
        if "degree" in raw.lower():
            return None          # 각도로 벌어지는 것은 일렬이 아니다
        spacing = number(raw)
        break
    if not spacing:
        return None

    times = AOE_TIMES.search(shape_raw)
    if times:
        count = int(times.group(1))
    else:
        found = BLAST_COUNT.search(description or "")
        if not found:
            return None
        token = found.group(1).lower()
        count = WORD_TO_NUMBER.get(token) or int(token)
    return {"count": count, "spacing": spacing} if count > 1 else None


SHAPE_WORDS = {"circle": "circle", "radial": "radial", "rectangle": "rectangle",
               "square": "square", "ring": "ring", "triangle": "triangle",
               "equilateral": "triangle"}


def one_shape(shape, values, label):
    """이름표 하나에 해당하는 도형을 만든다. 못 만들면 None."""
    geom = {"shape": shape, "label": label.strip() or shape}
    distance = number(pick(values["range"], label))
    if distance is not None:
        geom["range"] = distance

    if shape == "ring":
        text = pick(values["radius"], label) or ""
        inner, outer = INNER.search(text), OUTER.search(text)
        if not (inner and outer):
            return None
        geom["inner"], geom["outer"] = float(inner.group(1)), float(outer.group(1))
    elif shape in ("rectangle", "square"):
        width = number(pick(values["width"], label))
        height = number(pick(values["height"], label))
        if width is None:
            # 직사각형인데 너비·길이 대신 판정 상자로 적힌 경우 (들창코 충격파).
            # 이때 길이는 사거리 그 자체다 - 시전자에게서 그만큼 뻗어 나가므로
            # 사거리를 다시 오프셋으로 쓰면 두 번 미는 셈이 된다.
            box = HITBOX.search(pick(values["hitbox"], label) or "")
            if box:
                width, height = float(box.group(1)), number(pick(values["range"], label))
                geom.pop("range", None)
        if height is None and shape == "square":
            height = width
        if width is None or height is None:
            return None
        geom["width"], geom["height"] = width, height
    elif shape == "triangle":
        side = number(pick(values["width"], label))
        if side is None:
            return None
        geom["side"] = side
    else:
        radius = number(pick(values["radius"], label))
        if radius is None:
            return None
        geom["radius"] = radius
        if shape == "radial":
            arc = number(pick(values["arc"], label))
            if arc is None:
                return None
            geom["arc"] = arc
    return geom


def composite(fields, shape_raw):
    """'- Slam: Circle - Shockwave: Rectangle' 처럼 도형이 둘 이상인 스킬.

    이름표가 도형과 치수를 묶어 준다 - radius 는 '2.5 (slam)', range 는
    '- Slam: 2.5 - Shockwave: 17' 같은 식으로 같은 이름표를 달고 있다.
    """
    listed = LABELLED_LIST.findall(clean(shape_raw))
    if len(listed) < 2:
        return None
    values = {key: labelled(fields.get(key)) for key in
              ("radius", "width", "height", "arc", "hitbox", "range")}

    parts = []
    for label, word in listed:
        shape = SHAPE_WORDS.get(word.strip().split()[0].lower())
        if not shape:
            return None
        part = one_shape(shape, values, label.strip().lower())
        if not part:
            return None
        part["label"] = label.strip()
        parts.append(part)
    return {"shape": "composite", "label": clean(shape_raw), "parts": parts}


# 제이나 서리 고리처럼 한복판이 정말 비어 있는 경우에만 이 문구가 붙는다.
INNER_SAFE = re.compile(r"inner radius are not affected|not affected in any way", re.I)


def two_zones(fields, shape_raw, hollow, description):
    """안팎 반경이 따로 적힌 스킬.

    대개 안과 밖의 효과가 다르다 - 가운데는 기절, 바깥은 끌어당김 하는 식이다.
    그래서 기본은 '안쪽 원 + 바깥 고리' 두 겹으로 그린다. 한복판이 정말 비어서
    아무 일도 없는 경우(제이나 서리 고리)에만 속 빈 고리 하나로 그린다.
    """
    inner, outer = hollow
    arc = number(sized(fields, "arc"))
    distance = cast_range(fields.get("range"))
    text = "%s %s" % (fields.get("notes") or "", description or "")

    def finish(geom):
        if distance is not None:
            geom["range"] = distance
        elif arc is not None or "no target" in (fields.get("target") or "").lower():
            geom["noRange"] = "self"
        return geom

    if INNER_SAFE.search(text):
        geom = {"shape": "ring", "label": shape_raw, "inner": inner, "outer": outer}
        if arc is not None:
            geom["arc"] = arc
        return finish(geom)

    core = {"shape": "circle", "radius": inner, "label": "안쪽"}
    edge = {"shape": "ring", "inner": inner, "outer": outer, "label": "바깥"}
    if arc is not None:
        core = {"shape": "radial", "radius": inner, "arc": arc, "label": "안쪽"}
        edge["arc"] = arc
    return finish({"shape": "composite", "label": shape_raw, "parts": [edge, core]})


def geometry(fields, description=None):
    """범위 표시용 치수를 뽑는다. 그릴 수 없으면 None.

    길이 값은 모두 같은 좌표계(SC2 월드 유닛)라 영웅 반지름과 그대로 겹쳐 그릴 수
    있다. 위키의 unitRadius/range/radius 가 XML 값을 그대로 옮긴 것이기 때문이다.
    """
    shape_raw = clean(fields.get("aoe"))
    if not shape_raw:
        # aoe 표기가 없어도 반경과 각도가 있으면 부채꼴이다 (말티엘 사신의 징표)
        inner, outer = INNER.search(clean(fields.get("radius")) or ""), OUTER.search(clean(fields.get("radius")) or "")
        if inner and outer and number(sized(fields, "arc")) is not None:
            # aoe 표기가 없어도 안팎이 갈리면 같은 규칙을 태운다 (가로쉬 땅의 파괴자)
            return two_zones(fields, "Ring sector",
                             (float(inner.group(1)), float(outer.group(1))), description)
        if number(fields.get("radius")) is not None and number(sized(fields, "arc")) is not None:
            return {"shape": "radial", "label": "Radial (arc)", "shapeNote": "arc",
                    "radius": number(fields.get("radius")),
                    "arc": number(sized(fields, "arc")),
                    "range": number(fields.get("range"))} if fields.get("range") else {
                    "shape": "radial", "label": "Radial (arc)", "shapeNote": "arc",
                    "radius": number(fields.get("radius")),
                    "arc": number(sized(fields, "arc")), "noRange": "self"}
        # 도형 이름은 없고 폭만 적힌 맵 전체 빔 (아나 호루스의 눈의 고성능 탄환).
        # 폭이 있는데 사거리가 Global 이면 직선으로 훑고 지나가는 것뿐이다.
        beam = number(sized(fields, "width"))
        if beam is not None and (fields.get("range") or "").strip().lower() == "global":
            return {"shape": "rectangle", "label": "Beam (global)", "width": beam,
                    "height": 22.0, "openEnded": True, "global": True,
                    "noRange": "self"}
        # 돌진·논타겟처럼 범위 형태는 없고 투사체 판정만 적힌 스킬
        shot = skillshot_geometry(fields, description)
        if shot:
            return shot
        # aoe 표기만 빠졌을 뿐 반경이 적혀 있으면 원으로 그린다. radius 칸이 비었어도
        # prop 짝에 착지 반경·광역 반경이 적혀 있는 경우가 있다 (가로쉬 파쇄추).
        plain, note = damage_radius(fields.get("radius")), "radius"
        if plain is None:
            plain, label = prop_value(fields, PROP_AREA)
            note = label
        if plain is not None:
            geom = {"shape": "circle", "label": "Circle (radius only)",
                    "radius": plain, "shapeNote": note}
            distance = cast_range(fields.get("range"))
            target = (fields.get("target") or "").strip()
            if distance is not None:
                geom["range"] = distance
            elif "no target" in target.lower():
                geom["noRange"] = "self"
            elif not target:
                geom["noRange"] = "inherit"
            else:
                geom["noRange"] = "unstated"
            return geom
        return None

    # 도형이 둘 이상 적힌 스킬은 이름표로 묶어 각각 그린다
    if shape_raw.startswith("-"):
        return composite(fields, shape_raw)

    shape = re.split(r"[ (]", shape_raw)[0].lower()
    # "- Initial: Square - Return: Circle" 처럼 여러 모양이 섞인 것은 그리지 않는다.
    # 아는 모양만 그려야 그림이 거짓말을 하지 않는다.
    if shape not in ("circle", "radial", "rectangle", "square", "ring",
                     "triangle", "equilateral", "trapezoid"):
        return None

    # 안팎 반경이 같이 적혔으면 가운데가 빈 고리다. 바깥 반경만 그리면 안 맞는
    # 한복판까지 맞는 것처럼 보인다 (켈투자드 얼음 회오리, 태사다르 블랙홀 등).
    hollow = None
    if shape in ("circle", "radial"):
        text = clean(fields.get("radius"))
        inner, outer = INNER.search(text), OUTER.search(text)
        if inner and outer and float(inner.group(1)) > 0:
            hollow = (float(inner.group(1)), float(outer.group(1)))

    # 위키가 Circle 이라 적었어도 각도가 붙어 있으면 부채꼴이다. 각도는 원에 쓸 수
    # 없는 값이라 표기 쪽이 틀린 것 (알렉스트라자 폭풍 날개, 요한나 눈부신 방패).
    corrected = False
    if shape == "circle" and number(sized(fields, "arc")) is not None:
        shape, corrected = "radial", True

    if hollow:
        return two_zones(fields, shape_raw, hollow, description)

    geom = {"shape": shape, "label": shape_raw}
    if corrected:
        geom["shapeNote"] = "arc"
    if shape == "circle":
        # 일렬로 연달아 떨어지는 것은 원형뿐이다. 부채꼴 다발은 배치가 제각각이라
        # 함부로 그리지 않는다.
        repeat = repeat_of(fields, shape_raw, description)
        if repeat:
            geom["repeat"] = repeat
    distance = cast_range(fields.get("range"))
    target = (fields.get("target") or "").strip()
    if distance is not None:
        geom["range"] = distance
    elif (fields.get("range") or "").strip().lower() == "global":
        geom["global"] = True
    else:
        # 사거리가 비는 데는 이유가 세 가지뿐이다. 숫자를 지어내지 말고 어느 쪽인지
        # 밝힌다. (게임 XML 을 뒤져 봐도 대부분 '제한 없음' 센티넬 500 만 나온다)
        if shape in ("radial",) or "no target" in target.lower():
            # 부채꼴은 꼭짓점이 시전자에 붙어 있어 정의상 자기 중심이다.
            # 위키가 "Point target" 이라 적어도 그건 조준 방식을 말한 것뿐이다.
            geom["noRange"] = "self"
        elif not target:
            geom["noRange"] = "inherit"    # 부모 스킬의 사거리를 따르는 특성
        else:
            geom["noRange"] = "unstated"   # 위키가 적어두지 않았다

    radius_text = fields.get("radius") or ""
    if shape == "ring":
        inner, outer = INNER.search(radius_text), OUTER.search(radius_text)
        if not (inner and outer):
            return None
        geom["inner"], geom["outer"] = float(inner.group(1)), float(outer.group(1))
    elif shape == "trapezoid":
        # 앞으로 갈수록 넓어지거나 좁아지는 부채꼴 비슷한 사각형 (D.Va 방어 매트릭스)
        widths = labelled(sized(fields, "width"))
        inner = number(widths.get("inner")), number(widths.get("outer"))
        if None in inner:
            return None
        geom["inner"], geom["outer"] = inner
        geom["height"] = number(sized(fields, "height"))
        if geom["height"] is None:
            return None
    elif shape in ("triangle", "equilateral"):
        # 데커드 봉인의 두루마리. width 가 한 변의 길이다.
        side = number(sized(fields, "width"))
        if side is None:
            return None
        geom["side"] = side
    elif shape in ("rectangle", "square"):
        width = number(sized(fields, "width"))
        # 정사각형은 높이를 따로 적지 않는다 (데커드 호라드림의 함: width 8.0 뿐)
        height = number(sized(fields, "height"))
        if height is None and shape == "square":
            height = width
        elif height is None and shape == "rectangle" and not geom.get("global"):
            # 시전자와 대상 사이를 잇는 스킬은 사거리가 곧 길이다 (알라라크 번개 쇄도)
            height = number(fields.get("range"))
            geom.pop("range", None)
        if width is None:
            return None
        if height is None and geom.get("global"):
            # 조준한 곳까지 뻗는 빔. 끝이 없으니 보기 좋은 길이로 그리고
            # 끝을 열어 둔다 (아나 호루스의 눈, 피닉스 행성 분열기).
            height, geom["openEnded"] = 22.0, True
        if height is None:
            return None
        geom["width"], geom["height"] = width, height
        # 안팎으로 효과가 갈리는 직사각형. 위키가 prop 짝에 폭을 따로 적어 둔다
        # (오르페아 압도의 아귀: 끌어당김 10 / 피해 4.0, 길이는 공용 4.0)
        zones = rect_zones(fields, height)
        if zones:
            geom.pop("width"); geom.pop("height")
            geom["parts"] = zones
    else:
        radius = damage_number(radius_text)
        if radius is None:
            return None
        geom["radius"] = radius
        if shape == "radial":
            arc = number(sized(fields, "arc"))
            if arc is None:
                return None
            geom["arc"] = arc
    return geom


def load_overrides():
    """손으로 관리하는 범위 그림. 위키에서 뽑은 것 위에 덮어쓴다."""
    if not os.path.isfile(AOE_OVERRIDES):
        return {}
    data = json.load(open(AOE_OVERRIDES, encoding="utf-8"))
    skip = {k: None for k in (data.get("_skip") or {}) if not k.startswith("_")}
    manual = {k: v for k, v in data.items() if not k.startswith("_")}
    manual.update(skip)          # 값이 None 이면 그리지 않는다
    return manual


def main():
    rows, alias = {}, {}
    overrides = load_overrides()
    used = set()
    heroes = 0
    ids = hyperlink_ids()
    targets = talent_targets()          # 특성 -> 그 특성이 손보는 스킬
    names = {}                          # buttonId -> (한글 이름, 영문 이름)
    unresolved = []
    for filename in sorted(os.listdir(SRC)):
        if not filename.endswith(".json"):
            continue
        data = json.load(open(os.path.join(SRC, filename), encoding="utf-8"))
        heroes += 1
        wiki_name = data["hero"].replace("_", " ").replace(".", " ")
        hero_id = ids.get(normalize(wiki_name))
        if not hero_id:
            hero_id = data.get("hero_id") or data["hero"]
            unresolved.append(data["hero"])
        for entry in data["abilities"] + data["talents"]:
            key = entry["_match"].get("key")
            if not key:
                continue
            button_id = key.split("/", 2)[2]
            en, ko, note_en, note_ko = rows_of(entry)
            if not (en or note_en):
                continue
            fields = entry.get("fields") or {}
            geom = geometry(fields, entry.get("description"))
            # 시전자가 대상을 고르는 범위. 피해 범위와 기준점이 달라 따로 얹는다.
            search, _ = prop_value(fields, PROP_SEARCH)
            if search is not None and geom is not None:
                geom["search"] = search
            bounce = bounce_reach(fields)
            if bounce is not None:
                # 피해 범위와 기준점이 달라 도형에 섞지 않고 따로 얹는다. 범위 도형이
                # 아예 없는 스킬(스랄 연쇄 번개)은 튕김 거리만 그린다.
                if geom is None:
                    geom = {"shape": "bounce", "label": "Bounce reach"}
                    distance = cast_range(fields.get("range"))
                    if distance is not None:
                        geom["range"] = distance
                    else:
                        # 평타나 다른 스킬이 맞은 자리에서부터 튄다 (트레이서 도탄 등)
                        geom["noRange"] = "inherit"
                elif geom.get("radius") == bounce:
                    bounce = None           # 같은 값을 두 겹으로 그릴 이유가 없다
                if bounce is not None:
                    geom["bounce"] = bounce
            if geom:
                geom["src"] = "auto"

            # 대상 스킬의 범위를 늘려 주는 특성. 늘어난 뒤의 값을 하단 표에 적고,
            # 그릴 수 있으면 그 특성 카드에도 늘어난 범위를 그려 준다.
            target = targets.get(button_id)
            if target and target in rows:
                add_size = bonus_of(fields, BONUS_RADIUS)
                add_range = bonus_of(fields, BONUS_RANGE)
                if add_size is not None or add_range is not None:
                    grown, changes = apply_bonus(
                        rows[target]["geom"], add_size, add_range)
                    ability_ko, ability_en = names.get(target, (target, target))
                    row_en, row_ko = upgrade_rows(
                        ability_ko, ability_en, changes, add_size, add_range)
                    en.append(row_en)
                    ko.append(row_ko)
                    if grown is not None and geom is None:
                        # 늘기 전 수치를 함께 실어야 그림에 화살표로 표시할 수 있다
                        geom = dict(grown, src="upgrade", upgradeOf=ability_en,
                                    upgradeOfKo=ability_ko,
                                    grew=[{"field": f, "from": a, "to": b}
                                          for f, a, b in changes])

            if button_id in overrides:
                pinned = overrides[button_id]
                geom = dict(pinned, src="manual") if pinned else None
                used.add(button_id)
            names[button_id] = (entry.get("name_kr") or entry["name"], entry["name"])
            rows.setdefault(button_id, {
                "geom": geom,
                "en": en,
                "ko": ko,
                "noteEn": note_en,
                "noteKo": note_ko,
                "descEn": entry.get("description"),
                "descKo": entry.get("description_kr"),
            })
            alias.setdefault("%s|%s" % (hero_id, normalize(entry["name"])), button_id)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"rows": rows, "alias": alias}, fh, ensure_ascii=False,
                  separators=(",", ":"))
    shapes = collections.Counter(
        r["geom"].get("shape", "composite") for r in rows.values() if r["geom"])
    manual = sum(1 for r in rows.values() if (r["geom"] or {}).get("src") == "manual")
    print("영웅 %d명 / 항목 %d개 / 별칭 %d개" % (heroes, len(rows), len(alias)))
    print("  범위 도형 %d개 (자동 %d / 수동 %d): %s"
          % (sum(shapes.values()), sum(shapes.values()) - manual, manual,
             ", ".join("%s %d" % kv for kv in shapes.most_common())))
    missing = set(overrides) - used
    if missing:
        print("  [경고] 붙일 곳을 못 찾은 수동 항목: %s" % ", ".join(sorted(missing)))
    if unresolved:
        print("hyperlinkId 를 못 찾은 영웅: %s" % ", ".join(unresolved))
    print("%.1f MB -> %s" % (os.path.getsize(OUT) / 1048576, OUT))


if __name__ == "__main__":
    main()
