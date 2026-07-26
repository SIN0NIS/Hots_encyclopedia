"""파이프라인이 쓰는 모든 경로를 한 곳에서 정한다.

폴더 이름 앞의 숫자는 파이프라인 단계 번호다. 탐색기에서 위에서 아래로 읽으면
데이터가 흘러간 순서 그대로다.

  00_manual/            손으로 관리하는 파일 (빌드가 읽기만 한다)
  00_scripts/           실행 코드 (이 파일이 있는 곳)
  01_auto_casc/         게임 XML·게임스트링 원본
  02_auto_herodata/     영웅 JSON(en/ko)·아이콘
  03_auto_analysis/     영웅별로 다시 묶은 XML
  04_auto_wiki/         Fandom 위키 수집분
  05_auto_profile/      XML+위키를 합친 영웅 프로필
  06_auto_encyclopedia/ 백과사전 생성 작업물
  07_auto_localized/    한글화 결과와 리포트
  output/               최종 결과물 (이것만 보면 된다)

  auto 가 붙은 폴더는 빌드가 매번 통째로 다시 만든다. 손댈 곳은 00_manual 뿐이다.

옛 구조(mods/, image/, hots_ref/ 가 최상위에 흩어져 있는 형태)도 그대로 읽는다.
새 폴더가 없고 옛 폴더가 있으면 그쪽을 쓴다.
"""
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
VENDOR = os.path.join(SCRIPTS, "vendor")


def _pick(new, old):
    """새 구조를 기본으로 하되, 옛 폴더만 있으면 그쪽을 쓴다."""
    new_path = os.path.join(ROOT, *new)
    old_path = os.path.join(ROOT, *old)
    if not os.path.exists(new_path) and os.path.exists(old_path):
        return old_path
    return new_path


# 1. CASC 추출물. 파서가 -o 아래에 mods/ 를 만들므로 그 부모를 넘겨야 한다.
CASC = _pick(("01_auto_casc",), ())
MODS = os.path.join(CASC, "mods")

# 2. 영웅 JSON 과 이미지. 파서가 -o 아래에 data/ 와 images/ 를 만든다.
HERODATA = _pick(("02_auto_herodata",), ("image",))
HERODATA_DIR = os.path.join(HERODATA, "data")

# 3. 영웅별로 다시 묶은 XML (언어별로 하나씩)
ANALYSIS_ROOT = _pick(("03_auto_analysis",), ())
ANALYSIS = _pick(("03_auto_analysis", "kokr"), ("hots_analysis",))
ANALYSIS_EN = _pick(("03_auto_analysis", "enus"), ("hots_analysis_en",))
# 같은 3단계에서 사람이 열어보라고 따로 만드는 것들
BY_HERO = os.path.join(ANALYSIS_ROOT, "_by_hero")          # 영웅당 XML 한 장
MERGED = os.path.join(ANALYSIS_ROOT, "_merged")            # 게임스트링 통합본·로그

# 4. 위키 수집분
WIKI = _pick(("04_auto_wiki",), ("hots_ref", "output"))
WIKI_HEROES = os.path.join(WIKI, "heroes")
WIKI_ALL = os.path.join(WIKI, "all_heroes.json")

# 5. 영웅 프로필
PROFILE = _pick(("05_auto_profile",), ("out",))
PROFILE_HEROES = os.path.join(PROFILE, "heroes")

# 6. 백과사전
ENCYCLOPEDIA_DIR = _pick(("06_auto_encyclopedia",), ("hots_ref",))
ENCYCLOPEDIA = os.path.join(ENCYCLOPEDIA_DIR, "hots_encyclopedia.html")
ENCYCLOPEDIA_WORK = os.path.join(ENCYCLOPEDIA_DIR, "work")

# 7. 한글화 결과
LOCALIZED = _pick(("07_auto_localized",), ("hots_ref", "output"))
HEROES_KR = os.path.join(LOCALIZED, "heroes_kr")
WIKI_FIELDS = os.path.join(LOCALIZED, "wiki_fields.json")
ATTACK_TYPES = os.path.join(LOCALIZED, "attack_types.json")
REPORT = os.path.join(LOCALIZED, "report.md")

# 8. 최종 결과물. 이 폴더에는 완성된 HTML 만 둔다.
OUTPUT = _pick(("output",), ("hots_ref",))
FINAL = os.path.join(OUTPUT, "hots_encyclopedia_wiki.html")
# 사람이 처음 여는 문. 여기서 백과사전·용어집·바깥 사이트로 갈라진다.
INDEX = os.path.join(OUTPUT, "index.html")

# 사람이 손으로 관리하는 파일. 파이프라인은 읽기만 하고 절대 덮어쓰지 않으므로
# 게임이 패치돼도 여기 적은 것은 그대로 남는다. 폴더를 따로 둔 이유가 그것이다.
CUSTOM = _pick(("00_manual",), ("hots_kr", "custom"))
GLOSSARY = os.path.join(CUSTOM, "glossary.json")
OVERRIDES = os.path.join(CUSTOM, "name_overrides.json")
PASSIVE_FLAGS = os.path.join(CUSTOM, "passive_flags.json")
AOE_OVERRIDES = os.path.join(CUSTOM, "aoe_overrides.json")
SETTINGS = os.path.join(CUSTOM, "settings.json")


def settings():
    """빌드 설정을 읽는다. 없으면 빈 사전 - 부르는 쪽이 기본값을 갖는다."""
    import json
    if not os.path.isfile(SETTINGS):
        return {}
    return json.load(open(SETTINGS, encoding="utf-8"))

# 게임 XML 을 찾을 곳. 앞에서부터 있는 대로 모두 읽는다.
XML_SOURCES = [
    os.path.join(ANALYSIS, "heroes", "*", "*.xml"),
    os.path.join(ANALYSIS, "_core", "*.xml"),
    os.path.join(ROOT, "hots_xml", "*.xml"),
]
