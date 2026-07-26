# -*- coding: utf-8 -*-
"""이번 빌드 결과물을 archive/ 에 통째로 보관하고 변경 기록을 남긴다.

게임이 패치되면 백과사전이 통째로 바뀐다. 그때 예전 판이 사라지면 "그 스킬
전에는 어땠지" 를 다시 볼 길이 없다. 그래서 **빌드 번호가 바뀔 때마다** 그
판을 통째로 남긴다.

  archive/Build_97650/     그 시점 결과물 (index.html + 백과사전)
  archive/index.html       판 목록
  CHANGELOG.md             빌드마다 무엇이 달라졌는지

같은 빌드 번호로 다시 돌리면 아무것도 하지 않는다. 게임이 안 바뀌었는데
같은 것을 쌓아 봐야 저장소만 불어난다.

  python 00_scripts/archive_build.py
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ARCHIVE = os.path.join(paths.ROOT, "archive")
CHANGELOG = os.path.join(paths.ROOT, "CHANGELOG.md")


def build_number():
    """이번 결과물의 게임 빌드 번호. 백과사전 제목에 적혀 있다."""
    with open(paths.FINAL, encoding="utf-8") as fh:
        for line in fh:
            found = re.search(r"<title>(.*?)</title>", line)
            if found:
                number = re.search(r"Build\s*(\d+)", found.group(1))
                return number.group(1) if number else None
    return None


def counts():
    """리포트에서 요약 숫자를 긁는다. 없으면 빈 사전."""
    out = {}
    path = os.path.join(paths.LOCALIZED, "wiki_fields.json")
    if os.path.isfile(path):
        rows = json.load(open(path, encoding="utf-8"))["rows"]
        out["범위 그림"] = sum(1 for v in rows.values() if v.get("geom"))
    path = os.path.join(paths.LOCALIZED, "xml_check.md")
    if os.path.isfile(path):
        text = open(path, encoding="utf-8").read()
        for label, key in (("게임과 일치", "일치"), ("사람이 봐야 할 것", "확인 필요")):
            found = re.search(r"\| %s \| \*\*(\d+)" % re.escape(label), text)
            if found:
                out[key] = int(found.group(1))
    return out


def listing(builds):
    """예전 판을 골라 들어가는 작은 페이지. 백과사전과 같은 색을 쓴다."""
    rows = "\n".join(
        '  <a class="row" href="Build_{n}/index.html">'
        '<span class="n">Build {n}</span>'
        '<span class="go">열기 &rsaquo;</span></a>'.format(n=n) for n in builds)
    return """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>지난 판 — 히오스 백과사전</title>
<style>
:root {{ --p:#a333ff; --bg:#0b0b0d; --card:#16161a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; background:var(--bg); color:#eee; padding:36px 20px;
  font-family:"Malgun Gothic",-apple-system,sans-serif; display:flex; flex-direction:column;
  align-items:center; }}
h1 {{ margin:0 0 6px; font-size:22px; color:var(--p); }}
.lead {{ color:#7a7a88; font-size:12.5px; margin-bottom:24px; text-align:center;
  line-height:1.7; max-width:520px; }}
.list {{ width:100%; max-width:460px; display:flex; flex-direction:column; gap:8px; }}
.row {{ display:flex; align-items:center; justify-content:space-between;
  background:var(--card); border:1px solid #262630; border-left:3px solid var(--p);
  border-radius:8px; padding:13px 16px; text-decoration:none; color:inherit;
  transition:border-color .15s, transform .15s; }}
.row:hover {{ border-color:var(--p); transform:translateY(-1px); }}
.n {{ font-size:14px; font-weight:bold; }}
.go {{ color:#666; font-size:12px; }}
.back {{ margin-top:26px; color:#4a4a52; font-size:12px; }}
.back a {{ color:#7fd4f0; text-decoration:none; }}
</style>
</head>
<body>
<h1>지난 판</h1>
<div class="lead">게임이 패치될 때마다 그 시점 백과사전을 통째로 남긴다.
  숫자가 클수록 최근이다.</div>
<div class="list">
{rows}
</div>
<div class="back"><a href="../index.html">&lsaquo; 메인으로</a></div>
</body>
</html>
""".format(rows=rows)


def main():
    if not os.path.isfile(paths.FINAL):
        raise SystemExit("결과물이 없습니다. kr 단계를 먼저 돌리세요.")
    number = build_number()
    if not number:
        raise SystemExit("백과사전 제목에서 빌드 번호를 찾지 못했습니다.")

    target = os.path.join(ARCHIVE, "Build_%s" % number)
    if os.path.isdir(target):
        print("  Build %s 는 이미 보관돼 있습니다. 넘어갑니다." % number)
    else:
        os.makedirs(target, exist_ok=True)
        for name in os.listdir(paths.OUTPUT):
            source = os.path.join(paths.OUTPUT, name)
            if os.path.isfile(source):
                shutil.copy2(source, os.path.join(target, name))
        print("  보관 -> %s" % target)

        summary = counts()
        line = "- **Build %s** — %s\n" % (
            number, " · ".join("%s %s" % kv for kv in summary.items()) or "기록 없음")
        head = "# 변경 기록\n\n게임 빌드가 바뀔 때마다 한 줄씩 쌓인다. 그 시점 결과물은\n" \
               "[archive/](archive/index.html) 에 통째로 남아 있다.\n\n"
        old = ""
        if os.path.isfile(CHANGELOG):
            old = open(CHANGELOG, encoding="utf-8").read()
            old = old[len(head):] if old.startswith(head) else old
        with open(CHANGELOG, "w", encoding="utf-8") as fh:
            fh.write(head + line + old)
        print("  기록 -> %s" % CHANGELOG)

    builds = sorted((name[len("Build_"):] for name in os.listdir(ARCHIVE)
                     if name.startswith("Build_")), key=int, reverse=True)
    with open(os.path.join(ARCHIVE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(listing(builds))
    print("  판 목록 %d개 -> %s" % (len(builds), os.path.join(ARCHIVE, "index.html")))


if __name__ == "__main__":
    main()
