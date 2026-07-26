# -*- coding: utf-8 -*-
"""
hots_hero_parser.py — 히오스 영웅 프로필 추출기
hots_analysis 폴더(XML)와 all_heroes.json(위키)을 결합해 영웅별 통합 프로필 JSON 생성.

사용법:
    python hots_hero_parser.py <hots_analysis 경로> <all_heroes.json 경로> <출력 폴더>

출력:
    out/heroes/<영웅>.json   영웅별 통합 프로필
    out/summary_stats.csv    전 영웅 기본 스탯 비교표
    out/talent_links.csv     특성-능력 부모자식 매핑 전표
"""
import sys, os, re, json, csv, glob
import xml.etree.ElementTree as ET
from collections import defaultdict

# ---------------------------------------------------------------- 상수

TIER_TO_LEVEL = {1: 1, 2: 4, 3: 7, 4: 10, 5: 13, 6: 16, 7: 20}

# 폴더명 -> (위키 영어명 목록)  * 초갈은 Cho/Gall 두 영웅
FOLDER_TO_WIKI = {
    "abathur": ["Abathur"], "anubarak": ["Anub'arak"], "artanis": ["Artanis"],
    "arthas": ["Arthas"], "azmodan": ["Azmodan"], "barbarian": ["Sonya"],
    "brightwing": ["Brightwing"], "butcher": ["The Butcher"], "chen": ["Chen"],
    "crusader": ["Johanna"], "demonhunter": ["Valla"], "diablo": ["Diablo"],
    "dryad": ["Lunara"], "falstad": ["Falstad"], "genn": ["Greymane"],
    "illidan": ["Illidan"], "jaina": ["Jaina"], "kaelthas": ["Kael'thas"],
    "kerrigan": ["Kerrigan"], "l90etc": ["E.T.C."], "leoric": ["Leoric"],
    "lili": ["Li Li"], "lostvikings": ["The Lost Vikings"], "malfurion": ["Malfurion"],
    "medic": ["Lt. Morales"], "monk": ["Kharazim"], "muradin": ["Muradin"],
    "murky": ["Murky"], "necromancer": ["Xul"], "nova": ["Nova"],
    "raynor": ["Raynor"], "rehgar": ["Rehgar"], "rexxar": ["Rexxar"],
    "sgthammer": ["Sgt. Hammer"], "stitches": ["Stitches"], "sylvanas": ["Sylvanas"],
    "tassadar": ["Tassadar"], "thrall": ["Thrall"], "tinker": ["Gazlowe"],
    "tychus": ["Tychus"], "tyrael": ["Tyrael"], "tyrande": ["Tyrande"],
    "uther": ["Uther"], "witchdoctor": ["Nazeebo"], "wizard": ["Li-Ming"],
    "zagara": ["Zagara"], "zeratul": ["Zeratul"],
    "alarak": ["Alarak"], "alexstrasza": ["Alexstrasza"], "amazon": ["Cassia"],
    "ana": ["Ana"], "anduin": ["Anduin"], "auriel": ["Auriel"],
    "chogall": ["Cho", "Gall"], "chromie": ["Chromie"], "deathwing": ["Deathwing"],
    "deckard": ["Deckard"], "dehaka": ["Dehaka"], "dva": ["D.Va"],
    "fenix": ["Fenix"], "firebat": ["Blaze"], "garrosh": ["Garrosh"],
    "genji": ["Genji"], "guldan": ["Gul'dan"], "hanzo": ["Hanzo"],
    "hogger": ["Hogger"], "imperius": ["Imperius"], "junkrat": ["Junkrat"],
    "kelthuzad": ["Kel'Thuzad"], "lucio": ["Lúcio"], "maiev": ["Maiev"],
    "malganis": ["Mal'Ganis"], "malthael": ["Malthael"], "medivh": ["Medivh"],
    "meiow": ["Mei"], "mephisto": ["Mephisto"], "nexushunter": ["Qhira"],
    "orphea": ["Orphea"], "probius": ["Probius"], "samuro": ["Samuro"],
    "stukov": ["Stukov"], "thefirelords": ["Ragnaros"], "tracer": ["Tracer"],
    "valeera": ["Valeera"], "varian": ["Varian"], "whitemane": ["Whitemane"],
    "yrel": ["Yrel"], "zarya": ["Zarya"], "zuljin": ["Zul'jin"],
}

# 엔진 기본값 (core.stormmod 원본이 널 파일이라 알려진 값으로 보충)
ENGINE_DEFAULTS = {"Speed": 4.3984, "SightRadius": 12.0,
                   "EnergyMax": 500.0, "EnergyRegenRate": 3.0}

