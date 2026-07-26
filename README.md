# 히오스 백과사전

영웅 90명의 스킬·특성을 한글로 정리한 백과사전. 위키 상세 수치와 범위 그림이
들어 있다.

**보기 → https://sin0nis.github.io/Hots_encyclopedia/**

게임이 패치되면 **하루에 한 번 알아서 다시 만든다.** 손댈 일이 없다.

---

## 어떻게 도는가

매일 한국 시간 오전 8시에 블리자드 패치 서버를 보고, 새 빌드가 나왔을 때만
처음부터 다시 만든다. 그대로면 아무것도 하지 않는다.

```
1. 패치 서버에서 지금 빌드 번호를 읽는다
     http://us.patch.battle.net:1119/hero/versions  ->  97650
2. archive/Build_97650/ 이 이미 있으면 -> 그대로 둔다
3. 없으면 -> 아래 8단계를 처음부터 돌린다
```

| 단계 | 하는 일 |
|---|---|
| 1 casc | 블리자드 CDN 에서 게임 XML·게임스트링을 받는다 |
| 2 herodata | 영웅 JSON 을 받는다 |
| 3 analysis | 영웅별로 다시 묶는다 |
| 4 wiki | Fandom 위키를 긁는다 (평소엔 캐시를 쓴다) |
| 5 profile | XML + 위키를 합친다 |
| 6 build | 백과사전 HTML 을 만든다 |
| 7 kr | 한글화하고 위키 필드·범위 그림을 심는다 |
| 8 verify | 위키 수치를 게임 데이터와 맞대 본다 |

**게임 데이터는 저장소에 없다.** 파서의 `online` 모드가 리눅스에서 멀쩡히 돌아서
CI 가 그때그때 받아 온다. (윈도우에서는 `Not a valid Win32 FileTime` 으로 죽는다.
로컬에서 돌릴 때는 설치된 게임을 읽어야 한다.)

## 저장소에 있는 것

| 폴더 | 무엇 |
|---|---|
| `00_manual/` | **손으로 관리하는 값** — 범위 보정·용어집·설정. 여기만 고치면 된다 |
| `00_scripts/` | 파이프라인 코드 |
| `04_auto_wiki/` | Fandom 위키 수집분 (캐시) |
| `archive/` | 지난 판. 게임 빌드마다 그 시점 결과물이 통째로 남는다 |
| `CHANGELOG.md` | 빌드마다 한 줄씩 |

나머지는 전부 빌드가 만든다.

## 손으로 돌리고 싶으면

**Actions → 백과사전 빌드 → Run workflow**

| 칸 | 뜻 |
|---|---|
| `force` | 게임이 그대로여도 다시 만든다 (코드를 고쳤을 때) |
| `refresh_wiki` | Fandom 위키도 다시 긁는다 (90번 호출, 약 3분) |

`00_manual/` 이나 `00_scripts/` 를 고쳐 푸시해도 바로 다시 만든다.

## 지난 판

게임이 패치될 때마다 그 시점 백과사전이 `archive/Build_<번호>/` 에 통째로 남는다.
사이트에서는 메인 페이지 아래 **지난 판** 에서 들어간다.

## 나오는 것

- **사이트** — 메인 → 백과사전 → 용어집, 그리고 지난 판
- **아티팩트 `리포트`** — 빌드마다 남는 점검 결과
  - `xml_check.md` — 위키 수치를 게임 데이터와 맞댄 결과 (어느 XML 파일·태그에서
    읽었는지까지 적혀 있다)
  - `wiki_inventory.md` — 위키가 주는 데이터 전수 목록
  - `no_aoe.html` — 범위 그림이 없는 스킬 목록
  - `report.md` — 한글화 미검수 항목

## 처음 켤 때

- **Settings → Pages → Source** 를 **GitHub Actions** 로
- **Settings → Actions → Workflow permissions** 를 **Read and write** 로
  (봇이 `archive/` 와 `CHANGELOG.md` 를 되커밋한다)

파이프라인 자체 설명은 [README_pipeline.md](README_pipeline.md) 에 있다.
