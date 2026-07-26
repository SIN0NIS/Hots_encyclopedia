"""hots_ref/output/heroes/*.json 을 gamestring 기반으로 한글화한다.

  이름     : 위키 영문 표기 -> enus Button/Name 역인덱스 -> 내부 키 -> kokr
  설명     : 같은 내부 키의 kokr Button/Tooltip. <d ref/> 수치 자리는
             영문 툴팁과 위키 설명문을 토큰 정렬해 뽑아낸 실제 수치로 채운다.
  메타필드 : glossary.json 용어집으로 원소 단위 치환

사용:  python hots_kr/localize.py            (전체 빌드)
       python hots_kr/localize.py Jaina      (한 영웅만, 결과를 화면에 출력)
"""
import difflib
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
from gamestrings import (PLACEHOLDER, build_reverse, count_refs, load_lang,
                         normalize, strip_markup)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = paths.WIKI_HEROES
DST = paths.HEROES_KR
GLOSSARY = paths.GLOSSARY
OVERRIDES = paths.OVERRIDES
REPORT = paths.REPORT
GAMEDATA = paths.CASC        # gamestrings 는 mods/ 의 부모를 넘긴다

NAME_NAMESPACES = {"Button/Name/", "Abil/Name/", "Unit/Name/", "Hero/Name/"}
# 위키 설명문 꼬리에 붙는 "; 60; 60; heroic" 류의 파싱 잔재
PROSE_FIELDS = {"notes"}  # 위키 자체 해설 — gamestring 근거가 없어 번역하지 않는다

TAIL = re.compile(r";\s*(?:\d[\d\.,]*|trait|heroic|passive|active)\s*(?=;|$)", re.I)


# --------------------------------------------------------------------------
# 매칭
# --------------------------------------------------------------------------
class Matcher:
    def __init__(self, en, ko, overrides=None):
        self.en, self.ko = en, ko
        self.overrides = overrides or {}
        self.rev = build_reverse(en, NAME_NAMESPACES)
        # 위키 영웅명 -> 내부 영웅 ID (Hero/Name/Jaina=Jaina -> "jaina")
        self.hero_ids = {}
        for key, value in en.items():
            if key.startswith("Hero/Name/"):
                self.hero_ids[normalize(value)] = key[len("Hero/Name/"):]

    def hero_id(self, wiki_hero):
        """위키 파일명(Anub_arak, Lt._Morales)에서 내부 영웅 ID를 얻는다."""
        cleaned = normalize(wiki_hero.replace("_", " ").replace(".", " "))
        return self.hero_ids.get(cleaned)

    def candidates(self, name):
        """표기 변형을 차례로 시도해 후보 키 목록을 얻는다."""
        variants = [
            name,
            re.sub(r"\(.*?\)", "", name),        # "Sadism (Trait)"
            name.split(" - ")[-1],                # "Symbiote - Stab"
            name.split(" - ")[0],
            name.split(": ")[-1],                 # "Weapon Mode: Phase Bomb"
        ]
        for variant in variants:
            keys = self.rev.get(normalize(variant))
            if keys:
                return keys
        return []

    def match(self, wiki_hero, name):
        """(key, confidence) 반환. confidence: hero / unique / ambiguous / none"""
        pinned = self.overrides.get("%s|%s" % (wiki_hero, name))
        if pinned:
            return pinned, "override"
        keys = self.candidates(name)
        if not keys:
            return None, "none"
        hid = self.hero_id(wiki_hero)
        if hid:
            scoped = [k for k in keys
                      if normalize(k.rsplit("/", 1)[1]).startswith(normalize(hid))]
            if scoped:
                return self.best(scoped, hid, name), "hero"
        if len(set(self.ko.get(k) for k in keys)) == 1:
            return self.best(keys, hid, name), "unique"
        return self.best(keys, hid, name), "ambiguous"

    # 같은 이름에 걸린 여러 키 중 하나를 고른다. 한글 툴팁이 있는 키를 우선하고,
    # 그다음 <영웅ID><기술명> 정확 일치, 마지막으로 짧은 키.
    def best(self, keys, hid, name):
        target = normalize((hid or "") + name)

        def rank(key):
            suffix = key.split("/", 2)[2]
            return (
                0 if self.ko.get("Button/Tooltip/" + suffix) else 1,
                0 if normalize(suffix) == target else 1,
                len(key),
            )

        return min(keys, key=rank)


