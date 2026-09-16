FROM python:3.12-slim

# 작업 디렉토리
WORKDIR /app

# Python 의존성 설치 (재빌드 때 버전이 바뀌지 않도록 lock 파일 사용)
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# 소스코드 복사
COPY . .

# 봇 실행
CMD ["python", "main.py"]
