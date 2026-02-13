# 260212_feeling_traker

진행중 프로젝트. 웹앱 + 데스크톱 플로팅 위젯이 같은 데이터(SQLite)를 공유한다.

## 반영된 고도화

1. 앱/컴퓨터 연동: 공용 API 서버(`server.py`) + SQLite 저장
2. 컴퓨터 화면 앱: 웹 관리화면(`index.html`)과 플로팅 위젯(`desktop_widget.py`)
3. 통계 그래프: 최근 기록 점수 추세 캔버스 그래프
4. 알림 정책: 누락 알림은 최근 7일 구간만 (그 이전 누락은 알림 제외)
5. 채팅 세션: 감정 대화 로그 저장 + 분노 진정 페르소나 챗봇
6. 자동 실행: Linux autostart 스크립트 제공
7. 플로팅 단일 클릭: 빠른 기분 선택 팝업 (중복 생성 방지)
8. 기분 저장 후 한 번 더 클릭으로 채팅창 열기(단계 분리)
9. 아이콘 변경: 우클릭 메뉴에서 PNG 선택
10. 플로팅 이동/숨김: 드래그 이동, 우클릭 숨기기(iconify)
11. 플로팅 더블클릭: 관리화면(통계+채팅 포함) 열기

## 실행

터미널 1:
```bash
cd /home/dowon/securedir/git/codex/projects/260212_feeling_traker
./scripts/start_server.sh
```

터미널 2:
```bash
cd /home/dowon/securedir/git/codex/projects/260212_feeling_traker
./scripts/start_widget.sh
```

위젯이 안 보일 때(WSL):
```bash
cd /home/dowon/securedir/git/codex/projects/260212_feeling_traker
pkill -f desktop_widget.py || true
./scripts/start_widget.sh --reset-position
```

브라우저 관리화면:
- `http://127.0.0.1:8765`

플로팅 위젯 확인:
- `./scripts/start_widget.sh` 실행 시 데스크톱 위젯 창 표시
- 위젯 단일 클릭: 기분 선택 팝업
- 팝업의 `저장 후 채팅` 버튼: Calm Bot 채팅창 오픈
- 위젯 더블클릭: 관리화면(`http://127.0.0.1:8765`) 오픈

앱(모바일) 버전 상태:
- 현재는 별도 모바일 앱 바이너리는 아직 없음
- 대신 웹 관리화면 + 데스크톱 플로팅 위젯 2클라이언트가 동일 API/DB를 공유

## 저렴한 모델 옵션

환경변수 `OPENAI_API_KEY`가 있으면 `gpt-4o-mini`(기본) 사용.
없으면 로컬 rule-based 진정 코치로 동작.

옵션:
- `MOOD_CHAT_MODEL=gpt-4o-mini`
- `MOOD_APP_HOST=127.0.0.1`
- `MOOD_APP_PORT=8765`

예시:
```bash
export OPENAI_API_KEY="sk-..."
export MOOD_CHAT_MODEL="gpt-4o-mini"
./scripts/start_server.sh
```

## 주의

- 현재는 같은 서버를 바라보는 모든 클라이언트(웹/위젯)가 데이터 동기화됨.
- 모바일 앱 연동은 동일 API 엔드포인트를 호출하면 바로 가능.
