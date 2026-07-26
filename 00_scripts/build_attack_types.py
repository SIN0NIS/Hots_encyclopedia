"""영웅 기본 공격의 유형을 게임 XML 에서 뽑는다.

백과사전 데이터에는 무기의 사거리·주기·피해량만 있고 "어떻게 때리는가"가 없다.
그 정보는 XML 무기 정의와 이펙트 체인에만 있다.

  근접/원거리   <Options index="Melee"> — 무기 정의에 그대로 있다
  즉발/투사체   이펙트 체인에 CEffectLaunchMissile 이 있으면 날아가는 투사체
  광역          기본 평타에 광역은 없다. 전부 특성으로 붙는다.
                (DisplayEffect 에 AreaArray 를 가진 무기는 90명 중 0명)
                대신 "특성으로 광역이 붙을 수 있는 평타"를 따로 표시한다.

출력: hots_kr/attack_types.json
  { "heroes": { <hyperlinkId>: [ {nameId, melee, missile, talentSplash} ] },
    "references": [ {key, nameId, ko, en, range} ] }   범위 그림용 기준자
"""
import collections
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 파이프라인이 만드는 hots_analysis 를 먼저 본다. hots_xml 은 예전 방식으로
# 한 폴더에 펼쳐 둔 경우를 위한 대비책이다.
XML_SOURCES = paths.XML_SOURCES
ENCYCLOPEDIA = paths.ENCYCLOPEDIA
OUT = paths.ATTACK_TYPES

# 이펙트끼리 이어지는 참조 속성. 이 밖의 value 는 검증기·행동 등 다른 것을 가리킨다.
LINK = {"EffectArray", "Effect", "ImpactEffect", "PeriodicEffect", "FinalEffect"}
MAX_DEPTH = 5


def load_catalog():
    catalog = collections.defaultdict(list)
    files = 0
    for pattern in XML_SOURCES:
        for path in sorted(glob.glob(pattern)):
            try:
                root = ET.parse(path).getroot()
            except ET.ParseError:
                continue
            files += 1
            for element in root:
                if element.get("id"):
                    catalog[element.get("id")].append(element)
    if not files:
        raise SystemExit("게임 XML 을 찾지 못했습니다. analysis 단계를 먼저 돌리세요.\n  "
                         + "\n  ".join(XML_SOURCES))
    print("  XML %d개 / 정의 %d개" % (files, len(catalog)))
    return catalog


def chain(catalog, effect_id, seen=None, depth=0):
    """이펙트 체인을 훑어 거쳐가는 id 를 모은다."""
    seen = seen if seen is not None else set()
    if not effect_id or effect_id in seen or depth > MAX_DEPTH:
        return seen
    seen.add(effect_id)
    for element in catalog.get(effect_id, []):
        for child in element:
            if child.tag in LINK and child.get("value") in catalog:
                chain(catalog, child.get("value"), seen, depth + 1)
    return seen


def classify(catalog, weapon_id):
    weapon = next((e for e in catalog.get(weapon_id, [])
                   if e.tag.startswith("CWeapon")), None)
    if weapon is None:
        return None
    melee = any(c.tag == "Options" and c.get("index") == "Melee"
                and c.get("value") == "1" for c in weapon)
    effect = next((c.get("value") for c in weapon if c.tag == "Effect"), None)
    reached = chain(catalog, effect)

    missile = splash = False
    for node in reached:
        for element in catalog.get(node, []):
            if element.tag == "CEffectLaunchMissile":
                missile = True
            if element.tag == "CEffectEnumArea" or any(c.tag == "AreaArray"
                                                       for c in element):
                splash = True
    return {"nameId": weapon_id, "melee": melee, "missile": missile,
            "talentSplash": splash}


# 범위 그림에서 크기를 가늠할 기준자. 사람들이 몸으로 아는 두 사거리를 쓴다.
# 값을 박아두지 않고 XML 에서 뽑아 패치로 바뀌어도 따라가게 한다.
def references():
    """어느 무기를 크기 자로 쓸지는 settings.json 이 정한다."""
    gauges = (paths.settings().get("aoeGauges") or {}).get("weapons") or []
    return [g for g in gauges if not str(g.get("key", "")).startswith("_")]


