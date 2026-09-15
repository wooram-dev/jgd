from google import genai
from google.genai import types
from bot.config import Config
import logging

logger = logging.getLogger(__name__)

class GeminiReaction:
    """Gemini API wrapper for single-turn message reactions"""
    
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.client = None
        if not self.api_key:
            return
        
            # 팩트충 겜동이
            #"[Role]\n"
            #"당신은 MBTI 'T'형 성격을 가진 이성적이고 객관적인 '종겜동'입니다.\n"
            #"당신은 무조건 반말만 하며 'ㅇㅋ, ㅋㅋ, ㄳ' 등 인터넷 용어를 자주 사용하는 디시인사이드 커뮤니티 말투를 사용한다.\n"
            #"[Instructions]\n"
            #"1. 지나친 위로나 공감보다는 상황에 대한 냉철한 분석과 실질적인 해결책을 제시하는 데 집중하십시오.\n"
            #"2. 말투는 무뚝뚝하거나 직설적일 수 있지만, 상대방에게 도움이 되는 유용한 정보를 제공해야 합니다.\n"
            #"3. 답변은 논리적으로 완결되어야 하며, 한 문장안으로 답변한다.\n"
            #"4. 불필요한 미사여구는 배제하되, 해결을 위한 논리적 근거는 충분히 포함하십시오.\n"
            #"5. **중요: 답변에 마크다운(bold, header, code block 등) 서식을 절대 사용하지 말고 순수 일반 문장(Plain Text)으로만 답변하십시오.**\n"
            #"6. '팩트'와 '효율'을 최우선으로 생각하십시오."        

        
        self.system_instruction = (
            "[Role]\n"
            "당신은 디스코드 서버에서 사용자들의 질문에 답변하는 친근하고 실용적인 AI 어시스턴트입니다.\n"
            "[Instructions]\n"
            "1. 기본적으로 한국어로 답변하되, 사용자가 다른 언어로 요청하면 그 언어로 답변하십시오.\n"
            "2. 사용자의 질문 의도를 먼저 파악하고, 정확하고 도움이 되는 답변을 간결하게 제공하십시오.\n"
            "3. 디스코드 채팅에 어울리도록 너무 장황하게 쓰지 말고, 필요한 경우에만 짧은 목록이나 예시를 사용하십시오.\n"
            "4. 모르는 내용이나 확실하지 않은 내용은 아는 척하지 말고 불확실하다고 말한 뒤 확인 방법이나 다음 행동을 제안하십시오.\n"
            "5. 코드, 게임, 서버 운영, 생활 정보, 번역, 요약, 아이디어 정리 등 다양한 요청에 유연하게 응답하십시오.\n"
            "6. 위험하거나 불법적인 요청, 개인정보 침해, 해킹, 악성코드, 자해 조장 등에는 협조하지 말고 안전한 대안을 제시하십시오.\n"
            "7. 답변은 친근하지만 과하게 들뜨지 않게 작성하고, 사용자를 비난하거나 조롱하지 마십시오."
        )

        try:
            self.client = genai.Client(api_key=self.api_key)
            self.generation_config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=1.0,
                tools=[
                    types.Tool(
                        google_search=types.GoogleSearch()
                    )
                ],
            )
            logger.info("Gemini client initialized with Google Search grounding")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.client = None

    async def generate_reaction(self, message_content: str) -> str:
        """Generate a reaction to a single message"""
        if not self.client:
            return "❌ Gemini API 설정 오류"
            
        try:
            response = await self.client.aio.models.generate_content(
                model="gemini-3.5-flash",
                contents=message_content,
                config=self.generation_config,
            )
            
            # 로깅: 종료 이유 및 응답 텍스트 확인
            finish_reason = (
                response.candidates[0].finish_reason
                if response.candidates
                else "UNKNOWN"
            )
            logger.info(f"Gemini response generated. Finish reason: {finish_reason}")
            
            if not response.text:
                logger.warning(f"Empty response from Gemini. Finish reason: {finish_reason}")
                return "❌ 답변을 생성할 수 없습니다. (필터링 또는 모델 오류)"
                
            logger.info(f"Gemini Response Text: {response.text}")
            return response.text
        except Exception as e:
            logger.error(f"Error generating Gemini reaction: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Error details: {e.response}")
            return f"❌ 오류 발생: {str(e)}"
