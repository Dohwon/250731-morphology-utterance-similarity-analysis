# AGENTS.md - 260212_feeling_traker 로컬 규칙

## 적용 범위
- 이 파일이 있는 `260212_feeling_traker` 프로젝트 하위 경로 전체

## 스킬 사용 규칙
- 전역 스킬(관리자/기획/설계/구현/QA/아이디어)을 그대로 사용한다.
- 스킬 업데이트는 전역에 반영되므로, 이 프로젝트도 자동으로 최신 스킬을 사용한다.

## 메모리 격리 규칙 (중요)
- 대화 메모리/작업 로그/결정 이력은 `project_memory/`만 사용한다.
- 다른 프로젝트 폴더의 메모리 파일을 참조/수정하지 않는다.
- 루트 `manager_memory/`에는 요약 로그만 남기고, 상세 컨텍스트는 이 폴더에만 유지한다.

## 필수 업데이트 파일
- `project_memory/active_context.md`
- `project_memory/session_log.md`
- `project_memory/decisions.md`
- `project_memory/backlog.md`
