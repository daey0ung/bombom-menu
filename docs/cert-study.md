# 봄봄 메뉴 프로젝트로 보는 자격증 학습 노트

이 문서는 시험 문제 암기가 아니라 현재 프로젝트에서 확인할 수 있는 실무 개념을
정리한다. 시험 범위는 바뀔 수 있으므로 응시 전 공식 Study Guide를 다시 확인한다.

## GH-300 — GitHub Copilot

GH-300의 중심은 GitHub Copilot 사용, 프롬프트 작성, 책임 있는 AI, 데이터와 기능의
동작 이해다. 이 프로젝트에서 연결되는 부분은 다음과 같다.

- 사람이 목표와 제한을 명확히 설명하고 AI가 코드를 제안하도록 하는 과정
- 기존 JSON을 정답 데이터로 사용해 AI/OCR 결과를 검증하는 평가 사고방식
- 생성 결과를 그대로 신뢰하지 않고 `validate_menu.py`로 검사하는 책임 있는 사용
- Secret을 코드나 로그에 넣지 않는 보안 원칙
- AI가 실패해도 업무가 계속되는 fallback 설계

주의: GitHub Actions 전문 시험은 GH-200이다. 이 프로젝트의 `workflow_dispatch`,
permissions, cache, concurrency 같은 CI/CD 내용은 GH-300에도 도움이 되지만 GH-200에
더 직접적으로 대응한다.

실습 질문:

1. Copilot에게 OCR 좌표 분류 코드를 요청할 때 반드시 제공할 제약은 무엇인가?
2. Copilot이 만든 코드를 검증할 정답 데이터와 성공 기준은 무엇인가?
3. 공개 저장소의 Actions 로그에 Secret이 노출될 수 있는 경로는 무엇인가?

## AI-103 — Azure AI Apps and Agents Developer Associate

공식 범위에는 AI 솔루션 계획·관리, 생성형 AI와 에이전트, 컴퓨터 비전, 텍스트 분석,
정보 추출이 포함된다. 이 프로젝트는 Azure 서비스를 쓰지는 않지만 다음 개념을
작게 실습한다.

| AI-103 개념 | 프로젝트 예 |
|---|---|
| 컴퓨터 비전 | PaddleOCR가 포스터의 글자와 좌표 인식 |
| 정보 추출 | 인식 줄을 특식·기본찬·후식 JSON으로 변환 |
| 신뢰도 임계값 | `MIN_SCORE` 미만 결과 제외 |
| 모델 선택 | mobile/server detection의 품질/속도 비교 후 경량 모델 선택 |
| 평가 | 기존 3일 JSON과 OCR 결과 비교 |
| 운영 안정성 | 모델 캐시, 오류 처리, 이미지 fallback |
| 책임 있는 AI | 원본 이미지를 함께 게시하고 결과 한계를 표시 |

Azure로 확장한다면 로컬 PaddleOCR 대신 Azure AI Vision/Document Intelligence 또는
Foundry 모델을 배치하고, Managed Identity/Key Vault, 모니터링, 콘텐츠 안전성,
비용 한도를 함께 설계하는 문제로 이어진다.

실습 질문:

1. detection과 recognition은 어떤 차이가 있는가?
2. 임계값을 높이면 precision과 recall이 어떻게 변하는가?
3. 모델 정확도뿐 아니라 지연 시간과 비용을 함께 평가해야 하는 이유는 무엇인가?

## AB-100 — Agentic AI Business Solutions Architect

AB-100은 기술 하나보다 비즈니스 요구, 프로세스, 거버넌스, 보안, 운영, 여러 플랫폼의
통합을 전체적으로 설계하는 관점이 중요하다. 이 프로젝트를 Power Automate 흐름으로
보면 다음과 같다.

| 설계 요소 | 프로젝트 예 |
|---|---|
| Trigger | 사용자의 `workflow_dispatch` |
| Action | 수집, OCR, 검증, 렌더, 저장 |
| Condition | 새 이미지 여부와 JSON 검증 결과 |
| Connection | 현재는 GitHub만 사용, Teams는 비활성 |
| Human oversight | 원본 이미지와 OCR 결과를 함께 확인 |
| Exception path | OCR 실패 시 이미지 전용 게시 |
| Governance | 최소 권한, Secret 분리, 사용자가 실행 시점 통제 |
| Adoption | Actions Summary와 텍스트처럼 사용자가 읽기 쉬운 결과 제공 |

Teams를 나중에 추가할 때는 단순히 웹후크 URL만 붙이지 말고 다음을 설계해야 한다.

- 어느 Team/Channel이 업무 소유자인가?
- Workflow Connection 소유자가 퇴사하면 누가 이어받는가?
- 테스트와 운영 채널을 어떻게 분리하는가?
- 잘못된 OCR을 알림 전에 승인받아야 하는가?
- 실패와 재시도를 어디서 모니터링하는가?

## 이 프로젝트의 핵심 복습 흐름

```text
Trigger
  -> 외부 데이터 수집
  -> Computer Vision inference
  -> 정보 추출/구조화
  -> 스키마 검증 Condition
       -> 성공 경로: 이미지 + 텍스트
       -> 실패 경로: 이미지 전용
  -> 사용자용 Summary
  -> 버전 관리된 결과
```

이 흐름을 설명할 수 있으면 세 시험에서 반복되는 책임 있는 AI, 자동화, 보안,
거버넌스, 평가의 공통 기반을 함께 공부할 수 있다.
