# Workload Model Refinement

작성 기준: 2026-11-02 · 상태: workload 범위와 실험 변수의 정리

## 1. 이 문서의 목적

초기에 검토한 요소를 지우고 최종 다섯 개만 남기지 않는다. `초기 구상 → 검토 → 분류 변경 → 현재 범위 → 향후 확장`을 기록하여, 왜 지금의 모델이 되었는지 설명한다. 이전 대화에서 거창한 표현으로 지적된 “Design Evolution” 대신 **Workload Model Refinement**를 사용한다.

연구·검증 계획과 레퍼런스는 [Proposal](01-interdeliverable-proposal.md), 거리 계산과 selector의 기술 설계는 [Algorithm Design](02-algorithm-design.md)에 둔다.

## 2. 초기 broad considerations와 정제 과정

초기에는 물품 수, 물품 분산, 작업자 위치, 컨베이어 위치, 공간 패턴, 창고 크기·레이아웃, 통로 수·폭, 선반 간격, 걷기 속도, 물품 처리시간, 바구니 용량, 혼잡 등을 폭넓게 고려했다. 이들은 물류 작업에 의미가 있는 요소이며 목록에서 빠졌다고 중요성이 부정되는 것은 아니다.

| 단계 | 내용 | 판단과 이유 |
|---|---|---|
| 초기 탐색 | 작업과 환경·운영 조건을 함께 후보로 검토 | 영향을 줄 수 있는 요소를 넓게 수집 |
| 범위 축소 요청 | 수십 개 대신 5–8개 정도로 줄이기 | 알고리즘 선택에 필요한 설명력과 프로젝트 규모 고려 |
| 6개 후보 | Item Count, Dispersion, Picker-to-Item, Item-to-Conveyor, Spatial Pattern, Warehouse Layout | Layout은 작업마다 바뀌는 특성과 성격이 다름을 확인 |
| 현재 5개 core feature | 앞의 다섯 특성만 selector 입력으로 사용 | Layout은 먼저 고정 환경으로 분리하여 비교를 통제 |
| 후속 확장 | 레이아웃 변화, 혼잡, multi-picker | 1차 결과를 얻은 뒤 단계적으로 도입 |

이전의 ‘warehouse layout도 feature로 사용할 수 있다’는 구상은 다른 레이아웃으로의 일반화 검증 후보로 보존한다. 현재의 결정은 그 가능성을 삭제하는 것이 아니라 실험 단계를 나누는 것이다.

## 3. 현재의 5개 core workload feature

`P={p1,…,pn}`, `S`는 시작점, `C`는 고정 인계점, `d`는 통로 그래프 최단거리다. `n`은 중복 제거한 필수 피킹 위치 수이며 주문 수량과 구별한다.

| Feature | 현재 정의 | 실제 상황과의 연결 | 검증할 역할 |
|---|---|---|---|
| **Item Count** | `n = |P|` | 한 작업에서 접근해야 하는 위치 수 | Exact의 계산 가능 범위와 heuristic 전환 |
| **Item Dispersion** | `2/[n(n−1)] · Σ(i<j) d(pi,pj)` | 여러 통로·구역에 흩어진 피킹 위치 | NN 대비 2-opt 개선 여지 |
| **Picker-to-Item Distance** | `(1/n) · Σi d(S,pi)` | 작업자가 요청 위치군에서 떨어진 정도 | 시작점에 따른 순서 차이 |
| **Item-to-Conveyor Distance** | `(1/n) · Σi d(pi,C)` | 작업 후 인계 공정으로 이동해야 하는 부담 | 종점을 고려하는 greedy의 효과 |
| **Spatial Distribution Pattern** | Clustered / Random-Stow-like / Directional | 저장·수요 관계로 생기는 위치 패턴을 단순화 | 같은 평균 거리로 설명되지 않는 구조 차이 |

`n<2`이면 dispersion은 0으로 정의한다. `n=0`이면 두 평균 거리도 0으로 기록하고 selector 없이 `S→C`를 처리한다. 도달 불가능 위치는 feature 계산 전에 실패로 분리한다.

Dispersion은 거리라는 수치이고 pattern은 생성 조건이라는 범주다. 같은 평균 dispersion이라도 한쪽에 길게 놓인 사례와 여러 작은 군집 사례는 다른 순서를 요구할 수 있다. 그렇다고 두 feature가 통계적으로 독립이라고 가정하지 않는다. 중복·상관은 데이터에서 확인하고 ablation으로 추가 설명력을 평가한다.

### 생성 규칙 제안

- **Clustered:** 인접한 소수 통로나 구역에서 주로 위치를 뽑는다. 초기 제안의 1–3개 aisle 집중은 후보 설정으로 보존한다.
- **Random-Stow-like:** 고정된 저장 위치 중 창고 전역에서 작업 위치를 추출한다. 실제 쿠팡의 배치·수요 분포를 복원한 데이터라는 뜻은 아니다.
- **Directional:** 특정 방향·후방 구역 또는 길게 이어지는 영역으로 선택 확률을 편향시킨다. 구역과 편향 강도는 구현 전에 명시한다.

시작점은 front/depot, center, edge 등의 사례를 만들 수 있다. `C`는 front-center 같은 한 위치에 고정하고 물품군을 바꿔 conveyor-near/far 작업을 만든다. 매 작업마다 설비를 옮기는 실험으로 해석하지 않는다.