def reference_ranges(catalog):
    """기준 사거리를 무기 정의에서 읽는다. 작은 것부터 정렬해 둔다."""
    out = []
    for ref in references():
        weapon = next((e for e in catalog.get(ref["nameId"], [])
                       if e.tag.startswith("CWeapon")), None)
        if weapon is None:
            print("  [경고] 기준 무기를 찾지 못했습니다: %s" % ref["nameId"])
            continue
        value = next((c.get("value") for c in weapon if c.tag == "Range"), None)
        if value:
            out.append(dict(ref, range=float(value)))
    return sorted(out, key=lambda r: r["range"])


def hero_weapons():
    with open(ENCYCLOPEDIA, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("const dataEN = "):
                data = json.loads(line[len("const dataEN = "):].strip().rstrip(";"))
                return {h["hyperlinkId"]: [w["nameId"] for w in (h.get("weapons") or [])]
                        for h in data.values()}
    return {}


def attack_aoe():
    """기본 공격 자체가 광역인 영웅. 손으로 관리한다 (aoe_overrides.json)."""
    if not os.path.isfile(paths.AOE_OVERRIDES):
        return {}
    data = json.load(open(paths.AOE_OVERRIDES, encoding="utf-8"))
    return {k: v for k, v in (data.get("_attackAoe") or {}).items()
            if not k.startswith("_")}


def vector_targeting(catalog):
    """마우스를 끌어서 방향을 정하는 스킬. buttonId -> 끌 수 있는 범위.

    게임 데이터에서 <VectorRange x,y> 를 단 능력이 곧 드래그 조준이다. 보통
    스킬은 클릭 한 번으로 지점만 정하는데, 이쪽은 시작점에서 끌어 방향과 길이를
    잡는다 (알라라크 염동력, 데커드 로라나도).

    참고로 아나 호루스의 눈·피닉스 행성 분열기는 여기 없다. 그쪽은
    TargetAcrossMapPlane 으로 맵 어디든 한 점을 찍는 방식이라 끌지 않는다.
    """
    out = {}
    for ability_id, elements in catalog.items():
        for element in elements:
            if not element.tag.startswith("CAbil"):
                continue
            found = element.find("VectorRange")
            if found is None or not found.get("value"):
                continue
            reach = [float(n) for n in found.get("value").split(",") if n.strip()]
            if reach:
                out[ability_id] = max(reach)
    return out


def main():
    catalog = load_catalog()
    result, tally = {}, collections.Counter()
    for hero_id, weapon_ids in hero_weapons().items():
        entries = [classify(catalog, wid) for wid in weapon_ids]
        entries = [e for e in entries if e]
        if entries:
            result[hero_id] = entries
        for entry in entries:
            tally["근접" if entry["melee"] else "원거리"] += 1
            tally["투사체" if entry["missile"] else "즉발"] += 1
            if entry["talentSplash"]:
                tally["특성 광역 가능"] += 1

    references = reference_ranges(catalog)
    drag = vector_targeting(catalog)
    splash = attack_aoe()
    unknown = set(splash) - set(result)
    if unknown:
        print("  [경고] 모르는 영웅의 평타 광역 설정: %s" % ", ".join(sorted(unknown)))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"heroes": result, "references": references, "attackAoe": splash,
                   "drag": drag},
                  fh, ensure_ascii=False, separators=(",", ":"))
    print("영웅 %d명 / 무기 %d개" % (len(result), sum(len(v) for v in result.values())))
    print("  기준 사거리: " + ", ".join("%s %.1f" % (r["ko"], r["range"]) for r in references))
    if splash:
        print("  평타 광역(수동): " + ", ".join(sorted(splash)))
    print("  드래그 조준 %d개: %s" % (len(drag), ", ".join(sorted(drag))))
    print("  " + "  ".join("%s %d" % kv for kv in tally.most_common()))
    print("-> %s" % OUT)


if __name__ == "__main__":
    main()