# --------------------------------------------------------------------------
# 설명문: 한글 툴팁의 수치 자리 채우기
# --------------------------------------------------------------------------
TOKEN = re.compile(r"\d[\d,\.]*%?|[A-Za-z']+|" + re.escape(PLACEHOLDER))


def extract_numbers(en_tooltip, wiki_desc):
    """영문 툴팁 골격과 위키 설명문을 정렬해 <d ref/> 자리의 실제 수치를 뽑는다.

    영문 툴팁은 수치가 placeholder 인 채로, 위키 설명문은 수치가 채워진 채로
    거의 동일한 문장이다. 토큰 단위 diff 로 placeholder <-> 숫자를 짝짓는다.
    """
    src = TOKEN.findall(strip_markup(en_tooltip))
    dst = TOKEN.findall(wiki_desc)
    matcher = difflib.SequenceMatcher(
        None, [t.lower() for t in src], [t.lower() for t in dst], autojunk=False)
    values, aligned = [], True
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        for i in range(i1, i2):
            if src[i] != PLACEHOLDER:
                continue
            digits = [dst[j] for j in range(j1, j2) if dst[j][0].isdigit()]
            if tag == "replace" and len(digits) == 1:
                values.append(digits[0])
            else:
                aligned = False
    return (values, "aligned") if aligned else (None, "unaligned")


REF_ATTR = re.compile(r'ref\s*=\s*"(.*?)"', re.S)


def refs_of(tooltip):
    """툴팁 안 <d ref="..."/> 의 참조 경로를 등장 순서대로 반환."""
    return [REF_ATTR.search(tag).group(1).strip()
            for tag in re.findall(r"<d\s+ref=.*?/>", tooltip, flags=re.S)]


def fill(ko_tooltip, en_tooltip, wiki_desc):
    """한글 툴팁의 <d ref/> 를 실제 수치로 치환한 문자열과 방식을 반환.

    한글은 영문과 어순이 달라 같은 수치가 다른 자리에 온다. 따라서 위치가 아니라
    <d ref="..."/> 의 참조 경로로 짝지어야 한다. 경로가 어긋날 때만 순서에 기댄다.
    """
    need = count_refs(ko_tooltip)
    if need == 0:
        return strip_markup(ko_tooltip), "no-numbers"

    ko_refs = refs_of(ko_tooltip)
    values, how = (None, "no-en")
    by_ref = None
    if en_tooltip and count_refs(en_tooltip) == need:
        values, how = extract_numbers(en_tooltip, wiki_desc)
        if values and len(values) == need:
            table = dict(zip(refs_of(en_tooltip), values))
            if all(ref in table for ref in ko_refs):
                by_ref = [table[ref] for ref in ko_refs]

    if by_ref is not None:
        values, how = by_ref, "by-ref"
    elif values is None or len(values) != need:
        # 폴백: 위키 설명문에 등장하는 숫자를 등장 순서대로 밀어넣는다.
        found = re.findall(r"\d[\d,\.]*%?", wiki_desc)
        if len(found) < need:
            return None, "insufficient"
        values, how = found[:need], "by-order"
    else:
        how = "by-position"   # 참조 경로가 어긋나 영문 자리 순서를 그대로 썼다

    out, index = [], 0
    for chunk in re.split(r"(<d\s+ref=.*?/>)", ko_tooltip, flags=re.S):
        if chunk.startswith("<d "):
            out.append(values[index])
            index += 1
        else:
            if out and index:
                out[-1] = trim_slot(out[-1], chunk)
            out.append(chunk)
    return strip_markup("".join(out), placeholder=""), how


SLOT_SUFFIX = re.compile(r"^(?:</?[^>]+>)*(\d*)(%?)")


def trim_slot(value, following):
    """수치 자리 바로 뒤에 붙는 리터럴만큼 값에서 덜어낸다.

    원문이 "<d ... *10 />0%" 처럼 자릿수나 %를 문자열로 직접 이어 붙이는 경우가
    있다. 위키에서 뽑은 값은 이미 완성형("50%")이라 그대로 넣으면 겹친다.
    """
    digits, percent = SLOT_SUFFIX.match(following).groups()
    if percent and value.endswith("%"):
        value = value[:-1]
    if digits and value.endswith(digits) and len(value) > len(digits):
        value = value[:-len(digits)]
    return value