Low/Medium/High는 설명용 구간이다. 필요하면 보정 집합의 분위수를 사용하고 경계값을 저장하여 평가 집합에 동일하게 적용한다. 보지 않은 평가 데이터 전체를 보고 구간이나 선택 규칙을 재조정하지 않는다. 구간 외에도 실제 거리값과 단위를 반드시 보존한다.

## 4. 환경·운영 조건으로 분리한 항목

| 초기 고려 요소 | 현재 분류 | 1차 실험 처리 |
|---|---|---|
| Warehouse layout, aisle/cross-aisle 수, 크기·폭, 선반 간격 | 환경 | 하나의 이동 그래프로 고정 |
| Conveyor 위치 | 환경 | 고정 `C`; 요청 위치와의 상대 거리는 workload마다 변화 |
| Picker 위치 | 작업 입력 | `S`를 변화시키되 selector는 평균 시작 거리를 사용 |
| Walking speed, item retrieval time | 운영 상수 | 고정하고 선택 피처에서 제외 |
| Basket capacity | 작업 성립 조건 | 주어진 작업이 한 바구니에 들어간다고 가정. 용량 제한 다중 회차는 별도 확장 |
| Congestion, aisle capacity, route interference | 상호작용 조건 | 1차에서는 제외하고 multi-picker 단계에서 모델링 |

레이아웃은 실제 통로 거리 계산에 계속 반영된다. Selector의 직접 입력에서 제외한다고 그래프에서 삭제하는 것은 아니다. 또한 고정 `C`와 변화하는 `Item-to-Conveyor Distance`는 모순되지 않는다. 요청 물품의 위치가 바뀌기 때문이다.

## 5. 실제 물류창고와의 연결 및 한계

쿠팡 공식 WMS 자료는 여러 품목을 혼합 배치하고 수요 등을 고려해 동선을 줄이는 Random Stow를 설명한다. PDA와 경로 안내 설명은 작업자 시작점·물품 위치가 중요하다는 동기를 준다. 출처는 [Proposal R1–R2](01-interdeliverable-proposal.md#5-related-work와-레퍼런스)에 모았다.

여기서 다섯 피처로의 연결은 **본 프로젝트의 모델링 해석**이다. 쿠팡이 동일한 다섯 피처나 본 프로젝트의 알고리즘을 사용한다는 뜻은 아니다. Random Stow도 실제로 단순 무작위 배치라는 뜻이 아니므로, 합성 패턴에는 `-like`를 붙인다.

`C`는 출고 프로세스와 연결된 인계점으로 일반화한다. 실제 공정에는 rebin·packing 등의 중간 단계가 있을 수 있다. 정확한 센터 레이아웃, 작업당 물품 수 분포, 작업자 시작 위치 분포, conveyor 좌표는 현재 확보한 자료로 검증되지 않았다. 합성 데이터와 가정을 실제 측정값으로 표시하지 않는다.

초기에는 대형 풀필먼트센터의 전체 크기를 그대로 모델링하는 방향도 검토했다. 그러나 전체 센터는 피킹 외의 여러 공정과 자동화 영역을 포함할 수 있으므로, 현재는 **공개 운영 사례에서 동기를 얻은 하나의 manual PTG picking zone**으로 범위를 좁힌다. 이는 특정 쿠팡 센터의 디지털 복제본이 아니다.

### 환경 수치에 관한 이전 제안의 보존

이전 대화에는 약 10개 평행 picking aisle, 3개 cross aisle, aisle 길이 약 15m, 약 3m 폭/간격 규모, front-center 인계점이라는 시작안이 있었다. 이 값들은 **미확정 시뮬레이션 후보**로 보존한다. 서로 다른 연구 설정에서 가져온 수치를 하나의 실제 창고 측정치로 합치지 않는다. 특히 통로 폭과 통로 중심선 간격은 다르므로 각각 정의해야 한다.

현재 문서에서는 위 수치의 개별 문헌 본문 근거를 확정하지 않았다. [Proposal R7](01-interdeliverable-proposal.md#5-related-work와-레퍼런스)의 연구는 후속 simulation 참고문헌으로 두며, 본문 표·도면 확인 없이 정확한 치수의 출처라고 주장하지 않는다. 구현 시 독립적인 프로젝트 가정으로 채택하거나, 일관된 단일 문헌의 설정과 위치를 확인해 기록한다.

## 6. 현재 실험 구조와 변경 원칙

```text
Fixed Warehouse Environment + Variable Workload
  → Algorithm Selection → Route Generation → Performance Evaluation
```

첫 단계는 소수의 workload 특성이 알고리즘의 거리·비용 차이를 설명하는지 확인한다. 이후 레이아웃을 바꾸어 일반화를 평가하고, 여러 picker가 동시에 움직이면 혼잡·대기·작업 배분을 추가한다. 다섯 피처는 **통제된 1차 모델**이며 실제 피킹의 모든 결정 요인을 망라한다는 주장이 아니다.

후속 수정은 `초기 구상 / 관찰 또는 근거 / 수정 / 이유`를 남기는 방식으로 기록한다. 새 피처를 도입할 때에는 기존 다섯 피처로 설명되지 않는 현상과 필요한 검증을 함께 적는다.