EFFECT_TAGS = ("CEffect",)  # 접두
ABIL_TAG_PREFIX = "CAbil"

# ---------------------------------------------------------------- 카탈로그

class Catalog:
    """여러 XML 파일을 하나의 (태그,id) 인덱스로 병합. parent 상속 해석 포함."""

    def __init__(self):
        self.index = defaultdict(list)          # (tag, id) -> [element,...]
        self.by_id = defaultdict(list)          # id -> [(tag, element),...]
        self.defaults = defaultdict(list)       # tag -> [default element,...]

    def load_file(self, path):
        raw = open(path, "rb").read()
        if raw.strip(b"\x00") == b"":            # 추출 실패한 널 파일 스킵
            return False
        for enc in ("utf-8-sig", "utf-8", "utf-16"):
            try:
                root = ET.fromstring(raw.decode(enc))
                break
            except Exception:
                continue
        else:
            return False
        for el in root:
            eid = el.get("id")
            if eid:
                self.index[(el.tag, eid)].append(el)
                self.by_id[eid].append((el.tag, el))
            if el.get("default") == "1":
                self.defaults[el.tag].append(el)
        return True

    # ---- 조회 ----
    def elems(self, tag, eid):
        return self.index.get((tag, eid), [])

    def find_any(self, eid, tag_prefix=None):
        """id로 검색, 태그 접두 필터. (tag, element) 목록."""
        out = []
        for tag, el in self.by_id.get(eid, []):
            if tag_prefix is None or tag.startswith(tag_prefix):
                out.append((tag, el))
        return out

    def _iter_chain(self, tag, eid, _seen=None):
        """자기 정의들 -> parent 체인 -> 클래스 default 순서로 요소 나열."""
        if _seen is None:
            _seen = set()
        if (tag, eid) in _seen:
            return
        _seen.add((tag, eid))
        els = self.elems(tag, eid)
        for el in els:
            yield el
        for el in els:
            par = el.get("parent")
            if par:
                yield from self._iter_chain(tag, par, _seen)
        if eid is not None:
            for el in self.defaults.get(tag, []):
                yield el

    def get_value(self, tag, eid, path, attr="value"):
        """상속 체인을 따라 path의 attr 값을 찾음."""
        for el in self._iter_chain(tag, eid):
            node = el.find(path)
            if node is not None and node.get(attr) is not None:
                return node.get(attr)
        return None

    def get_float(self, tag, eid, path, attr="value"):
        v = self.get_value(tag, eid, path, attr)
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    def collect(self, tag, eid, path):
        """상속 체인 전체에서 path에 해당하는 요소를 모두 수집(자식 우선)."""
        out = []
        for el in self._iter_chain(tag, eid):
            out.extend(el.findall(path))
        return out

# ---------------------------------------------------------------- 문자열

class Strings:
    def __init__(self):
        self.map = {}

    def load(self, path):
        try:
            txt = open(path, "rb").read().decode("utf-8-sig", errors="replace")
        except OSError:
            return
        for line in txt.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                self.map.setdefault(k, v)

    _tag_re = re.compile(r"<[^>]+>")

    def get(self, key, clean=True):
        v = self.map.get(key)
        if v and clean:
            v = self._tag_re.sub("", v).strip()
        return v

    def name_of_button(self, face):
        return self.get(f"Button/Name/{face}")

    def simple_of_button(self, face):
        return self.get(f"Button/SimpleDisplayText/{face}")

# ---------------------------------------------------------------- 효과 트리 분류

# 자식 효과를 가리킬 수 있는 위치들 (요소 탐색 경로, 속성)
CHILD_EFFECT_PATHS = [
    "EffectArray", "Effect", "ImpactEffect", "FinalEffect", "PeriodicEffectArray",
    "ExpireEffect", "InitialEffect", "LaunchEffect", "CaseArray", "CaseDefault",
    "SpawnEffect", "TeleportEffect", "AreaArray",
]

CC_FLAG_HINTS = {
    "Stunned": "Stun", "Silenced": "Silence", "Rooted": "Root",
    "Sleep": "Sleep", "Timescale": "Slow(time)", "Blind": "Blind",
    "Dazed": "Daze", "Suppress": "Suppress",
}

