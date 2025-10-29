# MySQL 비밀번호 수동 초기화 가이드

## 1단계: 모든 MySQL 프로세스 종료

```bash
# 현재 실행 중인 MySQL 프로세스 확인
ps aux | grep mysql

# 모든 MySQL 프로세스 종료
sudo killall mysqld mysqld_safe

# 다시 확인 (아무것도 없어야 함)
ps aux | grep mysql
```

## 2단계: 안전 모드로 MySQL 시작 (비밀번호 없이)

```bash
# 백그라운드에서 안전 모드 시작
sudo /usr/local/mysql/bin/mysqld_safe --skip-grant-tables --skip-networking &

# 10초 대기
sleep 10
```

## 3단계: 비밀번호 없이 MySQL 접속

```bash
# 비밀번호 없이 root로 접속
mysql -u root

# MySQL 프롬프트에서 다음 명령어 실행:
```

## 4단계: MySQL 프롬프트 내에서 실행

```sql
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'your-mysql-password';
FLUSH PRIVILEGES;
EXIT;
```

## 5단계: MySQL 프로세스 정리 및 재시작

```bash
# MySQL 안전 모드 종료
sudo killall mysqld mysqld_safe

# 5초 대기
sleep 5

# 정상 모드로 재시작
sudo /usr/local/mysql/support-files/mysql.server start

# 5초 대기
sleep 5
```

## 6단계: 접속 테스트

```bash
# 새 비밀번호로 접속 테스트
mysql -u root -pyour-mysql-password -e "SELECT VERSION();"

# 성공하면 버전 정보가 출력됩니다!
```

---

## 🎯 한 번에 실행하기 (전체 명령어)

아래 명령어들을 **순서대로** 터미널에 붙여넣으세요:

```bash
# 1. 모든 MySQL 종료
sudo killall mysqld mysqld_safe
sleep 3

# 2. 안전 모드 시작
sudo /usr/local/mysql/bin/mysqld_safe --skip-grant-tables --skip-networking &
sleep 10

# 3. 비밀번호 변경
mysql -u root <<EOF
FLUSH PRIVILEGES;
ALTER USER 'root'@'localhost' IDENTIFIED BY 'your-mysql-password';
FLUSH PRIVILEGES;
EXIT;
EOF

# 4. MySQL 종료
sudo killall mysqld mysqld_safe
sleep 5

# 5. 정상 모드로 재시작
sudo /usr/local/mysql/support-files/mysql.server start
sleep 5

# 6. 테스트
mysql -u root -pyour-mysql-password -e "SELECT VERSION();"
```

만약 위 명령어가 실패하면, 아래 "문제 해결" 섹션을 참고하세요.

---

## 🐛 문제 해결

### 문제 1: "Access denied" 오류

```bash
# MySQL을 완전히 정리하고 다시 시작
sudo killall -9 mysqld mysqld_safe
sudo rm -rf /tmp/mysql.sock /tmp/mysql.sock.lock
sudo /usr/local/mysql/bin/mysqld_safe --skip-grant-tables --skip-networking &
```

### 문제 2: PID 파일을 찾을 수 없음

```bash
# PID 파일 위치 확인 및 삭제
sudo rm -f /usr/local/mysql/data/*.pid
```

### 문제 3: 포트가 이미 사용 중

```bash
# 3306 포트 사용 프로세스 확인
sudo lsof -i :3306

# 해당 프로세스 종료
sudo kill -9 <PID>
```

---

## ✅ 성공 확인

아래 명령어가 에러 없이 실행되면 성공입니다:

```bash
mysql -u root -pyour-mysql-password -e "SELECT 'Success!' AS message;"
```

출력 결과:
```
+---------+
| message |
+---------+
| Success!|
+---------+
```

