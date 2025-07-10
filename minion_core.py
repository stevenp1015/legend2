# minion_core.py
import re
import logging
from typing import Dict, Any, Optional, Tuple
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse, Content, Part

from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MinionAgent:
    def __init__(self, minion_id: str, name: str, model_id: str, persona_prompt: str, temperature: float = 0.7):
        self.minion_id = minion_id
        self.name = name
        self.model_id = model_id
        self.persona_prompt = persona_prompt
        self.temperature = temperature
        
        self.opinion_scores: Dict[str, int] = {settings.LEGION_COMMANDER_NAME: 50}
        self.last_diary: Optional[str] = None
        
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # Construct system instructions once for the life of the agent, potentially.
                # However, previous_diary changes, so it needs to be dynamic.
                # self.base_system_instructions = settings.get_emotional_engine_prompt(
                #     minion_name=self.name,
                #     persona_prompt=self.persona_prompt,
                #     previous_diary=self.last_diary # This makes it dynamic per call
                # )
                # self.model = genai.GenerativeModel(
                #     model_name=self.model_id,
                #     # system_instruction will be set per call due to dynamic diary
                # )
            except Exception as e:
                logger.error(f"Minion {self.name}: Failed to configure Gemini: {e}")
                # self.model = None # type: ignore
        else:
            logger.warning(f"Minion {self.name}: GEMINI_API_KEY not available. LLM calls will be mocked/fail.")
            # self.model = None # type: ignore

        logger.info(f"Minion Agent {self.name} (ID: {self.minion_id}) initialized. Model: {self.model_id}")

    def _get_current_system_instructions(self) -> Content:
        """ Constructs the current system instructions including the latest diary state. """
        emotional_engine_text = settings.get_emotional_engine_prompt(
            minion_name=self.name,
            persona_prompt=self.persona_prompt,
            previous_diary=self.last_diary
        )
        return {"parts": [{"text": emotional_engine_text}], "role": "model"} # system_instruction expects Content type or string

    def _extract_diary_and_content(self, response_text: str) -> Tuple[str, Optional[str]]:
        diary_regex = r"~\*\~([\s\S]*?)~\*\~"
        match = re.search(diary_regex, response_text)
        
        if match:
            diary_content = match.group(1).strip()
            main_content = response_text.replace(match.group(0), "").strip()
            return main_content, diary_content
        return response_text.strip(), None

    def _update_internal_state_from_diary(self, diary_text: Optional[str]):
        if not diary_text:
            return

        self.last_diary = diary_text # Store the full diary for next turn
        
        updated_scores_section_match = re.search(r"Updated Opinion Scores:\s*([\s\S]*?)(?:Selected Response Mode|Personal Notes:|$)", diary_text, re.MULTILINE)
        if updated_scores_section_match:
            scores_block = updated_scores_section_match.group(1)
            score_pattern = re.compile(r"-\s*([^:]+?):\s*(\d+)/100") # Made participant name non-greedy
            current_scores = self.opinion_scores.copy()
            for line in scores_block.split('\n'):
                match = score_pattern.search(line.strip())
                if match:
                    participant_name = match.group(1).strip()
                    try:
                        score = int(match.group(2))
                        current_scores[participant_name] = score
                    except ValueError:
                        logger.warning(f"Minion {self.name}: Could not parse score for {participant_name} in diary line: {line}")
            self.opinion_scores = current_scores
            logger.info(f"Minion {self.name} updated opinion scores: {self.opinion_scores}")
        else:
            logger.warning(f"Minion {self.name}: 'Updated Opinion Scores' section not found in diary.")


    async def process_message(
        self,
        user_message_content_for_task: str, # The specific user input that triggered this.
        channel_history_string: str,
        channel_name: str,
        last_message_sender_name: str
    ) -> Tuple[str, Optional[str]]: # Returns (spoken_response, full_llm_response_including_diary)
        
        if not settings.GEMINI_API_KEY: # Or self.model is None
            logger.error(f"Minion {self.name}: GEMINI_API_KEY not set or model not initialized. Cannot process message.")
            return "I am currently unable to process your request due to an internal configuration error.", None

        current_opinion_of_last_sender = self.opinion_scores.get(last_message_sender_name, 50)

        # The user_prompt_for_llm is the "Meta Prompt Task Instructions"
        user_prompt_for_llm_str = settings.get_meta_prompt_task_instructions(
            minion_name=self.name,
            current_opinion_of_last_sender=current_opinion_of_last_sender,
            last_message_sender_name=last_message_sender_name,
            channel_history_string=channel_history_string,
            channel_name=channel_name
        )
        
        system_instructions_content = self._get_current_system_instructions()

        logger.info(f"\n--- Minion {self.name} Processing ---")
        logger.info(f"System Prompt (Emotional Engine for LLM): \n{str(system_instructions_content)[:500]}...")
        logger.info(f"User/Task Prompt (Meta Instructions for LLM): \n{user_prompt_for_llm_str[:500]}...")

        try:
            # Initialize the model per call if system_instruction is dynamic (due to diary)
            # Or, if ADK allows dynamic system_instruction per call, that's better.
            # For google-generativeai, system_instruction is part of model config or GenerateContentConfig.
            # Let's use it with GenerateContentConfig for dynamic behavior.
            
            model_instance = genai.GenerativeModel(self.model_id) # Removed system_instruction from model init
            
            request_config = genai.types.GenerationConfig(temperature=self.temperature)

            # The GenerateContentParameters needs model, contents, and optionally config (which can include systemInstruction)
            # In the new API, system_instruction can be part of the config object passed to generateContent
            # This is a simplified direct call. ADK might wrap this differently.
            contents_for_api : Content = {"parts": [{"text": user_prompt_for_llm_str}], "role": "user"}

            request_payload = {
                "contents": contents_for_api,
                "generation_config": request_config,
                "system_instruction": system_instructions_content # Pass dynamic system instruction here
            }
            
            # Using the generateContent method for text
            response: GenerateContentResponse = await model_instance.generate_content_async(
                **request_payload # type: ignore
            )
            
            raw_llm_response = response.text

        except Exception as e:
            logger.error(f"Minion {self.name}: Error during Gemini API call: {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}", None
        
        logger.info(f"Raw LLM Response for {self.name}: {raw_llm_response[:500]}...")

        if raw_llm_response.strip() == "[SILENT]":
            logger.info(f"Minion {self.name} chose silence.")
            # No diary update on silence as per current meta-prompt
            return "[SILENT]", raw_llm_response # Return raw so backend knows it was [SILENT]

        spoken_response, extracted_diary = self._extract_diary_and_content(raw_llm_response)
        
        if extracted_diary:
            self._update_internal_state_from_diary(extracted_diary)
            logger.info(f"Minion {self.name} New Diary: {extracted_diary[:300]}...")
        else:
            logger.warning(f"Minion {self.name}: No diary extracted from response: {raw_llm_response[:200]}")
        
        logger.info(f"Minion {self.name} Spoken Response: {spoken_response}")
        logger.info(f"--- End Minion {self.name} Processing ---\n")

        return spoken_response, raw_llm_response # Backend will use raw_llm_response to get diary for ChatMessageResponse