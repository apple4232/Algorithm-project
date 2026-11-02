# A3 Team Project – InterDeliverable Proposal (Working Draft)

작성 기준: 2026-11-02 · 상태: 연구 제안 및 실험 계획, 구현·실험 결과 보고서 아님

## 문서 역할과 정리 원칙

이 문서는 연구질문, 연구방법, 검증 계획과 Related Work를 다룬다. 기술 명세는 [Algorithm Design](02-algorithm-design.md), 변수 정제의 근거와 이력은 [Workload Model Refinement](03-workload-model-refinement.md), 거시적 방향과 확장은 [Direction Summary](04-direction-summary-2026-11-02.md)에 둔다.

이번 정리는 확인 가능한 이전 대화와 로컬 초기 OB 피킹 제안 자료를 바탕으로 작성했다. 이전 대화 전체나 최초 문서 원문의 완전한 복원본은 아니다. 초기 구상은 아래에 보존하고 현재 범위를 별도로 명시한다. 아직 결정하지 않은 수치·규칙은 제안 또는 미확정으로 표시한다.

## 1. 배경과 문제 정의

대상은 작업자가 상품 위치로 직접 이동하는 manual Person-to-Goods(PTG) 피킹이다. 하나의 바구니에 담을 물품 위치들이 주어졌을 때, 시작 위치에서 출발해 모든 위치를 방문하고 출고 공정과 연결된 인계점까지 이동하는 경로를 구한다.

쿠팡의 공개 자료는 PDA를 이용한 작업 배정과 동선 안내, 여러 상품을 혼합 배치하는 Random Stow를 설명한다 [R1, R2]. 이는 위치 기반 피킹 문제의 동기가 되지만 실제 내부 알고리즘이나 작업 데이터가 공개되었다는 뜻은 아니다. 본 프로젝트의 `C`는 출고 컨베이어 공정으로 이어지는 **고정 drop-off / handoff point**의 추상화다. 집품 직후 곧바로 컨베이어에 투입한다는 공정 가정을 실제 센터 전체에 일반화하지 않는다.

입력은 이동 가능한 통로 그래프 `G`, 작업자 시작점 `S`, 필수 피킹 위치 집합 `P`, 인계점 `C`다. 목표는 `S → 모든 P → C`의 이동거리를 줄이는 것이다. `S`와 `C`는 같을 필요가 없고 출발점 복귀를 요구하지 않는다. 선반을 가로지르는 직선거리 대신 통로 최단거리를 사용한다.

## 2. 초기 구상에서 현재 연구질문으로

| 단계 | 당시 구상 | 현재의 처리와 이유 |
|---|---|---|
| 초기 OB 피킹 제안 | 약 10개 물품의 방문 순서를 개선하고 주어진 순서, NN, NN + 2-opt, Brute Force 비교 | 작은 사례의 출발점으로 보존. 약 10개는 실제 업무의 대표값이나 Exhaustive Search의 실행 가능성을 보장하는 기준이 아님 |
| 비교 범위 확장 | Exact / heuristic의 거리·계산시간 trade-off와 최종 인계점 효과 검토 | DP와 Conveyor-Aware 후보를 포함한 알고리즘 포트폴리오로 정리 |
| Workload-aware 구상 | 물품·작업자·창고·운영의 여러 조건에 따라 알고리즘 선택 | 단일 알고리즘의 우승보다 workload에 따른 선택의 효용을 연구 |
| 현재 정제 | 넓은 변수 목록에서 6개 후보를 거쳐 5개 core workload feature로 축소 | 창고 구조와 운영 상수는 먼저 고정하여 workload 효과를 해석 |

### 연구질문

- **RQ1 — 품질과 비용:** 같은 작업에서 Exact, NN, Conveyor-Aware 및 2-opt 조합은 거리와 계산시간 측면에서 어떤 차이를 보이는가?
- **RQ2 — Workload 효과:** 물품 수, 분산도, 시작점·인계점 거리, 공간 패턴은 알고리즘 간 차이를 얼마나 설명하는가?
- **RQ3 — 선택의 효용:** 다섯 피처를 사용하는 간단한 선택 규칙은 고정 알고리즘 및 물품 수만 사용하는 규칙보다, 주어진 계산 예산 안에서 더 짧은 경로를 제공하는가?

분산도가 높으면 2-opt의 이득이 커질 수 있고, 인계점과 물품군의 관계가 Conveyor-Aware의 효과를 바꿀 수 있다는 것은 **검증할 가설**이다. 특정 workload에서 특정 알고리즘이 우수하다고 미리 결론짓지 않는다. 연구 기여는 새로운 최적화 알고리즘 발명이라는 주장보다, 통제된 warehouse workload에서 알고리즘 선택의 타당성을 검증하는 데 둔다 [R3, R6].

## 3. 연구방법과 범위

