# -*- coding: utf-8 -*-
"""
히오스 영웅 데이터 수집 스크립트
사용법:  python collect_hero_data.py
  MODS_DIR 와 OUT_DIR 경로만 본인 환경에 맞게 수정하세요.

결과 구조:
  hots_analysis/
    _core/                     공용 기본값 XML (core + heroesdata 루트)
    _strings/
      core_gamestrings.txt
      heroesdata_gamestrings.txt      (구형 영웅 47명 공용)
      <영웅>_gamestrings.txt          (신형 영웅 개별)
    heroes/
      abathur/abathurdata.xml ...     (스킨/사운드 제외한 게임플레이 XML만)
      alarak/alarakdata.xml ...
    manifest.csv               수집된 파일 목록
"""
import shutil, csv, sys
from pathlib import Path

# ===== 경로 설정 =====
# pipeline.py 가 인자로 넘긴다.  사용법: collect_hero_data.py <mods> <out> [locale]
# 인자 없이 단독 실행하면 아래 기본값을 쓴다.
_ROOT = Path(__file__).resolve().parent.parent.parent
MODS_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else _ROOT / "mods"
OUT_DIR  = Path(sys.argv[2]) if len(sys.argv) > 2 else _ROOT / "hots_analysis"
LOCALE   = sys.argv[3] if len(sys.argv) > 3 else "kokr"   # 영어 원문은 "enus"

# 스킨/음성 등 게임플레이와 무관한 하위 폴더 제외 패턴
SKIP_DIR_KEYWORDS = ("skindata", "sounddata", "vodata", "vosounddata")

manifest = []

def copy_file(src: Path, dst: Path, category: str):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    manifest.append((category, str(src.relative_to(MODS_DIR)), str(dst.relative_to(OUT_DIR))))

def is_gameplay_xml(p: Path, base: Path) -> bool:
    """base 바로 아래(깊이 1)의 xml만 수집, 스킨/사운드 하위폴더 제외"""
    rel_parts = p.relative_to(base).parts
    if len(rel_parts) != 1:            # 하위 폴더 안이면 제외
        return False
    return p.suffix.lower() == ".xml"

def collect_hero_folder(gamedata_dir: Path, hero_name: str):
    """영웅 gamedata 폴더에서 게임플레이 XML 수집"""
    if not gamedata_dir.is_dir():
        print(f"  [경고] 없음: {gamedata_dir}")
        return
    n = 0
    for p in sorted(gamedata_dir.glob("*.xml")):
        copy_file(p, OUT_DIR / "heroes" / hero_name / p.name.lower(), f"hero:{hero_name}")
        n += 1
    # 일부 영웅은 게임플레이 XML이 하위 폴더에 더 있을 수 있음 → 스킨/사운드 아닌 폴더만 추가 탐색
    for sub in gamedata_dir.iterdir():
        if sub.is_dir() and not any(k in sub.name.lower() for k in SKIP_DIR_KEYWORDS):
            for p in sorted(sub.rglob("*.xml")):
                if any(k in str(p).lower() for k in SKIP_DIR_KEYWORDS):
                    continue
                copy_file(p, OUT_DIR / "heroes" / hero_name / p.name.lower(), f"hero:{hero_name}")
                n += 1
    print(f"  {hero_name}: XML {n}개")

def main():
    assert MODS_DIR.is_dir(), f"MODS_DIR 경로 확인 필요: {MODS_DIR}"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ---------- 1) 공용 기본값 ----------
    print("[1/4] 공용 기본값 XML")
    core_gd = MODS_DIR / "core.stormmod" / "base.stormdata" / "gamedata"
    for p in sorted(core_gd.glob("*.xml")):
        copy_file(p, OUT_DIR / "_core" / f"core_{p.name.lower()}", "core")
    hd_gd = MODS_DIR / "heroesdata.stormmod" / "base.stormdata" / "gamedata"
    for p in sorted(hd_gd.glob("*.xml")):
        copy_file(p, OUT_DIR / "_core" / f"heroesdata_{p.name.lower()}", "shared")

    # ---------- 2) 구형 영웅 47명 ----------
    print("[2/4] 구형 영웅 (heroesdata.stormmod)")
    heroes_root = hd_gd / "heroes"
    for hero_dir in sorted(heroes_root.iterdir()):
        if hero_dir.is_dir():
            name = hero_dir.name.lower().removesuffix("data")
            collect_hero_folder(hero_dir, name)

    # ---------- 3) 신형 영웅 (heromods) ----------
    print("[3/4] 신형 영웅 (heromods)")
    heromods = MODS_DIR / "heromods"
    for mod_dir in sorted(heromods.glob("*.stormmod")):
        name = mod_dir.name.removesuffix(".stormmod").lower()
        if name == "herointeractions":   # 영웅 아님
            continue
        gd = mod_dir / "base.stormdata" / "gamedata"
        collect_hero_folder(gd, name)
        # 신형 영웅은 GameStrings 가 mod별로 존재
        gs = mod_dir / f"{LOCALE}.stormdata" / "localizeddata" / "gamestrings.txt"
        if gs.is_file():
            copy_file(gs, OUT_DIR / "_strings" / f"{name}_gamestrings.txt", "strings")

    # ---------- 4) 공용 GameStrings ----------
    print("[4/4] 공용 GameStrings")
    for mod, label in [("core.stormmod", "core"), ("heroesdata.stormmod", "heroesdata"),
                       ("heroes.stormmod", "heroes")]:
        gs = MODS_DIR / mod / f"{LOCALE}.stormdata" / "localizeddata" / "gamestrings.txt"
        if gs.is_file():
            copy_file(gs, OUT_DIR / "_strings" / f"{label}_gamestrings.txt", "strings")
        else:
            print(f"  [참고] 없음: {gs}")

    # manifest 저장
    with open(OUT_DIR / "manifest.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["category", "source", "dest"])
        w.writerows(manifest)

    print(f"\n완료: 총 {len(manifest)}개 파일 → {OUT_DIR}")
    print("manifest.csv 에서 수집 내역을 확인하세요.")

if __name__ == "__main__":
    main()
