#!/bin/bash
# 서버 IP 자동 업데이트 스크립트

echo "🔧 서버 IP 주소 자동 업데이트"
echo "================================"
echo ""

# 1. 현재 IP 주소 감지
echo "1️⃣ 현재 IP 주소 감지 중..."
CURRENT_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)

if [ -z "$CURRENT_IP" ]; then
    echo "❌ IP 주소를 찾을 수 없습니다."
    echo "   Wi-Fi가 연결되어 있는지 확인하세요."
    exit 1
fi

echo "   현재 IP: $CURRENT_IP"
echo ""

# 2. .env 파일 확인
echo "2️⃣ .env 파일 확인..."
ENV_FILE="$(dirname "$0")/.env"

if [ ! -f "$ENV_FILE" ]; then
    echo "   .env 파일이 없습니다. 생성합니다..."
    cat > "$ENV_FILE" << EOF
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Google Cloud STT
GOOGLE_APPLICATION_CREDENTIALS=summariq-credentials.json

# MySQL Database Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=summariq

# Server Configuration
SERVER_HOST=$CURRENT_IP
SERVER_PORT=8000
EOF
    echo "   ✅ .env 파일 생성 완료"
else
    # 기존 .env 파일에서 SERVER_HOST 업데이트
    if grep -q "SERVER_HOST=" "$ENV_FILE"; then
        # Mac에서 sed 사용
        sed -i '' "s/SERVER_HOST=.*/SERVER_HOST=$CURRENT_IP/" "$ENV_FILE"
        echo "   ✅ SERVER_HOST 업데이트: $CURRENT_IP"
    else
        # SERVER_HOST가 없으면 추가
        echo "" >> "$ENV_FILE"
        echo "# Server Configuration" >> "$ENV_FILE"
        echo "SERVER_HOST=$CURRENT_IP" >> "$ENV_FILE"
        echo "SERVER_PORT=8000" >> "$ENV_FILE"
        echo "   ✅ SERVER_HOST 추가: $CURRENT_IP"
    fi
fi

echo ""

# 3. MySQL 녹음 URL 업데이트
echo "3️⃣ 기존 녹음의 오디오 URL 업데이트..."
cd "$(dirname "$0")"
source venv/bin/activate
python update_audio_urls.py

echo ""

# 4. 프론트엔드 IP 업데이트 안내
echo "4️⃣ 프론트엔드 설정"
echo "   lib/sttApi.ts 파일의 IP 주소도 업데이트하세요:"
echo ""
echo "   const API_BASE_URL = __DEV__ ? 'http://$CURRENT_IP:8000' : 'https://api.summariq.app';"
echo ""

# 5. 서버 재시작 여부 확인
echo "================================"
echo "✅ 완료!"
echo ""
echo "서버를 재시작하시겠습니까? (y/n)"
read -r RESTART

if [ "$RESTART" = "y" ] || [ "$RESTART" = "Y" ]; then
    echo ""
    echo "🔄 서버 재시작 중..."
    ./stop_server.sh
    sleep 2
    ./start_server.sh
    echo "✅ 서버 재시작 완료!"
fi

echo ""
echo "🎉 모든 작업이 완료되었습니다!"