1. 한 manual picking zone을 통로 그래프로 모델링한다. 레이아웃과 고정 인계점은 1차 실험에서 유지한다.
2. 동일 환경에서 작업들을 생성하고 다섯 core feature를 추출한다. 정의와 정제 이력은 [Refinement](03-workload-model-refinement.md)에 둔다.
3. Dijkstra로 위치 간 통로 최단거리를 구한다. 같은 거리 행렬을 모든 방문 순서 알고리즘에 제공한다.
4. 아래 포트폴리오를 같은 인스턴스에 적용하여 경로 품질과 계산비용을 비교한다.
5. 별도 보정 데이터로 선택 규칙을 정하고, 보지 않은 평가 데이터에서 고정 정책과 비교한다.

| 후보 | 연구에서의 역할 |
|---|---|
| 주어진 물품 순서 | 운영 개선의 단순 비교 기준. 실제 현장 작업자의 성능을 대변하지 않음 |
| Exhaustive Search / Brute Force | 작은 문제의 정확해 및 구현 검증 |
| Subset DP (Held–Karp 형태) | Exhaustive보다 큰 범위의 정확해 기준. 여전히 지수적 비용 [R5] |
| Nearest Neighbor (NN) | 빠른 greedy 기준 |
| Conveyor-Aware Greedy | 고정 종점 효과를 반영하는 실험 후보 |
| NN + 2-opt / Conveyor-Aware + 2-opt | 같은 개선 절차를 적용한 품질·비용 비교 |

현재 범위는 single-picker, 정적 물품 위치, 충돌과 혼잡이 없는 단일 작업이다. 바구니 한도 내 작업이 이미 주어진다고 가정한다. 주문 batching, 재고 위치 선택, 다중 회차, 실제 노동 생산성 예측은 별도 문제로 남긴다.

## 4. 검증과 실험 설계

### 데이터와 통제

- 작은 정확해 검증 사례와, 물품 수가 증가하는 확장 사례를 분리한다. 구체적인 크기 구간과 반복 수는 파일럿 후 고정한다.
- Clustered, Random-Stow-like, Directional 패턴에서 여러 seed로 생성한다. 시작 위치도 front / center / edge 등의 사례를 포함하되 `C`는 고정한다.
- 생성 후 실제 feature 값을 기록한다. 패턴이나 물품 수를 바꾸면 다른 거리 피처도 변할 수 있으므로 완전히 독립적인 실험 요인으로 간주하지 않는다.
- 분산도 구간, 선택 임계값, Conveyor-Aware 계수는 보정 집합에서 정하고 평가 집합에서는 고정한다. 동일·복제 인스턴스가 양쪽에 섞이지 않게 한다.
- 모든 후보는 동일 seed, 그래프, 거리 행렬, 시작점과 종점을 사용한다. 실행 순서를 섞고 실행 환경·시간 한도를 기록한다.

### 평가 지표

| 지표 | 정의 및 해석 |
|---|---|
| 총 이동거리 `L` | 마지막 물품에서 `C`까지 포함한 통로 거리 |
| 계산시간 | 최단경로 전처리, 피처 추출, 선택, 방문 순서 탐색을 분리하고 전체 지연도 보고 |
| Optimality gap | 정확해 `L* > 0`일 때 `100 × (L − L*) / L*`. 0거리 사례는 절대 차이로 보고 |
| 확장성 | 물품 수에 따른 시간·메모리·거리, timeout 비율 |
| 선택 regret | 같은 예산에서 완료된 후보 중 최단거리 대비 선택 경로의 거리 차이. 이는 전역 최적성 보장이 아님 |

정확해를 완료하지 못한 경우에는 최적해 gap을 주장하지 않고 best-known feasible 경로 대비 차이로 표시한다. Timeout을 누락하거나 성공한 실행만 평균 내지 않는다. 반복 사례의 중앙값·분위수, 같은 사례에서의 거리 차이와 불확실성 구간을 함께 보고한다.

선택기는 (a) 모든 작업에 하나의 알고리즘, (b) 물품 수만 사용하는 선택, (c) 다섯 피처 선택을 비교한다. 고정 알고리즘의 선택도 평가 데이터의 정답을 보고 결정하지 않는다. 거리 우선·시간 예산 제약을 기본 평가 관점으로 제안하며, 정확한 예산과 동률 처리 규칙은 실험 전에 확정한다. Selector의 비용까지 포함해 이득이 사라지는지도 확인한다.

### 정확성 확인 계획

작은 사례에서 Exhaustive와 DP의 거리 일치, 경로의 `S`·`C` 유지, 모든 필수 위치 방문, 통로 연결 및 거리 합계 일치를 검사한다. 2-opt가 초기 경로를 악화시키지 않는지 확인한다. 빈 작업, 물품 1개, 중복 위치, 도달 불가능 위치도 포함한다. 현재 저장소의 산출물은 문서이며 이 검증을 이미 수행했다는 의미는 아니다.

