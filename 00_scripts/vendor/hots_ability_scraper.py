#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heroes of the Storm Fandom 위키 - 전체 영웅 스킬/특성 수집기 (개선판 v2)
=====================================================================
MediaWiki 공식 API(api.php)를 사용하므로 일반 크롤링보다 안정적이고
차단 위험이 적습니다. (그래도 요청 간 딜레이를 꼭 지켜주세요)

v2 개선 사항 (데이터 누락 방지):
  1. {{hero data}} 추출을 정규식(비탐욕 `.*?`) 대신 중괄호 깊이를 세는
     스캐너로 교체 → 값 안에 `}}`가 있어도 템플릿이 중간에 잘리지 않음
  2. 스킬 레코드 분리를 "`}};`로 끝나는 블록" 가정 대신
     깊이 0 기준 줄 분할로 교체 → {{undoc-x}}가 없는 스킬도 수집됨
  3. undoc-x 추출/파싱을 중첩 인식 방식으로 교체 → 내부에 {{Slow}} 같은
     중첩 템플릿이 있어도 잘리지 않음
  4. 필드 분할(`;`, `|`)을 전부 깊이 인식 분할로 교체 → 설명에
     세미콜론·[[링크|별칭]]이 있어도 필드가 밀리지 않음
  5. talents 단일 파라미터뿐 아니라 talent_<tier>_<column> 개별
     파라미터도 수집 (실제 Data: 페이지가 이 형식을 쓰는 경우가 많음)
  6. 파싱에 실패/누락된 원본 조각을 output/debug/<영웅>.txt 에 남기고,
     실행 끝에 영웅별 개수 검증 리포트 출력 → 누락을 바로 발견 가능

사용법:
    pip install requests
    python hots_ability_scraper.py --all              # 전체 영웅
    python hots_ability_scraper.py Artanis Kerrigan   # 특정 영웅만
    python hots_ability_scraper.py --all --delay 2.0  # 딜레이 조정

결과물 (output/ 폴더):
    raw/<영웅>.wikitext      원본 위키텍스트 (디버깅/검증용)
    heroes/<영웅>.json       영웅별 구조화된 스킬 데이터
    debug/<영웅>.txt         파싱하지 못한 조각 (있을 때만 생성)
    all_heroes.json          전체 통합 JSON
    abilities_index.csv      모든 스킬의 하위 필드를 펼친 플랫 인덱스
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

import requests

API_URL = "https://heroesofthestorm.fandom.com/api.php"
HEADERS = {
    # Fandom은 식별 가능한 User-Agent를 권장합니다. 원하면 연락처로 바꾸세요.
    "User-Agent": "HotS-Ability-Indexer/2.0 (personal data project)"
}

# 네비게이션 박스 기준 전체 영웅 목록 (2026-07 기준, 90명)
HEROES = [
    # Bruiser
    "Artanis", "Chen", "Deathwing", "Dehaka", "D.Va", "Gazlowe", "Hogger",
    "Imperius", "Leoric", "Malthael", "Ragnaros", "Rexxar", "Sonya",
    "Thrall", "Varian", "Xul", "Yrel",
    # Healer
    "Alexstrasza", "Ana", "Anduin", "Auriel", "Brightwing", "Deckard",
    "Kharazim", "Li Li", "Lt. Morales", "Lúcio", "Malfurion", "Rehgar",
    "Stukov", "Uther", "Tyrande", "Whitemane",
    # Melee Assassin
    "Alarak", "The Butcher", "Illidan", "Kerrigan", "Maiev", "Murky",
    "Qhira", "Samuro", "Valeera", "Zeratul",
    # Ranged Assassin
    "Azmodan", "Cassia", "Chromie", "Falstad", "Fenix", "Gall", "Genji",
    "Greymane", "Gul'dan", "Hanzo", "Jaina", "Junkrat", "Kael'thas",
    "Kel'Thuzad", "Li-Ming", "Lunara", "Mephisto", "Nazeebo", "Nova",
    "Orphea", "Probius", "Raynor", "Sgt. Hammer", "Sylvanas", "Tassadar",
    "Tracer", "Tychus", "Valla", "Zagara", "Zul'jin",
    # Support
    "Abathur", "The Lost Vikings", "Medivh", "Zarya",
    # Tank
    "Anub'arak", "Arthas", "Blaze", "Cho", "Diablo", "E.T.C.", "Garrosh",
    "Johanna", "Mal'Ganis", "Mei", "Muradin", "Stitches", "Tyrael",
]

