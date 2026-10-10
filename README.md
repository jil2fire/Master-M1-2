# SeatScope AI

가상 공유 오피스의 일별 좌석 예약 건수를 기록하고, Firestore에 저장된 데이터의 통계·추세를 근거로 AI에게 질문하는 공개 데모입니다. 실제 운영 정보나 개인정보를 입력하지 마세요. 배포된 일반 데이터·대화·채팅 API에는 인증이 없어 다른 방문자가 기록과 대화를 조회하거나 변경할 수 있습니다.

## 기술 스택

- 백엔드: Python 3.10+, FastAPI, Pydantic, Firebase Admin SDK / Firestore, OpenAI SDK(Codyssey Chat Completions 또는 OpenAI Responses API)
- 프론트엔드: 프레임워크 없는 HTML, CSS, JavaScript, SVG
- 배포 대상: Render(백엔드), Vercel(프론트엔드)

## 현재 상태와 배포 주소

코드와 120행의 가상 데이터 CSV가 준비되어 있습니다. 로컬에서는 Firebase와 Codyssey 연결을 검증했으며, Render·Vercel 배포 주소 및 제출 스크린샷은 아직 생성되지 않았습니다.

|항목|주소|
|---|---|
|프론트엔드|배포 후 기입|
|백엔드 API|배포 후 기입|
|Swagger UI|배포 후 기입 (`<백엔드 URL>/docs`)|

## 로컬 실행

저장소 루트에서 PowerShell을 열고 실행합니다.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env # .env가 아직 없을 때만
```

`backend/.env`에 서버 환경 변수를 넣고 Firebase Firestore 데이터베이스를 생성합니다. 서비스 계정 키는 JSON 전체를 한 줄 값으로 넣거나 로컬 키 파일의 경로로 지정할 수 있습니다. 키 파일과 `.env`는 Git에 올리지 마세요.

```powershell
python seed_data.py
uvicorn main:app --reload
```

API는 `http://localhost:8000`, 문서는 `http://localhost:8000/docs`에서 확인합니다. 시드는 CSV의 120행을 날짜 고유성 트랜잭션으로 적재하며 이미 있는 날짜는 건너뜁니다. 수정된 기존 값을 초기 값으로 되돌리지는 않습니다. 초기 상태를 확인하려면 빈 Firestore 데이터셋에서 적재하세요.

새 PowerShell 창에서 프론트엔드를 실행합니다.

```powershell
cd frontend
Copy-Item config.js.example config.js
python -m http.server 5500
```

`http://localhost:5500`에 접속합니다. `frontend/config.js`는 로컬 설정 파일이며 Git에서 제외됩니다.

### 환경 변수

|위치|이름|용도|
|---|---|---|
|백엔드|`OPENAI_API_KEY`|Codyssey의 `sk-cody-` 가상 키 또는 공식 OpenAI API 키|
|백엔드|`AI_PROVIDER`|`codyssey` 또는 `openai`; 생략하면 키 접두어로 판별|
|백엔드|`OPENAI_BASE_URL`|Codyssey에서 `https://copa.codyssey.kr/v1`; 공식 OpenAI 모드에서는 사용하지 않음|
|백엔드|`OPENAI_MODEL`|Codyssey 기본 `gpt-5.4-mini`, 공식 OpenAI 기본 `gpt-4.1-mini`|
|백엔드|`OPENAI_MAX_OUTPUT_TOKENS`|응답 토큰 상한, 기본 300|
|백엔드|`FIREBASE_SERVICE_ACCOUNT_JSON`|서비스 계정 JSON 문자열 또는 키 파일 경로|
|백엔드|`ALLOWED_ORIGINS`|쉼표로 구분한 허용 브라우저 Origin|
|백엔드|`ACTION_API_KEY`|GPT Actions 전용 Bearer 키|
|백엔드|`CHAT_DAILY_LIMIT`|배포 전체의 UTC 일일 AI 채팅 한도, 기본 30|
|프론트 빌드|`API_BASE_URL`|Render API의 공개 HTTPS 주소|

## API와 계산 기준

`POST/GET/PUT/DELETE /api/data`, `GET /api/data/summary`, `POST/GET /api/conversations`, `GET/DELETE /api/conversations/{id}`, `POST /api/chat`을 제공합니다. Swagger UI에서 요청·응답 모델을 확인할 수 있습니다.

요약의 “최근”은 오늘이 아니라 저장된 데이터의 최신 날짜를 기준으로 합니다. 최근 14일과 직전 14일의 실제 관측 일수 및 평균을 비교합니다. 각 구간에 7일 미만의 기록만 있으면 추세를 판정하지 않습니다. 브라우저 그래프는 실제 기록 날짜를 표시하고 날짜별 달력상 최근 7일 이동 평균을 함께 보여 줍니다.

