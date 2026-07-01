# 히오스 스킬 연계 관계 참고 문서 (Build 97039)
생성일: 2026-07-01 13:34

이 파일은 백과사전 HTML이 스킬을 어떻게 부모-자식으로 엮었는지 정리한 참고용 문서입니다.
source 값 의미:
- `direct`: 게임 데이터의 subAbilities가 이미 알려진 능력을 직접 가리키는 정상적인 경우
- `nameId-match`: 특성의 abilityTalentLinkIds에 이 능력의 nameId가 직접 포함돼 있어 자동으로 부모를 추론한 경우
- `name-match`: 위 방법으로 못 찾아서, 같은 이름의 특성을 보조 단서로 사용해 추론한 경우
- `manual`: 데이터로는 추론이 불가능해 스크립트에 하드코딩으로 등록한 예외 (최상위 능력을 재배치)
- `manual-child`: 데이터로는 추론이 불가능해 하드코딩으로 등록한 예외 (연계그룹의 자식 하나만 재배치, 표시 이름도 겹치지 않게 변경됨)
- `unresolved`: 연계 능력인 것은 분명하지만 어떤 능력의 자식인지 자동으로 못 찾은 경우. 단, 이 부모(nameId)가 위 표의 다른 어딘가에 child로 재배치되어 있다면, 실제 페이지에서는 그 카드 밑에 자동으로 한 단계 더 중첩되어 표시됩니다 (예: 알라라크 '치명적인 돌진 사용'은 여기선 미해결이지만, 실제로는 '가학성 → 치명적인 돌진' 카드 밑에 다시 중첩됨).

## 수동 예외 테이블 (MANUAL_REPARENT)

| 능력 nameId | 부모로 지정 | 설명 |
|---|---|---|
| `SamuroSelectSamuroPrime` | `SamuroIllusionMaster` | 궁극기 '환영의 대가'를 선택해야 사용 가능 |
| `SamuroSelectAll` | `SamuroIllusionMaster` | 궁극기 '환영의 대가'를 선택해야 사용 가능 |
| `TinkerFocusTurrets` | `TinkerRockItTurret` | 설치된 '잘나가! 포탑'을 대상으로 사용 |

## 수동 자식 오버라이드 테이블 (MANUAL_CHILD_OVERRIDE)

| 능력 nameId | 부모로 지정 | 표시 이름 변경 | 설명 |
|---|---|---|---|
| `WizardArchonPurePowerDisintegrate` | `WizardDisintegrate` | 파열 (마인: 순수한 힘) | Lv20 '마인: 순수한 힘' 특성 필요 |

## 영웅별 연계 관계

### D.Va (`DVa`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 토끼뜀 (`DVaMechBunnyHopHeroic`) | 토끼뜀 (`DVaMechBunnyHopHeroic`) | direct |  |
| 부스터 (`DVaBoostersOn`) | 부스터 취소 (`DVaBoostersOff`) | direct |  |
| 방어 매트릭스 (`DVaMechDefenseMatrixOn`) | 방어 매트릭스 대상 변경 (`DVaMechDefenseMatrixRetarget`) | direct |  |
| 방어 매트릭스 (`DVaMechDefenseMatrixOn`) | 방어 매트릭스 취소 (`DvaCancelDefenseMatrix`) | direct |  |

### 가로쉬 (`Garrosh`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 방어력 증가 (`GarroshArmorUp`) | 방어력 상승 (`GarroshArmorUpDoubleUp`) | nameId-match | Lv16 '노련한 병사' 특성 필요 |

### 가즈로 (`Tinker`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 잘나가! 포탑 (`TinkerRockItTurret`) | 집중 포화! (`TinkerFocusTurrets`) | manual | 설치된 '잘나가! 포탑'을 대상으로 사용 |

### 갈 (`Gall`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 뒤틀린 황천 (`GallTwistingNether`) | 뒤틀린 황천 폭발시키기 (`GallTwistingNetherActivated`) | direct |  |
| 공포의 보주 (`GallDreadOrb`) | 백도 (`GallDoubleBack`) | direct |  |
| 오우거의 분노 (`GallOgreRage`) | 오우거의 분노 (`GallOgreRagePassive`) | direct |  |
| (미해결: GallShiftingNether) | 뒤틀린 황천 (`GallShiftingNether`) | unresolved |  |

