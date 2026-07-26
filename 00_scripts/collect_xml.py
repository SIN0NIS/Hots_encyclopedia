# -*- coding: utf-8 -*-
"""영웅별 대표 XML 을 한 폴더에 모으고, 흩어진 게임스트링을 한 파일로 합친다.

3단계(영웅별로 다시 묶기)의 두 번째 작업이다. collect_hero_data.py 가 원본 폴더
구조를 그대로 살려 영웅별 폴더를 만든다면, 이쪽은 **사람이 열어보기 좋은 형태**를
만든다.

  _by_hero/<영웅>.xml            영웅당 대표 XML 한 장
  _merged/gamestrings_<로케일>.txt  흩어진 게임스트링을 합친 한 파일

구·신 영웅이 서로 다른 경로 구조를 쓴다. 경로를 박아두지 않고 폴더 이름만 보고
가른다.

  (구) mods/heroesdata.stormmod/base.stormdata/gamedata/heroes/abathurdata/abathurdata.xml
  (신) mods/heromods/alarak.stormmod/base.stormdata/gamedata/alarakdata.xml

두 구조 모두 "영웅 이름" 또는 "영웅 이름 + data" 라는 파일 하나에 그 영웅의 정의가
거의 다 들어 있다. 나머지(gamedata·lightdata·sounddata …)는 화면·소리 쪽이라
_by_hero 에는 담지 않고 왜 뺐는지만 로그에 남긴다 — 판단 근거를 남겨야 나중에
"이건 왜 없지" 를 다시 파헤치지 않는다.

  python 00_scripts/collect_xml.py                 기본 경로로 실행
  python 00_scripts/collect_xml.py --dry-run       무엇이 처리될지만 확인
"""
import argparse
import csv
import os
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

BY_HERO = "_by_hero"
MERGED = "_merged"
LOCALES = ("kokr", "enus")


def hero_xml_files(root):
    """게임 데이터 XML 만 고른다.

    경로에 gamedata 폴더가 있어야 한다. 이 조건 하나로 localizeddata 쪽
    (게임스트링·자막)이 통째로 걸러진다.
    """
    return [p for p in root.rglob("*.xml")
            if "gamedata" in [part.lower() for part in p.parts]]


def stormmod_name(xml_path):
    """경로에서 가장 안쪽 .stormmod 폴더의 이름. 없으면 None."""
    name = None
    for part in xml_path.parts:
        if part.lower().endswith(".stormmod"):
            name = part[: -len(".stormmod")]
    return name


def folder_id(xml_path):
    """이 XML 이 어느 영웅 몫인지 나타내는 폴더 단위 이름.

    heroes/abathurdata/…      -> abathurdata
    heroes/common/…           -> common
    heromods/alarak.stormmod/ -> alarak
    """
    lower = [part.lower() for part in xml_path.parts]
    if "heroes" in lower:
        at = lower.index("heroes")
        if at + 1 < len(xml_path.parts) - 1:
            return xml_path.parts[at + 1]
        return xml_path.stem
    return stormmod_name(xml_path) or xml_path.parent.name


def base_name(name):
    """끝의 data 를 뗀 영웅 기본명. abathurdata -> abathur, alarak -> alarak"""
    if name.lower().endswith("data") and len(name) > 4:
        return name[:-4]
    return name


def is_hero_file(xml_path, base):
    """파일 이름이 <영웅> 또는 <영웅>data 인지. 대소문자는 보지 않는다."""
    stem = xml_path.stem.lower()
    return stem in (base.lower(), (base + "data").lower())


def collect_xml(root, out_dir, dry_run):
    """영웅당 대표 XML 한 장씩 _by_hero/ 에 모은다."""
    candidates = hero_xml_files(root)
    dest_dir = out_dir / BY_HERO
    taken, dropped = [], []

    for xml_path in candidates:
        base = base_name(folder_id(xml_path))
        if is_hero_file(xml_path, base):
            taken.append((base, xml_path))
        else:
            dropped.append({
                "source_path": str(xml_path.relative_to(root)),
                "folder_id": folder_id(xml_path),
                "expected_names": "%s.xml / %sdata.xml" % (base, base),
                "reason": "파일 이름이 영웅 이름과 다름",
            })

    groups = defaultdict(list)
    for base, xml_path in taken:
        groups[base].append(xml_path)

    if not dry_run:
        # auto 폴더는 매번 통째로 다시 만든다. 남아 있던 파일이 섞이면 지난 패치의
        # 영웅이 유령처럼 남는다.
        shutil.rmtree(dest_dir, ignore_errors=True)
        dest_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for hero, found in sorted(groups.items()):
        # 같은 영웅에 <영웅>.xml 과 <영웅>data.xml 이 둘 다 있으면 이름을 갈라 둔다
        many = len(found) > 1
        for xml_path in sorted(found):
            dest = dest_dir / ("%s__%s" % (hero, xml_path.name) if many
                               else "%s.xml" % hero)
            rows.append({"hero": hero,
                         "source_path": str(xml_path.relative_to(root)),
                         "dest_path": str(dest.name),
                         "size_bytes": xml_path.stat().st_size})
            if not dry_run:
                shutil.copy2(xml_path, dest)

    if not dry_run:
        write_csv(out_dir / MERGED / "xml_collect_log.csv", rows,
                  ["hero", "source_path", "dest_path", "size_bytes"])
        write_csv(out_dir / MERGED / "xml_excluded_log.csv", dropped,
                  ["source_path", "folder_id", "expected_names", "reason"])

    print("  XML: 후보 %d개 -> 영웅 %d명 %d개 수집, %d개는 영웅 파일이 아니라 제외"
          % (len(candidates), len(groups), len(rows), len(dropped)))
    return rows