체크인된 CSV를 계산한 예상값은 120건, 총 4,378건, 일평균 36.5건, 최고 2025-03-14의 71건, 최저 2025-04-19의 3건입니다. 데이터 최신일 2025-04-30 기준 최근 14일은 직전 14일보다 13.4% 감소했습니다. Firestore 적재 후 실제 `/api/data/summary` 응답과 대조해야 합니다.

채팅 요청마다 요약을 한 번 계산하여 시스템 프롬프트와 `get_reservation_summary` 함수 도구에 공통으로 사용합니다. 사용한 요약 전체를 AI 답변의 `analysis_summary`에 저장하므로 나중에 데이터가 바뀌어도 답변의 당시 근거가 남습니다. `get_conversation` 함수 도구는 현재 선택한 대화만 읽습니다. 이전 문맥은 최근 20개 메시지만 모델에 보내며 저장 대화는 최대 50개 메시지입니다. 공개 데모의 AI 질문은 배포 전체에서 UTC 날짜당 30회로 제한합니다. 모델 호출 실패도 이미 선점한 1회에 포함됩니다.

## 보너스 기능

- 요약에 평일·주말 평균과 최근 7일 평균을 포함합니다.
- SVG 예약 그래프, CSV 다운로드, 브라우저에 저장되는 다크 모드를 제공합니다.
- 함수 도구 `get_reservation_summary`, `get_conversation`을 연결했습니다. Codyssey에서는 Chat Completions의 `tool_calls` → 서버 실행 → `role: tool` 메시지를, 공식 OpenAI에서는 Responses API의 `function_call_output`을 사용합니다.
- `backend/actions/openapi.yaml`에는 GPT Actions용 읽기 전용 요약·데모 대화 조회 작업이 있습니다. 일반 대화는 Actions 경로에서 404를 반환합니다.

GPT Actions를 연결하려면 `backend/actions/openapi.yaml`의 `servers.url`을 실제 Render 주소로 바꾸고, Actions 인증에 `ACTION_API_KEY`를 Bearer 키로 설정합니다. `cd backend` 후 `python seed_demo_conversations.py`로 가상 데모 대화를 만들고 출력된 ID로 조회합니다. 웹 함수 호출과 Actions 호출의 실제 질문·인수·결과는 배포 후 검증해 이 문서에 기입해야 합니다.

## 배포

1. GitHub 저장소를 Render Web Service에 연결하고 Root Directory를 `backend`로 설정합니다. Build Command는 `pip install -r requirements.txt`, Start Command는 `uvicorn main:app --host 0.0.0.0 --port $PORT`입니다. 위 백엔드 환경 변수를 Render에 설정합니다.
2. 배포된 `/docs`에서 API를 확인하고 빈 Firestore 데이터셋에 `python seed_data.py`를 한 번 실행합니다. 로컬에서 동일한 서비스 계정으로 시드를 실행해도 됩니다.
3. GitHub 저장소를 Vercel에 연결하고 Root Directory를 `frontend`, Build Command를 `node build.mjs`, Output Directory를 `dist`로 설정합니다. `API_BASE_URL`에 Render HTTPS 주소를 넣습니다.
4. Vercel의 정확한 Origin을 Render `ALLOWED_ORIGINS`에 추가하고 재배포합니다. 브라우저에서 채팅·CRUD·대화 불러오기를 검증합니다.

## 검증 및 제출 증빙

로컬에서 `python -m unittest discover -s tests`(백엔드 디렉터리 기준)와 `node --check frontend/app.js`, `node --check frontend/build.mjs`로 순수 계산과 문법을 확인할 수 있습니다. Codyssey 키와 Firebase를 사용한 로컬 `POST /api/chat` 요청은 200 응답을 확인했습니다. 공개 배포와 아래 스크린샷은 별도 검증이 필요합니다.

- [ ] 데이터 요약이 보이는 채팅 화면: 질문과 실제 AI 답변
- [ ] 데이터 관리 화면: 추가·수정·삭제 중 한 동작의 결과
- [ ] 대화 기록 화면: 이전 대화의 메시지 복원
- [ ] 보너스: 그래프·CSV·다크 모드, 웹 함수 호출과 GPT Actions 호출 근거

스크린샷을 촬영하면 `docs/screenshots/`에 저장하고 이 README 본문에 상대 경로 이미지로 삽입합니다. 실제 CSV 통계와 답변 수치를 대조한 뒤 제출하세요.