### 겐지 (`Genji`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 용검 (`GenjiDragonblade`) | 용검 (`GenjiDragonbladeAttack`) | direct |  |
| 용검 (`GenjiDragonblade`) | 용검 (`GenjiDragonbladeAttack`) | direct |  |
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 굴단 (`Guldan`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 생명력 흡수 (`GuldanDrainLife`) | 생명력 흡수 취소 (`GuldanDrainLifeCancel`) | direct |  |
| 생명력 전환 (`GuldanLifeTap`) | 생명력 전환 (`GuldanLifeTapFree`) | nameId-match | Lv16 '내면의 어둠' 특성 필요 |

### 그레이메인 (`Greymane`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 늑대인간의 저주 (`GreymaneWorgenForm`) | 잔혹한 할퀴기  (`GreymaneRazorSwipe`) | direct |  |
| 늑대인간의 저주 (`GreymaneWorgenForm`) | 철수 (`GreymaneDisengage`) | direct |  |
| 내면의 야성 (`GreymaneInnerBeast`) | 내면의 야성 (`GreymaneInnerBeastActive`) | direct |  |

### 나지보 (`WitchDoctor`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 덩치 (`WitchDoctorGargantuan`) | 덩치 발구르기 (`WitchDoctorGargantuanStompCommand`) | direct |  |
| 굶주린 혼령 (`WitchDoctorRavenousSpirit`) | 굶주린 혼령 (`WitchDoctorRavenousSpiritCancel`) | direct |  |
| 좀비 벽 (`WitchDoctorZombieWall`) | 좀비 벽 (`WitchDoctorZombieWallCancel`) | direct |  |
| (미해결: WitchDoctorGargantuanStompCommand) | 덩치 발구르기 (`WitchDoctorGargantuanStomp`) | unresolved |  |

### 노바 (`Nova`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 누더기 (`Stitches`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 데스윙 (`Deathwing`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 용의 비상 (`DeathwingDragonflight`) | 파괴자 (`DeathwingDestroyerForm`) | direct |  |
| 용의 비상 (`DeathwingDragonflight`) | 세계 파괴자 (`DeathwingWorldbreakerForm`) | direct |  |
| 이글거리는 화염 (`DeathwingMoltenFlame`) | 취소 (`DeathwingMoltenFlameCancel`) | direct |  |
| 소각 (`DeathwingIncinerate`) | 용암 폭발 (`DeathwingLavaBurst`) | nameId-match | Lv4 '열기의 파도' 특성 필요 |
| 맹격 (`DeathwingOnslaught`) | 대지 분쇄 (`DeathwingEarthShatter`) | nameId-match | Lv13 '초토화' 특성 필요 |
| (미해결: DeathwingSkyfall) | 하늘붕괴 (`DeathwingSkyfall`) | unresolved |  |

### 데커드 (`Deckard`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 잠시 내 말 좀 들어보게나 (`DeckardStayAWhileAndListen`) | 잠시 내 말 좀 들어보게나 취소 (`DeckardStayAWhileAndListenCancel`) | direct |  |
| 케인의 수호자 (`DeckardFortitudeOfTheFaithful`) | 케인의 수호자 (`DeckardAncientBlessings`) | nameId-match | Lv16 '케인의 호위대' 특성 필요 |

### 데하카 (`Dehaka`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 잠복 (`DehakaBurrow`) | 잠복 취소 (`DehakaCancelBurrow`) | direct |  |

### 도살자 (`Butcher`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 무자비한 돌진 (`ButcherRuthlessOnslaught`) | 무자비한 돌진 취소 (`RuthlessOnslaughtCancel`) | direct |  |

### 들창코 (`Hogger`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 노획물 투척 (`HoggerHoardapult`) | 노획물 투척 파괴 (`HoggerCancelHoardapult`) | direct |  |
| 들창 폭풍 (`HoggerHoggWild`) | 들창 폭풍 취소  (`HoggerCancelHoggWild`) | direct |  |
| 노획물 더미 (`HoggerLootHoard`) | 노획물 더미 파괴 (`HoggerCancelLootHoard`) | direct |  |

### 디아블로 (`Diablo`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 번개 숨결 (`DiabloLightningBreath`) | 번개 숨결 중지 (`LightningBreathCancel`) | direct |  |

### 라그나로스 (`Ragnaros`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 설퍼라스 강화 (`RagnarosEmpowerSulfuras`) | 설퍼라스 강화 (`RagnarosEmpowerSulfurasActive`) | direct |  |
| (미해결: RagnarosLivingMeteorShiftingMeteor) | 선회하는 유성 (`RagnarosLivingMeteorShiftingMeteor`) | unresolved |  |

### 레가르 (`Rehgar`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 늑대 정령 (`RehgarGhostWolfActivate`) | 늑대 정령 비활성화 (`RehgarGhostWolfDeactivate`) | direct |  |
| (미해결: RehgarEarthbindTotemColossalTotem) | 토템 재배치 (`RehgarTotemicProjection`) | unresolved |  |

### 레오릭 (`Leoric`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 망자의 묘실 (`LeoricEntomb`) | 망자의 묘실 취소 (`LeoricEntombCancel`) | direct |  |
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 불사 (`LeoricUndyingTrait`) | 섬뜩한 휩쓸기 (`LeoricGhastlySwing`) | direct |  |
| 불사 (`LeoricUndyingTrait`) | 착취의 손아귀 (`LeoricDrainEssence`) | direct |  |
| 망령 걸음 (`LeoricWraithWalk`) | 망령 걸음 취소 (`LeoricCancelWraithWalk`) | direct |  |

### 레이너 (`Raynor`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 레이너 특공대 (`RaynorRaynorsRaidersDummy`) | 레이너 특공대 명령 내리기 (`RaynorRaynorsRaidersRedirect`) | direct |  |
| 뜨거운 맛을 보여주지 (`RaynorGiveEmSomePepper`) | 뜨거운 맛을 보여주지 (`RaynorBountyHunter`) | nameId-match | Lv20 '더 뜨거운 맛' 특성 필요 |

### 렉사르 (`Rexxar`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 루나라 (`Dryad`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 위습 (`DryadWisp`) | 위습 위치 변경 (`DryadWispRedirect`) | direct |  |
| 드리아드의 날렵함 (`DryadDryadsSwiftness`) | 드리아드의 날렵함 (`DryadGallopingGait`) | nameId-match | Lv1 '폴짝 폴짝' 특성 필요 |

### 루시우 (`Lucio`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 분위기 전환! (`LucioCrossfade`) | 분위기 전환! (`LucioCrossfade`) | direct |  |

### 리 리 (`LiLi`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 1,000잔 돌리기 (`LiLiJugof1000Cups`) | 1,000잔 돌리기 취소 (`LiLiCancelJugof1000Cups`) | direct |  |
| 빠른 발 (`LiLiFastFeet`) | 빠른 발 (`LiLiSafetySprint`) | nameId-match | Lv20 '괜찮아' 특성 필요 |

### 리밍 (`Wizard`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 파열 (`WizardDisintegrate`) | 파열 (취소) (`WizardDisintegrateCancel`) | direct |  |
| (미해결: WizardArchonPurePowerDisintegrate) | 파열 취소 (`WizardArchonPurePowerDisintegrateCancel`) | unresolved |  |
| 파열 (`WizardDisintegrate`) | 파열 → 파열 (마인: 순수한 힘) (`WizardArchonPurePowerDisintegrate`) | manual-child | Lv20 '마인: 순수한 힘' 특성 필요 |

### 마이에브 (`Maiev`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 속박의 원반 (`MaievContainmentDisc`) | 속박 (`MaievContainmentDiscContain`) | direct |  |
| 복수의 영혼 (`MaievSpiritOfVengeance`) | 점멸 (`MaievSpiritOfVengeanceBlink`) | direct |  |
| 그림자 목줄 (`MaievUmbralBind`) | 그림자 목줄 (`MaievUmbralBindPrimed`) | direct |  |

### 말가니스 (`MalGanis`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 지옥 발톱 (`MalGanisFelClawsFirst`) | 지옥 발톱 (`MalGanisFelClawsSecond`) | direct |  |
| 밤의 질주 (`MalGanisNightRush`) | 밤의 질주 (`MalGanisNightRushCancel`) | direct |  |
| 지옥 발톱 (`MalGanisFelClawsFirst`) | 지옥 발톱 (`MalGanisFelClawsThird`) | nameId-match | Lv20 '나약한 자는 처단한다' 특성 필요 |

### 말티엘 (`Malthael`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 말퓨리온 (`Malfurion`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 머키 (`Murky`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 멀록 대행진 (`MurkyMarchoftheMurlocs`) | 멀록 대행진 취소 (`MurkyCancelMarchoftheMurlocs`) | direct |  |

### 메디브 (`Medivh`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 까마귀 형상 (`MedivhTransformRaven`) | 까마귀 형상 취소 (`MedivhTransformRavenLand`) | direct |  |
| (미해결: MedivhPolyBombGlyphOfPolyBomb) | 변이 폭탄 (`MedivhPolyBombGlyphOfPolyBomb`) | unresolved |  |
| (미해결: MedivhLeyLineSealMedivhCheats) | 봉인의 지맥 경로 변경 (`MedivhLeyLineSealMedivhCheats`) | unresolved |  |
| (미해결: MedivhPortalPortalMastery) | 차원문 취소 (`MedivhPortalCancel`) | unresolved |  |

### 메이 (`MeiOW`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 얼음 활주 (`MeiOWIcing`) | 얼음 활주 (`MeiOWIcingCancel`) | direct |  |
| 급속 빙결 (`MeiOWCryoFreeze`) | 급속 빙결 (`MeiOWCryoFreezeCancel`) | direct |  |

### 메피스토 (`Mephisto`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 모랄레스 중위 (`Medic`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 치료 광선 (`MedicHealingBeam`) | 치료 광선 대상 변경 (`MedicRedirectHealingBeam`) | direct |  |
| 치료 광선 (`MedicHealingBeam`) | 치료 광선 취소 (`MedicCancelHealingBeam`) | direct |  |
| 변위 수류탄 (`MedicDisplacementGrenade`) | 변위 수류탄 폭발 (`MedicDetonateDisplacementGrenade`) | direct |  |

### 무라딘 (`Muradin`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 재기의 바람 (`MuradinSecondWind`) | 재기의 바람 (`Stoneform`) | nameId-match | Lv16 '석화' 특성 필요 |

### 바리안 (`Varian`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 영웅의 일격 (`VarianHeroicStrike`) | 영웅의 일격 (`VarianHeroicStrikeActive`) | direct |  |

### 발라 (`DemonHunter`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 발리라 (`Valeera`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 소멸 (`ValeeraStealth`) | 매복 (`ValeeraAmbush`) | direct |  |
| 소멸 (`ValeeraStealth`) | 비열한 습격 (`ValeeraCheapShot`) | direct |  |
| 소멸 (`ValeeraStealth`) | 목조르기 (`ValeeraGarrote`) | direct |  |
| 소멸 (`ValeeraStealth`) | 은신 취소 (`ValeeraCancelStealth`) | direct |  |

### 블레이즈 (`Firebat`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 연소 (`FirebatCombustion`) | 연소 취소 (`FirebatCombustionCancel`) | direct |  |

### 빛나래 (`FaerieDragon`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 점멸 치유 (`FaerieDragonBlinkHealDash`) | 폴짝용 (`BrightwingBlinkHealDoubleWyrmholeDash`) | direct |  |

### 사무로 (`Samuro`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 칼날폭풍 (`SamuroBladeStormDummy`) | 칼날폭풍 취소 (`SamuroBladestormCancel`) | direct |  |
| 환영의 대가 (`SamuroIllusionMaster`) | 사무로 선택 (`SamuroSelectSamuroPrime`) | manual | 궁극기 '환영의 대가'를 선택해야 사용 가능 |
| 환영의 대가 (`SamuroIllusionMaster`) | 모두 선택 (`SamuroSelectAll`) | manual | 궁극기 '환영의 대가'를 선택해야 사용 가능 |

### 소냐 (`Barbarian`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 도약 강타 (`BarbarianLeap`) | 도약 강타 취소 (`BarbarianCancelLeapArreatCrater`) | direct |  |
| 소용돌이 (`BarbarianWhirlwind`) | 소용돌이 취소 (`BarbarianWhirlwindCancel`) | direct |  |
| 분노 (`BarbarianFury`) | 분노 (`BarbarianShotofFury`) | nameId-match | Lv13 '도주 불가' 특성 필요 |

### 스랄 (`Thrall`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 세계의 분리 (`ThrallSundering`) | 세계의 분리 (`ThrallCancelSundering`) | direct |  |
| 서리늑대의 회복력 (`ThrallFrostwolfResilience`) | 서리늑대의 회복력 (`ThrallFrostwolfsGrace`) | nameId-match | Lv13 '서리늑대의 은총' 특성 필요 |

### 스투코프 (`Stukov`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 스멀거리는 팔 (`StukovLurkingArm`) | 스멀거리는 팔 취소 (`StukovLurkingArmCancel`) | direct |  |

### 실바나스 (`Sylvanas`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 울부짖는 화살 (`SylvanasWailingArrow`) | 울부짖는 화살 (`SylvanasWailingArrowActivate`) | direct |  |
| 정신 지배 (`SylvanasMindControlMissile`) | 정신 지배 취소 (`SylvanasMindControlCancel`) | direct |  |
| 유령의 파도 (`SylvanasHauntingWave`) | 유령의 순간이동 (`SylvanasHauntingWaveActivate`) | direct |  |
| 검은 화살 (`SylvanasBlackArrowsActive`) | 검은 화살 (`SylvanasBlackArrowsPassive`) | direct |  |
| (미해결: SylvanasHauntingWaveWindrunnerTalent) | 유령의 순간이동 (`SylvanasHauntingWaveActivateWindrunnerTalent`) | unresolved |  |
| 유령의 파도 (`SylvanasHauntingWave`) | 유령의 파도 (`SylvanasHauntingWaveWindrunnerTalent`) | nameId-match | Lv13 '바람길잡이' 특성 필요 |

### 아나 (`Ana`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 호루스의 눈 (`AnaEyeOfHorusActivate`) | 고성능 탄환 (`AnaEyeOfHorusAttackDummy`) | direct |  |
| 호루스의 눈 (`AnaEyeOfHorusActivate`) | 호루스의 눈 취소 (`AnaEyeOfHorusCancel`) | direct |  |
| 호루스의 눈 (`AnaEyeOfHorusActivate`) | 호루스의 눈 취소 (`AnaEyeOfHorusCancel`) | direct |  |
| 호루스의 눈 (`AnaEyeOfHorusActivate`) | 고성능 탄환 (`AnaEyeOfHorusAttackDummy`) | direct |  |
| 때까치 (`AnaAimDownSightsActivate`) | 때까치 취소 (`AnaAimDownSightsDeactivate`) | direct |  |

### 아눕아락 (`Anubarak`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 잠복 돌진 (`AnubarakBurrowCharge`) | 잠복 돌진 취소 (`AnubarakBurrowChargeCancel`) | direct |  |

### 아르타니스 (`Artanis`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 이연격 (`ArtanisTwinBlades`) | 이연격 (준비 완료) (`ArtanisTwinBladesPrimed`) | direct |  |

### 아바투르 (`Abathur`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 흉물 진화 (`AbathurEvolveMonstrosity`) | 흉물 진화 활성화됨 (`AbathurEvolveMonstrosityActiveSymbiote`) | direct |  |

### 아서스 (`Arthas`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 사자의 군대 (`ArthasArmyOfTheDead`) | 희생 (`ArthasArmyOfTheDeadSacrifice`) | direct |  |
| 서리 폭풍 (`ArthasFrozenTempest`) | 서리 폭풍 비활성화 (`ArthasFrozenTempestCancel`) | direct |  |
| 서리한이 굶주렸다 (`ArthasFrostmourneHungers`) | 서리한이 굶주렸다 준비 완료 (`ArthasFrostmourneHungersPrimed`) | direct |  |

### 아우리엘 (`Auriel`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 부활 (`AurielResurrect`) | 부활 (`AurielResurrectSelf`) | direct |  |

### 아즈모단 (`Azmodan`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 죄악의 물결 (`AzmodanTideOfSin`) | 죄악의 물결 (`AzmodanTideOfSinPassive`) | direct |  |
| 모두 다 불타리라 (`AzmodanAllShallBurn`) | 모두 다 불타리라 (`AzmodanAllShallBurnCancel`) | direct |  |

### 안두인 (`Anduin`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 빛의 권능: 구원 (`AnduinHolyWordSalvation`) | 빛의 권능: 구원 취소 (`AnduinHolyWordSalvationCancel`) | direct |  |

### 알라라크 (`Alarak`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 치명적인 돌진 (`AlarakDeadlyChargeActivate`) | 치명적인 돌진 사용 (`AlarakDeadlyChargeExecute`) | direct |  |
| 번개 쇄도 (`AlarakLightningSurge`) | 번개 쇄도 (`AlarakLightningSurgeLightningBarrage`) | nameId-match | Lv16 '번개 포화' 특성 필요 |
| (미해결: AlarakDeadlyChargeActivate2ndHeroic) | 치명적인 돌진 사용 (`AlarakDeadlyChargeExecute2ndHeroic`) | unresolved |  |
| 가학성 (`AlarakSadism`) | 치명적인 돌진 (`AlarakDeadlyChargeActivate2ndHeroic`) | nameId-match | Lv16 '우월한 일격' 특성 필요 |
| 가학성 (`AlarakSadism`) | 반격 (`AlarakCounterStrikeTargeted2ndHeroic`) | nameId-match | Lv16 '우월한 일격' 특성 필요 |

### 알렉스트라자 (`Alexstrasza`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 오르피아 (`Orphea`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 넘치는 혼돈 (`OrpheaOverflowingChaos`) | 넘치는 혼돈 (`OrpheaOverflowingChaosInvasiveMiasma`) | nameId-match | Lv20 '기괴한 전도' 특성 필요 |

### 요한나 (`Crusader`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 우서 (`Uther`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 헌신 (`UtherEternalDevotion`) | 빛의 섬광 (`UtherFlashofLight`) | direct |  |

### 이렐 (`Yrel`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 비호 (`YrelVindication`) | 비호 (`YrelVindicationCast`) | direct |  |
| 신성한 목적 (`YrelDivinePurpose`) | 정의의 망치 (`YrelRighteousHammerDivinePurpose`) | direct |  |
| 신성한 목적 (`YrelDivinePurpose`) | 응징의 격노 (`YrelAvengingWrathDivinePurpose`) | direct |  |
| 신성한 목적 (`YrelDivinePurpose`) | 신성한 목적 (`YrelDivinePurposeActive`) | direct |  |
| 정의의 망치 (`YrelRighteousHammerChannel`) | 정의의 망치 (`YrelRighteousHammer`) | direct |  |
| 응징의 격노 (`YrelAvengingWrath`) | 응징의 격노 (`YrelAvengingWrathChannel`) | direct |  |
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| (미해결: YrelDivineSteed) | 천상의 군마 (`YrelDivineSteedSummonMount`) | unresolved |  |

### 일리단 (`Illidan`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 임페리우스 (`Imperius`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 자가라 (`Zagara`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 자리야 (`Zarya`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 정예 타우렌 족장 (`L90ETC`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 광란의 도가니 (`L90ETCMoshPit`) | 광란의 도가니 취소 (`L90ETCMoshPitCancel`) | direct |  |

### 정크랫 (`Junkrat`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 죽이는 타이어 (`JunkratRIPTire`) | 점프! (`JunkratRIPTireJump`) | direct |  |
| 죽이는 타이어 (`JunkratRIPTire`) | 죽이는 타이어 폭발 (`JunkratDetonateRIPTire`) | direct |  |
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 충격 지뢰 (`JunkratConcussionMine`) | 지뢰 폭발 (`JunkratDetonateMine`) | direct |  |
| (미해결: JunkratIHateWaitingSummonMount) | 탈것 소환 해제 (`JunkratRocketRideDismount`) | unresolved |  |
| (미해결: JunkratIHateWaitingTalent) | 탈것 소환 (`JunkratIHateWaitingSummonMount`) | unresolved |  |

### 제라툴 (`Zeratul`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 네라짐의 힘 (`ZeratulMightOfTheNerazimDummy`) | 가르기 (`ZeratulCleaveMightOfTheNerazim`) | direct |  |
| 네라짐의 힘 (`ZeratulMightOfTheNerazimDummy`) | 특이점 폭발 (`ZeratulSingularitySpikeMightOfTheNerazim`) | direct |  |
| 네라짐의 힘 (`ZeratulMightOfTheNerazimDummy`) | 점멸 (`ZeratulBlinkMightOfTheNerazim`) | direct |  |
| 공허의 감옥 (`ZeratulVoidPrison`) | 공허의 감옥 취소 (`VoidPrisonCancel`) | direct |  |
| (미해결: ZeratulSeekerInTheDark) | 어둠 속의 추적자 (`ZeratulSeekerInTheDark`) | unresolved |  |
| (미해결: ZeratulWormhole) | 웜홀 (`ZeratulWormhole`) | unresolved |  |

### 제이나 (`Jaina`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 물의 정령 소환 (`JainaSummonWaterElemental`) | 물의 정령 조종 (`JainaCommandWaterElemental`) | direct |  |
| 동상 (`JainaTraitFrostbite`) | 향상된 얼음 방패 (`ImprovedIceBlock`) | direct |  |

### 줄 (`Necromancer`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 유령의 낫 (`NecromancerSpectralScythe`) | 유령의 낫 (`NecromancerSpectralScythe`) | direct |  |
| 저주의 수확 (`NecromancerCursedStrikes`) | 저주의 수확 (`NecromancerCursedStrikesPassive`) | direct |  |

### 줄진 (`Zuljin`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 재생 (`ZuljinRegeneration`) | 재생 취소 (`ZuljinCancelRegeneration`) | direct |  |
| 광전사 (`ZuljinBerserker`) | 광전사 취소 (`ZuljinCancelBerserker`) | direct |  |

### 첸 (`Chen`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 폭풍, 대지, 불 (`ChenStormEarthFire`) | 폭풍 (`ChenStorm`) | direct |  |
| 폭풍, 대지, 불 (`ChenStormEarthFire`) | 대지 (`ChenEarth`) | direct |  |
| 폭풍, 대지, 불 (`ChenStormEarthFire`) | 불 (`ChenFire`) | direct |  |
| 술통 부수기 (`ChenKegSmash`) | 불의 숨결 (`ChenBreathOfFire`) | direct |  |

### 초 (`Cho`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 쇄도의 주먹 (`ChoSurgingFistCast`) | 쇄도의 주먹 (`ChoSurgingFistTrigger`) | direct |  |
| 오우거의 가죽 (`ChoOgreHide`) | 오우거의 가죽 (`ChoOgreHidePassive`) | direct |  |

### 카라짐 (`Monk`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 연속 격파 (`MonkDeadlyReach`) | 연속 격파 활성화됨 (`MonkDeadlyReachActive`) | direct |  |
| (미해결: MonkIronFists) | 철권 (`MonkIronFists`) | unresolved |  |
| (미해결: MonkInsight) | 통찰 (`MonkInsight`) | unresolved |  |
| (미해결: MonkTranscendence) | 초월 (`MonkTranscendence`) | unresolved |  |

### 카시아 (`Amazon`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 난격 (`AmazonFend`) | 난격 취소 (`AmazonFendCancelChannel`) | direct |  |
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 공격 저지 (`AmazonAvoidance`) | 공격 저지 (`AmazonSurgeOfLight`) | nameId-match | Lv20 '거인의 복수' 특성 필요 |
| 공격 저지 (`AmazonAvoidance`) | 전쟁 여행자 (`AmazonWarTravelerSummonMount`) | nameId-match | Lv13 '전쟁 여행자' 특성 필요 |

### 캘타스 (`Kaelthas`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 불사조 (`KaelthasPhoenix`) | 불사조 위치 이동 (`KaelthasPhoenixRetargetPhoenixAbility`) | direct |  |
| 신록의 구슬 (`KaelthasVerdantSpheres`) | 신록의 구슬 활성화됨 (`KaelthasVerdantSpheresActive`) | direct |  |

### 케리건 (`Kerrigan`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 울트라리스크 소환 (`KerriganSummonUltralisk`) | 울트라리스크 명령 내리기 (`KerriganSummonUltraliskIssueOrder`) | direct |  |

### 켈투자드 (`KelThuzad`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 켈투자드의 사슬 (`KelThuzadChains`) | 켈투자드의 사슬 (`KelThuzadChainsLink`) | direct |  |
| 차디찬 어둠의 지배자 (`KelThuzadMasterOfTheColdDark`) | 혹한의 쐐기 (`KelThuzadGlacialSpike`) | direct |  |

### 크로미 (`Chromie`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 감속의 모래 (`ChromieSlowingSands`) | 감속의 모래 취소 (`ChromieSlowingSandsCancel`) | direct |  |
| 시간의 덫 (`ChromieTimeTrap`) | 시간의 덫 폭발 (`ChromieTimeTrapDetonate`) | direct |  |

### 키히라 (`NexusHunter`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 회전 휩쓸기 (`NexusHunterRevolvingSweep`) | 회전 휩쓸기 (`NexusHunterRevolvingSweepSecondary`) | direct |  |

### 타이커스 (`Tychus`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 드라켄 레이저 천공기 (`TychusDrakkenLaserDrill`) | 레이저 천공기 공격 명령 (`TychusDrakkenLaserDrillIssueOrder`) | direct |  |
| 오딘 출격 (`TychusOdinNoHealth`) | 몰살 (`TychusOdinAnnihilate`) | direct |  |
| 오딘 출격 (`TychusOdinNoHealth`) | 라그나로크 미사일 (`TychusOdinRagnarokMissilesTargeted`) | direct |  |
| 오딘 출격 (`TychusOdinNoHealth`) | 추진기 가동 (`TychusOdinThrusters`) | direct |  |
| 포화 (`TychusOverkillTargeted`) | 포화 대상 변경 (`OverkillTargetedRetarget`) | direct |  |
| 포화 (`TychusOverkillTargeted`) | 달려 쏴 (`TychusRunAndGunOverkill`) | direct |  |
| 미니건 (`TychusMinigun`) | 미니건 (`TychusMinigunActive`) | direct |  |

### 태사다르 (`Tassadar`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 집정관 (`TassadarArchon`) | 집정관 (`TassadarArchon`) | direct |  |
| 역장 (`TassadarForceWall`) | 역장벽 취소 (`TassadarForceWallCancel`) | direct |  |
| 공명 광선 (`TassadarResonanceBeam`) | 공명 광선 (`TassadarResonanceBeamArcDischargeDummy`) | nameId-match | Lv7 '아크 방전' 특성 필요 |

### 트레이서 (`Tracer`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 재장전 (`TracerReload`) | 완벽한 장전 (`TracerLockedandLoadedFailReload`) | direct |  |
| (미해결: TracerLockedandLoaded) | 완벽한 장전 (`TracerLockedandLoaded`) | unresolved |  |

### 티란데 (`Tyrande`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |

### 티리엘 (`Tyrael`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 축성 (`TyraelSanctificationStationary`) | 축성 취소 (`CancelSanctification`) | direct |  |
| 엘드루인의 힘 (`TyraelElDruinsMight`) | 엘드루인의 섬광 (`ElDruinsMightEldruinsFlash`) | direct |  |
| (미해결: TyraelAspectofJustice) | 대천사의 분노 (`TyraelAspectofJustice`) | unresolved |  |

### 폴스타트 (`Falstad`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 부메랑 망치 (`FalstadHammerang`) | 폭발 (`FalstadBOOMerang`) | direct |  |

### 피닉스 (`Fenix`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 행성 분열기 (`FenixPlanetCracker`) | 행성 분열기 취소 (`FenixPlanetCrackerCancel`) | direct |  |
| 무기 모드: 연발포 (`FenixPhaseBomb`) | 무기 모드: 위상 폭탄 (`FenixRepeaterCannon`) | direct |  |

### 한조 (`Hanzo`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| (미해결: HanzoPOTG) | 최고의 플레이 (`HanzoPOTG`) | unresolved |  |

### 해머 상사 (`SgtHammer`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 공성 모드 (`SgtHammerSiegeMode`) | 거미 지뢰 (`SgtHammerSpiderMinesSiegeMode`) | direct |  |
| 공성 모드 (`SgtHammerSiegeMode`) | 네이팜 포격 (`SgtHammerNapalmStrikeSiege`) | direct |  |
| 공성 모드 (`SgtHammerSiegeMode`) | 전차 모드 (`SgtHammerTankMode`) | direct |  |
| (미해결: SgtHammerConcussiveBlastEntrenched) | 방호벽 취소 (`ConcussiveBlastScrapCancel`) | unresolved |  |

### 화이트메인 (`Whitemane`)

| 부모 능력 | 자식(연계) 능력 | source | 설명 |
|---|---|---|---|
| 탈것 소환 (`Mount`) | 탈것 소환 해제 (`Dismount`) | direct |  |
| 심문 (`WhitemaneInquisition`) | 심문 (취소) (`WhitemaneInquisitionCancel`) | direct |  |
| 관용 (`WhitemaneInquisitionClemency`) | 심문 (취소) (`WhitemaneInquisitionCancel`) | direct |  |
