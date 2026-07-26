# HotS Encyclopedia

히어로즈 오브 더 스톰 영웅 백과사전. 90명 전체 영웅의 스킬·특성·능력치·연계 관계를 한 페이지에서 볼 수 있는 정적 HTML 사이트입니다.

**바로 보기:** GitHub Pages로 배포하면 `https://<사용자명>.github.io/Hots_encyclopedia/` 에서 바로 열립니다 (`index.html`이 루트에 있음).

## 파일 구성

| 파일 | 설명 |
|---|---|
| `index.html` / `hots_encyclopedia.html` | 완성된 백과사전 (동일한 내용, 두 이름 모두로 접근 가능) |
| `make_encyclopedia.py` | 패치 데이터(JSON)로부터 위 HTML을 생성하는 스크립트 |
| `hots_ability_links.md` | 스킬 부모-자식 / 특수 연계 관계 정리 문서 (사람이 읽는 용도) |
| `hots_ability_links.json` | 위 내용의 구조화 데이터 버전 |
| `herodata_<빌드번호>_kokr.json` / `_enus.json` | Heroes Data Parser로 추출한 원본 영웅 데이터 (한국어/영어) |

## 새 패치 반영하는 법

1. 새로운 `herodata_<빌드번호>_kokr.json`, `herodata_<빌드번호>_enus.json`을 저장소 루트(또는 `data/` 폴더)에 추가
2. `python3 make_encyclopedia.py` 실행
   - `index.html`, `hots_encyclopedia.html`, `encyclopedia_<타임스탬프>.html`(백업용), `hots_ability_links.md`, `hots_ability_links.json`이 갱신됨
3. 변경된 파일들을 커밋 & 푸시

```bash
python3 make_encyclopedia.py
git add -A
git commit -m "패치 <빌드번호> 반영"
git push
```

## 예외 케이스(연계 관계) 추가하는 법

특성으로만 열리는 스킬처럼 게임 데이터만으로는 자동으로 못 찾는 연계는
`make_encyclopedia.py` 안의 두 테이블에 등록되어 있습니다. 새로 발견하면
**두 곳 다** 추가해야 HTML과 참고 문서가 일치합니다:

- JS 쪽: `MANUAL_REPARENT`, `MANUAL_CHILD_OVERRIDE`
- Python 쪽(참고 문서 생성용): `MANUAL_REPARENT_PY`, `MANUAL_CHILD_OVERRIDE_PY`

무엇이 왜 그렇게 연결됐는지는 `hots_ability_links.md`에서 `source` 값(`direct` / `nameId-match` /
`name-match` / `manual` / `unresolved`)으로 확인할 수 있습니다.

## 참고

- 스킬/특성 아이콘, 초상화는 [SIN0NIS/images](https://github.com/SIN0NIS/images) 저장소를 CDN처럼 사용합니다.
- 상단 "🧩 특성 찍기" 버튼은 [hots_talent_build_auto_git](https://github.com/SIN0NIS/hots_talent_build_auto_git)의
  빌드 툴로 연결되며, 영웅을 선택하면 `?hero=<하이퍼링크ID>`가 자동으로 붙어 해당 영웅이 바로 선택됩니다
  (빌드 툴 쪽이 이 파라미터를 읽도록 패치되어 있어야 함).
- 이 저장소는 Blizzard Entertainment와 관련이 없는 비공식 팬 제작물이며, 게임 내 텍스트/아이콘의
  저작권은 Blizzard Entertainment에 있습니다.

## 알려진 제한

- `index.html`은 90명의 한국어+영어 데이터를 전부 인라인으로 포함해 약 4MB입니다. 패치마다
  파일 전체가 갱신되므로 git 히스토리가 매 커밋마다 수 MB씩 늘어납니다. 저장소 용량이 부담되면
  오래된 `encyclopedia_<타임스탬프>.html` 백업 파일들을 주기적으로 정리하는 것을 권장합니다.