## 5. Related Work와 레퍼런스

참고 링크 확인일: 2026-11-02. 아래 문헌은 연구 배경과 방법의 근거이며, 회사 내부 시스템 재현이나 실험 결과의 증거로 사용하지 않는다.

- **[R1] Coupang, 「쿠팡을 움직이는 WMS 물류 기술의 비밀」.** [공식 원문](https://www.coupang.jobs/kr/life-at-coupang/coupang-news/%EC%BF%A0%ED%8C%A1%EC%9D%84-%EC%9B%80%EC%A7%81%EC%9D%B4%EB%8A%94-wms-%EB%AC%BC%EB%A5%98-%EA%B8%B0%EC%88%A0%EC%9D%98-%EB%B9%84%EB%B0%80/). 혼합 배치와 데이터 기반 동선 안내를 이해하기 위한 운영 사례다. Random Stow를 단순 uniform random 배치와 동일시하지 않는다.
- **[R2] Coupang (2022), “A symphony of people and technology: An inside look at a Coupang fulfillment center.”** [공식 원문](https://www.coupang.jobs/en/life-at-coupang/coupang-news/a-symphony-of-people-and-technology-an-inside-look-at-a-coupang-fulfillment-center/). PDA 기반 작업 배정과 경로 최적화, AGV의 공존을 설명한다. 본 프로젝트는 이 중 작업자가 이동하는 피킹 구역에 초점을 맞춘다.
- **[R3] de Koster, R., Le-Duc, T., & Roodbergen, K. J. (2007), “Design and control of warehouse order picking: A literature review,” European Journal of Operational Research, 182(2), 481–501.** [DOI](https://doi.org/10.1016/j.ejor.2006.07.009), [저자 소속기관 서지·초록](https://research.rug.nl/en/publications/design-and-control-of-warehouse-order-picking-a-literature-review/). 레이아웃, 저장 정책, batching, routing이 연결된 문제라는 배경을 제공한다. 본 연구에서는 먼저 routing과 workload 선택으로 범위를 제한한다.
- **[R4] Ratliff, H. D., & Rosenthal, A. S. (1983), “Order-Picking in a Rectangular Warehouse: A Solvable Case of the Traveling Salesman Problem,” Operations Research, 31(3), 507–521.** [DOI 및 초록](https://pubsonline.informs.org/doi/10.1287/opre.31.3.507). 통로 양 끝에만 crossover가 있는 특수 구조의 효율적 정확해 연구다. 모든 창고 피킹 문제가 일반 TSP와 동일한 계산 난도를 갖는다고 주장하지 않으며, 이 특수 알고리즘을 현재의 임의 `S → P → C` 문제에 그대로 적용한다고 가정하지 않는다.
- **[R5] Held, M., & Karp, R. M. (1962), “A Dynamic Programming Approach to Sequencing Problems,” Journal of the Society for Industrial and Applied Mathematics, 10(1), 196–210.** [DOI](https://doi.org/10.1137/0110015). Subset DP의 근거다. 본 프로젝트에서는 고정 시작점과 별도 종점에 맞춰 종료식을 바꾼다.
- **[R6] Rice, J. R. (1976), “The Algorithm Selection Problem,” Advances in Computers, 15, 65–118.** [DOI](https://doi.org/10.1016/S0065-2458(08)60520-3). 문제의 특징에 따라 알고리즘을 선택한다는 관점의 배경이다. 처음부터 학습 모델을 필수로 도입하지 않고 해석 가능한 규칙부터 검증한다.
- **[R7] Winkelhaus, S., Zhang, M., Grosse, E. H., & Glock, C. H. (2022), “Hybrid order picking: A simulation model of a joint manual and autonomous order picking system,” Computers & Industrial Engineering, 167, 107981.** [DOI](https://doi.org/10.1016/j.cie.2022.107981). 공유 공간에서의 picker blocking 등을 다루는 확장 참고문헌이다. 수동·로봇 혼합 시스템의 결과를 현재 single-picker 실험 결과로 전용하지 않는다. 개별 창고 치수의 근거로 쓰려면 본문의 해당 설정을 별도로 확인해야 한다.

## 6. 예정 산출물과 미확정 항목

예정 산출물은 통로 그래프와 workload generator, 방문 순서 알고리즘 포트폴리오, 선택 규칙, 재현 가능한 실험 로그와 비교 보고서다. 현재는 그 설계를 문서화한 단계다.

구현 전에 레이아웃 치수·단위, 물품 수 구간, seed와 반복 수, 시간·메모리 예산, Conveyor-Aware 수식과 계수, 선택 규칙을 확정해야 한다. 후속 변경은 기존 구상의 위치를 남기고 `초기 구상 → 관찰 → 수정 → 이유` 형태로 덧붙인다.
