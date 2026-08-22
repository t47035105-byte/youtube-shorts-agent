# 유튜브 쇼츠 에이전트

텔레그램에서 `/make 주제`라고 보내면 GitHub Actions가 컴퓨터 없이도 다음 작업을 수행하도록 만든 프로젝트입니다.

1. 최신 웹 자료를 검색해 소비 검증형 대본과 출처 작성
2. 세로형 장면 이미지 생성
3. ElevenLabs 한국어 내레이션 생성
4. 1080×1920 쇼츠 렌더링
5. 완성 영상과 출처를 텔레그램으로 전송

## 텔레그램 명령

- `/make 배달앱 구독료, 누구에게 이득일까`
- `/status`
- `/help`

GitHub Actions는 5분 간격으로 새 명령을 확인합니다. 동시에 여러 제작이 겹치지 않도록 한 번에 한 편만 처리합니다.

## 필요한 GitHub Secrets

Repository → Settings → Secrets and variables → Actions에서 아래 항목을 등록합니다.

| 이름 | 내용 |
| --- | --- |
| `ELEVENLABS_API_KEY` | ElevenLabs에서 생성한 제한형 키 |
| `ELEVENLABS_VOICE_ID` | 선택한 ElevenLabs 음성 ID |
| `OPENAI_API_KEY` | 웹 검색·대본·이미지 생성을 위한 OpenAI API 키 |
| `TELEGRAM_BOT_TOKEN` | BotFather가 발급한 텔레그램 봇 토큰 |
| `TELEGRAM_ALLOWED_USERNAME` | 본인 텔레그램 사용자명에서 `@`를 뺀 값 |
| `TELEGRAM_ALLOWED_CHAT_ID` | 선택 사항. 사용자명 대신 본인 채팅 ID를 쓸 때 등록 |

키와 토큰은 코드, 이슈, 채팅에 적지 않습니다. GitHub Secrets에만 저장합니다.

## 비용 통제

- ElevenLabs 키는 30일 만료, 문자변환만 허용, 크레딧 10,000으로 제한합니다.
- 이미지 수는 Repository Variables의 `IMAGE_COUNT`로 조절합니다. 기본값은 4입니다.
- OpenAI 모델은 `OPENAI_MODEL`, 이미지 모델은 `OPENAI_IMAGE_MODEL` 변수로 변경할 수 있습니다.

## 로컬 검증

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m src.main --validate-plan sample/sample_plan.json
```

실제 제작은 모든 환경 변수가 준비된 후 실행합니다.

```bash
python -m src.main "배달앱 구독료 비교"
```

## 게시 안전장치

- 대본 생성 때 실시간 웹 검색을 강제합니다.
- 출처가 포함되지 않으면 기획안 검증을 통과하지 못합니다.
- 가격·조건은 게시 시점 기준이며 변경될 수 있다는 문구를 포함합니다.
- 완성물은 자동 업로드하지 않고 먼저 텔레그램으로 보내 검수하도록 설계했습니다.