ABILITY_HOTKEYS = {"TRAIT", "D", "Q", "W", "E", "R", "R1", "R2", "Z", "1", "2"}

# ---------------------------------------------------------------------------
# 1) API에서 위키텍스트 가져오기
# ---------------------------------------------------------------------------

def fetch_wikitext(session: requests.Session, title: str, retries: int = 3) -> str | None:
    """MediaWiki API로 문서의 원본 위키텍스트를 가져온다."""
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "redirects": 1,
        "titles": title,
        "format": "json",
        "formatversion": 2,
    }
    for attempt in range(1, retries + 1):
        try:
            r = session.get(API_URL, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
            pages = data.get("query", {}).get("pages", [])
            if not pages or pages[0].get("missing"):
                return None
            revisions = pages[0].get("revisions")
            if not revisions:
                return None
            return revisions[0]["slots"]["main"]["content"]
        except Exception as e:
            print(f"    [재시도 {attempt}/{retries}] {title}: {e}", file=sys.stderr)
            time.sleep(3 * attempt)
    return None


# ---------------------------------------------------------------------------
# 2) 깊이(중첩) 인식 저수준 파서 유틸
# ---------------------------------------------------------------------------

def find_template(text: str, name: str) -> str | None:
    """
    이름이 name인 최상위 {{...}} 템플릿의 '내부'를 반환 (중괄호 깊이 계산).
    기존의 re.search(r"\\{\\{hero data\\n(.*?)\\n\\}\\}") 방식은 값 안에
    줄 시작 `}}`가 나오는 순간 잘려서 이후 데이터가 통째로 누락됐다.
    """
    pat = re.compile(r"\{\{\s*" + re.escape(name) + r"\s*[\n|]", re.IGNORECASE)
    m = pat.search(text)
    if not m:
        return None
    start = m.start()
    depth, i, n = 0, start, len(text)
    while i < n - 1:
        two = text[i:i + 2]
        if two == "{{":
            depth += 1
            i += 2
        elif two == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return text[start + 2:i - 2]
        else:
            i += 1
    # 닫히지 않은 템플릿 — 있는 데까지라도 반환 (누락보단 낫다)
    return text[start + 2:]


def split_depth0(body: str, sep: str) -> list[str]:
    """{{}} / [[]] 중첩 내부를 무시하고 깊이 0의 sep 기준으로 분할."""
    parts, buf = [], []
    depth_t = depth_l = 0
    i, n = 0, len(body)
    while i < n:
        two = body[i:i + 2]
        if two == "{{":
            depth_t += 1; buf.append(two); i += 2; continue
        if two == "}}":
            depth_t = max(0, depth_t - 1); buf.append(two); i += 2; continue
        if two == "[[":
            depth_l += 1; buf.append(two); i += 2; continue
        if two == "]]":
            depth_l = max(0, depth_l - 1); buf.append(two); i += 2; continue
        if body[i] == sep and depth_t == 0 and depth_l == 0:
            parts.append("".join(buf)); buf = []; i += 1; continue
        buf.append(body[i]); i += 1
    parts.append("".join(buf))
    return parts


LINK_RE = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]")   # [[A|B]] -> B
BOLDITAL_RE = re.compile(r"'{2,5}")
TAG_RE = re.compile(r"<[^>]+>")
REF_RE = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S)
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def clean_wiki(value: str) -> str:
    """위키 마크업을 사람이 읽을 수 있는 텍스트로 정리."""
    value = COMMENT_RE.sub("", value)
    value = REF_RE.sub("", value)
    value = LINK_RE.sub(r"\1", value)
    value = BOLDITAL_RE.sub("", value)
    # 값 안의 인라인 템플릿({{Slow}}, {{Quest}} 등)은 이름/내용만 남긴다.
    # 중첩 대응을 위해 안쪽부터 반복 치환.
    for _ in range(5):
        new = re.sub(r"\{\{\s*([^|{}]+?)\s*\}\}", r"\1", value)
        new = re.sub(r"\{\{\s*([^|{}]+?)\s*\|([^{}]*)\}\}", r"\1 \2", new)
        if new == value:
            break
        value = new
    value = TAG_RE.sub(" ", value)
    # {{Quest|A|B}} 펼침 등으로 남은 파이프는 문장 구분으로 정리
    value = re.sub(r"\s*\|\s*", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def clean_icon(value: str) -> str:
    """아이콘 값 정리: File:/Image: 접두어와 밑줄 제거는 하지 않고 접두어만."""
    value = clean_wiki(value)
    return re.sub(r"^(File|Image)\s*:\s*", "", value, flags=re.IGNORECASE)


# ---------------------------------------------------------------------------
# 3) {{hero data}} 파라미터 파싱 (중첩 인식)
# ---------------------------------------------------------------------------

def extract_hero_data_template(wikitext: str) -> dict:
    """{{hero data}} 내부를 깊이 인식 방식으로 {key: raw_value}에 담는다."""
    body = find_template(wikitext, "hero data")
    if body is None:
        # 페이지에 따라 소문자/변형 이름 가능성 대비
        for alt in ("Hero data", "herodata"):
            body = find_template(wikitext, alt)
            if body is not None:
                break
    if body is None:
        return {}

    params = {}
    # 첫 조각은 템플릿 이름이므로 버린다
    for part in split_depth0(body, "|")[1:]:
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip().lower()
        v = v.strip()
        if k:
            params[k] = v
    return params


# ---------------------------------------------------------------------------
# 4) undoc-x 및 레코드 파싱
# ---------------------------------------------------------------------------

def extract_undoc(text: str) -> tuple[str, dict]:
    """
    text 안의 {{undoc-x|...}} (또는 {{undoc|...}})를 깊이 인식으로 찾아
    (undoc 제거된 텍스트, 필드 dict)를 반환. 여러 개면 병합.
    """
    fields = {}
    out = text
    while True:
        m = re.search(r"\{\{\s*undoc[^|{}]*\|", out, re.IGNORECASE)
        if not m:
            break
        start = m.start()
        depth, i, n = 0, start, len(out)
        end = None
        while i < n - 1:
            two = out[i:i + 2]
            if two == "{{":
                depth += 1; i += 2
            elif two == "}}":
                depth -= 1; i += 2
                if depth == 0:
                    end = i
                    break
            else:
                i += 1
        if end is None:
            end = n
        inner = out[start + 2:end - 2]
        # 첫 조각은 템플릿 이름
        for part in split_depth0(inner, "|")[1:]:
            if "=" in part:
                k, _, v = part.partition("=")
                k = k.strip().lower()
                v = clean_wiki(v)
                if k and v:
                    fields[k] = v
        out = out[:start] + out[end:]
    return out, fields


def looks_like_icon(s: str) -> bool:
    low = s.lower()
    return low.endswith((".png", ".jpg", ".jpeg", ".gif")) or "icon" in low


def split_records(raw: str) -> list[str]:
    """
    skills/talents 파라미터 값을 레코드 단위로 분할.
    - <!-- --> 주석 제거 (줄 연결용 주석 포함)
    - 깊이 0 기준 줄 분할
    - 필드 구분자(;)가 거의 없는 줄은 이전 레코드에 이어 붙임
    """
    raw = COMMENT_RE.sub("", raw)
    records = []
    for line in split_depth0(raw, "\n"):
        line = line.strip().strip(";").strip()
        if not line:
            continue
        n_fields = len(split_depth0(line, ";"))
        if n_fields >= 3 or not records:
            records.append(line)
        else:
            # 멀티라인 설명의 연속으로 간주
            records[-1] += " " + line
    return [r for r in records if r]


def parse_skill_record(record: str) -> dict | None:
    """
    스킬 레코드: 이름;단축키;아이콘;설명{{undoc-x|...}};cooldown;mana;...
    undoc-x가 없어도 수집한다 (기존 코드는 `}};` 없으면 버렸음 → 누락 원인).
    """
    parts = [p.strip() for p in split_depth0(record, ";")]
    if len(parts) < 4:
        return None

    name = clean_wiki(parts[0])
    hotkey = clean_wiki(parts[1]).upper()
    icon = clean_icon(parts[2])

    # 위치 기반 형식: ...;설명;cooldown;mana;?;False — 설명에 세미콜론이
    # 섞여도 안전하도록, 끝에서부터 숫자/불리언/빈 필드만 걷어내고
    # 나머지는 전부 설명으로.
    tail = parts[3:]
    trailing: list[str] = []
    while tail and re.fullmatch(r"[\d.\s]*|true|false", tail[-1].strip(),
                                re.IGNORECASE):
        trailing.insert(0, tail.pop().strip())
        if len(trailing) >= 5:
            break
    desc_raw = "; ".join(p for p in tail if p)

    desc_clean, undoc_fields = extract_undoc(desc_raw)
    description = clean_wiki(desc_clean)

    # 걷어낸 꼬리 필드 보존 — 위치 기준: cooldown;mana(cost);나머지
    def _is_bool(x: str) -> bool:
        return x.lower() in ("true", "false")

    if trailing:
        if trailing[0] and not _is_bool(trailing[0]):
            undoc_fields.setdefault("cooldown", trailing[0])
        if len(trailing) >= 2 and trailing[1] and not _is_bool(trailing[1]):
            undoc_fields.setdefault("cost", trailing[1])
        rest_extra = [t for t in trailing[2:] if t and not _is_bool(t)]
        if rest_extra:
            undoc_fields.setdefault("_extra", " | ".join(rest_extra))

    if not name:
        return None
    return {
        "name": name,
        "hotkey": hotkey,
        "icon": icon,
        "description": description,
        "fields": undoc_fields,
    }


def parse_talent_record(record: str, tier_hint: str = "", slot_hint: str = "") -> dict | None:
    """
    특성 레코드. 형식이 페이지마다 조금씩 달라서
    (이름;tier;slot;설명;아이콘 / 이름;설명;아이콘 등) 위치를 단정하지 않고
    휴리스틱으로 배치하되, 원본 필드를 _raw_fields로 전부 보존한다.
    """
    parts = [p.strip() for p in split_depth0(record, ";")]
    parts = [p for p in parts if p != ""]
    if not parts:
        return None

    record_no_undoc, undoc_fields = extract_undoc(record)
    parts_nu = [p.strip() for p in split_depth0(record_no_undoc, ";")]
    parts_nu = [p for p in parts_nu if p.strip() != ""]
    if not parts_nu:
        return None

    name = clean_wiki(parts_nu[0])
    tier, slot, icon = tier_hint, slot_hint, ""
    rest = parts_nu[1:]
    desc_parts: list[str] = []

    for p in rest:
        c = clean_wiki(p)
        if not c:
            continue
        if not tier and re.fullmatch(r"\d{1,2}", c):
            tier = c
        elif not slot and len(c) <= 7 and len(rest) > 2 \
                and re.fullmatch(r"\d|Q|W|E|R|D|Trait|Active|Passive", c, re.IGNORECASE):
            slot = c
        elif not icon and looks_like_icon(c):
            icon = clean_icon(c)
        else:
            desc_parts.append(c)

    # 텍스트 조각은 모두 설명으로 합침 (하나만 고르면 나머지가 누락됨)
    description = " ".join(desc_parts)

    if not name:
        return None
    return {
        "name": name,
        "tier": tier,
        "slot": slot,
        "icon": icon,
        "description": description,
        "fields": undoc_fields,
        "_raw_fields": [clean_wiki(p) for p in parts_nu],  # 누락 방지용 원본 보존
    }


# ---------------------------------------------------------------------------
# 5) 영웅 단위 파싱
# ---------------------------------------------------------------------------

TALENT_KEY_RE = re.compile(r"^talent[_\s]?(\d{1,2})[_\s]?(\d{1,2})$")


def parse_hero(hero: str, wikitext: str, debug_dir: Path | None = None) -> dict:
    hero_data = extract_hero_data_template(wikitext)
    unparsed: list[str] = []

    abilities: list[dict] = []
    talents: list[dict] = []
    other: list[dict] = []

    # --- skills 파라미터 ---
    if "skills" in hero_data:
        for rec in split_records(hero_data["skills"]):
            entry = parse_skill_record(rec)
            if entry is None:
                unparsed.append(f"[skills] {rec}")
                continue
            if entry["hotkey"] in ABILITY_HOTKEYS:
                abilities.append(entry)
            elif entry["hotkey"] == "":
                other.append(entry)
            else:
                # 단축키 자리에 tier 숫자 등이 오는 특성형 레코드
                t = parse_talent_record(rec)
                if t:
                    talents.append(t)
                else:
                    other.append(entry)

    # --- talents 단일 파라미터 ---
    if hero_data.get("talents"):
        for rec in split_records(hero_data["talents"]):
            t = parse_talent_record(rec)
            if t:
                talents.append(t)
            else:
                unparsed.append(f"[talents] {rec}")

    # --- talent_<tier>_<column> 개별 파라미터 (기존 코드가 놓치던 부분) ---
    for key, val in hero_data.items():
        m = TALENT_KEY_RE.match(key)
        if not m or not val.strip():
            continue
        tier, col = m.group(1), m.group(2)
        for rec in split_records(val):
            t = parse_talent_record(rec, tier_hint=tier, slot_hint=col)
            if t:
                talents.append(t)
            else:
                unparsed.append(f"[{key}] {rec}")

    # --- R 궁극기 2개 이상이면 두 번째부터는 10레벨 특성 성격도 있으나,
    #     실수로 데이터가 사라지지 않도록 abilities에 그대로 둔다. ---

    # --- 이름 기준 중복 제거 (talents 파라미터와 talent_x_y 가 겹칠 수 있음) ---
    def dedup(items: list[dict]) -> list[dict]:
        seen, out = set(), []
        for it in items:
            k = (it.get("name", ""), it.get("tier", ""), it.get("hotkey", ""))
            if k in seen:
                continue
            seen.add(k)
            out.append(it)
        return out

    abilities = dedup(abilities)
    talents = dedup(talents)

    # --- 특성 tier 표기 정규화: 페이지에 따라 1~7 '순번'(티어 인덱스) 또는
    #     1/4/7/10/13/16/20 '레벨'을 쓴다. 순번식이면 level 필드를 붙여준다. ---
    TIER_TO_LEVEL = {"1": "1", "2": "4", "3": "7", "4": "10",
                     "5": "13", "6": "16", "7": "20"}
    tier_vals = {t.get("tier", "") for t in talents if t.get("tier")}
    uses_index = tier_vals and tier_vals <= set(TIER_TO_LEVEL)
    for t in talents:
        tier = t.get("tier", "")
        if uses_index and tier in TIER_TO_LEVEL:
            t["level"] = TIER_TO_LEVEL[tier]
        elif tier:
            t["level"] = tier

    # --- Data: 페이지에 hero data가 아예 없으면 폴백:
    #     일반 문서의 최상위 템플릿에서 스킬 힌트 키를 가진 블록 수집 ---
    if not abilities and not talents:
        for _, body in _extract_top_templates(wikitext):
            tname, params = _parse_generic_template(body)
            if _looks_like_ability(params):
                entry = {
                    "name": params.get("name") or params.get("title") or tname,
                    "hotkey": (params.get("hotkey") or "").upper(),
                    "icon": params.get("icon", ""),
                    "description": params.get("description", ""),
                    "fields": {k: v for k, v in params.items()
                               if k not in ("name", "title", "hotkey", "icon", "description")},
                }
                if entry["hotkey"] in ABILITY_HOTKEYS:
                    abilities.append(entry)
                else:
                    other.append(entry)

    # --- 디버그: 파싱 못 한 조각 저장 ---
    if unparsed and debug_dir is not None:
        debug_dir.mkdir(parents=True, exist_ok=True)
        safe = re.sub(r"[^\w.\-]", "_", hero)
        (debug_dir / f"{safe}.txt").write_text(
            "\n\n".join(unparsed), encoding="utf-8")

    return {
        "hero": hero,
        "abilities": abilities,
        "talents": talents,
        "other": other,
        "_unparsed_count": len(unparsed),
    }


# ---- 폴백용: 일반 문서의 최상위 템플릿 파싱 (기존 코드 유지·정리) ----

def _extract_top_templates(text: str):
    results = []
    i, n = 0, len(text)
    while i < n - 1:
        if text[i:i + 2] == "{{":
            depth, j = 0, i
            while j < n - 1:
                if text[j:j + 2] == "{{":
                    depth += 1; j += 2
                elif text[j:j + 2] == "}}":
                    depth -= 1; j += 2
                    if depth == 0:
                        results.append((i, text[i + 2:j - 2]))
                        break
                else:
                    j += 1
            i = j if j > i else i + 2
        else:
            i += 1
    return results


ABILITY_HINT_KEYS = {
    "description", "cooldown", "cost", "mana", "type", "affects",
    "scaling", "range", "hitbox", "cast time", "casttime", "targeting",
    "properties", "hotkey",
}


def _parse_generic_template(body: str):
    parts = split_depth0(body, "|")
    name = parts[0].strip()
    params = {}
    for p in parts[1:]:
        if "=" in p:
            k, _, v = p.partition("=")
            params[k.strip().lower()] = clean_wiki(v)
    return name, params


def _looks_like_ability(params: dict) -> bool:
    return len(ABILITY_HINT_KEYS & set(params)) >= 2


# ---------------------------------------------------------------------------
# 6) 출력
# ---------------------------------------------------------------------------

def write_csv_index(all_data: list[dict], path: Path):
    """모든 스킬의 하위 필드를 '영웅/구분/스킬/필드/값' 형태로 펼친 인덱스."""
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["hero", "category", "ability_name", "hotkey_or_tier",
                    "field", "value"])
        for hero_data in all_data:
            for cat in ("abilities", "talents", "other"):
                for entry in hero_data.get(cat, []):
                    name = entry.get("name", "Unknown")
                    key2 = entry.get("hotkey") or entry.get("tier", "")
                    for k in ("icon", "description", "slot"):
                        if entry.get(k):
                            w.writerow([hero_data["hero"], cat, name, key2,
                                        k, entry[k]])
                    for k, v in entry.get("fields", {}).items():
                        if isinstance(v, list):
                            v = " | ".join(map(str, v))
                        w.writerow([hero_data["hero"], cat, name, key2,
                                    k, str(v)])


