"""범위 그림이 없는 스킬 목록을 만든다.

무엇이 없어서 못 그렸는지에 따라 갈래를 나눈다. 갈래마다 손볼 방법이 다르고,
어떤 것은 애초에 그릴 게 없다 (패시브·이동기).

출력: 07_localized/no_aoe.html   - 체크하며 고를 수 있는 목록
"""
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

OUT = os.path.join(paths.LOCALIZED, "no_aoe.html")

SHAPE_FIELDS = ("aoe", "radius", "width", "height", "arc", "hitbox")


def bucket_of(fields):
    """왜 못 그렸는지로 갈래를 정한다."""
    aoe = (fields.get("aoe") or "").strip()
    has = lambda *keys: any(k in fields for k in keys)

    if aoe:
        return "shape"          # 모양은 적혀 있는데 지원하지 않는 형태
    if "radius" in fields and "arc" in fields:
        return "cone"           # 반경+각도 = 부채꼴인데 aoe 표기가 없다
    if "radius" in fields:
        return "circle"         # 반경만 있다. 원으로 그릴 수 있다
    if has(*SHAPE_FIELDS):
        return "partial"        # 너비·판정만 있는 어중간한 경우
    if "range" in fields:
        return "range"          # 사거리만. 넓이는 없고 닿는 거리만 그릴 수 있다
    return "none"               # 그릴 게 없다 (패시브·변신·이동기)


BUCKETS = [
    ("circle", "반경만 있음 - 원으로 바로 그릴 수 있다",
     "aoe 표기가 없을 뿐 반경이 적혀 있다. 가장 손쉽게 늘릴 수 있는 갈래."),
    ("cone", "반경 + 각도 - 부채꼴로 그릴 수 있다",
     "각도가 있으니 부채꼴이다. 가로쉬 땅의 파괴자처럼 안팎 반경이 같이 적힌 것도 있다."),
    ("shape", "모양은 적혀 있으나 지원하지 않는 형태",
     "사다리꼴·복합 모양 등. 하나씩 그리는 법을 정해야 한다."),
    ("partial", "치수가 일부만 있음",
     "너비나 판정 범위만 있어 어디에 어떻게 놓을지 정보가 모자란다."),
    ("range", "사거리만 있음 - 넓이는 없다",
     "단일 대상이거나 위키가 넓이를 적지 않았다. 사거리 원만 그릴 수 있다."),
    ("none", "그릴 것이 없음",
     "패시브·변신·이동기 등. 수치 자체가 없다."),
]

TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>범위 그림이 없는 스킬</title>
<style>
:root {{ --p:#a333ff; --bg:#0b0b0d; --card:#16161a; --blue:#00d4ff; --gold:#ffd700; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:#eee; font-size:14px; line-height:1.6;
  font-family:"Malgun Gothic",-apple-system,sans-serif; }}
header {{ background:#000; padding:12px 18px; border-bottom:1px solid #2a2a2e;
  position:sticky; top:0; z-index:5; }}
header .t {{ color:var(--p); font-weight:bold; }}
header .m {{ color:#666; font-size:12px; margin-left:8px; }}
main {{ max-width:1080px; margin:0 auto; padding:20px 16px 70px; }}
.lead {{ background:var(--card); border:1px solid #262630; border-left:3px solid var(--gold);
  border-radius:8px; padding:13px 15px; color:#b9b9c4; font-size:12.5px; margin-bottom:20px; }}
h2 {{ font-size:15px; color:var(--p); margin:28px 0 4px; }}
h2 .n {{ color:#555; font-size:12px; font-weight:normal; margin-left:6px; }}
.why {{ color:#7a7a88; font-size:12px; margin-bottom:9px; }}
table {{ width:100%; border-collapse:collapse; background:var(--card);
  border:1px solid #262630; border-radius:8px; overflow:hidden; }}
th {{ background:#1a1a20; color:#8a8a95; font-size:11.5px; font-weight:normal;
  text-align:left; padding:7px 11px; }}
td {{ padding:5px 11px; border-top:1px solid #1f1f27; font-size:12.5px; vertical-align:top; }}
td.hero {{ color:#9a9aa6; width:120px; }}
td.key {{ color:#666; width:52px; font-size:11.5px; }}
td.name {{ color:#e8e8f0; width:210px; }}
td.data {{ color:#6f6f7a; font-size:11.5px; font-family:Consolas,monospace; }}
tr:hover td {{ background:#1c1c24; }}
label {{ display:flex; gap:7px; align-items:flex-start; cursor:pointer; }}
input {{ accent-color:var(--p); width:14px; height:14px; margin-top:3px; flex-shrink:0; }}
</style>
</head>
<body>
<header><span class="t">범위 그림이 없는 스킬</span><span class="m">{meta}</span></header>
<main>
<div class="lead">
  기본 스킬·궁극기·특질 {total}개 가운데 {missing}개에 범위 그림이 없다.
  왜 없는지에 따라 갈래를 나눴다 - 갈래마다 손볼 방법이 다르다.<br>
  특성은 뺐다 (대부분 부모 스킬의 범위를 그대로 쓴다).
</div>
{sections}
</main>
</body>
</html>
"""


def escape(text):
    return html.escape(str(text if text is not None else ""))


def main():
    rows = json.load(open(paths.WIKI_FIELDS, encoding="utf-8"))["rows"]
    groups = {key: [] for key, _, _ in BUCKETS}
    total = missing = 0

    for filename in sorted(os.listdir(paths.HEROES_KR)):
        if not filename.endswith(".json"):
            continue
        hero = json.load(open(os.path.join(paths.HEROES_KR, filename), encoding="utf-8"))
        for entry in hero["abilities"]:
            total += 1
            key = (entry["_match"].get("key") or "").split("/")[-1]
            if (rows.get(key) or {}).get("geom"):
                continue
            missing += 1
            fields = entry.get("fields") or {}
            shown = {k: v for k, v in fields.items()
                     if k in SHAPE_FIELDS + ("range", "target")}
            groups[bucket_of(fields)].append(
                (hero["hero_kr"], entry.get("hotkey") or "", entry["name_kr"],
                 ", ".join("%s=%s" % kv for kv in shown.items()) or "-"))

    sections = []
    for key, title, why in BUCKETS:
        items = groups[key]
        if not items:
            continue
        body = "".join(
            "<tr><td class='hero'>%s</td><td class='key'>%s</td>"
            "<td class='name'><label><input type='checkbox'><span>%s</span></label></td>"
            "<td class='data'>%s</td></tr>"
            % tuple(escape(c) for c in item) for item in items)
        sections.append(
            "<h2>%s<span class='n'>%d</span></h2><div class='why'>%s</div>"
            "<table><tr><th>영웅</th><th>키</th><th>스킬</th><th>있는 값</th></tr>%s</table>"
            % (escape(title), len(items), escape(why), body))

    meta = ""
    if os.path.isfile(paths.FINAL):
        with open(paths.FINAL, encoding="utf-8") as fh:
            found = re.search(r"Build\s*(\d+)", fh.read(4096))
        meta = "Build %s" % found.group(1) if found else ""

    os.makedirs(paths.LOCALIZED, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(meta=meta, total=total, missing=missing,
                                 sections="".join(sections)))
    print("범위 없는 스킬 %d/%d -> %s" % (missing, total, OUT))
    for key, title, _ in BUCKETS:
        if groups[key]:
            print("  %-4s %3d  %s" % (key, len(groups[key]), title))


if __name__ == "__main__":
    main()
