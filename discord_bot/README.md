```markdown
# 확장 가능한 디스코드 봇

파이썬으로 만든 모듈화된 디스코드 봇입니다. `/speak` 명령어를 통해 지정된 채널에 메시지를 전송할 수 있으며, 쉽게 새로운 기능을 추가할 수 있도록 설계되었습니다.

## 주요 기능

- **`/speak` 명령어**: 지정된 채널에 메시지 전송
- **모듈화된 구조**: 새로운 명령어를 쉽게 추가 가능
- **권한 관리**: 명령어별 권한 설정
- **에러 처리**: 통합된 에러 처리 시스템
- **로깅**: 명령어 사용 및 에러 로깅

## 프로젝트 구조
```

discord_bot/ ├── main.py # 봇 실행 파일 ├── bot/ │ ├── __init__.py │ ├── client.py # 봇 클라이언트 설정 │ └── config.py # 설정 관리 ├── commands/ │ ├── __init__.py │ ├── base.py # 명령어 기본 클래스 │ └── speak.py # speak 명령어 ├── utils/ │ ├── __init__.py │ └── helpers.py # 유틸리티 함수들 ├── .env # 환경 변수 (직접 설정 필요) ├── requirements.txt # 의존성 └── README.md # 이 파일

````javascript

## 설치 및 설정

### 1. 필요한 라이브러리 설치

```bash
pip install -r requirements.txt
````

### 2. 디스코드 봇 생성

1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속
2. "New Application" 클릭하여 새 애플리케이션 생성
3. 애플리케이션 이름 입력 후 생성
4. 좌측 메뉴에서 "Bot" 선택
5. "Add Bot" 클릭하여 봇 생성
6. "Token" 섹션에서 "Copy" 클릭하여 토큰 복사

### 3. 봇 권한 설정

1. 좌측 메뉴에서 "OAuth2" > "URL Generator" 선택

2. "Scopes"에서 `bot`과 `applications.commands` 선택

3. "Bot Permissions"에서 다음 권한들 선택:

   - Send Messages
   - Use Slash Commands
   - Read Message History
   - Manage Messages (speak 명령어용)

4. 생성된 URL로 봇을 서버에 초대

### 4. 환경 변수 설정

`.env` 파일을 열고 다음 값들을 설정하세요:

```env
# Discord Bot Configuration
DISCORD_TOKEN=여기에_봇_토큰_입력
GUILD_ID=여기에_서버_ID_입력_선택사항

# Bot Settings
BOT_PREFIX=!
DEBUG=True

# Minecraft 서버 - /마크_플레이어 명령어용
MINECRAFT_RCON_HOST=localhost
MINECRAFT_RCON_PORT=25575
MINECRAFT_RCON_PASSWORD=서버의_rcon_비밀번호
```

- `DISCORD_TOKEN`: 위에서 복사한 봇 토큰
- `GUILD_ID`: 테스트할 서버 ID (선택사항, 빠른 명령어 동기화용)
- `MINECRAFT_RCON_*`: 마인크래프트 서버 RCON 설정. Docker Compose 운영 시 봇과 Sunlit Valley 서버는 `jgd_default` 네트워크를 공유합니다.

### 5. 봇 실행

```bash
python main.py
```

## 사용법

### `/마크_플레이어` 명령어

Sunlit Valley 마인크래프트 서버에 **현재 접속 중인 플레이어 수와 목록**을 조회합니다.

- **사용법:** `/마크_플레이어`
- **권한:** 모든 사용자 사용 가능
- **필요 조건:** 서버에서 RCON을 활성화하고 Compose에 `MINECRAFT_RCON_HOST`, `MINECRAFT_RCON_PORT`, `MINECRAFT_RCON_PASSWORD`를 설정

### `/마크_재산순위` 명령어

Sunlit Valley 서버에 접속한 적이 있는 전체 플레이어의 Create: Numismatics 은행 잔액을 Spur 단위로 정렬합니다.

- **사용법:** `/마크_재산순위`
- **집계 범위:** `usercache.json`의 전체 플레이어
- **제외 항목:** 인벤토리·상자에 보관한 실물 동전과 아이템 가치

### `/서버_구조_내보내기` 명령어

관리자만 서버의 카테고리, 채널 종류, 포럼 태그와 접근 범위를 JSON 파일로
내보낼 수 있습니다. 메시지, 첨부파일, 멤버 목록, token과 webhook은 포함하지
않으며 Discord ID도 기본적으로 제외합니다. 실제 연동용 식별자가 필요할 때만
`include_ids` 옵션을 사용하세요.

### `/speak` 명령어

지정된 채널에 메시지를 전송합니다.

__사용법:__

```javascript
/speak channel:#채널명 message:전송할 메시지
```

__예시:__

- `/speak channel:general message:안녕하세요!`
- `/speak channel:#공지사항 message:중요한 공지입니다`
- `/speak channel:123456789012345678 message:채널 ID로도 가능합니다`

__필요한 권한:__

- 사용자: `Manage Messages` 권한
- 봇: 대상 채널에 `Send Messages` 권한

## 새로운 명령어 추가하기

새로운 명령어를 추가하려면 다음 단계를 따르세요:

### 1. 새 명령어 파일 생성

`commands/` 폴더에 새 파일을 생성합니다 (예: `ping.py`):

```python
import discord
from discord import app_commands
from commands.base import BaseCommand
from utils.helpers import format_success_message

class PingCommand(BaseCommand):
    @property
    def name(self) -> str:
        return "ping"
    
    @property
    def description(self) -> str:
        return "봇의 응답 시간을 확인합니다"
    
    async def execute(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = format_success_message(f"🏓 Pong! {latency}ms")
        await interaction.response.send_message(embed=embed)

def setup_command(bot):
    ping_cmd = PingCommand(bot)
    
    @app_commands.command(name=ping_cmd.name, description=ping_cmd.description)
    async def ping(interaction: discord.Interaction):
        await ping_cmd.run(interaction)
    
    return ping
```

### 2. 봇 재시작

봇을 재시작하면 새 명령어가 자동으로 로드됩니다.

## 로그 확인

봇 실행 중 발생하는 모든 로그는 `bot.log` 파일에 저장됩니다.

## 문제 해결

### 봇이 시작되지 않는 경우

1. `.env` 파일의 `DISCORD_TOKEN`이 올바른지 확인
2. 필요한 라이브러리가 모두 설치되었는지 확인
3. `bot.log` 파일에서 에러 메시지 확인

### 명령어가 나타나지 않는 경우

1. 봇이 서버에 올바른 권한으로 초대되었는지 확인
2. `GUILD_ID`를 설정한 경우 올바른 서버 ID인지 확인
3. 봇을 재시작하여 명령어 동기화 재시도

### speak 명령어가 작동하지 않는 경우

1. 사용자에게 `Manage Messages` 권한이 있는지 확인
2. 봇이 대상 채널에 메시지를 보낼 권한이 있는지 확인
3. 채널 이름이나 ID가 올바른지 확인

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

```
```
