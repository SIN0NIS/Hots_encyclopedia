# 손으로 관리하는 파일

**파이프라인은 이 폴더를 읽기만 한다.** 절대 덮어쓰지 않으므로 게임이 패치되고
데이터를 새로 뽑아도 여기 적은 것은 그대로 남는다.

반대로 [07_localized/](../07_localized/) 는 매번 통째로 다시 만들어진다. 거기를
고치면 다음 빌드에 날아간다.

| 파일 | 무엇 | 언제 고치나 |
|---|---|---|
| [glossary.json](glossary.json) | 위키 상세 필드의 한글 표기 214개 | 새 용어가 리포트에 쌓였을 때 |
| [aoe_overrides.json](aoe_overrides.json) | 범위 그림 수동 보정 | 자동으로 못 그리거나 틀리게 그릴 때 |
| [name_overrides.json](name_overrides.json) | 스킬 이름 ↔ 게임 문자열 짝짓기 | 위키 표기가 게임과 다를 때 |
| [passive_flags.json](passive_flags.json) | 액티브/패시브 표시 스냅숏 | 새 영웅이 나왔을 때만 |
| [settings.json](settings.json) | 사이트 링크·크기 기준자·그리기 옵션 | 취향을 바꿀 때 |

---

## settings.json — 빌드 설정

코드가 아니라 **취향·정책**에 해당하는 값만 모았다. 수치를 바꾸고 다시 빌드하면
바로 반영된다.

| 칸 | 무엇 |
|---|---|
| `links` | 메인 페이지 카드와 백과사전 우측 상단 바로가기 주소 |
| `aoeGauges.weapons` | 범위 그림에 겹칠 크기 자로 쓸 무기 (사거리 값 자체는 XML 에서 읽는다) |
| `aoeDrawing.partColors` | 도형이 여럿인 스킬에서 조각마다 돌려 쓰는 색 |

주소는 예전에 두 파일에 따로 박혀 있어 한쪽만 고치면 어긋났다. 이제 한 곳뿐이다.

## glossary.json — 용어집

스킬·특성 카드 아래의 **위키 상세** 필드는 위키 편집자가 영어로 붙인 값이라
게임에 대응하는 한글이 없다. 그래서 표기를 여기서 정한다.

```
"terms": { "적용 대상": { "Self": "자신", ... }, "피해": { ... } }
```

갈래별로 묶여 있고, 백과사전의 **좌측 상단 📘 용어집** 버튼으로 전체를 볼 수 있다.
아직 옮기지 않은 표현은 [07_localized/report.md](../07_localized/report.md) 아래쪽에
빈도순으로 쌓인다 — 거기서 자주 나오는 것부터 채우면 된다.

## aoe_overrides.json — 범위 그림 보정

키는 게임 문자열 버튼 ID (백과사전의 `buttonId`). **붙일 곳을 못 찾으면 빌드가
경고**하므로 오타나 개명은 바로 드러난다.

```json
"HanzoDragonstrike": {
  "parts": [
    {"shape": "rectangle", "width": 9.0, "height": 24, "label": "바깥"},
    {"shape": "rectangle", "width": 3.0, "height": 24, "label": "중심"}
  ],
  "range": 8.0,
  "note": "폭 9.0 인 바깥 구역 안에 폭 3.0 인 중심 구역이 겹쳐 있다."
}
```

| 모양 | 필요한 값 |
|---|---|
| `circle` | radius |
| `radial` | radius, arc — 부채꼴. 꼭짓점이 시전자 |
| `ring` | inner, outer |
| `rectangle` | width(폭), height(시전 방향 길이) |
| `square` | width, height |
| `trapezoid` | inner, outer, height |
| `triangle` | side |
| `skillshot` | width, depth — 관통 경로 |
| `blade` | width, height, flat — 양 끝이 뾰족한 베기 자국. 기준점이 한가운데 |
| `polygon` | points — 꼭짓점 `[[x, y], …]`. 게임 XML 의 VertexArray 를 그대로 옮길 때 |
| `grow` | from, to, over, travel — 날아가며 커지는 판정. over 까지 커지고 그 뒤로는 그대로 |
| `sweep` | arc, thickness, from, to — 밖으로 퍼져 나가는 부채꼴 띠 |

공통으로 `range`(시전자로부터 거리), `note`(그림 아래 설명), `parts[]`(여러 도형 겹치기)를
쓸 수 있다.

조각(`parts[]`)에는 두 칸이 더 있다. **놓이는 자리와 나아가는 길이는 다른 값**이라
따로 적는다.

| 칸 | 무엇 |
|---|---|
| `at` | 기준점에서 이만큼 앞에 조각을 놓는다 |
| `range` | `at` 을 쓰면 거기서 제 힘으로 나아가는 길이 (관통 스킬), 안 쓰면 놓이는 자리 |
| `rotate` | 조각을 제 자리에서 이만큼(도) 돌린다 |
| `across` | 시전 방향과 직각으로 이만큼 밀어 놓는다 |
| `color` | 조각 색을 고정한다. 같은 효과를 쪼갠 경우 한 덩어리로 읽힌다 |

카시아 번개의 격노가 이 셋을 다 쓴다 — 창이 11.1 을 날아가 갈라지고, 갈라진 번개
둘이 그 자리에서 좌우 45도로 8.95 씩 더 나간다.

```json
"parts": [
  {"shape":"skillshot","width":0.6,"depth":1.25,"at":0,   "range":11.1},
  {"shape":"skillshot","width":0.6,"depth":1.0, "at":11.1,"range":8.95,"rotate":-45},
  {"shape":"skillshot","width":0.6,"depth":1.0, "at":11.1,"range":8.95,"rotate": 45}
]
```

특별한 두 칸이 있다.

- **`_attackAoe`** — 스킬이 아니라 **평타 자체가 광역**인 영웅. 범위 그림이 아니라
  능력치의 `평타 광역` 줄로 나간다. 키는 영웅 `hyperlinkId`
  (말티엘 사신의 징표, 밸로그의 검)
- **`_skip`** — **그리지 않을** 스킬. 위키에 수치가 있어도 실제 동작이 무작위거나
  지형을 따라가 그림이 거짓말을 하는 경우다 (머키 대행진, 라그나로스 용암 파도)

그림 상세 표에 `출처: 손으로 넣은 값` 줄이 붙어 자동과 구분된다.

## name_overrides.json — 이름 짝짓기

위키 표기가 게임 내 최신 명칭과 어긋날 때 게임 문자열 키를 직접 지정한다.
형식은 `"<위키 영웅명>|<위키 스킬명>": "<게임 문자열 키>"`.

머키 "Big Tuna Kahuna" 가 게임에서는 "조기 폭발" 로 바뀐 것 같은 경우다.

## passive_flags.json — 액티브/패시브 스냅숏

새 파서(HDP 5.x)가 더는 내지 않는 표시라, 마지막으로 제대로 된 백과사전에서 떠 둔
것이다. 새 영웅은 여기 없어서 액티브로 보인다. 다시 뜨려면:

```bash
python 00_scripts/adapt_herodata.py --dump-passives output/hots_encyclopedia_wiki.html
```