# --------------------------------------------------------------------------
# 메타 필드 용어집
# --------------------------------------------------------------------------
class Glossary:
    SPLIT = re.compile(r"(\s*[,/]\s*)")
    PAREN = re.compile(r"^(.*?)\s*\((.+)\)$")
    # 수치 필드에 섞여 있는 단위·꼬리말
    UNITS = [
        (re.compile(r"\bper second\b", re.I), "초당"),   # "seconds" 규칙보다 먼저
        (re.compile(r"\bseconds?\b", re.I), "초"),
        (re.compile(r"\bdegrees?\b", re.I), "도"),
        (re.compile(r"\bthreshold\b", re.I), "조건부"),
        (re.compile(r"\bnone\b", re.I), "없음"),
        (re.compile(r"\binstant\b", re.I), "즉시"),
        (re.compile(r"\bglobal\b", re.I), "전역"),
        (re.compile(r"\binitial\b", re.I), "최초"),
        (re.compile(r"\bimpact\b", re.I), "충돌"),
        (re.compile(r"\bch\b", re.I), "정신집중"),
        (re.compile(r"\(x(\d+)\)"), r"(\1회)"),          # "1.0 per second (x3)"
        (re.compile(r"(?<=\d)\s*x\s*(?=\d)"), " × "),    # 판정 크기 "1.0 x 1.6"
        (re.compile(r"\bquest\b", re.I), "퀘스트"),
        (re.compile(r"\breward\b", re.I), "보상"),
        (re.compile(r"\bprimary\b", re.I), "주 대상"),
        (re.compile(r"\bsecondary\b", re.I), "부 대상"),
        (re.compile(r"\bpiercing\b", re.I), "관통"),
        (re.compile(r"\bstacking\b", re.I), "중첩"),
        (re.compile(r"\bthrow\b", re.I), "투척"),
        (re.compile(r"\bhitbox\b", re.I), "판정 범위"),
        (re.compile(r"\bhealing\b", re.I), "치유량"),
        (re.compile(r"\btrue\b", re.I), "예"),
        (re.compile(r"\bboth\b", re.I), "둘 다"),
        (re.compile(r"\bdamage\b", re.I), "피해량"),
        (re.compile(r"\bhealth\b", re.I), "생명력"),
    ]
    # 위 치환을 마친 뒤 남아도 되는 잔여물(숫자·기호·한글)
    RESIDUE = re.compile(r"[A-Za-z]")

    def __init__(self, path, fallback=None):
        data = json.load(open(path, encoding="utf-8"))
        self.labels = data["_field_labels"]
        # terms 는 갈래별로 묶여 있다. 찾을 때는 평평한 게 편하므로 펴서 쓴다.
        self.groups = data["terms"]
        self.terms = {word: korean
                      for bucket in self.groups.values()
                      for word, korean in bucket.items()}
        self.lower = {k.lower(): v for k, v in self.terms.items()}
        self.fallback = fallback      # 고유명사용 gamestring EN->KO 조회
        self.unknown = Counter()

    def units(self, text):
        for pattern, replacement in self.UNITS:
            text = pattern.sub(replacement, text)
        return text

    def term(self, atom):
        stripped = atom.strip()
        if not stripped:
            return atom
        hit = self.terms.get(stripped) or self.lower.get(stripped.lower())
        if hit:
            return atom.replace(stripped, hit)
        # "Crowd control (passive)" 처럼 괄호 단서가 붙은 형태는 안팎을 따로 옮긴다
        paren = self.PAREN.match(stripped)
        if paren:
            head, note = paren.group(1), paren.group(2)
            head_kr = self.terms.get(head) or self.lower.get(head.lower())
            if head_kr:
                return atom.replace(stripped, "%s(%s)" % (head_kr, self.value(note)))
        # 유닛·기술 고유명사(Misha, Spell Shield 등)는 gamestring 에 답이 있다
        if self.fallback:
            hit = self.fallback(stripped)
            if hit:
                return atom.replace(stripped, hit)
        converted = self.units(atom)
        # 단위 치환 후 영문이 남지 않으면 수치 표현이었을 뿐이다
        if not self.RESIDUE.search(converted):
            return converted
        self.unknown[stripped] += 1
        return converted

    def value(self, text):
        return self.units("".join(
            part if self.SPLIT.fullmatch(part) else self.term(part)
            for part in self.SPLIT.split(text)))

    def label(self, key):
        if key in self.labels:
            return self.labels[key]
        # prop1/val1 … 는 위키의 "부가 항목 n / 값 n" 쌍이다
        pair = re.fullmatch(r"(prop|val)(\d+)", key)
        if pair:
            return ("항목" if pair.group(1) == "prop" else "값") + pair.group(2)
        return key


