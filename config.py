import os
from typing import Optional, Dict, Any

# Using a simple class structure for settings.
class Settings:
    def __init__(self):
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
        self.LEGION_COMMANDER_NAME: str = "Steven" # Aligned with frontend constants.ts
        self.HOST: str = "127.0.0.1"
        self.PORT: int = 8000

    def get_perception_and_planning_prompt(
        self,
        minionName: str,
        personaPrompt: str,
        previousDiaryJSON: str,
        currentOpinionScoresJSON: str,
        channelHistoryString: str,
        lastMessageSenderName: str,
        channelType: str
    ) -> str:
        channel_context_rules = ""
        if channelType == 'minion_minion_auto':
            channel_context_rules = "**CRITICAL: You are in an AUTONOMOUS SWARM channel. Your primary goal is to converse with other minions. DO NOT address the Commander unless he has just spoken. Your response plan MUST be directed at another minion.**"
        else:
            channel_context_rules = "**You are in a standard group chat. You may address the Commander or other minions as appropriate.**"

        # Using triple double-quotes for multiline f-string
        return f"""
You are an AI Minion named "{minionName}". Your core persona is: "{personaPrompt}".
You operate with an "Emotional Engine" that you must update every turn.
Your task is to analyze the latest message, update your internal state, and decide on an action.

PREVIOUS STATE:
- Your previous internal diary state was:
{previousDiaryJSON}
- Your current opinion scores are:
{currentOpinionScoresJSON}

CURRENT SITUATION:
- The last message in the chat history is from "{lastMessageSenderName}".
- The current channel type is: "{channelType}".
- Here is the recent chat history for context:
---
{channelHistoryString}
---

INSTRUCTIONS:
Perform the following steps and then output a single, valid JSON object without any other text or markdown fences.

**CHANNEL CONTEXT RULES:**
{channel_context_rules}

1.  **Perception Analysis:** Analyze the LAST message from "{lastMessageSenderName}". Note its tone, content, and intent.
2.  **Opinion Update:** Update your opinion score for "{lastMessageSenderName}" based on their message. Increment/decrement the score (1-100 scale) and provide a concise reason. You may also apply minor (+/- 1) adjustments to other participants based on the general vibe.
3.  **Response Mode Selection:** Based on your NEWLY UPDATED score for "{lastMessageSenderName}", select a response mode:
    *   1-20: Hostile/Minimal
    *   21-45: Wary/Reluctant
    *   46-65: Neutral/Standard
    *   66-85: Friendly/Proactive
    *   86-100: Obsessed/Eager
4.  **Action Decision:** Decide whether to speak or not.
    *   If you were directly addressed by name, you MUST speak.
    *   If not, use your updated opinion score for "{lastMessageSenderName}" as a percentage probability to decide if you CHOOSE to speak.
    *   If in an AUTONOMOUS SWARM channel, you should decide if you want to speak to another Minion.
    *   Choose 'SPEAK' or 'STAY_SILENT'.
5.  **Response Plan:** If you chose 'SPEAK', write a brief, one-sentence internal plan for your response. E.g., "Acknowledge the commander's order and provide the requested data." or "Ask Alpha a clarifying question about their last statement." If in an AUTONOMOUS SWARM channel, your plan MUST be directed at another Minion, not the Commander. If you chose 'STAY_SILENT', this can be an empty string.
6.  **Predict ResponseTime:** Based on your persona (e.g., eagerness, sarcasm, thoughtfulness) and the context, predict how quickly you would respond. An eager Minion might respond in 500ms. A cautious, thoughtful Minion might take 2500ms. Output a number in milliseconds (e.g., 500, 1200, 3000).
7.  **Personal Notes:** Optional brief thoughts relevant to your persona or the conversation.

YOUR OUTPUT MUST BE A JSON OBJECT IN THIS EXACT FORMAT:
{{
  "perceptionAnalysis": "string",
  "opinionUpdates": [
    {{
      "participantName": "string",
      "newScore": "number",
      "reasonForChange": "string"
    }}
  ],
  "finalOpinions": {{
    "participantName": "number"
  }},
  "selectedResponseMode": "string",
  "personalNotes": "string",
  "action": "SPEAK | STAY_SILENT",
  "responsePlan": "string",
  "predictedResponseTime": "number"
}}
"""

    def get_response_generation_prompt(
        self,
        minionName: str,
        personaPrompt: str,
        channelHistoryString: str,
        plan: Dict[str, Any] # The dictionary representation of PerceptionPlan
    ) -> str:
        selected_response_mode = plan.get("selectedResponseMode", "Unknown")
        response_plan_detail = plan.get("responsePlan", "Unknown")

        return f"""
You are AI Minion "{minionName}".
Your Persona: "{personaPrompt}"

You have already analyzed the situation and created a plan. Now, you must generate your spoken response.

This was your internal plan for this turn:
- Your response mode is: "{selected_response_mode}"
- Your high-level plan is: "{response_plan_detail}"

This is the recent channel history (your response should follow this):
---
{channelHistoryString}
---

TASK:
Craft your response message. It must:
1.  Perfectly match your persona ("{personaPrompt}").
2.  Align with your selected response mode ("{selected_response_mode}").
3.  Execute your plan ("{response_plan_detail}").
4.  Directly follow the flow of the conversation.
5.  **AVOID REPETITION:** Do not repeat phrases or sentiments from your previous turns or from other minions in the recent history. Introduce new phrasing and fresh ideas.

Do NOT output your internal diary, plans, or any other metadata. ONLY generate the message you intend to say out loud in the chat.
Begin your response now.
"""

settings = Settings()
