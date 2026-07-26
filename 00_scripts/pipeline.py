"""게임 원본에서 한글화된 백과사전 HTML 까지 한 번에 만든다.

  1 casc      CASC 에서 게임 데이터 XML·게임스트링 추출        -> mods/
  2 herodata  영웅 JSON(en/ko)과 아이콘 이미지 추출            -> image/
  3 analysis  추출물을 영웅별 폴더로 재배치                     -> hots_analysis/
  4 wiki      Fandom 위키 API 수집                             -> hots_ref/output/
  5 profile   XML + 위키를 합쳐 영웅 프로필 생성               -> out/heroes/
  6 build     백과사전 HTML 생성                               -> hots_ref/hots_encyclopedia.html
  7 kr        한글화 + 위키 필드 주입                          -> hots_ref/hots_encyclopedia_wiki.html

1·2 는 CASC 를 내려받고 4 는 위키 API 를 90번 호출한다. 오래 걸리고 바깥에 나가므로
기본으로는 돌리지 않는다. 게임이 패치됐을 때만 --with-download / --with-wiki 를 준다.

  python hots_kr/pipeline.py                   3·5·6·7 (있는 데이터로 다시 빌드)
  python hots_kr/pipeline.py --all             1~7 전부
  python hots_kr/pipeline.py --only 6,7        지정한 단계만
  python hots_kr/pipeline.py --from 5          5단계부터 끝까지
  python hots_kr/pipeline.py --all --dry-run   실행 없이 계획만 출력
"""
import argparse
import glob
import os
import runpy
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ROOT = Path(paths.ROOT)
HOTS_KR = Path(paths.SCRIPTS)
VENDOR = Path(paths.VENDOR)

CASC = Path(paths.CASC)                 # 파서에 -o 로 넘길 폴더 (안에 mods/ 가 생긴다)
MODS = Path(paths.MODS)
IMAGE = Path(paths.HERODATA)
HERODATA_DIR = Path(paths.HERODATA_DIR)
ANALYSIS = Path(paths.ANALYSIS)
ANALYSIS_EN = Path(paths.ANALYSIS_EN)
WIKI_OUT = Path(paths.WIKI)
PROFILE_OUT = Path(paths.PROFILE)
ENCYCLOPEDIA = Path(paths.ENCYCLOPEDIA)
ENCYCLOPEDIA_WORK = Path(paths.ENCYCLOPEDIA_WORK)
LOCALIZED = Path(paths.LOCALIZED)
OUTPUT = Path(paths.OUTPUT)
FINAL = Path(paths.FINAL)
INDEX = Path(paths.INDEX)

PARSER = "dotnet-heroes-data-parser.exe"
DEFAULT_GAME_PATH = r"C:\Program Files (x86)\Heroes of the Storm"

# 게임플레이 XML 과 양쪽 언어 게임스트링만 가져온다.
#
# 파일 이름을 *data.xml 로 좁히면 안 된다. 영웅 정의가 담긴 파일 중에는 garrosh.xml,
# kelthuzad.xml 처럼 data 로 끝나지 않는 것이 있어서 그 두 영웅이 통째로 빠진다.
# core 의 기본값 XML 도 있어야 프로필 파서가 상속값을 풀 수 있다.
CASC_INCLUDES = [
    "mods/core.stormmod/base.stormdata/GameData/*.xml",
    "mods/heromods/*.stormmod/base.stormdata/GameData/*.xml",
    "mods/heroesdata.stormmod/base.stormdata/GameData/Heroes/*/*.xml",
    # 여러 영웅이 나눠 쓰는 정의(블록, 넥서스의 칼날, 되감기, 지게로봇 …)는
    # 영웅별 폴더가 아니라 이 최상위 GameData 에 들어 있다. Heroes/ 만 긁으면
    # abildata·talentdata·buttondata 를 통째로 놓친다.
    "mods/heroesdata.stormmod/base.stormdata/GameData/*.xml",
    "mods/core.stormmod/koKR.stormdata/LocalizedData/GameStrings.txt",
    "mods/core.stormmod/enUS.stormdata/LocalizedData/GameStrings.txt",
    "mods/heromods/*.stormmod/koKR.stormdata/LocalizedData/GameStrings.txt",
    "mods/heromods/*.stormmod/enUS.stormdata/LocalizedData/GameStrings.txt",
    "mods/heroesdata.stormmod/koKR.stormdata/LocalizedData/GameStrings.txt",
    "mods/heroesdata.stormmod/enUS.stormdata/LocalizedData/GameStrings.txt",
]