# --------------------------------------------------------------------------
# 빌드
# --------------------------------------------------------------------------
# 위키 편집자가 필드 이름을 잘못 적은 것들. 이름이 어긋나면 읽는 쪽이 못 알아보고
# 값이 통째로 버려지므로, 여기서 제 이름으로 편입시킨다. 같은 이름이 이미 있으면
# 원래 값을 남긴다 - 오타 쪽이 덮어쓰면 멀쩡한 값을 잃는다.
FIELD_TYPOS = {"typer": "type", "taget": "target", "tartget": "target",
               "afects": "affects", "properties": "props", "nohr2": "nohr",
               "pro1": "prop1"}


def fix_field_names(fields, stats):
    """오타 난 필드 이름을 제 이름으로 돌려놓는다."""
    if not any(key in FIELD_TYPOS for key in fields):
        return fields
    out = {}
    for key, value in fields.items():
        proper = FIELD_TYPOS.get(key, key)
        if proper != key:
            stats["field_typo_%s" % key] += 1
            if proper in fields:
                continue          # 제 이름 칸이 이미 차 있으면 그쪽이 맞다
        out[proper] = value
    return out


def localize_entry(entry, wiki_hero, matcher, glossary, stats):
    key, confidence = matcher.match(wiki_hero, entry["name"])
    out = dict(entry)
    out["_match"] = {"key": key, "confidence": confidence}
    stats["name_" + confidence] += 1

    if key:
        suffix = key.split("/", 2)[2]
        namespace = key.rsplit("/", 1)[0]
        out["name_kr"] = matcher.ko.get(key) or entry["name"]

        ko_tip = matcher.ko.get("Button/Tooltip/" + suffix)
        ko_simple = matcher.ko.get("Button/SimpleDisplayText/" + suffix)
        en_tip = matcher.en.get("Button/Tooltip/" + suffix)
        wiki_desc = TAIL.sub("", entry.get("description", "")).strip(" ;")

        if ko_tip:
            text, how = fill(ko_tip, en_tip, wiki_desc)
            if text:
                out["description_kr"], out["_match"]["desc"] = text, how
                stats["desc_" + how] += 1
            elif ko_simple:
                out["description_kr"] = strip_markup(ko_simple)
                out["_match"]["desc"] = "simple-fallback"
                stats["desc_simple-fallback"] += 1
            else:
                stats["desc_failed"] += 1
        elif ko_simple:
            out["description_kr"] = strip_markup(ko_simple)
            out["_match"]["desc"] = "simple"
            stats["desc_simple"] += 1
        else:
            stats["desc_missing"] += 1
        del namespace
    else:
        out["name_kr"] = entry["name"]
        stats["desc_missing"] += 1

    if entry.get("fields"):
        fields = fix_field_names(entry["fields"], stats)
        out["fields"] = fields
        out["fields_kr"] = {
            glossary.label(k): (v if k in PROSE_FIELDS else glossary.value(v))
            for k, v in fields.items()
        }
    return out


