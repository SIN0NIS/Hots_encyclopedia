"""백과사전 HTML 에 위키 필드 테이블을 심는다.

원본을 건드리지 않고 새 파일을 쓴다. 삽입한 조각은 모두 마커로 감싸므로,
이미 심은 파일을 다시 입력으로 줘도 옛 조각을 걷어내고 새로 넣는다(재실행 안전).

  python hots_kr/inject_wiki.py                     원본 -> hots_encyclopedia_wiki.html
  python hots_kr/inject_wiki.py <입력> -o <출력>     경로 직접 지정
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = paths.ENCYCLOPEDIA
TARGET = paths.FINAL
FIELDS = paths.WIKI_FIELDS
ATTACKS = paths.ATTACK_TYPES
GLOSSARY_BODY = os.path.join(paths.LOCALIZED, "glossary_body.html")

BEGIN = "/*<<WIKI-FIELDS>>*/"
END = "/*<</WIKI-FIELDS>>*/"
HTML_BEGIN = "<!--<<WIKI-FIELDS>>-->"
HTML_END = "<!--<</WIKI-FIELDS>>-->"


def wrap(text, html=False):
    begin, end = (HTML_BEGIN, HTML_END) if html else (BEGIN, END)
    return "%s%s%s" % (begin, text, end)


def unwrap_all(text):
    """이전에 심은 조각을 모두 걷어낸다."""
    for begin, end in ((re.escape(BEGIN), re.escape(END)),
                       (re.escape(HTML_BEGIN), re.escape(HTML_END))):
        text = re.sub(begin + r".*?" + end, "", text, flags=re.S)
    return text


# --------------------------------------------------------------------------
# 심을 조각들
# --------------------------------------------------------------------------
CSS = """
.wiki-fields { margin-top:8px; border-top:1px dashed #33333c; padding-top:7px; }
.wiki-fields-head { color:var(--blue); font-size:10.5px; letter-spacing:0.5px;
  text-transform:uppercase; margin-bottom:5px; display:flex; align-items:center; gap:5px; }
.wiki-fields-head .src { color:#555; text-transform:none; letter-spacing:0; font-size:10px; }
.wiki-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:3px 10px; }
.wiki-row { display:flex; gap:6px; font-size:11.5px; line-height:1.45; min-width:0; }
.wiki-row .k { color:#7a7a88; flex-shrink:0; }
.wiki-row .v { color:#cfcfd8; word-break:break-word; }
.wiki-note { margin-top:6px; background:#101016; border-left:2px solid #33333c;
  border-radius:0 4px 4px 0; color:#9a9aa6; font-size:11px; line-height:1.55; }
/* 손가락으로도 누를 수 있게 넉넉히. list-style 을 지워야 iOS 사파리에서 화살표가 겹치지 않는다. */
.wiki-note > summary { padding:5px 8px; cursor:pointer; color:#7a7a88; font-size:10.5px;
  letter-spacing:0.4px; text-transform:uppercase; list-style:none; user-select:none;
  min-height:24px; display:flex; align-items:center; gap:5px;
  -webkit-tap-highlight-color:rgba(163,51,255,0.25); }
.wiki-note > summary::-webkit-details-marker { display:none; }
.wiki-note > summary::before { content:'▸'; color:#555; font-size:11px; }
.wiki-note[open] > summary::before { content:'▾'; }
.wiki-note > summary:hover { color:var(--blue); }
.wiki-note-body { padding:0 8px 7px 8px; }
.talent-card .wiki-fields { border-top-color:#2a2a33; }
.atk-tag { display:inline-block; background:#000; border:1px solid #333; color:#bbb;
  font-size:10.5px; padding:1px 7px; border-radius:10px; margin-right:4px; }
/* 좁은 화면에서 190px 짜리 열이 페이지를 밀어내지 않도록 한 줄로 떨군다 */
@media (max-width: 700px) {
  .wiki-grid { grid-template-columns:1fr; }
  .wiki-row { font-size:11px; }
}

/* ---- 범위 그림 ---- */
.aoe-open { display:inline-flex; align-items:center; gap:4px; background:#0d1a22;
  border:1px solid #1f4b5e; color:#7fd4f0; font-size:10.5px; padding:2px 8px;
  border-radius:10px; cursor:pointer; margin-left:auto; min-height:22px;
  -webkit-tap-highlight-color:rgba(0,212,255,0.3); }
.aoe-open:hover { border-color:var(--blue); color:#bdefff; }
.ability-icon.has-aoe, .talent-card img.has-aoe { cursor:pointer; border-color:#2c6d85; }
.ability-icon.has-aoe:hover, .talent-card img.has-aoe:hover { border-color:var(--blue); }

.aoe-modal { position:fixed; inset:0; background:rgba(0,0,0,0.75); z-index:1000;
  display:none; align-items:center; justify-content:center; padding:16px; }
.aoe-modal.open { display:flex; }
.aoe-box { background:var(--card); border:1px solid var(--p); border-radius:10px;
  max-width:760px; width:100%; max-height:92vh; overflow:auto; }
.aoe-head { padding:10px 14px; border-bottom:1px solid #262630; display:flex;
  align-items:center; gap:8px; position:sticky; top:0; background:#1a1a20; }
.aoe-title { font-weight:bold; color:var(--p); font-size:14px; }
.aoe-sub { color:#777; font-size:11px; }
.aoe-close { margin-left:auto; background:#222; color:#fff; border:1px solid #444;
  border-radius:5px; font-size:16px; line-height:1; padding:5px 11px; cursor:pointer; }
.aoe-body { padding:12px 14px 16px; }
.aoe-legend { display:flex; flex-wrap:wrap; gap:10px; margin-top:10px; font-size:11.5px; }
.aoe-legend span { display:flex; align-items:center; gap:5px; color:#bbb; }
.aoe-key { width:13px; height:13px; border-radius:3px; flex-shrink:0; }
.aoe-note { margin-top:10px; color:#8a8a95; font-size:11px; line-height:1.6; }
.aoe-note b { color:#aaa; font-weight:normal; }

/* ---- 용어집 ---- */
.gl-btn { background:#1a1330; color:#c9a3ff; border:1px solid #4a2b7a; border-radius:5px;
  padding:4px 10px; font-size:12px; cursor:pointer; margin-left:10px; vertical-align:2px; }
.gl-btn:hover { border-color:var(--p); color:#e3ccff; }
.home-btn { background:#0d1a22; color:#7fd4f0; border-color:#1f4b5e;
  text-decoration:none; display:inline-block; }
.home-btn:hover { border-color:var(--blue); color:#bdefff; }
.gl-lead { background:var(--card); border:1px solid #262630; border-left:3px solid var(--gold);
  border-radius:8px; padding:13px 15px; color:#b9b9c4; font-size:12.5px; margin-bottom:18px;
  line-height:1.75; }
.gl-lead b { color:var(--gold); font-weight:normal; }
.gl-sec { break-inside:avoid; margin-bottom:16px; }
.gl-h { font-size:14px; color:var(--p); margin:22px 0 8px; padding-bottom:5px;
  border-bottom:1px solid #262630; font-weight:bold; }
.gl-h .gl-n { color:#555; font-size:11.5px; font-weight:normal; margin-left:6px; }
.gl-table { width:100%; border-collapse:collapse; background:var(--card);
  border:1px solid #262630; border-radius:8px; overflow:hidden; }
.gl-table th { background:#1a1a20; color:#8a8a95; font-size:11px; font-weight:normal;
  text-align:left; padding:6px 11px; letter-spacing:0.4px; }
.gl-table td { padding:5px 11px; border-top:1px solid #1f1f27; font-size:12.5px;
  vertical-align:top; }
.gl-table td.en { color:#9a9aa6; width:38%; }
.gl-table td.ko { color:#e8e8f0; width:30%; }
.gl-table td.note { color:#6f6f7a; font-size:11.5px; }
.gl-cols { column-count:2; column-gap:16px; }
.gl-foot { color:#4a4a52; font-size:11.5px; margin-top:28px; line-height:1.8; }
@media (max-width:760px) { .gl-cols { column-count:1; } .gl-table td.en { width:45%; } }
"""

TOGGLE_LABEL = ('<label><input type="checkbox" data-sec="wikifields" checked '
                'onchange="onToggleChange()"> 위키 상세 필드 (스킬·특성 하단)</label>')

# 바깥 사이트. 메인 페이지와 같은 곳을 보게 settings.json 하나에서 읽는다.
SETTINGS = paths.settings()
LINKS = SETTINGS.get("links") or {}
WIKI_URL = LINKS.get("wiki", "")
DRAWING = SETTINGS.get("aoeDrawing") or {}

TOP_LINKS = ('    <a class="set-btn" href="%s" target="_blank" rel="noopener">'
             '📚 위키</a>\n' % WIKI_URL)

# 좌측 상단, 제목 옆. 필드를 읽다가 바로 찾아볼 수 있는 자리다.
GLOSSARY_BUTTON = ('<button class="gl-btn" type="button" onclick="showGlossary()">'
                   '📘 용어집</button>')

# 들어온 길로 되돌아가는 문. index.html 이 첫 페이지이고 백과사전은 그 안으로
# 들어가는 곳이라, 여기서 나갈 길이 없으면 오간 데 없이 갇힌다.
HOME_BUTTON = ('<a class="gl-btn home-btn" href="index.html">'
               '🏠 메인</a>')

MODAL = """
<div class="aoe-modal" id="aoe-modal" onclick="if(event.target===this)closeAoe()">
  <div class="aoe-box">
    <div class="aoe-head">
      <span class="aoe-title" id="aoe-title"></span>
      <span class="aoe-sub" id="aoe-sub"></span>
      <button class="aoe-close" type="button" onclick="closeAoe()">&times;</button>
    </div>
    <div class="aoe-body" id="aoe-body"></div>
  </div>
</div>
"""

SCRIPT = """
// ---- 위키 상세 필드 -------------------------------------------------------
// hots wiki 에서 긁은 메타 필드를 스킬·특성 카드 하단에 붙인다. 조인 키는 buttonId
// (= gamestring 키의 접미사). 못 찾으면 nameId, 마지막으로 (영웅|이름)으로 찾는다.
const wikiFields = __WIKI_FIELDS__;

function wikiEntryFor(item, heroId) {
  const rows = wikiFields.rows;
  if (item.buttonId && rows[item.buttonId]) return rows[item.buttonId];
  if (item.nameId && rows[item.nameId]) return rows[item.nameId];
  const norm = (item.name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const aliased = wikiFields.alias[heroId + '|' + norm];
  return aliased ? rows[aliased] : null;
}

function renderWikiFields(item, heroId) {
  if (!toggles.wikifields) return '';
  const entry = wikiEntryFor(item, heroId);
  if (!entry) return '';
  const ko = currentLang === 'ko';
  const rows = (ko ? entry.ko : entry.en) || [];
  const note = ko ? (entry.noteKo || entry.noteEn) : entry.noteEn;
  if (!rows.length && !note) return '';

  // 마우스를 끌어서 방향을 정하는 스킬. 게임 XML 의 VectorRange 로 가려낸다.
  const drag = (attackTypes.drag || {})[item.buttonId];
  const dragRow = drag === undefined ? [] : [[
    ko ? '조준 방식' : 'Targeting',
    ko ? `드래그 조준 — 끌 수 있는 거리 ${drag}`
       : `Drag (vector) targeting — up to ${drag}`]];

  const cells = rows.concat(dragRow).map(r =>
    `<div class="wiki-row"><span class="k">${escapeWiki(r[0])}</span>` +
    `<span class="v">${escapeWiki(r[1])}</span></div>`).join('');
  // 비고는 길어서 기본으로 접어 둔다. <details> 는 PC·모바일 모두 기본 동작이라
  // 별도 스크립트 없이 눌러서 열린다.
  const noteHtml = note
    ? `<details class="wiki-note"><summary>${ko ? '비고' : 'Notes'}</summary>` +
      `<div class="wiki-note-body">${escapeWiki(note)}</div></details>` : '';

  const key = entry === wikiFields.rows[item.buttonId] ? item.buttonId : aoeKeyFor(item, heroId);
  const aoeButton = entry.geom
    ? `<button class="aoe-open" type="button">◎ ${ko ? '범위 보기' : 'Show area'}</button>` : '';

  return `<div class="wiki-fields"${entry.geom ? ` data-aoe="${key}"` : ''}>
    <div class="wiki-fields-head">📐 ${ko ? '위키 상세' : 'Wiki details'}
      <span class="src">heroesofthestorm.fandom</span>${aoeButton}</div>
    ${cells ? `<div class="wiki-grid">${cells}</div>` : ''}
    ${noteHtml}
  </div>`;
}

function aoeKeyFor(item, heroId) {
  const rows = wikiFields.rows;
  if (item.buttonId && rows[item.buttonId]) return item.buttonId;
  if (item.nameId && rows[item.nameId]) return item.nameId;
  const norm = (item.name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  return wikiFields.alias[heroId + '|' + norm] || '';
}

// ---- 용어집 -------------------------------------------------------------
// 별도 페이지가 아니라 백과사전 안의 한 화면이다. 영웅 페이지 자리를 빌려 쓴다.
const glossaryBody = __GLOSSARY_BODY__;

function showGlossary() {
  currentHeroId = null;
  document.getElementById('welcome').style.display = 'none';
  const page = document.getElementById('hero-page');
  page.style.display = 'block';
  page.innerHTML = `<div class="section"><div class="section-head">📘 ${
    currentLang === 'ko' ? '용어집 - 위키 상세 필드 표기' : 'Glossary - wiki detail fields'
  }</div><div class="section-body">${glossaryBody}</div></div>`;
  document.querySelectorAll('#hero-list .hero-item').forEach(x => x.classList.remove('active'));
  window.scrollTo(0, 0);
}

function escapeWiki(text) {
  return String(text == null ? '' : text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// ---- 범위 그림 -----------------------------------------------------------
// 길이 값은 전부 같은 좌표계(SC2 월드 유닛)다. 위키의 unitRadius / range / radius
// 가 모두 게임 XML 값을 그대로 옮긴 것이라 영웅 반지름과 겹쳐 그려도 된다.
//
// 다만 사거리의 '기준점'은 스킬마다 다르다. XML 의 RangeUseCasterRadius 플래그가
// 중심에서 잴지 몸통 가장자리에서 잴지를 정한다. 그 오차가 곧 시전자 반지름이므로
// 시전자 원을 같이 그려서 눈으로 가늠할 수 있게 한다.

// 범위 도형이 차지하는 상자. 원점은 범위의 기준점, +x 는 시전 방향이다.
// 직사각형은 시전자에게서 앞으로 뻗는 빔이라 뒤쪽(-x)으로는 퍼지지 않는다.
// 갈래별 각도. 가운데를 0 으로 두고 좌우 대칭으로 벌린다.
// 겐지 수리검(10도, 3갈래) -> [-10, 0, 10]
function aoeSpreadAngles(g) {
  if (!g.spread) return [0];
  const {angle, count} = g.spread;
  return Array.from({length: count}, (_, i) => (i - (count - 1) / 2) * angle);
}

// 튕김 거리는 맞은 대상을 중심으로 재므로 범위 도형과 기준점이 다르다.
// 도형 계산을 건드리지 않고 바깥에서 한 겹 덧씌운다.
// 피해 범위(빨강)·시전 사거리(청록)와 한눈에 갈리는 색이어야 한다
const BOUNCE_TINT = '#c07cff';
// 시전자가 대상을 고르는 범위. 피해가 아니라 '누가 걸리나' 라 또 다른 색이다.
const SEARCH_TINT = '#ffb347';

// 조각이 놓이는 자리와 조각 자신의 길이는 다른 값이다.
//   at    - 기준점에서 이만큼 앞에 놓는다
//   range - 거기서 제 힘으로 이만큼 더 나간다 (관통 스킬)
// at 을 안 쓴 조각은 예전처럼 range 를 '놓이는 자리' 로 읽는다.
function aoePartAt(part) {
  return part.at !== undefined ? part.at : (part.range || 0);
}

// 조각을 제 기준점 둘레로 돌린 뒤 다시 감싸는 상자. 네 모서리를 돌려 본다.
function aoeSpin(box, deg) {
  if (!deg) return box;
  const rad = deg * Math.PI / 180, cos = Math.cos(rad), sin = Math.sin(rad);
  const xs = [], ys = [];
  for (const x of [box.l, box.r]) for (const y of [box.t, box.b]) {
    xs.push(x * cos - y * sin); ys.push(x * sin + y * cos);
  }
  return {l: Math.min(...xs), r: Math.max(...xs),
          t: Math.min(...ys), b: Math.max(...ys)};
}

function aoeShapeBox(g) {
  const box = aoeShapeBoxCore(g);
  if (!g.bounce) return box;
  const r = g.bounce;
  return {l: Math.min(box.l, -r), r: Math.max(box.r, r),
          t: Math.min(box.t, -r), b: Math.max(box.b, r)};
}

function aoeShapeBoxCore(g) {
  if (g.shape === 'bounce') return {l: 0, r: 0, t: 0, b: 0};
  if (g.parts) {
    // 여러 도형이 겹친 스킬. 각 조각을 제 자리에 놓고 전부 감싸는 상자를 구한다.
    const boxes = g.parts.map(part => {
      const box = aoeSpin(aoeShapeBoxCore(part), part.rotate), at = aoePartAt(part);
      const side = part.across || 0;   // 시전 방향과 직각으로 밀어 놓은 조각
      return {l: at + box.l, r: at + box.r, t: side + box.t, b: side + box.b};
    });
    return {l: Math.min(...boxes.map(b => b.l)), r: Math.max(...boxes.map(b => b.r)),
            t: Math.min(...boxes.map(b => b.t)), b: Math.max(...boxes.map(b => b.b))};
  }
  if (g.shape === 'skillshot') {
    // 시전자에서 앞으로 훑고 지나간 자리. 투사체는 시전자에서 생겨 앞으로만
    // 나가므로 뒤쪽은 맞지 않는다 - 앞으로 두께의 절반만 더 나간다.
    // 여러 갈래면 가장 벌어진 각도까지 품어야 한다.
    const reach = g.range || 0;
    const box = {l: 0, r: reach + g.depth / 2,
                 t: -g.width / 2, b: g.width / 2};
    const widest = Math.max(...aoeSpreadAngles(g).map(Math.abs));
    if (widest > 0) {
      const far = reach + g.depth / 2, rad = widest * Math.PI / 180;
      const side = far * Math.sin(rad) + g.width / 2;
      box.t = -side; box.b = side;
      box.r = Math.max(box.r, far * Math.cos(rad) + g.width / 2);
    }
    return box;
  }
  if (g.shape === 'ring') {
    if (!g.arc || g.arc >= 360) return {l: -g.outer, r: g.outer, t: -g.outer, b: g.outer};
    // 고리 부채꼴은 앞쪽 한 조각만 차지한다 (가로쉬 땅의 파괴자, 누더기 지면 강타)
    const half = g.arc * Math.PI / 360, side = g.outer * Math.sin(half);
    return {l: Math.min(0, g.outer * Math.cos(half)), r: g.outer, t: -side, b: side};
  }
  if (g.shape === 'trapezoid') {
    // 앞뒤 폭이 다른 사각형. 기준점에서 앞으로 뻗는다.
    return {l: 0, r: g.height,
            t: -Math.max(g.inner, g.outer) / 2, b: Math.max(g.inner, g.outer) / 2};
  }
  if (g.shape === 'triangle' || g.shape === 'equilateral') {
    // 한 변 길이로 그리는 정삼각형. 무게중심을 기준점에 두고 꼭짓점이 앞을 본다.
    const far = g.side / Math.sqrt(3);
    return {l: -far / 2, r: far, t: -g.side / 2, b: g.side / 2};
  }
  if (g.shape === 'polygon') {
    // 게임 XML 이 꼭짓점을 그대로 적어 둔 모양. 어림하지 않고 그 좌표로 그린다.
    const xs = g.points.map(p => p[0]), ys = g.points.map(p => p[1]);
    return {l: Math.min(...xs), r: Math.max(...xs),
            t: Math.min(...ys), b: Math.max(...ys)};
  }
  if (g.shape === 'grow')
    // 날아가며 커지는 판정. 끝에서 가장 크다.
    return {l: -g.from, r: g.travel + g.to, t: -g.to, b: g.to};
  if (g.shape === 'sweep') {
    // 밖으로 퍼져 나가는 부채꼴 띠. 다 퍼진 모습이 곧 부채꼴 하나다.
    const half = g.arc * Math.PI / 360, side = g.to * Math.sin(half);
    return {l: Math.min(0, g.to * Math.cos(half)), r: g.to, t: -side, b: side};
  }
  if (g.shape === 'blade' || g.shape === 'square')
    // 기준점을 가운데 두고 그린다 (직사각형 빔과 달리 앞으로 뻗지 않는다)
    return {l: -g.height / 2, r: g.height / 2, t: -g.width / 2, b: g.width / 2};
  if (g.shape === 'rectangle')
    // 끝이 열린 빔은 화살표와 글자가 더 붙으므로 상자를 조금 넉넉히 잡는다
    return {l: 0, r: g.height * (g.openEnded ? 1.35 : 1),
            t: -g.width / 2, b: g.width / 2};
  if (g.shape === 'radial') {
    if (g.arc >= 180) return {l: -g.radius, r: g.radius, t: -g.radius, b: g.radius};
    const half = g.arc * Math.PI / 360, reach = g.radius * Math.sin(half);
    return {l: Math.min(0, g.radius * Math.cos(half)), r: g.radius, t: -reach, b: reach};
  }
  const trail = g.repeat ? (g.repeat.count - 1) * g.repeat.spacing : 0;
  return {l: -g.radius, r: g.radius + trail, t: -g.radius, b: g.radius};
}


// 크기를 가늠할 기준자. 그림 전체가 들어가는 가장 작은 기준을 고른다.
// 작은 스킬은 레이너 평타(6.5) 원 안에서, 그보다 크면 해머 공성(11) 원까지 넓혀
// 본다. 영웅마다 사거리가 제각각이라 같은 자를 대야 비교가 된다.
function aoeReference(span) {
  const list = attackTypes.references || [];
  return list.find(r => r.range >= span) || list[list.length - 1] || null;
}

function aoeSvg(g, casterRadius, innerRadius) {
  const W = 660, pad = 44, maxH = 520;
  const reach = g.range || 0;

  // 범위가 어디에 놓이는가. 보통은 사거리 끝(시전 지점)이지만, 관통 스킬은
  // 시전자에서 시작해 앞으로 훑고 지나가므로 시전자에 붙는다.
  const anchor = g.shape === 'skillshot' ? 0 : reach;

  // 모든 그림을 위에서 내려다본 평면도로 그린다. 예전에는 사거리가 범위보다
  // 훨씬 길면 가로로 편 단면도로 바꿨는데, 그러면 크기 기준 원이 사라져
  // 어떤 스킬은 기준자가 보이고 어떤 스킬은 안 보였다. 같은 눈으로 봐야
  // 스킬끼리 비교가 되므로 배치를 하나로 통일한다.
  const shape = aoeShapeBox(g);
  const box = {l: -casterRadius, r: casterRadius, t: -casterRadius, b: casterRadius};
  if (reach > 0 && g.shape !== 'skillshot') {
    box.l = Math.min(box.l, -reach); box.r = Math.max(box.r, reach);
    box.t = Math.min(box.t, -reach); box.b = Math.max(box.b, reach);
  }
  box.l = Math.min(box.l, anchor + shape.l); box.r = Math.max(box.r, anchor + shape.r);
  box.t = Math.min(box.t, shape.t);          box.b = Math.max(box.b, shape.b);

  // 대상을 고르는 범위는 시전자 둘레라 원점을 기준으로 상자를 넓힌다
  if (g.search) {
    box.l = Math.min(box.l, -g.search); box.r = Math.max(box.r, g.search);
    box.t = Math.min(box.t, -g.search); box.b = Math.max(box.b, g.search);
  }

  // 기준 원도 들어가야 하므로 상자에 함께 넣는다
  const span = Math.max(Math.abs(box.l), box.r, Math.abs(box.t), box.b);
  const ref = aoeReference(span);
  if (ref) {
    box.l = Math.min(box.l, -ref.range); box.r = Math.max(box.r, ref.range);
    box.t = Math.min(box.t, -ref.range); box.b = Math.max(box.b, ref.range);
  }

  const wide = box.r - box.l, tall = box.b - box.t;
  const s = Math.min((W - pad * 2) / wide, (maxH - pad * 2) / tall, 62);
  const H = Math.max(tall * s + pad * 2, 200);
  const ox = pad - box.l * s, oy = (H - tall * s) / 2 - box.t * s;
  const ax = ox + anchor * s;   // 범위를 그릴 자리
  const tip = ox + reach * s;   // 사거리 끝

  const castable = reach > 0 && g.shape !== 'skillshot'
    ? `<circle cx="${ox}" cy="${oy}" r="${reach * s}" fill="#00d4ff" fill-opacity="0.07"
        stroke="#00d4ff" stroke-width="1.4" stroke-dasharray="7 5"/>` : '';
  // 시전자에서 범위까지 잇는 선. 예전에는 단면도에서만 사거리 숫자를 적었는데,
  // 이제 배치가 하나뿐이라 어느 그림에서나 같은 자리에 적는다.
  const spine = reach > 0 && g.shape !== 'skillshot'
    ? `<line x1="${ox}" y1="${oy}" x2="${tip}" y2="${oy}" stroke="#00d4ff" stroke-width="1.4"/>
       <text x="${(ox + tip) / 2}" y="${oy - 9}" text-anchor="middle" font-size="11.5"
        fill="#7fd4f0">${currentLang === 'ko' ? '사거리' : 'Range'} ${g.range}</text>` : '';

  const gauge = ref ? `<circle cx="${ox}" cy="${oy}" r="${ref.range * s}" fill="none"
      stroke="#8a8a95" stroke-width="1.2" stroke-dasharray="2 6"/>
    <text x="${ox}" y="${oy - ref.range * s - 7}" text-anchor="middle" font-size="11.5"
      fill="#8a8a95">${currentLang === 'ko' ? ref.ko : ref.en} ${ref.range}</text>` : '';

  // 시전자가 대상을 고르는 범위. 여기 걸린 적이 스킬에 휘말린다 (가로쉬 파쇄추)
  const search = g.search ? `<circle cx="${ox}" cy="${oy}" r="${g.search * s}"
      fill="${SEARCH_TINT}" fill-opacity="0.07" stroke="${SEARCH_TINT}" stroke-width="1.6"
      stroke-dasharray="3 4"/>
    <text x="${ox}" y="${oy + g.search * s + 14}" text-anchor="middle" font-size="11"
      fill="${SEARCH_TINT}">${currentLang === 'ko' ? '대상 인식' : 'search'} ${g.search}</text>` : '';

  // 특성이 늘려 준 만큼을 화살표로. 크기는 도형 중심에서 위로, 사거리는 시전자에서
  // 앞으로 재고, 늘기 전 크기는 흐린 점선 원으로 남긴다.
  const growth = (g.grew || []).map(step => {
    const dim = `<circle cx="%CX%" cy="${oy}" r="${step.from * s}" fill="none"
        stroke="${GROWTH_TINT}" stroke-width="1.2" stroke-dasharray="4 4" opacity="0.45"/>`;
    const tag = `${step.from} → ${step.to}`;
    if (step.field === 'range') {
      // 사거리는 시전자 둘레로 자라므로 원도 시전자 중심이다
      return dim.replace('%CX%', ox) +
        aoeArrow(ox + step.from * s, oy + 15, ox + step.to * s, oy + 15, tag);
    }
    return dim.replace('%CX%', ax) +
      aoeArrow(ax, oy - step.from * s, ax, oy - step.to * s, tag);
  }).join('');

  return `<svg width="100%" viewBox="0 0 ${W} ${Math.round(H)}" xmlns="http://www.w3.org/2000/svg">
    ${aoeGrid(W, H, s, ox, oy)}
    ${gauge}
    ${search}
    ${castable}
    ${spine}
    ${aoeShape(g, ax, oy, s)}
    ${growth}
    ${aoeCaster(ox, oy, casterRadius * s, (innerRadius || 0) * s)}
    ${aoeScale(s, H, ref)}
  </svg>`;
}

const AOE_NO_RANGE = {
  self: {ko: '자기 중심 — 시전자를 기준으로 터진다', en: 'Centered on the caster'},
  inherit: {ko: '강화하는 스킬의 사거리를 그대로 따른다', en: 'Inherits the modified ability\\'s range'},
  unstated: {ko: '위키에 사거리가 적혀 있지 않다 (게임 데이터에도 제한값이 없다)',
             en: 'No range stated on the wiki (the game data sets no limit either)'},
};

const PART_COLORS = __PART_COLORS__;

function aoeShape(g, x, y, s, nested) {
  const core = aoeShapeCore(g, x, y, s, nested);
  if (!g.bounce) return core;
  // 점선에 옅은 채움 - 피해가 들어가는 자리가 아니라 '여기까지 튄다' 는 뜻이다.
  return `<circle cx="${x}" cy="${y}" r="${g.bounce * s}" fill="${BOUNCE_TINT}"
      fill-opacity="0.08" stroke="${BOUNCE_TINT}" stroke-width="2" stroke-dasharray="6 4"/>
    <text x="${x}" y="${y - g.bounce * s - 6}" text-anchor="middle" font-size="11"
      fill="${BOUNCE_TINT}">${currentLang === 'ko' ? '튕김' : 'bounce'} ${g.bounce}</text>
    ${core}`;
}

// nested 는 재귀 깊이다. g.depth(투사체 두께)와 이름이 겹치면 안 된다 -
// 예전에 depth 로 두었다가 g.depth 를 가려 모서리 반경이 NaN 으로 나갔다.
function aoeShapeCore(g, x, y, s, nested) {
  if (g.shape === 'bounce') return '';
  if (g.parts) {
    // 조각마다 색을 달리해 겹친 자리를 구분한다.
    return g.parts.map((part, i) => {
      const px = x + aoePartAt(part) * s, py = y + (part.across || 0) * s;
      const spin = part.rotate
        ? ` transform="rotate(${part.rotate} ${px} ${py})"` : '';
      // 같은 효과를 여러 조각으로 쪼갠 경우(티리엘 강타의 원 5개)는 색을 지정해
      // 한 덩어리로 읽히게 한다. 안 주면 조각마다 색을 돌려 구분한다.
      return `<g opacity="0.9"${spin}>${aoeShapeCore(
        Object.assign({}, part, {_color: part.color || PART_COLORS[i % 3]}),
        px, py, s, (nested || 0) + 1)}</g>`;
    }).join('');
  }
  const tint = g._color || '#ff5f5f';
  const fill = `fill="${tint}" fill-opacity="0.28" stroke="${tint}" stroke-width="2"`;
  if (g.shape === 'skillshot') {
    // 훑고 지나간 자리를 채우고, 투사체 자체의 판정 상자는 도착점에 점선으로.
    // 여러 갈래로 나가는 스킬(겐지 수리검)은 갈래마다 같은 경로를 돌려 그린다.
    // at 을 쓴 조각은 놓이는 자리가 따로 있으므로 range 는 온전히 '나아간 길이' 다
    const reach = (nested && g.at === undefined ? 0 : (g.range || 0)) * s,
          half = g.width * s / 2,
          thick = g.depth * s;
    const lane = `<rect x="0" y="${-half}" width="${reach + thick / 2}"
        height="${g.width * s}" rx="${Math.min(half, thick / 2)}" ${fill}/>
      <rect x="${reach - thick / 2}" y="${-half}" width="${thick}"
        height="${g.width * s}" fill="none" stroke="#ffd700" stroke-width="1.5"
        stroke-dasharray="4 3"/>`;
    return aoeSpreadAngles(g).map(a =>
      `<g transform="translate(${x} ${y}) rotate(${a})">${lane}</g>`).join('');
  }
  if (g.shape === 'ring' && g.arc && g.arc < 360) {
    // 고리에서 각도만큼 잘라낸 조각. 바깥 호를 따라갔다가 안쪽 호로 되돌아온다.
    const half = g.arc * Math.PI / 360, ro = g.outer * s, ri = g.inner * s;
    const big = g.arc > 180 ? 1 : 0;
    const p = (r, a) => `${x + r * Math.cos(a)} ${y + r * Math.sin(a)}`;
    return `<path d="M ${p(ri, -half)} L ${p(ro, -half)}
      A ${ro} ${ro} 0 ${big} 1 ${p(ro, half)} L ${p(ri, half)}
      A ${ri} ${ri} 0 ${big} 0 ${p(ri, -half)} Z" ${fill}/>`;
  }
  if (g.shape === 'ring') {
    return `<path d="M ${x - g.outer * s} ${y} a ${g.outer * s} ${g.outer * s} 0 1 0 ${g.outer * s * 2} 0
      a ${g.outer * s} ${g.outer * s} 0 1 0 ${-g.outer * s * 2} 0 Z
      M ${x - g.inner * s} ${y} a ${g.inner * s} ${g.inner * s} 0 1 1 ${g.inner * s * 2} 0
      a ${g.inner * s} ${g.inner * s} 0 1 1 ${-g.inner * s * 2} 0 Z" fill-rule="evenodd" ${fill}/>`;
  }
  if (g.shape === 'triangle' || g.shape === 'equilateral') {
    // 정삼각형. 무게중심에서 세 꼭짓점까지가 한 변/√3 이고, 한 꼭짓점이 앞을 본다.
    const far = g.side * s / Math.sqrt(3);
    const points = [0, 120, 240].map(a => {
      const rad = a * Math.PI / 180;
      return `${x + far * Math.cos(rad)},${y + far * Math.sin(rad)}`;
    }).join(' ');
    return `<polygon points="${points}" ${fill}/>`;
  }
  if (g.shape === 'trapezoid') {
    const near = g.inner * s / 2, far = g.outer * s / 2, len = g.height * s;
    return `<polygon points="${x},${y - near} ${x + len},${y - far}
      ${x + len},${y + far} ${x},${y + near}" ${fill}/>`;
  }
  if (g.shape === 'square') {
    return `<rect x="${x - g.height * s / 2}" y="${y - g.width * s / 2}"
      width="${g.height * s}" height="${g.width * s}" ${fill}/>`;
  }
  if (g.shape === 'polygon') {
    // 꼭짓점을 그대로 잇는다. 기준점이 원점이고 +x 가 시전 방향이다.
    return `<polygon points="${g.points.map(p =>
      `${x + p[0] * s},${y + p[1] * s}`).join(' ')}" ${fill}/>`;
  }
  if (g.shape === 'sweep') {
    // 시전자에게서 밖으로 퍼져 나가는 부채꼴 띠. 어느 한 순간에는 두께 thickness
    // 인 띠 하나뿐이고, 그게 from 에서 to 까지 나아간다 (안두인 응징).
    const steps = 9, half = g.arc * Math.PI / 360;
    const band = (outer) => {
      const inner = Math.max(outer - g.thickness, 0);
      const ro = outer * s, ri = inner * s, big = g.arc > 180 ? 1 : 0;
      const p = (r, a) => `${x + r * Math.cos(a)} ${y + r * Math.sin(a)}`;
      return `M ${p(ri, -half)} L ${p(ro, -half)}
        A ${ro} ${ro} 0 ${big} 1 ${p(ro, half)} L ${p(ri, half)}
        A ${ri} ${ri} 0 ${big} 0 ${p(ri, -half)} Z`;
    };
    let out = '';
    for (let i = 0; i <= steps; i++) {
      const outer = g.from + (g.to - g.from) * i / steps;
      out += `<path d="${band(outer)}" fill="${tint}" fill-opacity="0.12" stroke="none"/>`;
    }
    // 다 지나간 자리 전체를 테두리로 둘러 어디까지 닿는지 보인다
    const far = g.to * s;
    const edge = (a) => `${x + far * Math.cos(a)} ${y + far * Math.sin(a)}`;
    return out + `<path d="M ${x} ${y} L ${edge(-half)}
      A ${far} ${far} 0 ${g.arc > 180 ? 1 : 0} 1 ${edge(half)} Z"
      fill="none" stroke="${tint}" stroke-width="1.6" stroke-dasharray="5 4"/>`;
  }
  if (g.shape === 'grow') {
    // 날아가며 판정이 커지는 투사체. 같은 원을 여러 번 겹쳐 그려 "점점 커진다" 를
    // 보인다. over 까지 커지고 그 뒤로는 그대로다 (리밍 비전 보주).
    const steps = 16;
    let out = '';
    for (let i = 0; i <= steps; i++) {
      const at = g.travel * i / steps;
      const grown = g.from + (g.to - g.from) * Math.min(at / g.over, 1);
      out += `<circle cx="${x + at * s}" cy="${y}" r="${grown * s}"
        fill="${tint}" fill-opacity="0.13" stroke="none"/>`;
    }
    // 가장 커진 뒤의 테두리만 실선으로 남겨 어디까지 굵어지는지 보이게 한다
    const end = g.travel * s, big = g.to * s;
    out += `<path d="M ${x} ${y - g.from * s}
        L ${x + Math.min(g.over, g.travel) * s} ${y - big} L ${x + end} ${y - big}
        M ${x} ${y + g.from * s}
        L ${x + Math.min(g.over, g.travel) * s} ${y + big} L ${x + end} ${y + big}"
      fill="none" stroke="${tint}" stroke-width="1.6"/>`;
    return out;
  }
  if (g.shape === 'blade') {
    // 양 끝이 뾰족한 베기 자국. 가운데 flat 만큼은 폭이 그대로고 거기서부터
    // 양 끝까지 삼각형으로 좁아진다 (겐지 폭렬참). 기준점이 한가운데다.
    const far = g.height * s / 2, mid = g.flat * s / 2, half = g.width * s / 2;
    return `<polygon points="${x - far},${y} ${x - mid},${y - half}
      ${x + mid},${y - half} ${x + far},${y} ${x + mid},${y + half}
      ${x - mid},${y + half}" ${fill}/>`;
  }
  if (g.shape === 'rectangle') {
    // 폭 x 길이. 길이는 시전 방향으로 뻗으므로 기준점에서 오른쪽으로 그린다.
    const box = `<rect x="${x}" y="${y - g.width * s / 2}"
      width="${g.height * s}" height="${g.width * s}" ${fill}/>`;
    if (!g.openEnded) return box;
    // 끝이 정해지지 않은 빔. 먼 쪽 테두리를 지우고 화살표로 이어 붙인다.
    const far = x + g.height * s, half = g.width * s / 2;
    return `${box}
      <rect x="${far - 3}" y="${y - half - 2}" width="6" height="${g.width * s + 4}"
        fill="#1a1a22"/>
      <line x1="${far - 4}" y1="${y}" x2="${far + 22}" y2="${y}" stroke="${tint}"
        stroke-width="2" stroke-dasharray="5 4"/>
      <polygon points="${far + 22},${y} ${far + 14},${y - 5} ${far + 14},${y + 5}"
        fill="${tint}"/>
      <text x="${far + 26}" y="${y + 4}" font-size="11" fill="${tint}">${
        currentLang === 'ko' ? '조준한 곳까지' : 'to wherever aimed'}</text>`;
  }
  if (g.shape === 'radial') {
    const half = g.arc * Math.PI / 360, r = g.radius * s;
    const x1 = x + r * Math.cos(-half), y1 = y + r * Math.sin(-half);
    const x2 = x + r * Math.cos(half), y2 = y + r * Math.sin(half);
    return `<path d="M ${x} ${y} L ${x1} ${y1} A ${r} ${r} 0 ${g.arc > 180 ? 1 : 0} 1 ${x2} ${y2} Z" ${fill}/>`;
  }
  if (g.repeat) {
    // 시전 지점이 첫 발이고, 나머지는 같은 방향으로 간격만큼 더 나간다.
    return Array.from({length: g.repeat.count}, (_, i) => {
      const cx = x + i * g.repeat.spacing * s;
      return `<circle cx="${cx}" cy="${y}" r="${g.radius * s}" ${fill}/>` +
        `<text x="${cx}" y="${y + 4}" text-anchor="middle" font-size="11"
          fill="#ffd9d9" fill-opacity="0.85">${i + 1}</text>`;
    }).join('');
  }
  return `<circle cx="${x}" cy="${y}" r="${g.radius * s}" ${fill}/>`;
}

// 시전자. 충돌 반지름과 피격 반지름이 다른 영웅(디아블로 1.19 / 0.94 등)은 둘 다
// 그린다. 중심은 같으므로 어느 쪽을 보든 격자 교차점에 놓인다.
function aoeCaster(x, y, r, inner) {
  const hit = inner && Math.abs(inner - r) > 0.01
    ? `<circle cx="${x}" cy="${y}" r="${Math.max(inner, 1.5)}" fill="none"
        stroke="#fff" stroke-width="1" stroke-dasharray="3 3" opacity="0.8"/>` : '';
  return `<circle cx="${x}" cy="${y}" r="${Math.max(r, 2)}" fill="#eee" fill-opacity="0.5"
      stroke="#fff" stroke-width="1.5"/>${hit}
    <path d="M ${x - 4} ${y} H ${x + 4} M ${x} ${y - 4} V ${y + 4}" stroke="#fff"
      stroke-width="1" opacity="0.9"/>`;
}

// 격자는 시전자에 맞춰 깐다. 시전자 원의 중심이 격자 교차점에 정확히 놓여야
// 거기서부터 몇 칸인지 눈으로 셀 수 있다.
function aoeGrid(W, H, s, ox, oy) {
  // 1단위 격자가 너무 촘촘하면 눈이 아프므로 간격이 12px 밑으로 내려가면 5단위로 넓힌다
  const step = s < 12 ? s * 5 : s;
  const dx = ((ox % step) + step) % step, dy = ((oy % step) + step) % step;
  return `<defs><pattern id="aoegrid" width="${step}" height="${step}"
      patternUnits="userSpaceOnUse" patternTransform="translate(${dx} ${dy})">
      <path d="M ${step} 0 H 0 V ${step}" fill="none" stroke="#3a3a46" stroke-width="0.5"/>
    </pattern></defs>
    <rect width="${W}" height="${H}" fill="url(#aoegrid)"/>`;
}

// 특성으로 범위가 늘어난 자리. 늘기 전 크기를 흐린 점선으로 남기고 그 사이를
// 화살표로 이어 "여기서 여기까지 늘었다" 를 한눈에 보인다.
const GROWTH_TINT = '#7ee787';

function aoeArrow(x1, y1, x2, y2, label) {
  const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy);
  if (len < 6) return '';                 // 너무 짧으면 화살촉만 뭉쳐 지저분하다
  const ux = dx / len, uy = dy / len, head = Math.min(7, len / 2);
  // 화살촉은 진행 방향으로 삼각형 하나. marker 를 쓰면 defs 이름이 겹칠 수 있다.
  const bx = x2 - ux * head, by = y2 - uy * head;
  const tip = `${bx - uy * head * 0.5},${by + ux * head * 0.5}
               ${x2},${y2} ${bx + uy * head * 0.5},${by - ux * head * 0.5}`;
  // 세로로 자란 것은 화살촉 바깥에 적는다 - 가운데에 적으면 도형 테두리에 겹친다.
  // 가로(사거리)는 이미 시전선 아래 빈 자리라 가운데가 읽기 좋다.
  const upright = Math.abs(uy) > Math.abs(ux);
  const tx = upright ? x2 : (x1 + x2) / 2;
  const ty = upright ? y2 + uy * 12 + 4 : (y1 + y2) / 2 + 15;
  return `<line x1="${x1}" y1="${y1}" x2="${bx}" y2="${by}" stroke="${GROWTH_TINT}"
      stroke-width="2"/>
    <polygon points="${tip}" fill="${GROWTH_TINT}"/>
    <text x="${tx}" y="${ty}" text-anchor="middle" font-size="11"
      fill="${GROWTH_TINT}">${label}</text>`;
}

// 아래쪽 눈금자. 기준 사거리가 있으면 그 길이만큼 재서 이름과 값을 붙인다.
function aoeScale(s, H, ref) {
  const ko = currentLang === 'ko';
  const px = ref ? ref.range * s : (s < 12 ? 10 : 5) * s;
  const label = ref ? `${ko ? ref.ko : ref.en} ${ko ? '사거리' : 'range'}(${ref.range})`
                    : `${s < 12 ? 10 : 5} ${ko ? '단위' : 'units'}`;
  const y = H - 16, x = 14;
  return `<line x1="${x}" y1="${y}" x2="${x + px}" y2="${y}" stroke="#ddd" stroke-width="2"/>
    <line x1="${x}" y1="${y - 5}" x2="${x}" y2="${y + 5}" stroke="#ddd" stroke-width="2"/>
    <line x1="${x + px}" y1="${y - 5}" x2="${x + px}" y2="${y + 5}" stroke="#ddd" stroke-width="2"/>
    <text x="${x + px + 8}" y="${y + 4}" font-size="12" fill="#ddd">${label}</text>`;
}

function openAoe(buttonId, heroId) {
  const entry = wikiFields.rows[buttonId];
  if (!entry || !entry.geom) return;
  const g = entry.geom, ko = currentLang === 'ko';
  const hero = getActiveData()[currentHeroId] || {};
  const casterRadius = hero.radius || 0.625;
  const rows = (ko ? entry.ko : entry.en) || [];
  const name = aoeNameOf(buttonId) || buttonId;

  const facts = [
    g.parts ? [ko ? '겹친 도형' : 'Parts',
               g.parts.map(x => x.label || x.shape).join(' + ')] : null,
    g.search ? [ko ? '대상 인식 범위' : 'Search radius',
                g.search + (ko ? ' — 이 안의 적을 골라 끌어들인다'
                               : ' around the caster — picks the target')] : null,
    g.bounce ? [ko ? '튕김 반경' : 'Bounce reach',
                (ko ? '맞은 대상에서 ' : 'Up to ') + g.bounce +
                (ko ? ' 안의 다음 대상으로 튄다' : ' from the target it hit')] : null,
    g.note ? [ko ? '설명' : 'Note', g.note] : null,
    g.src === 'upgrade' ? [ko ? '출처' : 'Source',
                           ko ? `이 특성을 찍었을 때의 ${g.upgradeOfKo} 범위`
                              : `${g.upgradeOf} area with this talent taken`] : null,
    g.src === 'manual' ? [ko ? '출처' : 'Source',
                          ko ? '손으로 넣은 값 (위키 데이터로는 그릴 수 없음)'
                             : 'Hand-authored (not derivable from the wiki)'] : null,
    [ko ? '범위 형태' : 'Shape',
     g.shape === 'skillshot' ? (ko ? '관통 경로 (판정 상자 기준)' : 'Skillshot path (from hitbox)')
                             : g.label],
    g.shape === 'skillshot'
      ? [ko ? '판정 폭 × 두께' : 'Hitbox width × depth', g.width + ' × ' + g.depth] : null,
    g.shapeNote === 'arc'
      ? [ko ? '도형 보정' : 'Shape corrected',
         ko ? '위키는 Circle 로 적었지만 각도가 있어 부채꼴로 그림'
            : 'Wiki says Circle but an arc is given, so drawn as a cone'] : null,
    g.repeat ? [ko ? '연속 폭발' : 'Repeat',
                (ko ? '%d회 · 간격 %s' : '%d hits · %s apart')
                  .replace('%d', g.repeat.count).replace('%s', g.repeat.spacing)] : null,
    [ko ? '시전자 충돌 반지름' : 'Caster radius', casterRadius.toFixed(3)],
    g.range != null ? [ko ? '시전 사거리' : 'Range', String(g.range)] : null,
    g.global ? [ko ? '시전 사거리' : 'Range', ko ? '전역' : 'Global'] : null,
    g.noRange ? [ko ? '시전 사거리' : 'Range',
                 (ko ? '없음 · ' : 'None · ') + AOE_NO_RANGE[g.noRange][ko ? 'ko' : 'en']] : null,
  ].filter(Boolean).concat(rows.filter(r => /반경|각도|너비|높이|판정|Radius|Arc|Width|Height|Hitbox/.test(r[0])));

  document.getElementById('aoe-title').textContent = name;
  document.getElementById('aoe-sub').textContent =
    ko ? '게임 단위 실척 · 격자 1칸 = 1단위' : 'To scale in game units · 1 grid = 1 unit';
  document.getElementById('aoe-body').innerHTML =
    aoeSvg(g, casterRadius, hero.innerRadius) +
    `<div class="aoe-legend">
      <span><i class="aoe-key" style="background:#eee"></i>${ko ? '시전자' : 'Caster'}${
        hero.innerRadius && Math.abs(hero.innerRadius - casterRadius) > 0.01
          ? (ko ? ' (실선 충돌 · 점선 피격)' : ' (solid = collision, dashed = hitbox)') : ''}</span>
      ${g.range ? `<span><i class="aoe-key" style="background:#00d4ff;opacity:0.5"></i>${
        ko ? '시전 가능 영역' : 'Castable area'}</span>` : ''}
      <span><i class="aoe-key" style="background:#ff5f5f"></i>${ko ? '피해 범위' : 'Area of effect'}</span>
      ${g.shape === 'skillshot' ? `<span><i class="aoe-key" style="background:#ffd700"></i>${
        ko ? '투사체 판정 상자' : 'Projectile hitbox'}</span>` : ''}
      <span><i class="aoe-key" style="background:#8a8a95"></i>${
        ko ? '크기 기준자' : 'Size gauge'}</span>
    </div>
    <div class="aoe-grid-facts wiki-grid" style="margin-top:10px;">${
      facts.map(f => `<div class="wiki-row"><span class="k">${escapeWiki(f[0])}</span>` +
        `<span class="v">${escapeWiki(f[1])}</span></div>`).join('')}</div>
    <div class="aoe-note">${ko
      ? '<b>기준점 주의.</b> 사거리를 시전자 중심에서 재는지 몸통 가장자리에서 재는지는 ' +
        '스킬마다 다르다(게임 XML 의 RangeUseCasterRadius). 차이는 위 시전자 원의 반지름만큼이다. ' +
        '기본 공격 사거리는 서로의 몸통을 빼고 잰다.'
      : '<b>Reference point.</b> Whether range is measured from the caster\\'s center or its ' +
        'edge varies per ability (RangeUseCasterRadius in the game XML). The difference is the ' +
        'caster circle drawn above. Basic attack range is measured edge to edge.'}</div>`;
  document.getElementById('aoe-modal').classList.add('open');
}

function aoeNameOf(buttonId) {
  const hero = getActiveData()[currentHeroId];
  if (!hero) return null;
  let found = null;
  const scan = list => (list || []).forEach(a => { if (a.buttonId === buttonId) found = a.name; });
  Object.values(hero.abilities || {}).forEach(scan);
  Object.values(hero.talents || {}).forEach(scan);
  (hero.subAbilities || []).forEach(s => Object.values(s).forEach(
    groups => Object.values(groups).forEach(scan)));
  return found;
}

function closeAoe() { document.getElementById('aoe-modal').classList.remove('open'); }

// 아이콘을 눌러도 열리게 한다. 카드가 다시 그려져도 살아 있도록 위임으로 붙인다.
document.addEventListener('click', e => {
  const card = e.target.closest && e.target.closest('.ability-item, .talent-card');
  if (!card) return;
  const holder = card.querySelector('.wiki-fields[data-aoe]');
  if (!holder) return;
  if (e.target.tagName === 'IMG' || e.target.closest('.aoe-open')) {
    openAoe(holder.getAttribute('data-aoe'), currentHeroId);
  }
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeAoe(); });

// ---- 기본 공격 유형 -------------------------------------------------------
// 게임 XML 무기 정의에서 뽑았다. 백과사전 데이터에는 사거리·주기·피해량만 있고
// "어떻게 때리는가"가 없어서 따로 만든 것이다.
const attackTypes = __ATTACK_TYPES__;

function attackTypeStats(h) {
  const ko = currentLang === 'ko';
  const list = attackTypes.heroes[h.hyperlinkId];
  // 무기가 하위 유닛에만 있는 영웅(길 잃은 바이킹)도 평타 광역은 보여줘야 한다
  if (!list || !list.length) return attackAoeStat(h, ko);
  const many = list.length > 1;
  return list.map((a, i) => {
    const parts = [
      ko ? (a.melee ? '근접' : '원거리') : (a.melee ? 'Melee' : 'Ranged'),
      ko ? (a.missile ? '투사체' : '즉발') : (a.missile ? 'Projectile' : 'Instant'),
    ];
    if (a.talentSplash) parts.push(ko ? '광역 가능(특성)' : 'Splash via talent');
    const splash = (attackTypes.attackAoe || {})[h.hyperlinkId];
    if (splash) parts.push(ko ? '광역 평타' : 'Cleaving attack');
    return {
      l: (ko ? '공격 유형' : 'Attack type') + (many ? ` ${i + 1}` : ''),
      v: parts.map(p => `<span class="atk-tag">${p}</span>`).join(''),
      g: 0,
    };
  }).concat(attackAoeStat(h, ko));
}

// 평타 자체가 광역인 영웅은 그 모양과 크기를 한 줄 더 붙인다.
function attackAoeStat(h, ko) {
  const splash = (attackTypes.attackAoe || {})[h.hyperlinkId];
  if (!splash) return [];
  const size = splash.shape === 'radial'
    ? `${ko ? '부채꼴' : 'Cone'} ${splash.radius} · ${splash.arc}${ko ? '도' : '°'}`
    : `${ko ? '직사각형' : 'Rect'} ${splash.width} × ${splash.height}`;
  const who = splash.unit ? ` (${splash.unit})` : '';
  return [{
    l: (ko ? '평타 광역' : 'Attack area'),
    v: `<span class="atk-tag">${size}</span>` +
       `<span style="color:#7a7a88;font-size:11px">${(splash.label || '') + who}</span>`,
    g: 0,
  }];
}
"""


def replace_once(text, old, new, label=""):
    """기존 코드를 고쳐 쓴다. 이미 고쳐진 파일이면 조용히 넘어간다(재실행 안전)."""
    if new in text:
        return text
    if text.count(old) != 1:
        raise SystemExit("수정 지점이 %d 곳입니다(1곳이어야 함): %s"
                         % (text.count(old), label or old[:60]))
    return text.replace(old, new)


PLACEHOLDER = re.compile(r"__[A-Z_]+__")


def fill_placeholders(script, values):
    """스크립트의 __NAME__ 자리를 채우고, 하나라도 남으면 멈춘다.

    빠뜨린 자리는 그대로 JS 로 나가 페이지에서 ReferenceError 를 낸다. 조용히
    깨진 결과물을 내보내느니 여기서 멈추는 편이 낫다.
    """
    for name, value in values.items():
        script = script.replace(name, value)
    left = PLACEHOLDER.findall(script)
    if left:
        raise SystemExit("채우지 못한 자리표시자: %s" % ", ".join(sorted(set(left))))
    return script


def patch(text, marker, addition, where="after", label=""):
    """marker 를 찾아 그 앞/뒤에 addition 을 끼워 넣는다."""
    if marker not in text:
        raise SystemExit("삽입 지점을 찾지 못했습니다: %s" % (label or marker[:60]))
    if text.count(marker) != 1:
        raise SystemExit("삽입 지점이 %d 곳입니다(1곳이어야 함): %s"
                         % (text.count(marker), label or marker[:60]))
    return (text.replace(marker, marker + addition) if where == "after"
            else text.replace(marker, addition + marker))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default=SOURCE)
    parser.add_argument("-o", "--output", default=TARGET)
    args = parser.parse_args()

    html = inject(unwrap_all(open(args.input, encoding="utf-8").read()))
    with open(args.output, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("%s\n  -> %s (%.1f MB)"
          % (args.input, args.output, os.path.getsize(args.output) / 1048576))


def inject(html):
    with open(FIELDS, encoding="utf-8") as fh:
        data = fh.read()
    with open(ATTACKS, encoding="utf-8") as fh:
        attacks = fh.read()
    with open(GLOSSARY_BODY, encoding="utf-8") as fh:
        # HTML 을 JS 문자열로 넣는다. 따옴표·역따옴표가 섞여 있어 json 으로 감싼다.
        glossary = json.dumps(fh.read(), ensure_ascii=False)

    # 1. CSS
    html = patch(html, "\n</style>", wrap(CSS, html=True), where="before", label="</style>")

    # 2. 설정 패널 토글
    html = patch(
        html,
        '<label><input type="checkbox" data-sec="portraits"',
        wrap(TOGGLE_LABEL + "\n  ", html=True),
        where="before", label="설정 패널")

    # 3. toggles 기본값
    html = patch(html, "talents:true,", wrap(" wikifields:true,"), label="toggles 기본값")

    # 3-1. 범위 그림을 띄울 모달 (한 번만 만들어 두고 내용만 갈아 끼운다)
    html = patch(html, "\n</body>", wrap(MODAL, html=True), where="before", label="</body>")

    # 3-2. 좌측 상단, 제목 옆에 용어집 버튼
    html = patch(
        html,
        '<span class="meta">Build',
        wrap(HOME_BUTTON + " " + GLOSSARY_BUTTON + " ", html=True),
        where="before", label="좌측 상단 메인·용어집 버튼")

    # 3-3. 상단 바에 바로가기. 특성 찍기 링크는 원본에 이미 있으므로 그 앞에 끼운다.
    html = patch(
        html,
        '    <a class="set-btn builder-link" id="builder-link"',
        wrap(TOP_LINKS + "\n", html=True),
        where="before", label="상단 바 바로가기")

    # 4. 데이터 + 렌더 함수
    html = patch(
        html,
        "function renderAbilityItem(",
        wrap(fill_placeholders(SCRIPT, {
            "__WIKI_FIELDS__": data,
            "__ATTACK_TYPES__": attacks,
            "__GLOSSARY_BODY__": glossary,
            "__PART_COLORS__": json.dumps(
                DRAWING.get("partColors") or ["#ff5f5f", "#ffb84a", "#4aa3ff"]),
        }) + "\n"),
        where="before", label="renderAbilityItem 앞")

    # 5. 스킬 카드에 삽입 (관련 특성 칩 위)
    html = patch(
        html,
        "      ${linkedTalents.length?`<div class=\"desc-label\"",
        wrap("      ${renderWikiFields(a, currentHeroId)}\n", html=True),
        where="before", label="스킬 카드")

    # 6. 특성 카드에 삽입
    html = patch(
        html,
        "          <div class=\"td\">${processTooltip(t.fullTooltip||t.shortTooltip||'')}</div>",
        wrap("\n          ${renderWikiFields(t, currentHeroId)}", html=True),
        label="특성 카드")

    html = shift_levels(html)
    html = extra_stats(html)
    return html


# --------------------------------------------------------------------------
# 레벨 0 기준으로 곡선을 한 칸 민다
# --------------------------------------------------------------------------
def shift_levels(html):
    """패치노트가 0레벨 기준이라 데이터 원값이 Lv0 이 되도록 지수를 바꾼다.

    바꾸기 전: 값(lv) = 기본값 x (1+성장률)^(lv-1)   -> Lv1 이 데이터 원값
    바꾼 뒤:   값(lv) = 기본값 x (1+성장률)^lv       -> Lv0 이 데이터 원값
    """
    html = replace_once(
        html,
        "  return (Math.pow(1 + (scale||0), lv - 1) - 1) * 100;",
        "  return (Math.pow(1 + (scale||0), lv) - 1) * 100;",
        "totalGrowthPct")
    html = replace_once(
        html,
        "  return (base * Math.pow(1 + (scale||0), lv-1)).toFixed(0);",
        "  return (base * Math.pow(1 + (scale||0), lv)).toFixed(0);",
        "calcScaled")
    html = replace_once(
        html,
        "    const val = base * Math.pow(1 + rate, currentLevel - 1);",
        "    const val = base * Math.pow(1 + rate, currentLevel);",
        "processTooltip 수치 계산")

    # 성장 폭을 견주는 기준선도 Lv1 에서 Lv0 으로 내려간다
    html = html.replace("Lv1${currentLang==='ko'?'대비':'→'}",
                        "Lv0${currentLang==='ko'?'대비':'→'}")

    # 슬라이더를 0 부터 시작하게 하고 눈금 위치를 다시 계산한다 (이제 0~30, 31칸)
    ticks = "".join(
        '            <span class="tick highlight" '
        'style="left:calc(8px + (100%% - 16px) * %.5f);">%d</span>\n' % (lv / 30, lv)
        for lv in (0, 1, 4, 7, 10, 13, 16, 20, 30))
    def slider(minimum, tail=""):
        return ('          <input type="range" min="%s" max="30" value="${currentLevel}" '
                'oninput="updateLevel(this.value)">\n'
                '          <div class="slider-ticks">\n' % minimum) + tail

    new_slider = slider("0", ticks)
    # 이미 고친 파일이면 min="0" 형태로 남아 있다 (재실행 안전)
    head = next((s for s in (slider("1"), slider("0")) if s in html), None)
    if head is None:
        raise SystemExit("레벨 슬라이더를 찾지 못했습니다")
    start = html.index(head)
    end = html.index("          </div>\n", start)
    if html[start:end] != new_slider:
        html = html[:start] + new_slider + html[end:]
    return html


# --------------------------------------------------------------------------
# 능력치 칸: 반지름 두 가지와 기본 공격 유형
# --------------------------------------------------------------------------
def extra_stats(html):
    return replace_once(
        html,
        "  if (h.radius) sArr.push({l: currentLang==='ko'?'피격 반지름':'Radius', "
        "v: h.radius.toFixed(2), g: 0});",
        "  if (h.radius) sArr.push({l: currentLang==='ko'?'충돌 반지름 (Radius)':'Radius', "
        "v: h.radius.toFixed(2), g: 0});\n"
        "  if (h.innerRadius) sArr.push({l: currentLang==='ko'?'피격 반지름 (Inner Radius)'"
        ":'Inner Radius', v: h.innerRadius.toFixed(2), g: 0});\n"
        "  attackTypeStats(h).forEach(s => sArr.push(s));",
        "반지름·공격 유형")


if __name__ == "__main__":
    main()
