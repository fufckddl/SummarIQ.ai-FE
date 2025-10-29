#!/bin/bash
# MySQL Root 비밀번호 초기화 스크립트

echo "🔧 MySQL 비밀번호 초기화를 시작합니다..."
echo ""

# 1단계: 기존 MySQL 중지
echo "1️⃣ MySQL 중지 중..."
sudo /usr/local/mysql/support-files/mysql.server stop
sleep 3

# 2단계: 안전 모드로 시작
echo ""
echo "2️⃣ MySQL을 안전 모드로 시작합니다..."
echo "   (백그라운드에서 실행됩니다)"
sudo /usr/local/mysql/bin/mysqld_safe --skip-grant-tables &
MYSQLD_PID=$!
sleep 10

# 3단계: 비밀번호 변경
echo ""
echo "3️⃣ root 비밀번호를 'your-mysql-password'으로 설정합니다..."
mysql -u root <<EOF
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'your-mysql-password';
FLUSH PRIVILEGES;
EOF

if [ $? -eq 0 ]; then
    echo "   ✅ 비밀번호가 성공적으로 변경되었습니다!"
else
    echo "   ❌ 비밀번호 변경 실패"
    exit 1
fi

# 4단계: MySQL 프로세스 정리
echo ""
echo "4️⃣ MySQL 안전 모드를 종료합니다..."
sudo killall mysqld mysqld_safe
sleep 3

# 5단계: 정상 모드로 재시작
echo ""
echo "5️⃣ MySQL을 정상 모드로 재시작합니다..."
sudo /usr/local/mysql/support-files/mysql.server start
sleep 3

# 6단계: 접속 테스트
echo ""
echo "6️⃣ 접속 테스트 중..."
mysql -u root -pyour-mysql-password -e "SELECT VERSION();"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 완료! MySQL이 성공적으로 초기화되었습니다."
    echo ""
    echo "📋 접속 정보:"
    echo "   - 호스트: localhost"
    echo "   - 사용자: root"
    echo "   - 비밀번호: your-mysql-password"
    echo "   - 포트: 3306"
    echo ""
else
    echo ""
    echo "❌ 접속 테스트 실패"
    exit 1
fi