DOWNLOAD_STEPS = {"casc", "herodata"}
NETWORK_STEPS = DOWNLOAD_STEPS | {"wiki"}


class Skip(Exception):
    """이 단계는 할 일이 없다 - 실패가 아니다."""


# --------------------------------------------------------------------------
# 실행 도우미
# --------------------------------------------------------------------------
class Runner:
    def __init__(self, dry_run):
        self.dry_run = dry_run

    def command(self, args, cwd=None):
        printable = " ".join('"%s"' % a if " " in str(a) else str(a) for a in args)
        print("    $ %s" % printable)
        if self.dry_run:
            return
        result = subprocess.run([str(a) for a in args], cwd=str(cwd or ROOT))
        if result.returncode != 0:
            raise SystemExit("  실패 (종료 코드 %d)" % result.returncode)

    def require(self, path, produced_by):
        """앞 단계 산출물이 있는지 본다. 계획만 볼 때는 아직 없는 게 정상이다."""
        if Path(path).exists():
            return
        if self.dry_run:
            print("    (아직 없음: %s - %s 단계가 만든다)" % (path, produced_by))
            return
        raise SystemExit("  입력이 없습니다: %s\n  -> %s 단계를 먼저 돌리세요."
                         % (path, produced_by))

    def script(self, path, argv, cwd=None):
        """스크립트를 같은 프로세스에서 실행한다.

        cwd 를 주면 그 폴더에서 돌린다 - 산출물을 현재 폴더에 쓰는 스크립트가 있다.
        """
        print("    $ python %s %s" % (Path(path).name, " ".join(str(a) for a in argv)))
        if self.dry_run:
            return
        saved_argv, saved_cwd = sys.argv[:], os.getcwd()
        sys.argv = [str(path)] + [str(a) for a in argv]
        if cwd:
            Path(cwd).mkdir(parents=True, exist_ok=True)
            os.chdir(str(cwd))
        try:
            runpy.run_path(str(path), run_name="__main__")
        finally:
            sys.argv = saved_argv
            os.chdir(saved_cwd)


def newest(pattern):
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return Path(matches[0]) if matches else None


def require(path, produced_by):
    if not Path(path).exists():
        raise SystemExit(
            "  입력이 없습니다: %s\n  -> %s 단계를 먼저 돌리세요." % (path, produced_by))


# --------------------------------------------------------------------------
# 각 단계
# --------------------------------------------------------------------------
def step_casc(run, args):
    """CASC 에서 게임 데이터 XML 과 양쪽 언어 게임스트링을 꺼낸다."""
    command = [PARSER, "casc-extract", args.storage, "-o", CASC]
    if args.storage == "game":
        command += ["-s", args.game_path]
    for pattern in CASC_INCLUDES:
        command += ["-i", pattern]
    run.command(command)


def step_herodata(run, args):
    """영웅 JSON(en/ko)과 아이콘·초상화 이미지를 꺼낸다.

    casc-extract 는 원본 파일만 꺼내므로 herodata JSON 은 나오지 않는다.
    JSON 과 이미지는 최상위 명령의 Hero 추출기가 만든다.
    """
    # 백과사전 템플릿은 "184 (+4% per level)" 꼴을 정규식으로 읽어 레벨별 수치를
    # 다시 계산한다. 기본 RawText 로 뽑으면 그 문구가 없어 성장 표기가 죽는다.
    command = [PARSER, args.storage,
               "-e", "Hero" if args.no_images else "Hero:images",
               "-l", "enUS", "-l", "koKR",
               "-g", "ColoredTextWithScaling", "--gs-replace-constant-vars",
               "-o", IMAGE]
    if args.storage == "game":
        command += ["-s", args.game_path]
    run.command(command)