def _num(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d

class EffectWalker:
    """효과 트리를 재귀 순회하며 type.dat 스타일 태그·수치를 수집."""

    def __init__(self, cat: Catalog, scaling_map):
        self.cat = cat
        self.scaling = scaling_map  # (catalog,entry,field)->scale

    def walk(self, effect_id, depth=0, seen=None, out=None):
        if out is None:
            out = {"tags": set(), "damage": [], "heal": [], "cc": [],
                   "shield": [], "summon": [], "aoe": [], "notes": []}
        if seen is None:
            seen = set()
        if not effect_id or effect_id in seen or depth > 12:
            return out
        seen.add(effect_id)

        for tag, el in self.cat.find_any(effect_id, "CEffect"):
            self._classify(tag, el, effect_id, out)
            # 부모 효과의 자식 체인도 상속되므로 함께 순회
            par = el.get("parent")
            if par:
                self.walk(par, depth + 1, seen, out)
            # 자식 효과 재귀
            for path in CHILD_EFFECT_PATHS:
                for node in el.findall(path):
                    ref = node.get("value") or node.get("Effect")
                    if ref:
                        self.walk(ref, depth + 1, seen, out)
                    # AreaArray는 자체 속성으로도 참조
                    if node.tag == "AreaArray":
                        r = _num(node.get("Radius"))
                        if r:
                            out["aoe"].append({"from": effect_id, "radius": r,
                                               "arc": _num(node.get("Arc"))})
                        eref = node.get("Effect")
                        if eref:
                            self.walk(eref, depth + 1, seen, out)
            # ApplyBehavior -> 버프 분석
            for node in el.findall("Behavior"):
                self._behavior(node.get("value"), effect_id, out)
        return out

    def _scale_of(self, catalog, entry, field):
        return self.scaling.get((catalog, entry, field))

    def _classify(self, tag, el, eid, out):
        if tag == "CEffectDamage":
            amt = el.find("Amount")
            kind = (el.find("Kind").get("value") if el.find("Kind") is not None else "")
            val = _num(amt.get("value")) if amt is not None else None
            if val is None:
                val = self.cat.get_float(tag, eid, "Amount")
            if val is None:
                return  # 수치 없는 템플릿 효과는 기록 생략
            is_spell = kind not in ("Melee", "Ranged", "Basic")
            out["tags"].add("Spell Damage" if is_spell else "Physical Damage")
            out["damage"].append({
                "effect": eid, "amount": val, "kind": kind or "Ability",
                "scaling": self._scale_of("Effect", eid, "Amount"),
            })
        elif tag in ("CEffectModifyVital", "CEffectVitals"):
            for vit in el.findall("Vital"):
                idx, chg = vit.get("index"), _num(vit.get("Change"))
                if chg is None:
                    ch = vit.find("Change")
                    chg = _num(ch.get("value")) if ch is not None else None
                if idx == "Life" and chg:
                    if chg > 0:
                        out["tags"].add("Healing")
                        out["heal"].append({"effect": eid, "amount": chg,
                                            "scaling": self._scale_of("Effect", eid, "Change")})
                    else:
                        out["tags"].add("Self-damage")
                elif idx == "Energy" and chg and chg > 0:
                    out["tags"].add("Mana restoration")
                elif idx == "Shields" and chg and chg > 0:
                    out["tags"].add("Shield")
        elif tag == "CEffectHeal" or tag == "CEffectHealVital":
            amt = el.find("Amount")
            val = _num(amt.get("value")) if amt is not None else None
            if val is None:
                val = self.cat.get_float(tag, eid, "Amount")
            out["tags"].add("Healing")
            out["heal"].append({"effect": eid, "amount": val,
                                "scaling": self._scale_of("Effect", eid, "Amount")})
        elif tag == "CEffectCreateUnit":
            u = el.find("SpawnUnit")
            out["tags"].add("Summon")
            out["summon"].append(u.get("value") if u is not None else "?")
        elif tag == "CEffectTeleport":
            out["tags"].add("Movement: Teleport")
        elif tag in ("CEffectForceMove", "CEffectApplyForce"):
            out["tags"].add("Crowd control")
            out["cc"].append({"effect": eid, "type": "Knockback"})
        elif tag == "CEffectCreateHealer":
            rate = _num(el.find("RechargeVitalRate").get("value")) \
                if el.find("RechargeVitalRate") is not None else None
            if rate is None:
                rate = self.cat.get_float(tag, eid, "RechargeVitalRate")
            out["tags"].add("Healing")
            out["heal"].append({"effect": eid, "per_second": rate,
                                "scaling": self._scale_of("Effect", eid, "RechargeVitalRate")})
        elif tag == "CEffectLaunchMissile":
            out["tags"].add("Skillshot/Missile")
        elif tag == "CEffectEnumArea":
            for aa in el.findall("AreaArray"):
                r = _num(aa.get("Radius"))
                if r:
                    out["aoe"].append({"from": eid, "radius": r, "arc": _num(aa.get("Arc"))})

    PARENT_CC = {"stormstun": "Stun", "stormsilence": "Silence",
                 "stormroot": "Root", "stormpolymorph": "Polymorph",
                 "stormsleep": "Sleep", "stormtimestop": "Time Stop",
                 "stormblind": "Blind", "stormtaunted": "Taunt",
                 "stormmindcontrol": "Mind Control", "stormfeared": "Fear"}

    def _behavior(self, beh_id, src, out):
        if not beh_id:
            return
        # 부모 체인 이름으로 CC 판정 (StormStun/StormSilence 등 공용 부모)
        chain = [beh_id]
        cur, guard = beh_id, 0
        while cur and guard < 8:
            par = None
            for _t, _e in self.cat.find_any(cur, "CBehavior"):
                par = _e.get("parent") or par
            if not par or par in chain:
                break
            chain.append(par); cur = par; guard += 1
        for cid in chain:
            key = cid.lower()
            for pname, cctype in self.PARENT_CC.items():
                if key == pname:
                    dur = self.cat.get_float("CBehaviorBuff", beh_id, "Duration")
                    out["tags"].add("Crowd control")
                    out["cc"].append({"behavior": beh_id, "type": cctype,
                                      "duration": dur})
                    return
        for tag, el in self.cat.find_any(beh_id, "CBehavior"):
            if tag != "CBehaviorBuff":
                continue
            mod = el.find("Modification")
            if mod is None:
                out["tags"].add("Status effect")
                continue
            classified = False
            # 이동속도 변화
            ms = mod.find("MoveSpeedMultiplier")
            if ms is not None:
                v = _num(ms.get("value"))
                if v is not None and v < 1:
                    out["tags"].add("Crowd control")
                    out["cc"].append({"behavior": beh_id, "type": "Slow",
                                      "value": round((1 - v) * 100)})
                    classified = True
                elif v is not None and v > 1:
                    out["tags"].add("Status effect")
                    classified = True
            # 상태 플래그 (기절/침묵/속박 등)
            for mf in mod.findall("ModifyFlags") + mod.findall("StateFlags"):
                idx = mf.get("index")
                if idx in CC_FLAG_HINTS and mf.get("value") == "1":
                    out["tags"].add("Crowd control")
                    out["cc"].append({"behavior": beh_id, "type": CC_FLAG_HINTS[idx]})
                    classified = True
            # 보호막
            for vm in mod.findall("VitalMaxArray"):
                if vm.get("index") == "Shields" and _num(vm.get("value")):
                    out["tags"].add("Shield")
                    out["shield"].append({"behavior": beh_id,
                                          "amount": _num(vm.get("value"))})
                    classified = True
            # 방어력(받는 피해 감소/증가)
            dr = mod.find("DamageResponse")
            if dr is not None:
                mfrac = dr.find("ModifyFraction")
                v = _num(mfrac.get("value")) if mfrac is not None else None
                if v is not None:
                    out["tags"].add("Defensive damage modifier" if v < 1
                                    else "Status effect")
                    classified = True
            # 주는 피해 증가
            for dd in mod.findall("DamageDealtFraction") + mod.findall("DamageDealtScaled"):
                out["tags"].add("Offensive damage modifier")
                classified = True
            if not classified:
                out["tags"].add("Status effect")

# ---------------------------------------------------------------- 영웅 추출

def load_scaling_map(cat: Catalog, hero_el):
    m = {}
    for arr in hero_el.findall("LevelScalingArray"):
        for mod in arr.findall("Modifications"):
            g = lambda t: (mod.find(t).get("value") if mod.find(t) is not None else None)
            key = (g("Catalog"), g("Entry"), g("Field"))
            val = _num(g("Value"))
            if all(key) and val is not None:
                # Field가 'Amount[0]' 같은 배열 표기면 기본 필드명도 함께 등록
                m[key] = val
                base_field = key[2].split("[")[0]
                m.setdefault((key[0], key[1], base_field), val)
    return m


def extract_weapon(cat, unit_id, scaling):
    out = []
    for w in cat.collect("CUnit", unit_id, "WeaponArray"):
        link = w.get("Link")
        if not link:
            continue
        rng = cat.get_float("CWeaponLegacy", link, "Range")
        period = cat.get_float("CWeaponLegacy", link, "Period")
        disp = cat.get_value("CWeaponLegacy", link, "DisplayEffect")
        dmg = scale = None
        if disp:
            dmg = cat.get_float("CEffectDamage", disp, "Amount")
            scale = scaling.get(("Effect", disp, "Amount"))
        out.append({"weapon": link, "range": rng, "period": period,
                    "damage": dmg, "scaling_per_level": scale,
                    "dps": round(dmg / period, 1) if dmg and period else None})
    # 중복 제거(상속으로 같은 무기 두 번 등장 가능)
    seen, uniq = set(), []
    for w in out:
        if w["weapon"] not in seen:
            seen.add(w["weapon"]); uniq.append(w)
    return uniq


def extract_unit_stats(cat: Catalog, strings: Strings, unit_id, scaling):
    g = lambda p: cat.get_float("CUnit", unit_id, p)
    stats = {
        "unit_id": unit_id,
        "life_max": g("LifeMax"),
        "life_regen": g("LifeRegenRate"),
        "life_scaling_per_level": scaling.get(("Unit", unit_id, "LifeMax")),
        "shield_max": g("ShieldsMax"),
        "energy_max": g("EnergyMax"),
        "energy_regen": g("EnergyRegenRate"),
        "speed": g("Speed"),
        "radius_collision": g("Radius"),
        "radius_inner": g("InnerRadius"),
        "sight": g("SightRadius"),
    }
    # 자원 이름 (기본: 마나) - CActorUnit(같은 id/unitName)에 정의됨
    vn = (cat.get_value("CActorUnit", unit_id, "VitalNames[@index='Energy']")
          or cat.get_value("CUnit", unit_id, "VitalNames[@index='Energy']"))
    if vn is None:
        for _tag, _el in cat.by_id.get(unit_id, []):
            node = _el.find("VitalNames[@index='Energy']")
            if node is not None:
                vn = node.get("value"); break
    res_key = (vn or "UI/HeroEnergyType/Mana").rsplit("/", 1)[-1]
    stats["resource_type"] = res_key
    stats["resource_name_ko"] = strings.get(f"UI/HeroEnergyType/{res_key}") or res_key
    # 엔진 기본값 보충
    filled = []
    for field, dflt in (("speed", "Speed"), ("sight", "SightRadius"),
                        ("energy_max", "EnergyMax"), ("energy_regen", "EnergyRegenRate")):
        if stats[field] is None:
            stats[field] = ENGINE_DEFAULTS[dflt]
            filled.append(field)
    stats["engine_default_filled"] = filled
    if stats["energy_max"] == 0:
        stats["resource_type"] = "None"
        stats["resource_name_ko"] = "-"
    return stats


def extract_ability(cat, strings, walker, abil_id, button, flags):
    info = {"id": abil_id, "button": button, "flags": flags,
            "name_ko": strings.name_of_button(button) or strings.get(f"Abil/Name/{abil_id}"),
            "summary_ko": strings.simple_of_button(button)}
    if not abil_id:
        return info
    found = cat.find_any(abil_id, ABIL_TAG_PREFIX)
    if not found:
        return info
    tag, el = found[0]
    info["abil_class"] = tag
    # 비용/쿨다운 (상속 체인 고려)
    for cost in cat.collect(tag, abil_id, "Cost"):
        v = cost.find("Vital")
        if v is not None and v.get("value"):
            info["cost"] = _num(v.get("value"))
            info["cost_vital"] = v.get("index")
        cd = cost.find("Cooldown")
        if cd is not None and cd.get("TimeUse"):
            info["cooldown"] = _num(cd.get("TimeUse"))
        ch = cost.find("Charge")
        if ch is not None:
            if ch.get("CountMax"):
                info["charges"] = _num(ch.get("CountMax"))
            if ch.get("TimeUse"):
                info["charge_cooldown"] = _num(ch.get("TimeUse"))
        if "cooldown" in info or "cost" in info:
            break
    rng = cat.get_float(tag, abil_id, "Range")
    if rng is not None:
        info["range"] = rng if rng < 400 else None   # 500 = 사실상 무제한 표기
    cast = cat.get_float(tag, abil_id, "CastIntroTime")
    if cast:
        info["cast_time"] = cast
    # 효과 트리
    roots = []
    for p in ("Effect", "PrepEffect", "CursorEffect"):
        for node in el.findall(p):
            ref = node.get("value")
            if ref:
                roots.append(ref)
    # 다단계 능력 보정: 툴팁 오버라이드 문자열에 실제 쿨다운/비용이 있으면 사용
    for key_base in filter(None, [button, abil_id]):
        cdo = strings.get(f"Abil/{key_base}ButtonCooldownCostOverride")
        vco = strings.get(f"Abil/{key_base}ButtonVitalCostOverride")
        if cdo:
            m2 = re.search(r"([\d.]+)", cdo)
            if m2 and (info.get("cooldown") is None or info["cooldown"] < float(m2.group(1))):
                info["cooldown"] = float(m2.group(1))
                info["cooldown_source"] = "tooltip_override"
        if vco:
            m2 = re.search(r"([\d.]+)", vco)
            if m2 and info.get("cost") is None:
                info["cost"] = float(m2.group(1))
                info["cost_source"] = "tooltip_override"
        if cdo or vco:
            break
    res = None
    for r in roots:
        res = walker.walk(r, out=res)
    if res:
        info["derived_tags"] = sorted(res["tags"])
        for k in ("damage", "heal", "cc", "shield", "summon", "aoe"):
            if res[k]:
                seen_e, ded = set(), []
                for item in res[k]:
                    key = json.dumps(item, sort_keys=True, ensure_ascii=False) \
                        if isinstance(item, dict) else item
                    if key not in seen_e:
                        seen_e.add(key); ded.append(item)
                info[k] = ded
    return info


def classify_talent(cat, talent_el, base_abils):
    """특성 종류 판정: upgrade / new_active / passive / quest 조합."""
    kinds = []
    abil = talent_el.find("Abil")
    abil_id = abil.get("value") if abil is not None else None
    if talent_el.find("QuestData") is not None:
        kinds.append("quest")
    if talent_el.find("Trait") is not None:
        kinds.append("passive")
    if talent_el.find("Active") is not None:
        kinds.append("active")
    if abil_id:
        if abil_id in base_abils:
            kinds.append("upgrade")            # 기존 스킬 강화
        elif "active" in kinds:
            kinds.append("granted_ability")    # 새 사용 효과 부여
    if talent_el.find("AbilityModificationArray") is not None and "upgrade" not in kinds:
        kinds.append("modifies_ability")
    if not kinds:
        kinds.append("passive")
    return kinds, abil_id


def extract_hero(cat: Catalog, strings: Strings, hero_id):
    hero_els = cat.elems("CHero", hero_id)
    if not hero_els:
        return None
    hero = hero_els[0]
    scaling = {}
    for h in hero_els:
        scaling.update(load_scaling_map(cat, h))
    walker = EffectWalker(cat, scaling)

    unit_id = cat.get_value("CHero", hero_id, "Unit") or f"Hero{hero_id}"
    unit_id = unit_id.replace("##id##", hero_id)
    if not cat.elems("CUnit", unit_id):
        unit_id = f"Hero{hero_id}"
    profile = {
        "internal_id": hero_id,
        "name_ko": strings.get(f"Hero/Name/{hero_id}"),
        "role": cat.get_value("CHero", hero_id, "ExpandedRole")
                or cat.get_value("CHero", hero_id, "Role"),
        "melee": cat.get_value("CHero", hero_id, "Melee") == "1",
        "stats": extract_unit_stats(cat, strings, unit_id, scaling),
        "weapons": extract_weapon(cat, unit_id, scaling),
    }

    # ---- 능력 ----
    abilities, base_abil_ids = [], set()
    qwe = 0
    heroic_n = 0
    rows = []
    for h in hero_els:
        rows += h.findall("HeroAbilArray")
    for row in rows:
        abil_id = row.get("Abil")
        button = row.get("Button")
        flags = [f.get("index") for f in row.findall("Flags") if f.get("value") == "1"]
        if "ShowInHeroSelect" not in flags and abil_id is None:
            continue
        a = extract_ability(cat, strings, walker, abil_id, button, flags)
        if "Heroic" in flags:
            heroic_n += 1
            a["hotkey"] = "R"
            a["heroic_index"] = heroic_n
        elif "Trait" in flags:
            a["hotkey"] = "TRAIT"
        else:
            qwe += 1
            a["hotkey"] = {1: "Q", 2: "W", 3: "E"}.get(qwe, f"+{qwe}")
        abilities.append(a)
        if abil_id:
            base_abil_ids.add(abil_id)
    profile["abilities"] = abilities

    # ---- 특성 ----
    talents = []
    links = defaultdict(list)
    trows = []
    for h in hero_els:
        trows += h.findall("TalentTreeArray")
    for row in trows:
        tid = row.get("Talent")
        tier = int(row.get("Tier", "0"))
        col = int(row.get("Column", "0"))
        tels = cat.elems("CTalent", tid)
        face = cat.get_value("CTalent", tid, "Face") or tid
        kinds, abil_link = (["unknown"], None)
        if tels:
            kinds, abil_link = classify_talent(cat, tels[0], base_abil_ids)
        t = {"id": tid, "tier": tier, "level": TIER_TO_LEVEL.get(tier),
             "column": col, "face": face,
             "name_ko": strings.name_of_button(face),
             "summary_ko": strings.simple_of_button(face),
             "kinds": kinds, "linked_ability": abil_link}
        talents.append(t)
        if abil_link:
            links[abil_link].append(tid)
    profile["talents"] = sorted(talents, key=lambda t: (t["tier"], t["column"]))
    profile["ability_talent_links"] = dict(links)
    return profile

# ---------------------------------------------------------------- 위키 매칭

import unicodedata

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def match_wiki(profile, wiki_hero):
    """XML 프로필 <- 위키 항목 결합 (능력=단축키, 특성=레벨+슬롯)."""
    if not wiki_hero:
        return profile
    profile["wiki_name"] = wiki_hero["hero"]

    # 능력 매칭
    wiki_by_key = defaultdict(list)
    for wa in wiki_hero.get("abilities", []):
        hk = (wa.get("hotkey") or "").upper()
        wiki_by_key[hk].append(wa)
    r_used = 0
    for a in profile["abilities"]:
        hk = a.get("hotkey")
        cand = []
        if hk == "R":
            cand = wiki_by_key.get("R", [])
            if len(cand) > a.get("heroic_index", 1) - 1:
                cand = [cand[a["heroic_index"] - 1]]
            r_used += 1
        elif hk == "TRAIT":
            cand = wiki_by_key.get("TRAIT", []) or wiki_by_key.get("D", [])
        else:
            cand = wiki_by_key.get(hk, [])
        if cand:
            wa = cand[0]
            a["wiki"] = {"name": wa.get("name"),
                         "description": wa.get("description"),
                         "fields": wa.get("fields", {})}

    # 특성 매칭 (tier -> level 문자열, slot)
    wiki_tal = {}
    for wt in wiki_hero.get("talents", []):
        key = (str(wt.get("level") or wt.get("tier")), str(wt.get("slot")))
        wiki_tal[key] = wt
    for t in profile["talents"]:
        wt = (wiki_tal.get((str(t["level"]), str(t["column"])))
              or wiki_tal.get((str(t["tier"]), str(t["column"]))))
        if wt:
            t["wiki"] = {"name": wt.get("name"),
                         "description": wt.get("description"),
                         "fields": wt.get("fields", {})}
    return profile

# ---------------------------------------------------------------- 메인

def main(base, wiki_json, outdir):
    os.makedirs(os.path.join(outdir, "heroes"), exist_ok=True)
    wiki = {h["hero"]: h for h in json.load(open(wiki_json, encoding="utf-8"))}

    # 공용 카탈로그 (heroesdata_* + 정상 core_*)
    shared = Catalog()
    n = 0
    for f in sorted(glob.glob(os.path.join(base, "_core", "*.xml"))):
        n += bool(shared.load_file(f))
    print(f"공용 XML {n}개 로드")

    # 공용/영웅별 문자열
    strings_common = Strings()
    for f in ("heroesdata_gamestrings.txt", "heroes_gamestrings.txt"):
        strings_common.load(os.path.join(base, "_strings", f))

    summary, link_rows, type_rows = [], [], []
    folders = sorted(d for d in os.listdir(os.path.join(base, "heroes"))
                     if os.path.isdir(os.path.join(base, "heroes", d)))
    for folder in folders:
        if folder == "common":
            continue
        wiki_names = FOLDER_TO_WIKI.get(folder, [folder.capitalize()])
        cat = Catalog()
        cat.index.update(shared.index); cat.by_id.update(shared.by_id)
        cat.defaults.update(shared.defaults)
        cat = _merge_into(shared, cat_folder(base, folder))
        strings = Strings()
        strings.map.update(strings_common.map)
        strings.load(os.path.join(base, "_strings", f"{folder}_gamestrings.txt"))

        # CHero 후보: 위키명 정규화와 일치하는 id 우선, 없으면 파일 내 CHero 전부
        hero_ids = [eid for (tag, eid) in cat.index if tag == "CHero"]
        for wname in wiki_names:
            hid = _pick_hero_id(hero_ids, wname, folder)
            if not hid:
                print(f"[경고] {folder}: CHero id 미확인 ({wname}) 후보={hero_ids[:5]}")
                continue
            prof = extract_hero(cat, strings, hid)
            if not prof:
                continue
            prof["folder"] = folder
            match_wiki(prof, wiki.get(wname))
            out_name = norm(wname) or hid.lower()
            with open(os.path.join(outdir, "heroes", f"{out_name}.json"),
                      "w", encoding="utf-8") as f:
                json.dump(prof, f, ensure_ascii=False, indent=1)
            s = prof["stats"]
            w = prof["weapons"][0] if prof["weapons"] else {}
            summary.append([wname, prof.get("name_ko"), prof.get("role"),
                            "근접" if prof["melee"] else "원거리",
                            s["life_max"], s["life_regen"],
                            s.get("life_scaling_per_level"),
                            s["resource_name_ko"], s["energy_max"], s["energy_regen"],
                            w.get("damage"), w.get("period"), w.get("range"),
                            w.get("dps"), s["speed"], s["radius_collision"], s["sight"],
                            len(prof["abilities"]), len(prof["talents"])])
            for t in prof["talents"]:
                link_rows.append([wname, t["level"], t["column"],
                                  t.get("name_ko") or t["id"],
                                  "+".join(t["kinds"]), t.get("linked_ability") or "-",
                                  (t.get("wiki") or {}).get("name") or "-"])
            for a in prof["abilities"]:
                wf = (a.get("wiki") or {}).get("fields", {})
                dmg = a.get("damage") or []
                type_rows.append([wname, a.get("hotkey"), a.get("name_ko"),
                                  (a.get("wiki") or {}).get("name") or "-",
                                  a.get("cooldown"), a.get("cost"),
                                  a.get("cost_vital") or "-",
                                  "; ".join(a.get("derived_tags") or []),
                                  wf.get("type") or "-",
                                  dmg[0]["amount"] if dmg else None,
                                  dmg[0]["scaling"] if dmg else None,
                                  wf.get("scaling") or "-"])
            print(f"  {wname}: 능력 {len(prof['abilities'])} 특성 {len(prof['talents'])}")

    with open(os.path.join(outdir, "summary_stats.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["hero", "이름", "역할", "근접/원거리", "생명력", "생명력재생",
                    "생명력스케일", "자원", "자원최대", "자원재생", "공격력",
                    "공격주기", "사거리", "DPS", "이동속도", "충돌반경", "시야",
                    "능력수", "특성수"])
        w.writerows(summary)
    with open(os.path.join(outdir, "talent_links.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["hero", "레벨", "슬롯", "특성명", "종류", "연결된 능력", "wiki특성명"])
        w.writerows(link_rows)
    with open(os.path.join(outdir, "ability_types.csv"), "w", newline="",
              encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["hero", "키", "능력명(ko)", "wiki명", "쿨다운", "비용", "자원",
                    "XML유래 태그", "wiki type", "기본피해량", "XML스케일링", "wiki스케일링"])
        w.writerows(type_rows)
    print(f"\n완료: {len(summary)}명 -> {outdir}")


def cat_folder(base, folder):
    c = Catalog()
    for f in sorted(glob.glob(os.path.join(base, "heroes", folder, "*.xml"))):
        c.load_file(f)
    # 구형 영웅 공용(common) 데이터도 포함
    for f in sorted(glob.glob(os.path.join(base, "heroes", "common", "*.xml"))):
        c.load_file(f)
    return c


def _merge_into(shared, own):
    """영웅 전용 정의가 공용보다 우선하도록 병합."""
    m = Catalog()
    for k, v in own.index.items():
        m.index[k].extend(v)
    for k, v in shared.index.items():
        m.index[k].extend(v)
    for k, v in own.by_id.items():
        m.by_id[k].extend(v)
    for k, v in shared.by_id.items():
        m.by_id[k].extend(v)
    for k, v in own.defaults.items():
        m.defaults[k].extend(v)
    for k, v in shared.defaults.items():
        m.defaults[k].extend(v)
    return m


HERO_ID_OVERRIDES = {"brightwing": "FaerieDragon"}

def _pick_hero_id(hero_ids, wiki_name, folder):
    if folder in HERO_ID_OVERRIDES and HERO_ID_OVERRIDES[folder] in hero_ids:
        return HERO_ID_OVERRIDES[folder]
    tgt = norm(wiki_name)
    # 1) 정확 일치
    for hid in hero_ids:
        if norm(hid) == tgt:
            return hid
    # 2) 폴더명 일치
    for hid in hero_ids:
        if norm(hid) == norm(folder):
            return hid
    # 3) 부분 일치
    for hid in hero_ids:
        if tgt and (tgt in norm(hid) or norm(hid) in tgt):
            return hid
    return hero_ids[0] if len(hero_ids) == 1 else None


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "hots_analysis"
    wiki = sys.argv[2] if len(sys.argv) > 2 else "all_heroes.json"
    out = sys.argv[3] if len(sys.argv) > 3 else "out"
    main(base, wiki, out)
