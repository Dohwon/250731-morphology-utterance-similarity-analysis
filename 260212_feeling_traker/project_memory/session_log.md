# Session Log

## 2026-02-12

- 프로젝트 초기 생성
- 메모리 격리 구조(`project_memory/`) 적용

## 2026-02-12 23:00

- 고도화 1차 구현 완료
- `server.py` 추가: mood/chat/summary API + SQLite 저장
- `desktop_widget.py` 추가: 플로팅 quick check + 드래그 + 더블클릭 관리화면
- 웹앱 탭 확장: 기분체크 / 통계이력 / 감정대화
- 7일 누락 알림 정책 반영

## 2026-02-12 23:30

- 위젯 가시성 이슈 대응
- `desktop_widget.py`에 `--debug-visible`, `--reset-position`, 강제 전면 표시(`lift/deiconify`) 추가
- `scripts/start_widget.sh`를 WSL 기본 디버그 가시모드로 변경
- README에 WSL 트러블슈팅 실행 절차(`pkill` 후 `--reset-position`) 추가

## 2026-02-12 23:50

- 위젯 UX/한글 가독성 개선
- 클릭 이벤트 재설계: 단일 클릭(빠른 기분), 더블클릭(관리화면) 충돌 제거
- 중복 창 생성 방지: quick/chat 창 단일 인스턴스 유지
- 빠른 기분 팝업을 카드형 선택 UI로 변경, `저장`과 `저장 후 채팅` 분리
- 채팅창에서 `/api/chat` 응답의 감정/원인/행동 분석을 함께 표시
- 한국어 폰트 자동 선택 로직 추가(WSL 포함)