def step_analysis(run, args):
    """추출한 mods/ 를 영웅별 폴더 구조로 재배치한다.

    두 가지를 만든다. 앞은 뒤 단계가 읽는 것이고, 뒤는 사람이 열어보는 것이다.
      <로케일>/  원본 구조를 살린 영웅별 폴더 - 이후 단계가 이걸 읽는다
      _by_hero/ 영웅당 대표 XML 한 장, _merged/ 게임스트링 통합본
    """
    run.require(MODS, "casc")
    for locale, out in (("kokr", ANALYSIS), ("enus", ANALYSIS_EN)):
        run.script(VENDOR / "collect_hero_data.py", [MODS, out, locale])
    run.script(HOTS_KR / "collect_xml.py", [])


def step_wiki(run, args):
    """Fandom 위키 API 로 스킬·특성 원문을 수집한다."""
    run.script(VENDOR / "hots_ability_scraper.py",
               ["--all", "--delay", args.delay, "--out", WIKI_OUT])


def step_profile(run, args):
    """XML 과 위키 수집분을 합쳐 영웅 프로필 JSON 을 만든다."""
    run.require(ANALYSIS, "analysis")
    run.require(WIKI_OUT / "all_heroes.json", "wiki")
    run.script(VENDOR / "hots_hero_parser.py",
               [ANALYSIS, WIKI_OUT / "all_heroes.json", PROFILE_OUT])


def step_build(run, args):
    """백과사전 HTML 을 생성한다.

    생성기(make_encyclopedia.py)는 구형 HDP 스키마를 기대하므로 5.x 출력을 먼저
    옮긴 뒤, 작업 폴더를 현재 디렉터리로 삼아 돌린다. 생성기는 이름이 정해진
    파일을 CWD 에 쓰기 때문이다.
    """
    english = newest(str(HERODATA_DIR / "herodata_*enus.json"))
    korean = newest(str(HERODATA_DIR / "herodata_*kokr.json"))
    if not (english and korean):
        if not run.dry_run:
            raise SystemExit("  herodata en/ko JSON 이 모두 필요합니다 "
                             "-> herodata 단계를 돌리세요.")
        english = english or HERODATA_DIR / "herodata_<빌드>_enus.json"
        korean = korean or HERODATA_DIR / "herodata_<빌드>_kokr.json"

    work = ENCYCLOPEDIA_WORK
    for source in (english, korean):
        run.script(HOTS_KR / "adapt_herodata.py",
                   [source, work / Path(source).name])

    run.script(VENDOR / "make_encyclopedia.py", [], cwd=work)

    if not run.dry_run:
        if ENCYCLOPEDIA.exists():
            backup = ENCYCLOPEDIA.with_suffix(".html.bak")
            shutil.copy2(ENCYCLOPEDIA, backup)
            print("    직전 파일 백업: %s" % backup.name)
        shutil.copy2(work / "hots_encyclopedia.html", ENCYCLOPEDIA)
        print("    -> %s (%.1f MB)"
              % (ENCYCLOPEDIA, ENCYCLOPEDIA.stat().st_size / 1048576))


def step_kr(run, args):
    """게임스트링으로 한글화하고 위키 필드를 백과사전에 심는다."""
    run.require(ENCYCLOPEDIA, "build")
    run.require(MODS, "casc")
    for script in ("localize.py", "build_wiki_fields.py",
                   "build_attack_types.py", "build_glossary.py",
                   "inject_wiki.py", "build_index.py"):
        run.script(HOTS_KR / script, [])