LOCALE_DIR = re.compile(r"^([a-zA-Z]{4})\.stormdata$")


def locale_of(path):
    """경로 안의 kokr.stormdata / enus.stormdata 에서 로케일 코드를 읽는다."""
    for part in path.parts:
        found = LOCALE_DIR.match(part)
        if found:
            return found.group(1).lower()
    return None


def read_strings(path):
    """게임스트링 한 파일을 {키: 값} 으로 읽는다.

    값 안에도 = 가 들어가므로 첫 번째 것만 구분자로 쓴다. BOM 이 여러 겹
    붙어 있는 파일이 있어 모두 걷어낸다.
    """
    raw = path.read_bytes()
    while raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    out = {}
    for line in raw.decode("utf-8", errors="replace").splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            out[key] = value
    return out


def merge_strings(root, out_dir, locale, dry_run):
    """로케일 하나의 게임스트링을 전부 합친다. 어느 파일이 이겼는지도 남긴다."""
    files = [p for p in root.rglob("gamestrings.txt") if locale_of(p) == locale]

    # core 를 먼저 깔고 영웅별 파일로 덮는다. 영웅별 쪽이 더 구체적이고 최신이다.
    def order(path):
        return (0 if "core" in [x.lower() for x in path.parts] else 1, str(path))

    merged, came_from, clashes, log = {}, {}, [], []
    for index, path in enumerate(sorted(files, key=order), start=1):
        entries = read_strings(path)
        fresh = beaten = 0
        for key, value in entries.items():
            if key in merged:
                if merged[key] != value:
                    clashes.append({
                        "key": key,
                        "old_value": merged[key],
                        "old_source": str(came_from[key].relative_to(root)),
                        "new_value": value,
                        "new_source": str(path.relative_to(root)),
                    })
                    beaten += 1
            else:
                fresh += 1
            merged[key] = value
            came_from[key] = path
        log.append({"order": index, "source_path": str(path.relative_to(root)),
                    "key_count_in_file": len(entries),
                    "new_keys_added": fresh, "keys_overwritten": beaten})

    if not dry_run:
        target = out_dir / MERGED
        target.mkdir(parents=True, exist_ok=True)
        with open(target / ("gamestrings_%s.txt" % locale), "w",
                  encoding="utf-8-sig", newline="\r\n") as fh:
            for key in sorted(merged):
                fh.write("%s=%s\n" % (key, merged[key]))
        write_csv(target / ("gamestrings_%s_sources.csv" % locale), log,
                  ["order", "source_path", "key_count_in_file",
                   "new_keys_added", "keys_overwritten"])
        if clashes:
            write_csv(target / ("gamestrings_%s_conflicts.csv" % locale), clashes,
                      ["key", "old_value", "old_source", "new_value", "new_source"])

    print("  게임스트링(%s): 파일 %d개 -> 키 %d개, 값이 엇갈린 키 %d개"
          % (locale, len(files), len(merged), len(clashes)))
    return merged


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig 로 써야 엑셀에서 한글이 깨지지 않는다
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="영웅별 대표 XML 수집 + 게임스트링 병합")
    parser.add_argument("--root", default=paths.MODS,
                        help="뒤질 mods 폴더 (기본: 1단계 추출물)")
    parser.add_argument("--out", default=paths.ANALYSIS_ROOT,
                        help="결과를 둘 폴더 (기본: 3단계 폴더)")
    parser.add_argument("--dry-run", action="store_true",
                        help="파일을 쓰지 않고 무엇이 처리될지만 본다")
    args = parser.parse_args()

    root, out_dir = Path(args.root).resolve(), Path(args.out).resolve()
    if not root.exists():
        raise SystemExit("mods 폴더가 없습니다: %s\n  -> casc 단계를 먼저 돌리세요." % root)

    collect_xml(root, out_dir, args.dry_run)
    for locale in LOCALES:
        merge_strings(root, out_dir, locale, args.dry_run)
    if not args.dry_run:
        print("-> %s" % (out_dir / BY_HERO))
        print("-> %s" % (out_dir / MERGED))


if __name__ == "__main__":
    main()
