import json
import os
import glob
import re
from datetime import datetime

def generate_encyclopedia():
    search_dirs = ['.', 'data', 'json', 'assets', 'source']
    ko_files, en_files = [], []
    for d in search_dirs:
        ko_files += glob.glob(os.path.join(d, '*kokr*.json'))
        en_files += glob.glob(os.path.join(d, '*enus*.json'))
    if not ko_files or not en_files:
        print("오류: 데이터 JSON 파일을 찾을 수 없습니다. (현재 폴더 또는 data/json/assets/source 폴더를 확인)")
        return

    ko_path = max(ko_files, key=os.path.getmtime)
    en_path = max(en_files, key=os.path.getmtime)

    # 패치(빌드) 번호는 파일명에서 추출 (예: herodata_97039_kokr.json -> 97039)
    m = re.search(r'(\d{4,6})', os.path.basename(ko_path))
    patch_build = m.group(1) if m else "Unknown"

    with open(ko_path, 'r', encoding='utf-8') as f:
        data_ko = json.load(f)
    with open(en_path, 'r', encoding='utf-8') as f:
        data_en = json.load(f)

    hero_list = []
    for h_id, v_ko in data_ko.items():
        if 'name' not in v_ko:
            continue
        v_en = data_en.get(h_id, {})
        hero_list.append({
            "id": h_id,
            "name_ko": v_ko['name'],
            "name_en": v_en.get('name', h_id),
            "role": v_ko.get('expandedRole', ''),
            "franchise": v_ko.get('franchise', ''),
            "type": v_ko.get('type', ''),
            "rarity": v_ko.get('rarity', ''),
        })
    hero_list = sorted(hero_list, key=lambda x: x['name_ko'])

    now = datetime.now()
    timestamp = now.strftime("%y%m%d_%H%M")
    output_file = f"encyclopedia_{timestamp}.html"
    img_base = "https://raw.githubusercontent.com/SIN0NIS/images/main/abilitytalents/"
    portrait_base = "https://raw.githubusercontent.com/SIN0NIS/images/main/heroportraits/"
    unit_base = "https://raw.githubusercontent.com/SIN0NIS/images/main/units/"

    html_content = HTML_TEMPLATE.format(
        patch_build=patch_build,
        gen_date=now.strftime("%Y-%m-%d %H:%M"),
        data_ko=json.dumps(data_ko, ensure_ascii=False),
        data_en=json.dumps(data_en, ensure_ascii=False),
        hero_list=json.dumps(hero_list, ensure_ascii=False),
        img_base=img_base,
        portrait_base=portrait_base,
        unit_base=unit_base,
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    with open('hots_encyclopedia.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"--- 생성 완료: {output_file} (영웅 {len(hero_list)}명, 패치 빌드 {patch_build}) ---")
    print("--- index.html 도 함께 생성됨 (GitHub Pages 루트로 바로 서빙됨) ---")

    build_link_reference(data_ko, patch_build, now)
    return output_file


# ────────────────────────────────────────────────────────────────────────────
# 스킬 부모-자식 / 특수 연계 관계를 별도 파일로 정리 (HTML의 JS 로직(resolveLinks)과 동일 규칙)
# 필요한 예외 케이스가 더 있으면 아래 MANUAL_REPARENT_PY 와 make_encyclopedia.py 안의
# JS MANUAL_REPARENT 두 곳에 똑같이 추가해주면 된다.
# ────────────────────────────────────────────────────────────────────────────

MANUAL_REPARENT_PY = {
    "SamuroSelectSamuroPrime": {
        "parent": "SamuroIllusionMaster",
        "note_ko": "궁극기 '환영의 대가'를 선택해야 사용 가능",
        "note_en": "Usable only when the 'Illusion Master' heroic is chosen",
    },
    "SamuroSelectAll": {
        "parent": "SamuroIllusionMaster",
        "note_ko": "궁극기 '환영의 대가'를 선택해야 사용 가능",
        "note_en": "Usable only when the 'Illusion Master' heroic is chosen",
    },
    "TinkerFocusTurrets": {
        "parent": "TinkerRockItTurret",
        "note_ko": "설치된 '잘나가! 포탑'을 대상으로 사용",
        "note_en": "Used together with deployed 'Rock-it! Turret's",
    },
}

# 자식 nameId 기준 수동 오버라이드: 자동 탐지가 아예 불가능하거나(레벨20 보상 특성에
# abilityTalentLinkIds가 없는 경우 등) 이름이 겹쳐 혼동되는 케이스를 직접 등록.
MANUAL_CHILD_OVERRIDE_PY = {
    "WizardArchonPurePowerDisintegrate": {
        "parent": "WizardDisintegrate",
        "display_name_ko": "파열 (마인: 순수한 힘)",
        "display_name_en": "Disintegrate (Mine: Pure Power)",
        "note_ko": "Lv20 '마인: 순수한 힘' 특성 필요",
        "note_en": "Requires Lv20 talent 'Mine: Pure Power'",
    },
}


def _build_sub_map(unit):
    m = {}
    for entry in (unit.get('subAbilities') or []):
        for key, cats in entry.items():
            parent = key.split('|')[0]
            for cat_list in cats.values():
                for a in cat_list:
                    m.setdefault(parent, []).append(a)
    return m


def _known_ability_ids(abilities):
    ids = set()
    for cat in ['basic', 'heroic', 'trait', 'mount', 'activable', 'hearth', 'spray', 'voice']:
        for a in abilities.get(cat, []) or []:
            ids.add(a['nameId'])
    return ids


def _resolve_hero_links(hero):
    """hero(단일 영웅 dict, ko 데이터)의 최종 스킬 트리(links)를 계산.
    반환: list of {parent, parent_name, child, child_name, source, note_ko, note_en, nested_type}
    source: 'direct'(정상 subAbilities) | 'nameId-match' | 'name-match' | 'manual'
    """
    sub_map = _build_sub_map(hero)
    known_ids = _known_ability_ids(hero.get('abilities', {}))

    # 이름 조회용 (능력 목록 전체에서 nameId -> 표시이름)
    name_lookup = {}
    for cat in hero.get('abilities', {}).values():
        for a in cat:
            name_lookup.setdefault(a['nameId'], a['name'])
    for children in sub_map.values():
        for c in children:
            name_lookup.setdefault(c['nameId'], c['name'])

    links = []  # 최종 결과 누적

    # 0) 정상적으로 알려진 부모(known ability)에 바로 붙는 것들은 'direct'로 기록
    for parent_id, children in list(sub_map.items()):
        if parent_id in known_ids:
            for child in children:
                links.append({
                    'parent': parent_id, 'parent_name': name_lookup.get(parent_id, parent_id),
                    'child': child['nameId'], 'child_name': child['name'],
                    'source': 'direct', 'note_ko': '', 'note_en': '',
                })

    # 1) 고아 그룹 재배치 (nameId 다수결 매칭 -> 이름 매칭 순)
    all_talents = []
    for lv, talents in (hero.get('talents') or {}).items():
        lvnum = ''.join(ch for ch in lv if ch.isdigit())
        for t in talents:
            all_talents.append({'level': lvnum, 'name': t['name'], 'linkIds': t.get('abilityTalentLinkIds') or []})

    for parent_id in list(sub_map.keys()):
        if parent_id in known_ids:
            continue
        children = sub_map[parent_id]
        for child in children:
            override = MANUAL_CHILD_OVERRIDE_PY.get(child['nameId'])
            if override:
                links.append({
                    'parent': override['parent'], 'parent_name': name_lookup.get(override['parent'], override['parent']),
                    'child': child['nameId'],
                    'child_name': f"{child['name']} → {override['display_name_ko']}",
                    'source': 'manual-child', 'note_ko': override['note_ko'], 'note_en': override['note_en'],
                })
                continue
            target = None
            matched_talent = None
            source = None
            referencing = [t for t in all_talents if child['nameId'] in t['linkIds']]
            if referencing:
                tally = {}
                for t in referencing:
                    for id_ in t['linkIds']:
                        if id_ != child['nameId'] and id_ in known_ids:
                            tally[id_] = tally.get(id_, 0) + 1
                if tally:
                    target = max(tally, key=lambda k: tally[k])
                    candidates = [t for t in referencing if target in t['linkIds']]
                    matched_talent = max(candidates, key=lambda t: int(t['level'] or 0))
                    source = 'nameId-match'
            if not target:
                ability_names = set(name_lookup.values())
                for t in all_talents:
                    if t['name'] == child['name'] and t['linkIds'] and t['name'] not in ability_names:
                        target = t['linkIds'][0]
                        matched_talent = t
                        source = 'name-match'
                        break
            if target:
                note_ko = f"Lv{matched_talent['level']} '{matched_talent['name']}' 특성 필요"
                note_en = f"Requires Lv{matched_talent['level']} talent '{matched_talent['name']}'"
                links.append({
                    'parent': target, 'parent_name': name_lookup.get(target, target),
                    'child': child['nameId'], 'child_name': child['name'],
                    'source': source, 'note_ko': note_ko, 'note_en': note_en,
                })
            else:
                links.append({
                    'parent': None, 'parent_name': f"(미해결: {parent_id})",
                    'child': child['nameId'], 'child_name': child['name'],
                    'source': 'unresolved', 'note_ko': '', 'note_en': '',
                })

    # 2) 수동 예외 테이블
    for name_id, rule in MANUAL_REPARENT_PY.items():
        found = None
        for cat in ['basic', 'heroic', 'trait', 'mount', 'activable']:
            for a in hero.get('abilities', {}).get(cat, []) or []:
                if a['nameId'] == name_id:
                    found = a
        if not found:
            continue
        links.append({
            'parent': rule['parent'], 'parent_name': name_lookup.get(rule['parent'], rule['parent']),
            'child': name_id, 'child_name': found['name'],
            'source': 'manual', 'note_ko': rule['note_ko'], 'note_en': rule['note_en'],
        })

    return links


def build_link_reference(data_ko, patch_build, now):
    """모든 영웅의 스킬 부모-자식/특수 연계 관계를 JSON + Markdown으로 저장."""
    report = {}
    for hid, hero in data_ko.items():
        if 'name' not in hero:
            continue
        links = _resolve_hero_links(hero)
        if links:
            report[hid] = {'name': hero['name'], 'links': links}

    json_path = 'hots_ability_links.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'patch_build': patch_build,
            'generated': now.strftime('%Y-%m-%d %H:%M'),
            'manual_overrides': MANUAL_REPARENT_PY,
            'manual_child_overrides': MANUAL_CHILD_OVERRIDE_PY,
            'heroes': report,
        }, f, ensure_ascii=False, indent=2)

    md_lines = [
        f"# 히오스 스킬 연계 관계 참고 문서 (Build {patch_build})",
        f"생성일: {now.strftime('%Y-%m-%d %H:%M')}",
        "",
        "이 파일은 백과사전 HTML이 스킬을 어떻게 부모-자식으로 엮었는지 정리한 참고용 문서입니다.",
        "source 값 의미:",
        "- `direct`: 게임 데이터의 subAbilities가 이미 알려진 능력을 직접 가리키는 정상적인 경우",
        "- `nameId-match`: 특성의 abilityTalentLinkIds에 이 능력의 nameId가 직접 포함돼 있어 자동으로 부모를 추론한 경우",
        "- `name-match`: 위 방법으로 못 찾아서, 같은 이름의 특성을 보조 단서로 사용해 추론한 경우",
        "- `manual`: 데이터로는 추론이 불가능해 스크립트에 하드코딩으로 등록한 예외 (최상위 능력을 재배치)",
        "- `manual-child`: 데이터로는 추론이 불가능해 하드코딩으로 등록한 예외 (연계그룹의 자식 하나만 재배치, 표시 이름도 겹치지 않게 변경됨)",
        "- `unresolved`: 연계 능력인 것은 분명하지만 어떤 능력의 자식인지 자동으로 못 찾은 경우. 단, 이 부모(nameId)가 위 표의 다른 어딘가에 child로 재배치되어 있다면, 실제 페이지에서는 그 카드 밑에 자동으로 한 단계 더 중첩되어 표시됩니다 (예: 알라라크 '치명적인 돌진 사용'은 여기선 미해결이지만, 실제로는 '가학성 → 치명적인 돌진' 카드 밑에 다시 중첩됨).",
        "",
        "## 수동 예외 테이블 (MANUAL_REPARENT)",
        "",
        "| 능력 nameId | 부모로 지정 | 설명 |",
        "|---|---|---|",
    ]
    for name_id, rule in MANUAL_REPARENT_PY.items():
        md_lines.append(f"| `{name_id}` | `{rule['parent']}` | {rule['note_ko']} |")
    md_lines.append("")
    md_lines.append("## 수동 자식 오버라이드 테이블 (MANUAL_CHILD_OVERRIDE)")
    md_lines.append("")
    md_lines.append("| 능력 nameId | 부모로 지정 | 표시 이름 변경 | 설명 |")
    md_lines.append("|---|---|---|---|")
    for name_id, rule in MANUAL_CHILD_OVERRIDE_PY.items():
        md_lines.append(f"| `{name_id}` | `{rule['parent']}` | {rule['display_name_ko']} | {rule['note_ko']} |")
    md_lines.append("")
    md_lines.append("## 영웅별 연계 관계")
    md_lines.append("")

    for hid in sorted(report.keys(), key=lambda k: report[k]['name']):
        info = report[hid]
        md_lines.append(f"### {info['name']} (`{hid}`)")
        md_lines.append("")
        md_lines.append("| 부모 능력 | 자식(연계) 능력 | source | 설명 |")
        md_lines.append("|---|---|---|---|")
        for l in info['links']:
            parent_disp = f"{l['parent_name']} (`{l['parent']}`)" if l['parent'] else l['parent_name']
            child_disp = f"{l['child_name']} (`{l['child']}`)"
            note = l['note_ko'] or ''
            md_lines.append(f"| {parent_disp} | {child_disp} | {l['source']} | {note} |")
        md_lines.append("")

    md_path = 'hots_ability_links.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

    print(f"--- 연계 관계 참고 파일 생성 완료: {json_path}, {md_path} ---")



HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
<title>히오스 영웅 백과사전 - Build {patch_build}</title>
<style>
:root {{
  --p:#a333ff; --bg:#0b0b0d; --card:#16161a; --card2:#1c1c22; --blue:#00d4ff;
  --gold:#ffd700; --green:#3ddc84; --red:#ff5f5f; --gray:#8a8a95; --fs:14px;
  --q:#4aa3ff; --w:#ffb84a; --e:#4aff8f; --heroic:#ffd700; --trait:#c46bff; --z:#8a8a95; --active:#ff7b7b;
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:#eee; font-family:"Malgun Gothic",-apple-system,sans-serif; font-size:var(--fs); }}
a {{ color:var(--blue); }}
#top-bar {{ background:#000; padding:8px 14px; border-bottom:1px solid #2a2a2e; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:500; }}
#top-bar .title {{ font-weight:bold; color:var(--p); }}
#top-bar .meta {{ color:#777; font-size:11px; }}
.lang-btn, .set-btn {{ background:#222; color:#fff; border:1px solid var(--p); padding:5px 12px; border-radius:5px; cursor:pointer; font-size:12px; font-weight:bold; margin-left:6px; }}

#layout {{ display:flex; min-height:calc(100vh - 42px); }}
#sidebar {{ width:280px; flex-shrink:0; background:#131316; border-right:1px solid #2a2a2e; padding:12px; position:sticky; top:42px; height:calc(100vh - 42px); overflow-y:auto; }}
.search-box {{ width:100%; padding:10px; background:#222; color:white; border:1px solid var(--p); border-radius:6px; font-size:14px; outline:none; margin-bottom:8px; }}
.filter-row {{ display:flex; gap:4px; margin-bottom:10px; flex-wrap:wrap; }}
.filter-chip {{ background:#222; border:1px solid #333; color:#aaa; padding:3px 8px; border-radius:12px; font-size:11px; cursor:pointer; }}
.filter-chip.active {{ background:var(--p); color:#fff; border-color:var(--p); }}
.hero-count {{ color:#666; font-size:11px; margin-bottom:6px; }}
.hero-item {{ padding:8px 10px; border-radius:6px; cursor:pointer; display:flex; justify-content:space-between; align-items:center; }}
.hero-item:hover {{ background:#222; }}
.hero-item.active {{ background:var(--p); color:#fff; }}
.hero-item .r {{ font-size:10px; color:#888; }}
.hero-item.active .r {{ color:#eee; }}

#main {{ flex:1; padding:16px 22px 60px; max-width:980px; }}
#welcome {{ padding:60px 20px; text-align:center; color:#666; }}

.settings-panel {{ position:fixed; top:50px; right:12px; background:#1c1c22; border:1px solid var(--p); border-radius:8px; padding:14px; width:260px; z-index:900; display:none; box-shadow:0 6px 24px rgba(0,0,0,0.5); }}
.settings-panel h4 {{ margin:0 0 8px; color:var(--gold); font-size:13px; }}
.settings-panel label {{ display:flex; align-items:center; gap:8px; padding:4px 0; font-size:12.5px; color:#ddd; cursor:pointer; }}
.settings-panel input[type=checkbox] {{ accent-color: var(--p); width:15px; height:15px; }}
.settings-panel .hint {{ color:#777; font-size:10.5px; margin-top:8px; line-height:1.4; }}

.hero-header {{ display:flex; gap:16px; align-items:flex-start; margin-bottom:16px; }}
.portrait-img {{ width:96px; height:96px; border-radius:50%; border:2px solid var(--p); object-fit:cover; background:#000; flex-shrink:0; }}
.hero-title-block h1 {{ margin:0; font-size:26px; }}
.hero-title-block .subtitle {{ color:var(--gold); font-size:14px; margin-top:2px; }}
.tag-row {{ display:flex; gap:6px; flex-wrap:wrap; margin-top:8px; }}
.tag {{ background:#222; border:1px solid #333; padding:3px 9px; border-radius:12px; font-size:11px; color:#ccc; }}
.tag.diff {{ border-color:var(--red); color:var(--red); }}
.tag.rarity-Legendary {{ border-color:var(--gold); color:var(--gold); }}
.tag.rarity-Epic {{ border-color:#c46bff; color:#c46bff; }}
.tag.rarity-Rare {{ border-color:#4aa3ff; color:#4aa3ff; }}

.section {{ background:var(--card); border:1px solid #262630; border-radius:10px; margin-bottom:14px; overflow:hidden; }}
.section-head {{ padding:10px 14px; background:#1a1a20; border-bottom:1px solid #262630; font-weight:bold; color:var(--p); font-size:14px; display:flex; align-items:center; gap:6px; }}
.section-body {{ padding:14px; }}
.desc-text {{ line-height:1.6; color:#ccc; margin:0 0 8px; }}
.desc-label {{ color:#888; font-size:11px; text-transform:uppercase; letter-spacing:0.5px; margin-top:8px; }}

.rating-row {{ display:flex; align-items:center; gap:10px; margin:6px 0; }}
.rating-label {{ width:70px; color:#aaa; font-size:12px; flex-shrink:0; }}
.rating-bar-bg {{ flex:1; background:#000; border-radius:6px; height:10px; overflow:hidden; }}
.rating-bar-fill {{ height:100%; background:linear-gradient(90deg,var(--p),var(--blue)); border-radius:6px; }}
.rating-val {{ width:28px; text-align:right; color:#ddd; font-size:12px; font-weight:bold; }}

.level-row {{ display:flex; align-items:center; gap:10px; margin-bottom:4px; }}
.track-container {{ flex:1; position:relative; }}
.track-container input[type=range] {{
  width:100%; display:block; -webkit-appearance:none; appearance:none;
  height:6px; border-radius:3px; background:#333; outline:none; margin:0;
}}
.track-container input[type=range]::-webkit-slider-thumb {{
  -webkit-appearance:none; width:16px; height:16px; border-radius:50%;
  background:var(--gold); border:2px solid #000; cursor:pointer;
}}
.track-container input[type=range]::-moz-range-thumb {{
  width:16px; height:16px; border-radius:50%; background:var(--gold); border:2px solid #000; cursor:pointer;
}}
.track-container input[type=range]::-moz-range-track {{ height:6px; border-radius:3px; background:#333; }}
.level-badge {{ background:#000; border:1px solid var(--gold); color:var(--gold); padding:3px 10px; border-radius:5px; font-weight:bold; font-size:12px; min-width:52px; text-align:center; }}
.slider-wrapper {{ position:relative; margin-bottom:20px; }}
.slider-ticks {{ position:relative; height:14px; margin-top:4px; }}
.tick {{ font-size:10px; color:#666; position:absolute; top:0; transform:translateX(-50%); text-align:center; }}
.tick::before {{ content:'|'; display:block; font-size:8px; margin-bottom:-2px; color:#444; }}
.tick.highlight {{ color:var(--gold); font-weight:bold; }}
.growth-total {{ color:#8fd3ff; font-size:0.8em; margin-left:4px; }}

.stat-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(140px,1fr)); gap:8px; }}
.stat-item {{ background:#111; padding:8px 10px; border-radius:6px; }}
.stat-label {{ color:#888; font-size:11px; display:flex; justify-content:space-between; }}
.stat-value {{ color:#fff; font-weight:bold; font-size:17px; margin-top:2px; }}
.growth-tag {{ color:var(--green); }}
.dps-tag {{ color:var(--gold); font-size:11px; margin-left:4px; }}

.ability-group-title {{ font-size:12px; color:#888; text-transform:uppercase; letter-spacing:0.5px; margin:12px 0 6px; }}
.ability-group-title:first-child {{ margin-top:0; }}
.ability-item {{ display:flex; gap:10px; background:#111; padding:8px 10px; border-radius:8px; margin-bottom:6px; border-left:3px solid var(--gray); }}
.ability-item.type-Q {{ border-left-color:var(--q); }}
.ability-item.type-W {{ border-left-color:var(--w); }}
.ability-item.type-E {{ border-left-color:var(--e); }}
.ability-item.type-Heroic {{ border-left-color:var(--heroic); }}
.ability-item.type-Trait {{ border-left-color:var(--trait); }}
.ability-item.type-Z {{ border-left-color:var(--z); }}
.ability-item.type-Active {{ border-left-color:var(--active); }}
.ability-icon {{ width:36px; height:36px; border:1px solid #333; border-radius:6px; flex-shrink:0; background:#000; object-fit:contain; }}
.ability-item.nested {{ margin-top:-2px; background:#0d0d10; border-left-style:dashed; border-left-color:#444; opacity:0.92; position:relative; }}
.ability-item.nested::before {{ content:'↳'; position:absolute; left:-18px; top:8px; color:#555; font-size:14px; }}
.link-badge {{ font-size:10px; padding:1px 7px; border-radius:4px; background:#1a2e1a; color:#7dd87d; border:1px solid #2f4f2f; }}
.linked-talents {{ display:flex; flex-wrap:wrap; gap:5px; margin-top:6px; }}
.linked-talent-chip {{ display:flex; align-items:center; gap:4px; background:#000; border:1px solid #333; border-radius:12px; padding:4px 10px 4px 4px; font-size:10.5px; color:#9fd9ff; cursor:pointer; min-height:24px; -webkit-tap-highlight-color:rgba(255,215,0,0.3); }}
.linked-talent-chip:hover, .linked-talent-chip:active {{ border-color:var(--gold); background:#1a1a00; }}
.linked-talent-chip img {{ width:16px; height:16px; border-radius:3px; object-fit:contain; background:#111; }}
.linked-talent-chip .lv {{ color:var(--gold); font-weight:bold; }}
.ability-name-row {{ display:flex; align-items:center; gap:6px; flex-wrap:wrap; }}
.ability-type-badge {{ font-size:10px; padding:1px 6px; border-radius:4px; background:#000; color:#aaa; border:1px solid #333; }}
.state-badge {{ font-size:10px; padding:1px 7px; border-radius:4px; border:1px solid #333; }}
.state-badge.active {{ color:#3ddc84; border-color:#3ddc84; }}
.state-badge.passive {{ color:#8a8a95; border-color:#555; }}
.requires-note {{ display:inline-flex; align-items:center; gap:4px; background:#241a00; border:1px solid var(--gold); color:var(--gold); font-size:10.5px; padding:2px 8px; border-radius:10px; margin-top:6px; }}
.ability-name {{ font-weight:bold; color:#fff; }}
.ability-cd {{ color:var(--blue); font-size:11px; }}
.ability-desc {{ color:#bbb; font-size:12.5px; margin-top:3px; line-height:1.5; }}
.ability-charges {{ color:var(--gold); font-size:11px; }}

.subgroup-title {{ font-weight:bold; color:var(--blue); font-size:13px; margin:14px 0 6px; padding-top:10px; border-top:1px dashed #333; }}
.subgroup-title:first-child {{ margin-top:0; border-top:none; padding-top:0; }}
.unit-card {{ background:#111; border:1px solid #262630; border-radius:8px; padding:10px; margin-bottom:10px; }}
.unit-card-head {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
.unit-card-head img {{ width:32px; height:32px; border-radius:5px; border:1px solid #333; background:#000; object-fit:contain; }}
.unit-card-head .n {{ font-weight:bold; color:var(--gold); }}
.unit-mini-stats {{ display:flex; gap:12px; color:#999; font-size:11px; margin-bottom:6px; flex-wrap:wrap; }}

.talent-level-block {{ margin-bottom:14px; }}
.talent-level-head {{ display:flex; align-items:center; gap:8px; margin-bottom:6px; }}
.talent-level-num {{ background:var(--p); color:#fff; font-weight:bold; font-size:12px; padding:2px 9px; border-radius:12px; }}
.talent-row {{ display:flex; gap:8px; flex-wrap:wrap; }}
.talent-card {{ width:220px; background:#111; border:1px solid #262630; border-radius:8px; padding:8px; display:flex; gap:8px; transition:box-shadow 0.3s, border-color 0.3s; }}
.talent-card.talent-highlight {{ border-color:var(--gold); box-shadow:0 0 0 3px rgba(255,215,0,0.35); }}
.talent-card img {{ width:34px; height:34px; border-radius:5px; border:1px solid #333; flex-shrink:0; background:#000; object-fit:contain; }}
.talent-card .tn {{ font-weight:bold; font-size:12.5px; color:#fff; }}
.talent-card .td {{ font-size:11px; color:#aaa; margin-top:2px; line-height:1.4; }}

.chip-list {{ display:flex; flex-wrap:wrap; gap:6px; }}
.chip {{ background:#111; border:1px solid #262630; padding:4px 10px; border-radius:6px; font-size:11.5px; color:#bbb; }}
.tech-table {{ width:100%; border-collapse:collapse; font-size:12px; }}
.tech-table td {{ padding:5px 8px; border-bottom:1px solid #222; color:#bbb; vertical-align:top; }}
.tech-table td:first-child {{ color:#777; width:150px; white-space:nowrap; }}

.hidden-section {{ display:none !important; }}
.portrait-mini-grid {{ display:flex; flex-wrap:wrap; gap:10px; }}
.portrait-mini {{ text-align:center; }}
.portrait-mini img {{ width:64px; height:64px; object-fit:contain; border-radius:6px; border:1px solid #333; background:#000; }}
.portrait-mini div {{ font-size:10px; color:#777; margin-top:3px; }}

.home-intro {{ color:#888; font-size:13px; margin-bottom:18px; }}
.home-role-section {{ margin-bottom:26px; }}
.home-role-title {{ font-size:16px; font-weight:bold; color:var(--gold); border-bottom:1px solid #262630; padding-bottom:6px; margin-bottom:12px; display:flex; align-items:baseline; gap:8px; }}
.home-role-count {{ font-size:11px; color:#666; font-weight:normal; }}
.home-hero-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(84px,1fr)); gap:14px; }}
.home-hero-card {{ display:flex; flex-direction:column; align-items:center; gap:6px; cursor:pointer; padding:6px; border-radius:8px; text-align:center; }}
.home-hero-card:hover {{ background:#1a1a20; }}
.home-hero-portrait {{ width:64px; height:64px; border-radius:50%; border:2px solid #333; object-fit:cover; background:#111; }}
.home-hero-card:hover .home-hero-portrait {{ border-color:var(--p); }}
.home-hero-name {{ font-size:11.5px; color:#ddd; line-height:1.3; }}

/* ── 모바일 반응형 ── */
@media (max-width: 760px) {{
  #top-bar {{ flex-wrap:wrap; gap:6px; padding:8px 10px; }}
  #top-bar > div:last-child {{ display:flex; flex-wrap:wrap; gap:6px; }}
  #top-bar .meta {{ display:block; width:100%; margin-top:2px; }}
  .set-btn, .lang-btn {{ margin-left:0; padding:6px 10px; font-size:11.5px; }}

  #layout {{ flex-direction:column; min-height:0; }}
  #sidebar {{
    width:100%; height:auto; max-height:none; position:relative; top:0;
    border-right:none; border-bottom:1px solid #2a2a2e;
  }}
  #sidebar.collapsed #hero-list, #sidebar.collapsed .filter-row, #sidebar.collapsed .hero-count {{ display:none; }}
  #sidebar-toggle {{ display:flex; }}
  #main {{ max-width:100%; padding:14px 12px 60px; }}

  .settings-panel {{ right:8px; left:8px; width:auto; max-width:none; top:auto; }}
  .hero-header {{ flex-wrap:wrap; }}
  .stat-grid {{ grid-template-columns:repeat(2,1fr); }}
  .home-hero-grid {{ grid-template-columns:repeat(auto-fill,minmax(72px,1fr)); gap:10px; }}
  .home-hero-portrait {{ width:56px; height:56px; }}
  .talent-card {{ width:100%; }}
}}
#sidebar-toggle {{ display:none; align-items:center; justify-content:space-between; background:#1a1a20; padding:8px 10px; border-radius:6px; margin-bottom:8px; color:#ccc; font-size:12.5px; cursor:pointer; }}
</style>
</head>
<body>
<div id="top-bar">
  <div><span class="title" id="home-btn" onclick="showHome()" style="cursor:pointer;">📖 히오스 영웅 백과사전</span> <span class="meta">Build {patch_build} · 생성일 {gen_date}</span></div>
  <div>
    <a class="set-btn" href="https://github.com/SIN0NIS/Hots_encyclopedia" target="_blank" rel="noopener">🔗 GitHub</a>
    <a class="set-btn builder-link" id="builder-link" href="https://sin0nis.github.io/hots_talent_build_auto_git/hots_talent_build.html" target="_blank" rel="noopener">🧩 특성 찍기</a>
    <button class="set-btn" onclick="toggleSettings()">⚙ 표시 설정</button>
    <button class="lang-btn" onclick="toggleLanguage()">KO / EN</button>
  </div>
</div>

<div class="settings-panel" id="settings-panel">
  <h4>표시할 항목 선택</h4>
  <label><input type="checkbox" data-sec="overview" checked onchange="onToggleChange()"> 개요 (초상화·기본정보·설명)</label>
  <label><input type="checkbox" data-sec="ratings" checked onchange="onToggleChange()"> 평점 지표 (복잡도·피해량 등)</label>
  <label><input type="checkbox" data-sec="stats" checked onchange="onToggleChange()"> 능력치 (레벨별 계산)</label>
  <label><input type="checkbox" data-sec="abilities" checked onchange="onToggleChange()"> 기본 스킬 / 궁극기 / 특질</label>
  <label><input type="checkbox" data-sec="voicespray" onchange="onToggleChange()"> 스프레이·보이스 감정표현 (전 영웅 공통)</label>
  <label><input type="checkbox" data-sec="subunits" checked onchange="onToggleChange()"> 하위 유닛 (연계능력은 스킬 항목에 표시됨)</label>
  <label><input type="checkbox" data-sec="talents" checked onchange="onToggleChange()"> 특성 전체 목록</label>
  <label><input type="checkbox" data-sec="portraits" onchange="onToggleChange()"> 초상화 모음</label>
  <label><input type="checkbox" data-sec="extra" onchange="onToggleChange()"> 스킨·보이스라인·기술정보(ID)</label>
  <div class="hint">체크를 해제하면 해당 항목이 모든 영웅 페이지에서 숨겨집니다. 설정은 브라우저에 저장됩니다.</div>
</div>

<div id="layout">
  <div id="sidebar">
    <div id="sidebar-toggle" onclick="toggleSidebarCollapse()">
      <span id="sidebar-toggle-label">영웅 목록</span>
      <span id="sidebar-toggle-icon">▾</span>
    </div>
    <input type="text" id="hero-search" class="search-box" placeholder="영웅 검색 (초성 지원)..." oninput="handleSearch(this.value)">
    <div class="filter-row" id="role-filters"></div>
    <div class="hero-count" id="hero-count"></div>
    <div id="hero-list"></div>
  </div>
  <div id="main">
    <div id="welcome"></div>
    <div id="hero-page" style="display:none;"></div>
  </div>
</div>

<script>
const dataKO = {data_ko};
const dataEN = {data_en};
const heroList = {hero_list};
const imgBase = "{img_base}";
const portraitBase = "{portrait_base}";
const unitBase = "{unit_base}";
const FOLDER_URLS = {{ at: imgBase, hp: portraitBase, un: unitBase }};

// 이미지가 저장소 폴더마다 흩어져 있는 경우가 있어, 실패 시 다른 폴더를 순서대로 재시도한다.
// 그래도 모두 실패하면(백과사전 내 극소수 아이콘) 깨진 이미지 대신 자연스럽게 숨긴다.
function imgFallback(el) {{
  const tried = (el.dataset.tried || '').split(',').filter(Boolean);
  const order = (el.dataset.order || '').split(',').filter(Boolean);
  const name = el.dataset.name;
  const next = order.find(f => !tried.includes(f));
  if (!next) {{ el.style.display = 'none'; return; }}
  tried.push(next);
  el.dataset.tried = tried.join(',');
  el.src = FOLDER_URLS[next] + name;
}}
function iconTag(name, cls, order) {{
  if (!name) return '';
  order = order || ['at','un','hp'];
  const first = order[0];
  return `<img class="${{cls}}" src="${{FOLDER_URLS[first]}}${{name}}" loading="lazy" data-name="${{name}}" data-order="${{order.join(',')}}" data-tried="${{first}}" onerror="imgFallback(this)">`;
}}

let currentLang = 'ko', currentHeroId = null, currentLevel = 1, activeRoleFilter = null;
let toggles = {{overview:true, ratings:true, stats:true, abilities:true, voicespray:false, subunits:true, talents:true, portraits:false, extra:false}};

// ---- persistence ----
(function loadToggles() {{
  try {{
    const saved = JSON.parse(localStorage.getItem('hots_enc_toggles') || 'null');
    if (saved) toggles = Object.assign(toggles, saved);
  }} catch(e) {{}}
  document.querySelectorAll('.settings-panel input[type=checkbox]').forEach(cb => {{
    cb.checked = !!toggles[cb.dataset.sec];
  }});
}})();

function toggleSettings() {{
  const p = document.getElementById('settings-panel');
  p.style.display = (p.style.display === 'block') ? 'none' : 'block';
}}
function onToggleChange() {{
  document.querySelectorAll('.settings-panel input[type=checkbox]').forEach(cb => {{
    toggles[cb.dataset.sec] = cb.checked;
  }});
  localStorage.setItem('hots_enc_toggles', JSON.stringify(toggles));
  applyToggles();
}}
function applyToggles() {{
  Object.keys(toggles).forEach(k => {{
    document.querySelectorAll('.sec-' + k).forEach(el => {{
      el.classList.toggle('hidden-section', !toggles[k]);
    }});
  }});
}}

// "🔧 관련 특성" 칩을 누르면(모바일 탭 / PC 클릭 둘 다 동일한 click 이벤트로 처리됨)
// 특성 섹션이 꺼져 있으면 켠 다음, 해당 특성 카드로 부드럽게 스크롤하고 잠깐 반짝여서 위치를 알려준다.
function goToTalent(nameId) {{
  if (!toggles.talents) {{
    toggles.talents = true;
    const cb = document.querySelector('.settings-panel input[data-sec="talents"]');
    if (cb) cb.checked = true;
    localStorage.setItem('hots_enc_toggles', JSON.stringify(toggles));
    applyToggles();
  }}
  setTimeout(() => {{
    const el = document.getElementById('talent-' + nameId);
    if (!el) return;
    el.scrollIntoView({{behavior:'smooth', block:'center'}});
    el.classList.add('talent-highlight');
    setTimeout(() => el.classList.remove('talent-highlight'), 1600);
  }}, 60);
}}

function getActiveData() {{ return currentLang === 'ko' ? dataKO : dataEN; }}

function toggleLanguage() {{
  currentLang = (currentLang === 'ko') ? 'en' : 'ko';
  renderRoleFilters();
  handleSearch(document.getElementById('hero-search').value);
  if (currentHeroId) renderHeroPage(); else renderHomePage();
}}

const ROLE_ORDER_KO = ['전사','투사','근접 암살자','원거리 암살자','지원가','치유사'];

// 메인 화면: 역할군별로 초상화+이름을 쭉 나열. 사이드바 검색/필터와 별개로,
// 처음 들어왔을 때나 상단 타이틀(🏠)을 눌렀을 때 보여주는 진입 화면.
function renderHomePage() {{
  const data = getActiveData();
  const groups = {{}};
  heroList.forEach(h => {{
    const key = h.role || (currentLang==='ko'?'기타':'Other');
    (groups[key] = groups[key] || []).push(h);
  }});
  const order = Object.keys(groups).sort((a,b) => {{
    const ia = ROLE_ORDER_KO.indexOf(a), ib = ROLE_ORDER_KO.indexOf(b);
    return (ia===-1?99:ia) - (ib===-1?99:ib);
  }});
  let html = `<div class="home-intro">${{currentLang==='ko'?`영웅 ${{heroList.length}}명 · 역할군별로 살펴보세요.`:`${{heroList.length}} heroes · browse by role.`}}</div>`;
  order.forEach(role => {{
    const list = groups[role].slice().sort((a,b) => currentLang==='ko'
      ? a.name_ko.localeCompare(b.name_ko, 'ko')
      : a.name_en.localeCompare(b.name_en));
    html += `<div class="home-role-section">
      <div class="home-role-title">${{role}} <span class="home-role-count">${{list.length}}</span></div>
      <div class="home-hero-grid">`;
    list.forEach(h => {{
      const hd = data[h.id];
      const img = (hd && hd.portraits) ? (hd.portraits.heroSelect || hd.portraits.draftScreen || hd.portraits.loading) : '';
      html += `<div class="home-hero-card" onclick="selectHero('${{h.id}}')">
        ${{img?iconTag(img, 'home-hero-portrait', ['hp','un','at']):'<div class="home-hero-portrait"></div>'}}
        <div class="home-hero-name">${{currentLang==='ko'?h.name_ko:h.name_en}}</div>
      </div>`;
    }});
    html += `</div></div>`;
  }});
  document.getElementById('welcome').innerHTML = html;
}}

function showHome() {{
  currentHeroId = null;
  document.getElementById('hero-page').style.display = 'none';
  document.getElementById('welcome').style.display = 'block';
  document.getElementById('sidebar').classList.remove('collapsed');
  updateSidebarToggleLabel();
  const link = document.getElementById('builder-link');
  if (link) link.href = BUILDER_BASE_URL;
  renderHomePage();
  handleSearch(document.getElementById('hero-search').value);
}}

function getChosung(str) {{
  const cho = ["ㄱ","ㄲ","ㄴ","ㄷ","ㄸ","ㄹ","ㅁ","ㅂ","ㅃ","ㅅ","ㅆ","ㅇ","ㅈ","ㅉ","ㅊ","ㅋ","ㅌ","ㅍ","ㅎ"];
  let res = "";
  for (let i=0; i<str.length; i++) {{
    let c = str.charCodeAt(i) - 44032;
    if (c >= 0 && c < 11172) res += cho[Math.floor(c/588)];
    else res += str.charAt(i);
  }}
  return res;
}}

function renderRoleFilters() {{
  const roles = [...new Set(heroList.map(h => h.role).filter(Boolean))].sort();
  let html = `<div class="filter-chip ${{activeRoleFilter===null?'active':''}}" onclick="setRoleFilter(null)">전체</div>`;
  roles.forEach(r => {{
    html += `<div class="filter-chip ${{activeRoleFilter===r?'active':''}}" onclick="setRoleFilter('${{r}}')">${{r}}</div>`;
  }});
  document.getElementById('role-filters').innerHTML = html;
}}
function setRoleFilter(r) {{
  activeRoleFilter = r;
  renderRoleFilters();
  handleSearch(document.getElementById('hero-search').value);
}}

function handleSearch(v) {{
  const s = (v||"").toLowerCase().replace(/\s/g, "");
  const choInput = getChosung(s);
  let fil = heroList.filter(h => {{
    const n_ko = h.name_ko.toLowerCase().replace(/\s/g, "");
    const n_en = h.name_en.toLowerCase().replace(/\s/g, "");
    return n_ko.includes(s) || n_en.includes(s) || getChosung(n_ko).includes(choInput);
  }});
  if (activeRoleFilter) fil = fil.filter(h => h.role === activeRoleFilter);
  renderHeroListUI(fil);
}}

function renderHeroListUI(list) {{
  document.getElementById('hero-count').innerText = `${{list.length}}명 표시 중 (전체 ${{heroList.length}}명)`;
  document.getElementById('hero-list').innerHTML = list.map(h => `
    <div class="hero-item ${{h.id===currentHeroId?'active':''}}" onclick="selectHero('${{h.id}}')">
      <span>${{currentLang==='ko'?h.name_ko:h.name_en}}</span>
      <span class="r">${{h.role}}</span>
    </div>`).join("");
}}

function selectHero(id) {{
  currentHeroId = id;
  currentLevel = 1;
  document.getElementById('welcome').style.display = 'none';
  document.getElementById('hero-page').style.display = 'block';
  handleSearch(document.getElementById('hero-search').value);
  updateBuilderLink(id);
  renderHeroPage();
  // 모바일에서는 영웅을 고르면 목록을 자동으로 접어서 바로 본문이 보이게 한다.
  if (window.innerWidth <= 760) {{
    document.getElementById('sidebar').classList.add('collapsed');
    updateSidebarToggleLabel();
    window.scrollTo({{top:0, behavior:'smooth'}});
  }}
}}

function toggleSidebarCollapse() {{
  document.getElementById('sidebar').classList.toggle('collapsed');
  updateSidebarToggleLabel();
}}
function updateSidebarToggleLabel() {{
  const collapsed = document.getElementById('sidebar').classList.contains('collapsed');
  document.getElementById('sidebar-toggle-icon').textContent = collapsed ? '▸' : '▾';
}}

const BUILDER_BASE_URL = "https://sin0nis.github.io/hots_talent_build_auto_git/hots_talent_build.html";
function updateBuilderLink(heroId) {{
  const link = document.getElementById('builder-link');
  if (!link) return;
  const h = dataKO[heroId];
  const hyperlinkId = (h && h.hyperlinkId) ? h.hyperlinkId : heroId;
  link.href = `${{BUILDER_BASE_URL}}?hero=${{encodeURIComponent(hyperlinkId)}}`;
}}

function totalGrowthPct(scale, lv) {{
  return (Math.pow(1 + (scale||0), lv - 1) - 1) * 100;
}}

// 데이터에는 "170 (+4% per level)"처럼 레벨 성장률이 고정 텍스트로 박혀 있고
// 실제 계산된 값이 아니다. 이를 파싱해서 현재 레벨 기준 실수치로 바꿔서 보여준다.
function processTooltip(t) {{
  if (!t) return "";
  let p = t.replace(/<[^>]*>?/gm, "").replace(/\n/g, "<br>");
  p = p.replace(/(\d+(?:\.\d+)?)\s*\(\+(\d+(?:\.\d+)?)%\s*per level\)/g, (m, baseStr, rateStr) => {{
    const base = parseFloat(baseStr);
    const rate = parseFloat(rateStr) / 100;
    const val = base * Math.pow(1 + rate, currentLevel - 1);
    const decimals = (baseStr.indexOf('.') === -1) ? 0 : 1;
    const totalPct = totalGrowthPct(rate, currentLevel);
    const totalTxt = totalPct > 0 ? ` · Lv1${{currentLang==='ko'?'대비':'→'}} +${{totalPct.toFixed(0)}}%` : '';
    return `<strong>${{val.toFixed(decimals)}}</strong><span class="growth-tag">(+${{(rate*100).toFixed(1)}}%/Lv${{totalTxt}})</span>`;
  }});
  return p;
}}

function calcScaled(base, scale, lv) {{
  return (base * Math.pow(1 + (scale||0), lv-1)).toFixed(0);
}}

function abilityTypeClass(t) {{
  if (['Q','W','E','Heroic','Trait','Z','Active'].includes(t)) return t;
  return 'Active';
}}

// isActive:false 이거나 isPassive:true면 패시브, 그 외(대부분의 Q/W/E/궁극기)는 액티브로 간주한다.
function isPassiveAbility(a) {{
  return a.isActive === false || a.isPassive === true;
}}

// 데이터만으로는 유추할 수 없는 예외 케이스(특정 궁극기를 선택해야만 쓸 수 있는 하위 명령 등)를
// 수동으로 등록해두는 테이블 (능력nameId -> 부모능력 nameId + 설명 문구).
// 필요한 영웅이 더 있으면 여기에 항목만 추가하면 된다.
const MANUAL_REPARENT = {{
  SamuroSelectSamuroPrime: {{ parent: 'SamuroIllusionMaster', note: {{
    ko: "궁극기 '환영의 대가'를 선택해야 사용 가능", en: "Usable only when the 'Illusion Master' heroic is chosen" }} }},
  SamuroSelectAll: {{ parent: 'SamuroIllusionMaster', note: {{
    ko: "궁극기 '환영의 대가'를 선택해야 사용 가능", en: "Usable only when the 'Illusion Master' heroic is chosen" }} }},
  TinkerFocusTurrets: {{ parent: 'TinkerRockItTurret', note: {{
    ko: "설치된 '잘나가! 포탑'을 대상으로 사용", en: "Used together with deployed 'Rock-it! Turret's" }} }},
}};

// 일부 서브 능력은 이름이 부모 스킬과 완전히 같아서(예: 리밍 '마인: 순수한 힘'의 '파열') 자동 매칭이
// 엉뚱한 특성('파열'이라는 이름의 레벨10 궁극기 선택지 자체)에 걸리기 쉽고, 또 이 기능을 실제로 여는
// 레벨20 보상 특성은 게임 데이터에 abilityTalentLinkIds가 비어 있어 자동 탐지가 아예 불가능하다.
// 이런 경우를 자식 nameId 기준으로 직접 등록해 부모를 지정하고, 표시 이름도 겹치지 않게 바꿔준다.
const MANUAL_CHILD_OVERRIDE = {{
  WizardArchonPurePowerDisintegrate: {{ parent: 'WizardDisintegrate',
    displayName: {{ ko: '파열 (마인: 순수한 힘)', en: 'Disintegrate (Mine: Pure Power)' }},
    note: {{ ko: "Lv20 '마인: 순수한 힘' 특성 필요", en: "Requires Lv20 talent 'Mine: Pure Power'" }} }},
}};

// subAbilities의 키(예: "MedivhTransformRaven|MedivhTransformRaven|Z")는
// "부모능력nameId|부모버튼id|타입" 형식이라 첫 토큰이 부모 능력의 nameId와 일치한다.
// 이를 이용해 "취소/변형/연계 능력"을 원래 능력 카드 밑에 자식으로 붙여준다.
function buildSubMap(hData) {{
  const map = {{}};
  (hData.subAbilities||[]).forEach(entry => {{
    Object.keys(entry).forEach(key => {{
      const parentNameId = key.split('|')[0];
      const cats = entry[key];
      Object.keys(cats).forEach(catKey => {{
        cats[catKey].forEach(a => {{
          (map[parentNameId] = map[parentNameId] || []).push(a);
        }});
      }});
    }});
  }});
  return map;
}}

// 특성 중 abilityTalentLinkIds로 특정 스킬을 언급하는 경우, 그 스킬이
// "이 특성을 찍어야 강화/변경되는 스킬"이라는 뜻이므로 역방향 맵을 만들어 보여준다.
function buildTalentLinkMap(hData) {{
  const map = {{}};
  Object.keys(hData.talents||{{}}).forEach(lv => {{
    const lvNum = lv.replace(/\D/g,'');
    (hData.talents[lv]||[]).forEach(t => {{
      (t.abilityTalentLinkIds||[]).forEach(linkId => {{
        (map[linkId] = map[linkId] || []).push({{level: lvNum, name: t.name, icon: t.icon, nameId: t.nameId}});
      }});
    }});
  }});
  return map;
}}

// 부모 nameId가 실제 최상위 능력이 아닌 "고아" 연계그룹(예: 데스윙 하늘붕괴)은
// 자식 능력의 이름과 똑같은 이름을 가진 특성을 찾아서, 그 특성이 강화하는 능력 밑으로 옮겨 붙인다.
// 또한 MANUAL_REPARENT에 등록된 예외 케이스(사무로 등)도 함께 적용한다.
function resolveLinks(hData, subMap) {{
  const skipTopLevel = new Set();
  const knownIds = new Set();
  const nameLookup = {{}};
  ['basic','heroic','trait','mount','activable','hearth','spray','voice'].forEach(k => {{
    (hData.abilities[k]||[]).forEach(a => {{ knownIds.add(a.nameId); nameLookup[a.nameId] = a.name; }});
  }});

  // 1) 고아 연계그룹 -> 자식의 nameId가 어떤 특성의 abilityTalentLinkIds에 들어있는지 먼저 찾고
  //    (있다면 같은 특성이 가리키는 다른 '진짜' 능력이 실제 부모), 없으면 이름이 일치하는 특성으로 보조 추론.
  //    이렇게 하면 알라라크의 "번개 쇄도 강화"나 "2번째 궁극기(가학성 경유)"처럼 여러 단계로
  //    이어지는 연계도 하드코딩 없이 자동으로 정리된다.
  const allTalents = [];
  Object.keys(hData.talents||{{}}).forEach(lv => {{
    const lvNum = lv.replace(/\D/g,'');
    (hData.talents[lv]||[]).forEach(t => allTalents.push({{level: lvNum, name: t.name, linkIds: t.abilityTalentLinkIds||[]}}));
  }});
  Object.keys(subMap).forEach(parentNameId => {{
    if (knownIds.has(parentNameId)) return; // 정상적인 경우, 손댈 필요 없음
    const children = subMap[parentNameId];
    const stillOrphan = [];
    children.forEach(child => {{
      let target = null, matchedTalent = null;
      // 1-0) 수동 자식 오버라이드 (최우선)
      const override = MANUAL_CHILD_OVERRIDE[child.nameId];
      if (override) {{
        (subMap[override.parent] = subMap[override.parent] || []).push(
          Object.assign({{}}, child, {{ _requiresNote: override.note, _displayName: override.displayName }})
        );
        return;
      }}
      // 1-a) nameId 직접 매칭 (가장 신뢰도 높음). 단, 이 자식 nameId를 언급하는 특성이 여러 개일 수 있고
      // (예: 데미지만 버프하는 무관한 특성들도 같이 걸려있는 경우) 그중 첫 번째가 우연히 엉뚱한 능력을
      // 가리킬 수 있어, 언급된 모든 특성에서 "다른 진짜 능력" 후보를 집계해 가장 많이 겹치는 것을 택한다.
      const referencing = allTalents.filter(t => t.linkIds.includes(child.nameId));
      if (referencing.length) {{
        const tally = {{}};
        referencing.forEach(t => {{
          t.linkIds.forEach(id => {{
            if (id !== child.nameId && knownIds.has(id)) tally[id] = (tally[id]||0) + 1;
          }});
        }});
        const ranked = Object.keys(tally).sort((a,b) => tally[b]-tally[a]);
        if (ranked.length) {{
          target = ranked[0];
          const candidates = referencing.filter(t => t.linkIds.includes(target));
          matchedTalent = candidates.reduce((best,t) => (parseInt(t.level) > parseInt(best.level) ? t : best), candidates[0]);
        }}
      }}
      // 1-b) 이름 문자열 매칭 (보조 수단). 단, 이름이 실제 능력과 완전히 같은 "궁극기 선택지 자체" 같은
      // 특성(예: 리밍 레벨10 '파열' - 그냥 궁극기 고르는 항목일 뿐 실제 강화 특성이 아님)은 제외한다.
      if (!target) {{
        const abilityNames = new Set(Object.values(nameLookup));
        const t2 = allTalents.find(t => t.name === child.name && t.linkIds.length && !abilityNames.has(t.name));
        if (t2 && t2.linkIds[0]) {{ target = t2.linkIds[0]; matchedTalent = t2; }}
      }}
      if (target) {{
        const note = {{
          ko: `Lv${{matchedTalent.level}} '${{matchedTalent.name}}' 특성 필요`,
          en: `Requires Lv${{matchedTalent.level}} talent '${{matchedTalent.name}}'`
        }};
        (subMap[target] = subMap[target] || []).push(Object.assign({{}}, child, {{_requiresNote: note}}));
      }} else {{
        stillOrphan.push(child);
      }}
    }});
    if (stillOrphan.length === 0) delete subMap[parentNameId];
    else subMap[parentNameId] = stillOrphan;
  }});

  // 2) 수동 예외 테이블 적용
  Object.keys(MANUAL_REPARENT).forEach(nameId => {{
    if (!knownIds.has(nameId)) return; // 이 영웅에게 해당 없음
    const rule = MANUAL_REPARENT[nameId];
    let found = null;
    ['basic','heroic','trait','mount','activable'].forEach(k => {{
      (hData.abilities[k]||[]).forEach(a => {{ if (a.nameId === nameId) found = a; }});
    }});
    if (!found) return;
    const tagged = Object.assign({{}}, found, {{_requiresNote: rule.note}});
    (subMap[rule.parent] = subMap[rule.parent] || []).push(tagged);
    skipTopLevel.add(nameId);
  }});

  return skipTopLevel;
}}

function renderAbilityItem(a, subMap, talentLinkMap, depth, ancestors, transformNote) {{
  subMap = subMap || {{}}; talentLinkMap = talentLinkMap || {{}};
  ancestors = ancestors || new Set();
  depth = depth || 0;
  const nested = depth > 0;
  const cls = abilityTypeClass(a.abilityType);
  const passive = isPassiveAbility(a);
  let extra = "";
  if (a.cooldownTooltip) extra += `<span class="ability-cd">${{a.cooldownTooltip}}</span>`;
  if (a.charges) extra += ` <span class="ability-charges">${{currentLang==='ko'?'충전':'Charges'}}: ${{a.charges.countMax}}</span>`;

  const linkedTalents = talentLinkMap[a.nameId] || [];
  let talentHtml = "";
  if (linkedTalents.length) {{
    talentHtml = `<div class="linked-talents">` + linkedTalents.map(lt => `
      <span class="linked-talent-chip" onclick="goToTalent('${{lt.nameId}}')"><span class="lv">Lv${{lt.level}}</span> ${{iconTag(lt.icon,'',['at','un','hp'])}}${{lt.name}}</span>
    `).join('') + `</div>`;
  }}

  const requiresNote = a._requiresNote ? `<div class="requires-note">🔓 ${{currentLang==='ko'?a._requiresNote.ko:a._requiresNote.en}}</div>` : '';
  const transformHtml = (transformNote && a.abilityType==='Trait') ? `<div class="requires-note">🔄 ${{currentLang==='ko'?transformNote.ko:transformNote.en}}</div>` : '';

  // 자식 능력 분류: 이름·설명이 부모와 완전히 같은 것(예: 굴단 '생명력 전환'의 특성 조건부 무료 버전)은
  // 다시 카드를 그리면 중복으로 보이므로 조건 문구만 압축해서 부모 카드에 붙이고,
  // 진짜 다른 연계 능력만 아래에 한 단계 더 들여써서 별도 카드로 그린다.
  const nextAncestors = new Set(ancestors);
  nextAncestors.add(a.nameId);
  const children = subMap[a.nameId];
  const conditionNotes = [];
  let childrenHtml = '';
  if (children && children.length) {{
    children.forEach(child => {{
      const isIdentical = child.name === a.name && (child.fullTooltip||'') === (a.fullTooltip||'');
      if (isIdentical) {{
        if (child._requiresNote) conditionNotes.push(child._requiresNote);
        return;
      }}
      if (child.nameId === a.nameId) {{
        childrenHtml += renderAbilityItem(child, {{}}, talentLinkMap, depth+1, nextAncestors);
        return;
      }}
      if (nextAncestors.has(child.nameId)) return;
      childrenHtml += renderAbilityItem(child, subMap, talentLinkMap, depth+1, nextAncestors);
    }});
    delete subMap[a.nameId]; // 같은 nameId를 가진 다른 카드(예: trait/heroic 중복 등)에서 중복 표시 방지
  }}
  const conditionHtml = conditionNotes.map(n => `<div class="requires-note">⚡ ${{currentLang==='ko'?'조건부 동일 효과: ':'Conditional same effect: '}}${{currentLang==='ko'?n.ko:n.en}}</div>`).join('');

  const html = `<div class="ability-item type-${{cls}}${{nested?' nested':''}}" style="${{nested?`margin-left:${{depth*24}}px;`:''}}">
    ${{iconTag(a.icon, 'ability-icon', ['at','un','hp'])}}
    <div style="flex:1;">
      <div class="ability-name-row">
        ${{nested?`<span class="link-badge">${{currentLang==='ko'?'↳ 연계':'↳ Linked'}}</span>`:''}}
        <span class="ability-type-badge">${{a.abilityType||''}}</span>
        <span class="state-badge ${{passive?'passive':'active'}}">${{passive?(currentLang==='ko'?'패시브':'Passive'):(currentLang==='ko'?'액티브':'Active')}}</span>
        <span class="ability-name">${{a._displayName ? (currentLang==='ko'?a._displayName.ko:a._displayName.en) : a.name}}</span>
        ${{extra}}
      </div>
      <div class="ability-desc">${{processTooltip(a.fullTooltip||a.description||a.shortTooltip||'')}}</div>
      ${{requiresNote}}
      ${{transformHtml}}
      ${{conditionHtml}}
      ${{linkedTalents.length?`<div class="desc-label" style="margin-top:6px;">${{currentLang==='ko'?'🔧 관련 특성 (이 스킬을 강화/변경)':'🔧 Related Talents'}}</div>${{talentHtml}}`:''}}
    </div>
  </div>`;

  return html + childrenHtml;
}}

function renderAbilityGroup(list, labelKo, labelEn, subMap, talentLinkMap, skipTopLevel, transformNote) {{
  if (!list || list.length===0) return "";
  skipTopLevel = skipTopLevel || new Set();
  const visible = list.filter(a => !skipTopLevel.has(a.nameId));
  if (visible.length===0) return "";
  let html = `<div class="ability-group-title">${{currentLang==='ko'?labelKo:labelEn}}</div>`;
  visible.forEach(a => html += renderAbilityItem(a, subMap, talentLinkMap, false, null, transformNote));
  return html;
}}

// 부모를 찾지 못한 연계 능력(드문 경우)은 별도로 모아서 보여준다.
function renderOrphanSubAbilities(hData, subMap) {{
  const parentIds = new Set();
  ['basic','heroic','trait','mount','activable','hearth','spray','voice'].forEach(k => {{
    (hData.abilities[k]||[]).forEach(a => parentIds.add(a.nameId));
  }});
  let html = "";
  Object.keys(subMap).forEach(parentNameId => {{
    if (parentNameId.startsWith('__used_')) return;
    if (parentIds.has(parentNameId)) return;
    subMap[parentNameId].forEach(a => html += renderAbilityItem(a, {{}}, {{}}, false));
  }});
  if (!html) return "";
  return `<div class="ability-group-title">${{currentLang==='ko'?'기타 연계 능력':'Other Linked Abilities'}}</div>` + html;
}}

function renderHeroUnits(hData) {{
  if (!hData.heroUnits || hData.heroUnits.length===0) return "";
  let html = `<div class="subgroup-title">${{currentLang==='ko'?'하위 유닛':'Hero Units'}}</div>`;
  hData.heroUnits.forEach(entry => {{
    Object.keys(entry).forEach(unitId => {{
      const u = entry[unitId];
      const img = (u.portraits && (u.portraits.targetInfo||u.portraits.minimap)) || '';
      html += `<div class="unit-card">
        <div class="unit-card-head">
          ${{img?iconTag(img, '', ['un','hp','at']):''}}
          <span class="n">${{u.name||unitId}}</span>
        </div>
        <div class="unit-mini-stats">
          ${{u.life?`<span>HP ${{Math.round(u.life.amount)}}</span>`:''}}
          ${{u.radius?`<span>Radius ${{u.radius}}</span>`:''}}
          ${{u.speed?`<span>Speed ${{u.speed}}</span>`:''}}
          ${{u.sight?`<span>Sight ${{u.sight}}</span>`:''}}
        </div>`;
      if (u.abilities) {{
        // 유닛 자체도 취소/연계 서브 능력(subAbilities)을 가질 수 있어(예: 라그나로스 화산 심장부의
        // '돌아가기 취소') 메인 영웅과 동일한 방식으로 자체 subMap을 만들어 중첩 표시한다.
        const unitSubMap = buildSubMap(u);
        ['basic','heroic','trait','mount','activable'].forEach(k => {{
          if (u.abilities[k]) u.abilities[k].forEach(a => html += renderAbilityItem(a, unitSubMap, {{}}, false));
        }});
      }}
      html += `</div>`;
    }});
  }});
  return html;
}}

function renderTalents(hData) {{
  const lvs = Object.keys(hData.talents).filter(l => hData.talents[l].length>0)
    .sort((a,b) => parseInt(a.replace(/\D/g,'')) - parseInt(b.replace(/\D/g,'')));
  let html = "";
  lvs.forEach(lv => {{
    const lvNum = lv.replace(/\D/g,'');
    html += `<div class="talent-level-block">
      <div class="talent-level-head"><span class="talent-level-num">Lv.${{lvNum}}</span></div>
      <div class="talent-row">`;
    hData.talents[lv].forEach(t => {{
      html += `<div class="talent-card" id="talent-${{t.nameId}}">
        ${{iconTag(t.icon, '', ['at','un','hp'])}}
        <div>
          <div class="tn">[${{t.abilityType}}] ${{t.name}}</div>
          <div class="td">${{processTooltip(t.fullTooltip||t.shortTooltip||'')}}</div>
        </div>
      </div>`;
    }});
    html += `</div></div>`;
  }});
  return html;
}}

function renderPortraits(hData) {{
  if (!hData.portraits) return "";
  let html = `<div class="portrait-mini-grid">`;
  Object.keys(hData.portraits).forEach(k => {{
    let v = hData.portraits[k];
    if (Array.isArray(v)) v = v[0];
    if (!v) return;
    html += `<div class="portrait-mini">${{iconTag(v, '', ['hp','un','at'])}}<div>${{k}}</div></div>`;
  }});
  html += `</div>`;
  return html;
}}

function updateLevel(lv) {{
  currentLevel = parseInt(lv);
  renderHeroPage(true);
}}

function renderHeroPage(keepScroll) {{
  if (!currentHeroId) return;
  const h = getActiveData()[currentHeroId];
  if (!h) return;

  const energyMap = {{ "Mana":"마나","Energy":"기력","Fury":"분노","Rage":"광기","Essence":"정수","Soul":"영혼","Focus":"집중","Brew":"취기" }};
  const w = (h.weapons && h.weapons[0]) || null;

  // ---- overview ----
  const loadingImg = h.portraits ? (h.portraits.heroSelect || h.portraits.draftScreen || h.portraits.loading) : '';
  let overviewHtml = `
    <div class="hero-header">
      ${{loadingImg?iconTag(loadingImg, 'portrait-img', ['hp','un','at']):''}}
      <div class="hero-title-block">
        <h1>${{h.name}}</h1>
        <div class="subtitle">${{h.title||''}}</div>
        <div class="tag-row">
          ${{h.expandedRole?`<span class="tag">${{h.expandedRole}}</span>`:''}}
          ${{h.type?`<span class="tag">${{h.type}}</span>`:''}}
          ${{h.franchise?`<span class="tag">${{h.franchise}}</span>`:''}}
          ${{h.difficulty?`<span class="tag diff">${{currentLang==='ko'?'난이도':'Difficulty'}}: ${{h.difficulty}}</span>`:''}}
          ${{h.rarity?`<span class="tag rarity-${{h.rarity}}">${{h.rarity}}</span>`:''}}
          ${{h.releaseDate?`<span class="tag">${{h.releaseDate}}</span>`:''}}
        </div>
      </div>
    </div>
    ${{h.description?`<p class="desc-text">${{h.description}}</p>`:''}}
    ${{h.infoText?`<div class="desc-label">${{currentLang==='ko'?'설정':'Lore'}}</div><p class="desc-text">${{h.infoText}}</p>`:''}}
  `;

  // ---- ratings ----
  let ratingsHtml = "";
  if (h.ratings) {{
    const labels = currentLang==='ko'
      ? {{complexity:'복잡도', damage:'피해량', survivability:'생존력', utility:'유틸리티'}}
      : {{complexity:'Complexity', damage:'Damage', survivability:'Survivability', utility:'Utility'}};
    Object.keys(labels).forEach(k => {{
      const val = h.ratings[k] || 0;
      ratingsHtml += `<div class="rating-row">
        <div class="rating-label">${{labels[k]}}</div>
        <div class="rating-bar-bg"><div class="rating-bar-fill" style="width:${{val*10}}%"></div></div>
        <div class="rating-val">${{val}}</div>
      </div>`;
    }});
  }}

  // ---- stats ----
  let statsHtml = "";
  const sArr = [];
  if (h.life) sArr.push({{l: currentLang==='ko'?'생명력':'HP', v: calcScaled(h.life.amount, h.life.scale, currentLevel), g: h.life.scale}});
  if (h.shield) sArr.push({{l: currentLang==='ko'?'보호막':'Shield', v: calcScaled(h.shield.amount, h.shield.scale, currentLevel), g: h.shield.scale}});
  if (h.energy && h.energy.type && h.energy.type !== 'None') {{
    const eName = currentLang==='ko' ? (energyMap[h.energy.type]||h.energy.type) : h.energy.type;
    const eScale = (h.energy.type === 'Mana') ? 0.04 : 0;
    sArr.push({{l: eName, v: calcScaled(h.energy.amount, eScale, currentLevel), g: eScale}});
  }}
  if (w) {{
    const dmg = parseFloat(calcScaled(w.damage, w.damageScale, currentLevel));
    const dps = (dmg / (w.period||1)).toFixed(1);
    sArr.push({{l: currentLang==='ko'?'공격력':'Attack', v: dmg + `<span class="dps-tag">(DPS ${{dps}})</span>`, g: w.damageScale}});
    sArr.push({{l: currentLang==='ko'?'공격 주기':'Period', v: (w.period||0).toFixed(2) + 's', g: 0}});
    sArr.push({{l: currentLang==='ko'?'사거리':'Range', v: (w.range||0).toFixed(1), g: 0}});
  }}
  if (h.radius) sArr.push({{l: currentLang==='ko'?'피격 반지름':'Radius', v: h.radius.toFixed(2), g: 0}});
  if (h.sight) sArr.push({{l: currentLang==='ko'?'시야':'Sight', v: h.sight.toFixed(1), g: 0}});
  if (h.speed) sArr.push({{l: currentLang==='ko'?'이동 속도':'Speed', v: h.speed.toFixed(2), g: 0}});
  statsHtml = `<div class="slider-wrapper">
      <div class="level-row">
        <span>${{currentLang==='ko'?'레벨':'Level'}}</span>
        <div class="track-container">
          <input type="range" min="1" max="30" value="${{currentLevel}}" oninput="updateLevel(this.value)">
          <div class="slider-ticks">
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 0);">1</span>
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 0.10345);">4</span>
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 0.20690);">7</span>
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 0.31034);">10</span>
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 0.41379);">13</span>
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 0.51724);">16</span>
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 0.65517);">20</span>
            <span class="tick highlight" style="left:calc(8px + (100% - 16px) * 1);">30</span>
          </div>
        </div>
        <span class="level-badge">Lv.${{currentLevel}}</span>
      </div>
    </div>
    <div class="stat-grid">` +
    sArr.map(s => {{
      const totalPct = s.g ? totalGrowthPct(s.g, currentLevel) : 0;
      return `<div class="stat-item">
        <div class="stat-label"><span>${{s.l}}</span><span class="growth-tag">${{s.g?('(+'+(s.g*100).toFixed(1)+'%/lv)'):''}}</span></div>
        <div class="stat-value">${{s.v}}${{totalPct>0?`<span class="growth-total">Lv1${{currentLang==='ko'?'대비':'→'}} +${{totalPct.toFixed(0)}}%</span>`:''}}</div>
      </div>`;
    }}).join("") + `</div>`;

  // ---- abilities ----
  const subMap = buildSubMap(h);
  const talentLinkMap = buildTalentLinkMap(h);
  const skipTopLevel = resolveLinks(h, subMap);
  let abilitiesHtml = "";
  abilitiesHtml += renderAbilityGroup(h.abilities.basic, '기본 스킬 (Q/W/E)', 'Basic Abilities', subMap, talentLinkMap, skipTopLevel);
  abilitiesHtml += renderAbilityGroup(h.abilities.heroic, '궁극기 (Heroic)', 'Heroic Abilities', subMap, talentLinkMap, skipTopLevel);
  const transformNote = (h.heroUnits && h.heroUnits.length) ? {{
    ko: `다른 형태로 변신 - 아래 '하위 유닛' 항목에서 변신 중 Q/W/E 확인 가능`,
    en: `Transforms into another form - see the 'Hero Units' section below for its Q/W/E`
  }} : null;
  abilitiesHtml += renderAbilityGroup(h.abilities.trait, '특질 (Trait)', 'Trait', subMap, talentLinkMap, skipTopLevel, transformNote);
  abilitiesHtml += renderAbilityGroup(h.abilities.mount, '이동기', 'Mount', subMap, talentLinkMap, skipTopLevel);
  abilitiesHtml += renderAbilityGroup(h.abilities.activable, '활성 능력', 'Activable', subMap, talentLinkMap, skipTopLevel);
  abilitiesHtml += renderAbilityGroup(h.abilities.hearth, '귀환', 'Hearth', subMap, talentLinkMap, skipTopLevel);
  abilitiesHtml += renderOrphanSubAbilities(h, subMap);
  const voiceSprayHtml = renderAbilityGroup(h.abilities.spray, '스프레이', 'Spray', subMap, talentLinkMap, skipTopLevel)
    + renderAbilityGroup(h.abilities.voice, '보이스', 'Voice', subMap, talentLinkMap, skipTopLevel);
  if (voiceSprayHtml) abilitiesHtml += `<div class="sec-voicespray">${{voiceSprayHtml}}</div>`;

  // ---- subunits (하위 유닛만 - 연계능력은 위 스킬 카드에 자식으로 붙어서 표시됨) ----
  let subunitsHtml = renderHeroUnits(h);
  if (!subunitsHtml.trim()) subunitsHtml = `<p style="color:#666;">${{currentLang==='ko'?'해당 없음':'None'}}</p>`;

  // ---- talents ----
  const talentsHtml = renderTalents(h);

  // ---- portraits ----
  const portraitsHtml = renderPortraits(h);

  // ---- extra (skins / voicelines / technical) ----
  let extraHtml = `<div class="subgroup-title">${{currentLang==='ko'?'스킨':'Skins'}}</div>
    <div class="chip-list">${{(h.skins||[]).map(s=>`<span class="chip">${{s}}</span>`).join("")}}</div>`;
  if (h.variationSkins && h.variationSkins.length) {{
    extraHtml += `<div class="subgroup-title">${{currentLang==='ko'?'변형 스킨':'Variation Skins'}}</div>
      <div class="chip-list">${{h.variationSkins.map(s=>`<span class="chip">${{s}}</span>`).join("")}}</div>`;
  }}
  extraHtml += `<div class="subgroup-title">${{currentLang==='ko'?'보이스라인':'Voice Lines'}} (${{(h.voiceLines||[]).length}})</div>
    <div class="chip-list">${{(h.voiceLines||[]).slice(0,40).map(s=>`<span class="chip">${{s}}</span>`).join("")}}</div>`;
  extraHtml += `<div class="subgroup-title">${{currentLang==='ko'?'기술 정보':'Technical Info'}}</div>
    <table class="tech-table">
      <tr><td>unitId</td><td>${{h.unitId||''}}</td></tr>
      <tr><td>hyperlinkId</td><td>${{h.hyperlinkId||''}}</td></tr>
      <tr><td>attributeId</td><td>${{h.attributeId||''}}</td></tr>
      <tr><td>scalingLinkId</td><td>${{h.scalingLinkId||''}}</td></tr>
      <tr><td>defaultMountId</td><td>${{h.defaultMountId||''}}</td></tr>
      <tr><td>units</td><td>${{(h.units||[]).join(', ')}}</td></tr>
      <tr><td>searchText</td><td style="color:#555;">${{h.searchText||''}}</td></tr>
    </table>`;

  const page = `
    <div class="section sec-overview">
      <div class="section-head">📋 ${{currentLang==='ko'?'개요':'Overview'}}</div>
      <div class="section-body">${{overviewHtml}}</div>
    </div>
    <div class="section sec-ratings">
      <div class="section-head">📊 ${{currentLang==='ko'?'평점 지표':'Ratings'}}</div>
      <div class="section-body">${{ratingsHtml}}</div>
    </div>
    <div class="section sec-stats">
      <div class="section-head">⚔️ ${{currentLang==='ko'?'능력치':'Stats'}}</div>
      <div class="section-body">${{statsHtml}}</div>
    </div>
    <div class="section sec-abilities">
      <div class="section-head">✨ ${{currentLang==='ko'?'스킬':'Abilities'}}</div>
      <div class="section-body">${{abilitiesHtml}}</div>
    </div>
    <div class="section sec-subunits">
      <div class="section-head">🧩 ${{currentLang==='ko'?'하위 유닛':'Hero Units'}}</div>
      <div class="section-body">${{subunitsHtml}}</div>
    </div>
    <div class="section sec-talents">
      <div class="section-head">🌟 ${{currentLang==='ko'?'특성 전체 목록':'All Talents'}}</div>
      <div class="section-body">${{talentsHtml}}</div>
    </div>
    <div class="section sec-portraits">
      <div class="section-head">🖼️ ${{currentLang==='ko'?'초상화 모음':'Portraits'}}</div>
      <div class="section-body">${{portraitsHtml}}</div>
    </div>
    <div class="section sec-extra">
      <div class="section-head">🗂️ ${{currentLang==='ko'?'스킨 · 보이스 · 기술정보':'Skins / Voice / Technical'}}</div>
      <div class="section-body">${{extraHtml}}</div>
    </div>
  `;
  document.getElementById('hero-page').innerHTML = page;
  applyToggles();
}}

renderRoleFilters();
handleSearch("");
renderHomePage();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    generate_encyclopedia()