def preflight(plan, args):
    """돌리기 전에 필요한 게 다 있는지 본다. 30분짜리 작업이 중간에 죽지 않도록."""
    problems, notes = [], []

    if set(plan) & DOWNLOAD_STEPS:
        if not shutil.which(PARSER):
            problems.append("%s 를 PATH 에서 찾지 못했습니다." % PARSER)
        else:
            notes.append("파서: %s" % shutil.which(PARSER))
        if args.storage == "game" and not Path(args.game_path).is_dir():
            problems.append("게임 폴더가 없습니다: %s" % args.game_path)
        notes.append("추출 원본: %s%s" % (
            args.storage, "" if args.storage == "online" else " (%s)" % args.game_path))

    if "wiki" in plan:
        try:
            import requests  # noqa: F401
        except ImportError:
            problems.append("위키 수집에 requests 가 필요합니다: pip install requests")

    needed = {"analysis": ["collect_hero_data.py"], "wiki": ["hots_ability_scraper.py"],
              "profile": ["hots_hero_parser.py"], "build": ["make_encyclopedia.py"]}
    for step, files in needed.items():
        if step not in plan:
            continue
        for name in files:
            if not (VENDOR / name).is_file():
                problems.append("스크립트가 없습니다: hots_kr/vendor/%s" % name)

    # 앞 단계를 함께 돌지 않으면서 그 산출물도 없는 경우
    inputs = [("analysis", MODS, "casc"), ("profile", ANALYSIS, "analysis"),
              ("profile", WIKI_OUT / "all_heroes.json", "wiki"),
              ("build", PROFILE_OUT / "heroes", "profile"),
              ("kr", ENCYCLOPEDIA, "build"), ("kr", MODS, "casc")]
    for step, path, source in inputs:
        if step in plan and source not in plan and not Path(path).exists():
            problems.append("%s 단계 입력이 없습니다: %s (%s 단계가 만듭니다)"
                            % (step, path, source))
    if "build" in plan and "herodata" not in plan:
        if not (newest(str(HERODATA_DIR / "herodata_*enus.json"))
                and newest(str(HERODATA_DIR / "herodata_*kokr.json"))):
            problems.append("build 단계에 herodata en/ko JSON 이 둘 다 필요합니다.")

    for note in notes:
        print("  %s" % note)
    if problems:
        print("\n준비되지 않았습니다:")
        for problem in problems:
            print("  - %s" % problem)
        raise SystemExit(1)
    print("  준비 완료.")


def step_verify(run, args):
    """마지막 점검. 백과사전이 내보내는 수치를 게임 XML 과 맞대 본다.

    앞 단계들의 숫자는 대부분 위키에서 온 것이라 패치를 놓쳤을 수 있다. 여기서
    걸린 값은 틀렸다는 뜻이 아니라 사람이 한 번 봐야 한다는 뜻이다.
    """
    run.require(MODS, "casc")
    run.require(paths.WIKI_FIELDS, "kr")
    run.script(HOTS_KR / "verify_xml.py", [])


STEPS = [
    ("casc", step_casc, "CASC 에서 XML·게임스트링 추출"),
    ("herodata", step_herodata, "영웅 JSON(en/ko)·이미지 추출"),
    ("analysis", step_analysis, "영웅별 폴더로 재배치"),
    ("wiki", step_wiki, "Fandom 위키 수집"),
    ("profile", step_profile, "XML+위키 -> 영웅 프로필"),
    ("build", step_build, "백과사전 HTML 생성"),
    ("kr", step_kr, "한글화 + 위키 필드 주입"),
    ("verify", step_verify, "게임 XML 과 수치 대조"),
]
NAMES = [name for name, _, _ in STEPS]


def selected(args):
    if args.only:
        wanted = parse_list(args.only)
    elif getattr(args, "from_step", None):
        start = resolve(args.from_step)
        wanted = NAMES[NAMES.index(start):]
    elif args.all:
        wanted = list(NAMES)
    else:
        wanted = [n for n in NAMES if n not in NETWORK_STEPS]
        if args.with_download:
            wanted = [n for n in NAMES if n in DOWNLOAD_STEPS or n in wanted]
        if args.with_wiki:
            wanted = [n for n in NAMES if n == "wiki" or n in wanted]
    return [n for n in NAMES if n in set(wanted) - set(parse_list(args.skip))]