def print_report(all_data: list[dict]):
    """영웅별 수집 개수 검증 — 누락 의심 항목을 한눈에."""
    print("\n===== 수집 검증 리포트 =====")
    suspicious = []
    for d in all_data:
        n_ab, n_tal = len(d["abilities"]), len(d["talents"])
        flags = []
        # 대부분 영웅: 기본기 Q/W/E + 특성기 + 궁 2개 → 최소 5개 기대
        if n_ab < 4:
            flags.append(f"스킬 {n_ab}개(적음)")
        # 특성은 보통 7티어 × 2~5개 → 최소 14개 기대
        if 0 < n_tal < 14:
            flags.append(f"특성 {n_tal}개(적음)")
        if n_tal == 0:
            flags.append("특성 0개")
        if d.get("_unparsed_count"):
            flags.append(f"미파싱 {d['_unparsed_count']}건(debug/ 확인)")
        if flags:
            suspicious.append((d["hero"], ", ".join(flags)))
    if not suspicious:
        print("모든 영웅 정상 범위 ✔")
    else:
        for hero, msg in suspicious:
            print(f"  ⚠️ {hero}: {msg}")
        print(f"→ 의심 {len(suspicious)}명. output/raw/ 원본과 output/debug/ 를 비교해 보세요.")


def main():
    ap = argparse.ArgumentParser(description="HotS Fandom 스킬 수집기 (개선판)")
    ap.add_argument("heroes", nargs="*", help="수집할 영웅 이름 (영문, 위키 문서명)")
    ap.add_argument("--all", action="store_true", help="전체 영웅 수집")
    ap.add_argument("--delay", type=float, default=1.5, help="요청 간 딜레이(초), 기본 1.5")
    ap.add_argument("--out", default="output", help="출력 폴더")
    args = ap.parse_args()

    targets = HEROES if args.all else args.heroes
    if not targets:
        ap.error("영웅 이름을 지정하거나 --all 옵션을 사용하세요.")

    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "heroes").mkdir(parents=True, exist_ok=True)
    debug_dir = out / "debug"

    session = requests.Session()
    all_data, failed = [], []

    for idx, hero in enumerate(targets, 1):
        print(f"[{idx}/{len(targets)}] {hero} ...", flush=True)

        # 먼저 Data: 페이지 시도 (스킬/특성 데이터 용)
        wikitext = fetch_wikitext(session, f"Data:{hero}")
        source = "Data"
        if not wikitext:
            wikitext = fetch_wikitext(session, hero)
            source = "일반"

        if not wikitext:
            print(f"    !! 문서를 찾지 못함: {hero} (또는 Data:{hero})", file=sys.stderr)
            failed.append(hero)
            time.sleep(args.delay)
            continue

        safe = re.sub(r"[^\w.\-]", "_", hero)
        (out / "raw" / f"{safe}.wikitext").write_text(wikitext, encoding="utf-8")

        data = parse_hero(hero, wikitext, debug_dir=debug_dir)

        # Data: 페이지 파싱 결과가 비었으면 일반 문서로 한 번 더 시도 (누락 방지 폴백)
        if source == "Data" and not data["abilities"] and not data["talents"]:
            fallback = fetch_wikitext(session, hero)
            if fallback:
                fb_data = parse_hero(hero, fallback, debug_dir=debug_dir)
                if fb_data["abilities"] or fb_data["talents"]:
                    data = fb_data
                    (out / "raw" / f"{safe}.wikitext").write_text(fallback, encoding="utf-8")
            time.sleep(args.delay)

        (out / "heroes" / f"{safe}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        all_data.append(data)

        n_a, n_t = len(data["abilities"]), len(data["talents"])
        status = f"    스킬 {n_a}개 / 특성 {n_t}개"
        if n_a == 0 and n_t == 0:
            status += " [⚠️ 데이터 없음 - raw/ 원본 확인 필요]"
        elif data.get("_unparsed_count"):
            status += f" [미파싱 {data['_unparsed_count']}건 → debug/]"
        print(status)
        time.sleep(args.delay)

    (out / "all_heroes.json").write_text(
        json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv_index(all_data, out / "abilities_index.csv")

    print(f"\n완료! 결과: {out.resolve()}")
    if failed:
        print(f"실패한 문서({len(failed)}): {', '.join(failed)}")
        print("→ 위키 문서명이 다를 수 있으니 사이트에서 정확한 제목을 확인하세요.")
    print_report(all_data)


if __name__ == "__main__":
    main()