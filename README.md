# 근현대사 고증 AI

일제강점기(1910~1945) 사료 기반 RAG 검색 시스템.  
소설 집필 고증용 — 국공립 아카이브 사료를 Claude AI가 분석해 답변.

## 구조

```
Docker Compose
├── Frontend  (React + Vite)     → http://localhost
├── Backend   (FastAPI)          → http://localhost:8000
├── ChromaDB  (벡터 DB)           → http://localhost:8001
└── Nginx     (리버스 프록시)
```

## 빠른 시작

### 1. API 키 준비

```bash
cp .env.example .env
```

`.env` 파일 열어서 입력:

```
ANTHROPIC_API_KEY=sk-ant-...       # Anthropic Console에서 발급
PUBLIC_DATA_API_KEY=...             # data.go.kr 에서 발급 (무료)
```

### 2. 공공데이터 API 키 발급 (무료)

1. https://www.data.go.kr 접속 → 회원가입
2. 검색창에 **"한국독립운동사"** 검색
3. OpenAPI 활용신청 → 즉시 발급 (자동승인)
4. 발급된 키를 `.env`의 `PUBLIC_DATA_API_KEY`에 입력

### 3. 실행

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

첫 실행 시 한국어 임베딩 모델(`jhgan/ko-sroberta-multitask`) 자동 다운로드  
**약 5~10분 소요**

### 4. 접속

- 웹사이트: http://localhost
- API 문서: http://localhost:8000/docs

---

## 사용법

### 고증 검색
- "고증 검색" 탭에서 질문 입력
- 예: `1922년 경성 병원 풍경은?`
- 예: `의열단 조직원 신원 노출 시 처리 방법`

### 데이터 수집 (먼저 해야 검색 됨!)

**방법 A — 공공 API 자동 수집**
1. "자료 수집" 탭 → 키워드 입력 (예: `의열단`)
2. 수집 소스 선택 후 "수집 시작"
3. 백그라운드에서 임베딩 처리 (1~2분)

**방법 B — 직접 텍스트 붙여넣기 (API 키 없어도 됨)**
```json
[
  {
    "id": "doc001",
    "text": "우리역사넷에서 복사한 사료 텍스트...",
    "source": "우리역사넷",
    "year": "1922",
    "url": "https://..."
  }
]
```

### 사진 자료
- "사진 자료" 탭에서 검색
- 공유마당(저작권 무료) 연동
- 원본 다운로드 링크 제공

---

## 추천 초기 데이터 수집 키워드

소설 배경에 맞게 순서대로 수집 추천:

1. `의열단` — 독립운동 조직
2. `경성 1920` — 도시 생활
3. `토지조사사업` — 농촌 수탈
4. `3·1운동` — 저항 운동
5. `6·10 만세운동` — 1926년 사건
6. `광주학생운동` — 1929년 사건

---

## 종료

```bash
docker compose down
```

데이터 완전 삭제:
```bash
docker compose down -v
```
