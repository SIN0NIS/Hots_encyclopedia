"""output/ 에 들어갈 메인 페이지를 만든다.

백과사전·위키·특성 찍기로 들어가는 문 역할만 한다. 결과물 폴더를 열었을 때
어디로 가야 할지 바로 보이도록.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

OUT = os.path.join(paths.OUTPUT, "index.html")

LINKS = paths.settings().get("links") or {}
WIKI_URL = LINKS.get("wiki", "")
BUILDER_URL = LINKS.get("builder", "")

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>히오스 자료 모음</title>
<style>
:root {{ --p:#a333ff; --bg:#0b0b0d; --card:#16161a; --blue:#00d4ff; --gold:#ffd700; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; background:var(--bg); color:#eee; display:flex;
  flex-direction:column; align-items:center; justify-content:center; padding:32px 20px;
  font-family:"Malgun Gothic",-apple-system,sans-serif; }}
header {{ text-align:center; margin-bottom:34px; }}
h1 {{ margin:0 0 8px; font-size:26px; color:var(--p); font-weight:bold; }}
.meta {{ color:#666; font-size:12px; }}
/* 넷이 3+1 로 떨어지지 않게 2x2 로 묶는다 */
.past {{ margin-top:18px; font-size:12.5px; }}
.past a {{ color:#7fd4f0; text-decoration:none; border-bottom:1px dotted #2c6d85; }}
.past a:hover {{ color:#bdefff; }}
.cards {{ display:grid; gap:14px; width:100%; max-width:640px;
  grid-template-columns:repeat(auto-fit,minmax(270px,1fr)); }}
.card {{ background:var(--card); border:1px solid #262630; border-left:3px solid var(--accent);
  border-radius:10px; padding:18px 18px 16px; text-decoration:none; color:inherit;
  display:flex; flex-direction:column; gap:6px; transition:border-color .15s, transform .15s; }}
.card:hover {{ border-color:var(--accent); transform:translateY(-2px); }}
.icon {{ font-size:26px; line-height:1; }}
.name {{ font-size:15px; font-weight:bold; color:var(--accent); }}
.desc {{ font-size:12.5px; color:#9a9aa6; line-height:1.6; }}
.host {{ font-size:11px; color:#555; margin-top:auto; padding-top:8px; word-break:break-all; }}
footer {{ margin-top:30px; color:#4a4a52; font-size:11px; text-align:center; line-height:1.7; }}
</style>
</head>
<body>
<header>
  <h1>히오스 자료 모음</h1>
  <div class="meta">{meta}</div>
</header>

<div class="cards">
  <a class="card" style="--accent:var(--p)" href="{local}">
    <span class="icon">📖</span>
    <span class="name">영웅 백과사전</span>
    <span class="desc">영웅 {heroes}명의 스킬·특성 전체. 위키 상세 수치와 범위 그림이
      들어 있다. 레벨 0부터 30까지 수치가 바뀐다.</span>
    <span class="host">{local}</span>
  </a>

  <a class="card" style="--accent:var(--blue)" href="{local}#glossary">
    <span class="icon">📘</span>
    <span class="name">용어집</span>
    <span class="desc">스킬·특성 하단 필드의 한글 표기를 정리했다. 게임 번역이 아니라
      직접 정한 말들이라 어디서 왔는지 적어 두었다.</span>
    <span class="host">백과사전 안에 있다</span>
  </a>

  <a class="card" style="--accent:var(--gold)" href="{builder}" target="_blank" rel="noopener">
    <span class="icon">🧩</span>
    <span class="name">특성 찍기</span>
    <span class="desc">영웅별 특성 빌드를 짜고 공유한다.</span>
    <span class="host">sin0nis.github.io</span>
  </a>

  <a class="card" style="--accent:#3ddc84" href="{wiki}" target="_blank" rel="noopener">
    <span class="icon">📚</span>
    <span class="name">HotS 위키</span>
    <span class="desc">Fandom 원문 위키. 백과사전의 상세 수치가 여기서 온다.</span>
    <span class="host">heroesofthestorm.fandom.com</span>
  </a>
</div>
{archive}
<footer>위 두 장은 이 폴더 안에 있고, 아래 둘은 바깥 사이트다.</footer>
</body>
</html>
"""


def read_encyclopedia():
    """빌드 번호와 영웅 수를 백과사전에서 직접 읽는다. 손으로 적으면 어긋난다."""
    if not os.path.isfile(paths.FINAL):
        return "백과사전이 아직 없습니다", 0
    heroes = 0
    title = ""
    with open(paths.FINAL, encoding="utf-8") as fh:
        for line in fh:
            if not title:
                found = re.search(r"<title>(.*?)</title>", line)
                if found:
                    title = found.group(1)
            if line.startswith("const heroList = "):
                heroes = len(json.loads(line[len("const heroList = "):].strip().rstrip(";")))
                break
    build = re.search(r"Build\s*(\d+)", title)
    return ("Build %s" % build.group(1) if build else title or "히오스"), heroes


def past_versions():
    """지난 판이 보관돼 있으면 그리로 가는 줄을 넣는다. 없으면 아무것도 안 넣는다.

    보관함은 저장소 루트의 archive/ 에 있지만, 배포할 때 결과물 폴더 안으로
    함께 복사되므로 링크는 결과물 기준으로 적는다.
    """
    folder = os.path.join(paths.ROOT, "archive")
    if not os.path.isdir(folder):
        return ""
    kept = [n for n in os.listdir(folder) if n.startswith("Build_")]
    if not kept:
        return ""
    return ('<div class="past">지난 판 %d개가 남아 있다 — '
            '<a href="archive/index.html">보러 가기</a></div>' % len(kept))


def main():
    os.makedirs(paths.OUTPUT, exist_ok=True)
    local = os.path.basename(paths.FINAL)
    with open(OUT, "w", encoding="utf-8") as fh:
        meta, heroes = read_encyclopedia()
        fh.write(TEMPLATE.format(meta=meta, heroes=heroes, local=local,
                                 wiki=WIKI_URL, builder=BUILDER_URL,
                                 archive=past_versions()))
    print("메인 페이지 -> %s" % OUT)
    for stray in glob.glob(os.path.join(paths.OUTPUT, "*")):
        name = os.path.basename(stray)
        if name not in (local, "index.html"):
            print("  [참고] 결과물 폴더에 다른 파일이 있습니다: %s" % name)


if __name__ == "__main__":
    main()