def make_noun_lookup(matcher):
    """위키 메타 필드에 등장하는 고유명사(유닛·기술명)를 gamestring 으로 옮긴다.

    용어집에 없고 사람이 옮길 필요도 없는 값들 — Misha, Rexxar, Spell Shield 등 —
    은 이미 게임이 번역해 두었으므로 영문 표기로 되찾아 쓴다.
    """
    def lookup(text):
        keys = matcher.rev.get(normalize(text))
        if not keys and text.endswith("s"):
            keys = matcher.rev.get(normalize(text[:-1]))
        if not keys:
            return None
        values = {matcher.ko.get(k) for k in keys if matcher.ko.get(k)}
        return values.pop() if len(values) == 1 else None
    return lookup


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    print("gamestring 로드 중...")
    en = load_lang(GAMEDATA, "enus")
    ko = load_lang(GAMEDATA, "kokr")
    print("  enus %d개 / kokr %d개 키" % (len(en), len(ko)))

    overrides = {k: v for k, v in json.load(open(OVERRIDES, encoding="utf-8")).items()
                 if not k.startswith("_")}
    matcher = Matcher(en, ko, overrides)
    glossary = Glossary(GLOSSARY, fallback=make_noun_lookup(matcher))
    stats = Counter()
    unmatched = []

    if not only:
        os.makedirs(DST, exist_ok=True)

    files = sorted(f for f in os.listdir(SRC) if f.endswith(".json"))
    for filename in files:
        hero = filename[:-5]
        if only and normalize(hero) != normalize(only):
            continue
        data = json.load(open(os.path.join(SRC, filename), encoding="utf-8"))
        hid = matcher.hero_id(data["hero"])
        data["hero_kr"] = ko.get("Hero/Name/" + hid, data["hero"]) if hid else data["hero"]
        data["hero_id"] = hid
        if not hid:
            stats["hero_id_missing"] += 1

        for section in ("abilities", "talents"):
            data[section] = [
                localize_entry(e, data["hero"], matcher, glossary, stats)
                for e in data.get(section, [])
            ]
            for e in data[section]:
                flag = e["_match"]["confidence"]          # override 는 검수 완료본
                if flag not in ("none", "ambiguous"):
                    flag = e["_match"].get("desc")
                    if flag not in ("by-order", "by-position", "simple-fallback"):
                        continue
                unmatched.append((data["hero"], section, e["name"],
                                  flag, e["_match"]["key"]))

        if only:
            print(json.dumps(data, ensure_ascii=False, indent=1)[:6000])
        else:
            with open(os.path.join(DST, filename), "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=1)

    write_report(stats, unmatched, glossary, len(files))
    print("\n".join("  %-22s %d" % kv for kv in sorted(stats.items())))
    print("리포트: %s" % REPORT)
    if not only:
        print("출력:   %s" % DST)


def write_report(stats, unmatched, glossary, hero_count):
    total = sum(v for k, v in stats.items() if k.startswith("name_"))
    lines = ["# 한글화 빌드 리포트", "",
             "영웅 %d명 / 기술·특성 %d개" % (hero_count, total), "",
             "## 이름 매칭"]
    for level, label in [("override", "수동 지정"), ("hero", "영웅 스코프 확정"), ("unique", "전역 유일"),
                         ("ambiguous", "동명이인 — 검수 필요"), ("none", "미매칭 — 수동 필요")]:
        n = stats.get("name_" + level, 0)
        lines.append("- %s: %d (%.1f%%)" % (label, n, 100 * n / total if total else 0))

    lines += ["", "## 설명문"]
    labels = {"by-ref": "참조 경로로 수치 주입 (정확)",
              "by-position": "영문 자리 순서로 주입 — 검수 권장",
              "aligned": "토큰 정렬로 수치 주입", "by-order": "숫자 순서 폴백 — 검수 권장",
              "no-numbers": "수치 없는 툴팁", "simple": "요약문 사용",
              "simple-fallback": "수치 실패 → 요약문", "insufficient": "수치 부족",
              "missing": "한글 원문 없음", "failed": "실패", "no-en": "영문 툴팁 없음"}
    for key, count in sorted(stats.items()):
        if key.startswith("desc_"):
            kind = key[5:]
            lines.append("- %s: %d (%.1f%%)"
                         % (labels.get(kind, kind), count, 100 * count / total if total else 0))

    lines += ["", "## 용어집 미등록 (메타 필드, 빈도순)", ""]
    if glossary.unknown:
        lines += ["| 원문 | 빈도 |", "|---|---|"]
        lines += ["| %s | %d |" % kv for kv in glossary.unknown.most_common(80)]
        lines.append("")
        lines.append("총 %d종 / 누적 %d건" % (len(glossary.unknown), sum(glossary.unknown.values())))
    else:
        lines.append("없음")

    lines += ["", "## 검수 대상 기술·특성", "", "| 영웅 | 구분 | 이름 | 상태 | 매칭된 키 |", "|---|---|---|---|---|"]
    lines += ["| %s | %s | %s | %s | %s |" % row for row in unmatched]

    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
