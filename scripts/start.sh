#!/bin/bash

echo "🏛️  근현대사 고증 AI — 시작 스크립트"
echo "======================================"

# .env 없으면 생성 안내
if [ ! -f .env ]; then
  echo ""
  echo "⚠️  .env 파일이 없습니다. .env.example을 복사하고 API 키를 입력하세요:"
  echo ""
  echo "  cp .env.example .env"
  echo "  # 그 다음 .env 파일에서 API 키 입력"
  echo ""
  read -p "지금 .env.example을 복사할까요? (y/n): " yn
  if [ "$yn" = "y" ]; then
    cp .env.example .env
    echo "✅ .env 생성 완료. ANTHROPIC_API_KEY를 입력하세요."
    exit 0
  fi
fi

echo ""
echo "Docker Compose 빌드 & 실행 중..."
echo "(첫 실행 시 한국어 임베딩 모델 다운로드로 5~10분 소요)"
echo ""

docker compose up --build -d

echo ""
echo "✅ 실행 완료!"
echo ""
echo "  🌐 웹사이트:  http://localhost"
echo "  📡 API 문서:  http://localhost:8000/docs"
echo "  🗄️  ChromaDB: http://localhost:8001"
echo ""
echo "로그 확인: docker compose logs -f backend"
