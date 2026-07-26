"""HotS gamestring 로더 / 인덱서.

mods/ 아래 흩어진 enus·kokr gamestrings.txt 를 모두 읽어
  - EN: key -> 영문 문자열
  - KO: key -> 한글 문자열
  - 영문 값 -> key 역인덱스 (위키 영문 표기로 내부 키를 찾기 위한 것)
를 만든다.
"""
import glob
import html
import os
import re
from collections import defaultdict

MODS_GLOB = "mods/**/{lang}.stormdata/localizeddata/gamestrings.txt"


def _read(path):
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if not line or line.startswith("//") or "=" not in line:
                continue
            yield line.split("=", 1)


def load_lang(root, lang):
    """mods/ 전체를 훑어 한 언어의 key->value 사전을 만든다."""
    table = {}
    pattern = os.path.join(root, MODS_GLOB.format(lang=lang))
    for path in sorted(glob.glob(pattern, recursive=True)):
        for key, value in _read(path):
            table[key] = value
    return table


def normalize(text):
    """표기 흔들림(공백/아포스트로피/대소문자)을 지운 매칭용 키."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def build_reverse(en, prefixes):
    """영문 값 -> [key] 역인덱스. prefixes 로 대상 네임스페이스를 제한한다."""
    rev = defaultdict(list)
    for key, value in en.items():
        ns = key.rsplit("/", 1)[0] + "/"
        if ns in prefixes:
            rev[normalize(value)].append(key)
    return rev


PLACEHOLDER = ""


def strip_markup(text, placeholder=PLACEHOLDER):
    """<d ref=.../> 수치 참조를 placeholder 로 바꾸고 나머지 태그를 제거한다."""
    text = re.sub(r"<d\s+ref=.*?/>", placeholder, text, flags=re.S)
    text = re.sub(r"<n\s*/>", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = text.replace("%%", "%")   # gamestring 의 퍼센트 이스케이프
    return re.sub(r"[ 	]{2,}", " ", text).strip()


def count_refs(text):
    return len(re.findall(r"<d\s+ref=", text))