def resolve(token):
    token = token.strip()
    if token.isdigit():
        index = int(token) - 1
        if not 0 <= index < len(NAMES):
            raise SystemExit("단계 번호는 1~%d 입니다: %s" % (len(NAMES), token))
        return NAMES[index]
    if token not in NAMES:
        raise SystemExit("모르는 단계입니다: %s (%s)" % (token, ", ".join(NAMES)))
    return token


def parse_list(value):
    return [resolve(t) for t in value.split(",")] if value else []


def main():
    # 콘솔이 cp949 라 Lúcio 같은 이름에서 출력이 터진다. 로그 한 줄 때문에
    # 파이프라인 전체가 멈추면 안 되므로 못 쓰는 글자는 대체 문자로 흘린다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(
        description="히오스 백과사전 빌드 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="단계: " + "  ".join("%d.%s" % (i + 1, n) for i, n in enumerate(NAMES)))
    parser.add_argument("--all", action="store_true", help="1~7 전부 실행")
    parser.add_argument("--only", help="지정한 단계만 (번호 또는 이름, 쉼표 구분)")
    parser.add_argument("--from", dest="from_step", help="이 단계부터 끝까지")
    parser.add_argument("--skip", help="제외할 단계")
    parser.add_argument("--with-download", action="store_true",
                        help="CASC·herodata 추출 포함 (네트워크)")
    parser.add_argument("--with-wiki", action="store_true",
                        help="위키 수집 포함 (네트워크)")
    parser.add_argument("--storage", choices=("online", "game"),
                        help="추출 원본. 기본은 게임이 설치돼 있으면 game, 아니면 online")
    parser.add_argument("--game-path", default=DEFAULT_GAME_PATH)
    parser.add_argument("--no-images", action="store_true",
                        help="herodata 단계에서 아이콘·초상화는 건너뛰고 JSON 만")
    parser.add_argument("--delay", default="1.5", help="위키 API 요청 간 딜레이(초)")
    parser.add_argument("--dry-run", action="store_true", help="실행 없이 계획만 출력")
    parser.add_argument("--open", action="store_true",
                        help="다 만들고 나서 메인 페이지를 브라우저로 연다")
    parser.add_argument("--check", action="store_true",
                        help="필요한 도구·입력이 다 있는지만 확인하고 끝낸다")
    args = parser.parse_args()
    if not args.storage:
        args.storage = "game" if Path(args.game_path).is_dir() else "online"

    plan = selected(args)
    if not plan:
        raise SystemExit("실행할 단계가 없습니다.")

    print("실행 계획: " + " -> ".join(plan))
    preflight(plan, args)
    if args.check:
        return
    if args.dry_run:
        print("(--dry-run: 실제로는 실행하지 않습니다)")

    run = Runner(args.dry_run)
    if not args.dry_run:
        # 빈 폴더에서 시작해도 돌아가야 한다. 각 단계가 결과를 쓸 자리를 미리 판다.
        for folder in (CASC, IMAGE, WIKI_OUT, PROFILE_OUT,
                       ENCYCLOPEDIA.parent, LOCALIZED, OUTPUT):
            folder.mkdir(parents=True, exist_ok=True)
    started = time.time()
    for index, (name, function, label) in enumerate(STEPS, 1):
        if name not in plan:
            continue
        print("\n[%d/%d] %s - %s" % (index, len(STEPS), name, label))
        mark = time.time()
        try:
            function(run, args)
        except Skip as reason:
            print("    건너뜀: %s" % reason)
            continue
        print("    %.1f초" % (time.time() - mark))

    print("\n전체 %.1f초" % (time.time() - started))
    if "kr" in plan and not args.dry_run:
        # 백과사전이 아니라 index 를 알려 준다. 거기가 들어가는 문이다.
        print("결과: %s" % INDEX)
        if args.open:
            webbrowser.open(Path(INDEX).resolve().as_uri())


if __name__ == "__main__":
    main()
