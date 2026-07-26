# 히오스 백과사전 — GitHub Actions 판

[hots_date260725](../hots_date260725) 와 같은 파이프라인인데, **3단계부터 GitHub
Actions 가 돌린다.** 결과물은 GitHub Pages 로 올라간다.

푸시하면 자동으로 다시 만들어지고, 매주 월요일에도 한 번 돈다.

---

## 왜 1·2단계는 여기서 못 도는가

파이프라인 8단계 중 앞의 두 개만 **게임 원본**을 건드린다.

| 단계 | 하는 일 | Actions 에서 |
|---|---|---|
| 1 casc | 게임 XML·게임스트링 추출 | ❌ |
| 2 herodata | 영웅 JSON·아이콘 추출 | ❌ |
| 3 analysis ~ 8 verify | 나머지 전부 | ✅ |

이유는 둘이다.

1. **게임이 설치돼 있어야 한다.** 러너에는 히오스가 없다.
2. **파서의 `online` 모드가 죽는다.** 블리자드 CDN 에서 바로 받아 오는 길이
   있긴 한데, 실제로 돌려 보면 1.4초 만에 `Not a valid Win32 FileTime` 으로
   끝난다. 파서가 CDN 메타데이터를 못 읽는다.

   ```
   $ dotnet-heroes-data-parser casc-extract online -o out -i "..."
   Error: Not a valid Win32 FileTime.
   ```

그래서 **1·2단계의 결과물만 저장소에 커밋해 두고** Actions 는 3단계부터 돌린다.
게임이 패치되면 그때만 로컬에서 1·2를 돌려 커밋하면 된다.

## 저장소에 무엇이 들어 있나

| 폴더 | 크기 | 무엇 |
|---|---|---|
| `00_manual/` | 76K | 손으로 관리하는 값 (범위 보정·용어집·설정) |
| `00_scripts/` | 412K | 파이프라인 코드 |
| `01_auto_casc/` | 39M | 게임 XML·게임스트링 — **1단계 결과물** |
| `02_auto_herodata/data/` | 6.4M | 영웅 JSON — **2단계 결과물** |
| `04_auto_wiki/` | 7.6M | Fandom 위키 수집분 (캐시) |
| | **54M** | |

**영웅 아이콘 43MB 는 넣지 않았다.** 백과사전이 아이콘을
`raw.githubusercontent.com` 에서 불러오기 때문에 빌드에 필요 없다. 그것만 빼도
저장소가 절반 아래로 줄었다.

3·5·6·7 단계 폴더와 `output/` 은 `.gitignore` 로 뺐다. Actions 가 매번 다시
만든다.

## 게임이 패치되면

로컬(게임이 깔린 컴퓨터)에서 앞의 두 단계만 돌리고 커밋한다.

```bash
python 00_scripts/pipeline.py --only casc,herodata
git add 01_auto_casc 02_auto_herodata
git commit -m "게임 데이터 갱신 (Build XXXXX)"
git push
```

푸시하면 Actions 가 나머지를 만들어 Pages 에 올린다.

## 위키를 다시 긁고 싶으면

위키는 사람이 손으로 고치는 곳이라 게임 패치와 따로 논다. Actions 탭에서
**Run workflow** 를 누르고 `refresh_wiki` 를 켜면 90개 영웅을 다시 긁는다
(약 3분). 새로 긁은 결과는 봇이 `04_auto_wiki/` 에 되커밋한다.

평소 빌드는 커밋된 캐시를 그대로 쓴다.

## 나오는 것

- **Pages** — `index.html` (메인) → 백과사전 → 용어집
- **아티팩트 `리포트`** — 빌드마다 남는 점검 결과
  - `xml_check.md` — 위키 수치를 게임 데이터와 맞댄 결과
  - `wiki_inventory.md` — 위키가 주는 데이터 전수 목록
  - `no_aoe.html` — 범위 그림이 없는 스킬 목록
  - `report.md` — 한글화 미검수 항목

## 처음 켤 때

저장소 **Settings → Pages → Source** 를 **GitHub Actions** 로 둔다.
`refresh_wiki` 를 쓰려면 **Settings → Actions → Workflow permissions** 를
**Read and write** 로 둬야 봇이 되커밋할 수 있다.

## 한 가지 짚고 갈 것

`01_auto_casc/` 와 `02_auto_herodata/` 는 **블리자드의 게임 데이터**다. 공개
저장소에 올리면 그 자체를 재배포하는 셈이 된다. 결과물(백과사전)만 공개하는
것과는 무게가 다르다.

- **비공개 저장소**로 두고 Pages 만 공개하는 쪽이 안전하다
  (Pages 는 비공개 저장소에서도 GitHub Pro 이상이면 공개로 낼 수 있다)
- 공개로 갈 거면 최소한 게임 데이터를 뺀 채로 두고, 빌드할 때만 넣는 방법을
  따로 마련하는 편이 낫다

파이프라인 자체 설명은 [README_pipeline.md](README_pipeline.md) 에 있다.
