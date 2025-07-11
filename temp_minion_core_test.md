import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from google.adk.agents import LlmAgent, CallbackContext
from google.adk.models import LlmRequest, LlmResponse, BaseLlm

# Corrected import for genai.types - this is the primary client library namespace
import google.generativeai as genai
# Specific types are then typically available under genai.types or directly if very common
from google.generativeai.types import GenerateContentConfig, Content, Part, FunctionCall, SafetySetting, HarmCategory # Added SafetySetting, HarmCategory

from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants for State Keys ---
# {session_id}_{minion_name}_...
OPINION_SCORES_KEY_TPL = "{session_id}_{minion_name}_opinion_scores"
LAST_DIARY_STATE_KEY_TPL = "{session_id}_{minion_name}_last_diary_state"
PERCEPTION_PLAN_KEY_TPL = "{session_id}_{minion_name}_perception_plan" # Stores the dict plan
RUN_MODE_KEY_TPL = "{session_id}_{minion_name}_run_mode"
API_KEY_LOG_PERCEPTION_TPL = "{session_id}_{minion_name}_api_key_log_perception"
API_KEY_LOG_RESPONSE_TPL = "{session_id}_{minion_name}_api_key_log_response"
ACTIVE_PERCEPTION_PLAN_TPL = "{session_id}_{minion_name}_active_perception_plan"

class ManagedApiKeyLlm(BaseLlm):
    def __init__(self, model_id: str,
                 api_key_objects_pool: Optional[List[Dict[str,str]]] = None,
                 specific_api_key_id: Optional[str] = None):
        super().__init__(model=model_id)
        self.actual_model_id = model_id
        self.api_key_pool = api_key_objects_pool if api_key_objects_pool is not None else []
        self.specific_api_key_id = specific_api_key_id
        self.round_robin_index = 0

        if not settings.GEMINI_API_KEY and not self.specific_api_key_id and not self.api_key_pool:
             logger.warning(f"ManagedApiKeyLlm for {model_id}: No API key strategy defined (global, specific, or pool). Calls may fail if global key isn't set.")

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> LlmResponse:
        selected_key_value = None
        selected_key_name = "Unknown"
        selected_key_method = "Unknown"

        if self.specific_api_key_id:
            key_obj_dict = next((k for k in self.api_key_pool if k.get("id") == self.specific_api_key_id), None)
            if key_obj_dict:
                selected_key_value = key_obj_dict.get("key")
                selected_key_name = key_obj_dict.get("name", "Specified ID")
                selected_key_method = "Assigned"
            else:
                logger.warning(f"ManagedApiKeyLlm: Specific API key ID '{self.specific_api_key_id}' not found in pool. Falling back.")

        if not selected_key_value and self.api_key_pool:
            if self.api_key_pool:
                key_info_obj_dict = self.api_key_pool[self.round_robin_index]
                selected_key_value = key_info_obj_dict.get("key")
                selected_key_name = key_info_obj_dict.get("name", f"PoolKey_{self.round_robin_index}")
                selected_key_method = "Load Balanced"
                self.round_robin_index = (self.round_robin_index + 1) % len(self.api_key_pool)
            else:
                selected_key_method = "Fallback (Pool Empty)"

        if not selected_key_value:
            selected_key_value = settings.GEMINI_API_KEY
            selected_key_name = "Global Settings Key"
            selected_key_method = "Fallback (Global)"
            if not selected_key_value: # Critical: no key at all
                 selected_key_method = "ERROR - No Key Resolvable"
                 logger.critical(f"ManagedApiKeyLlm ({self.actual_model_id}): NO API KEY RESOLVED. ALL LLM CALLS WILL FAIL.")

        api_key_to_use = selected_key_value

        api_key_log_info = {
            "key_name": selected_key_name, "key_method": selected_key_method,
            "timestamp": datetime.now(timezone.utc).timestamp(), "model_id": self.actual_model_id
        }

        if not api_key_to_use:
            logger.error(f"ManagedApiKeyLlm ({self.actual_model_id}): No API key available. Log: {api_key_log_info}")
            return LlmResponse(text="Error: No API key available.", data={"error": "No API Key", "isError": True, "apiKeyLog": api_key_log_info})

        try:
            current_global_key = None
            if hasattr(genai, 'shared_config') and hasattr(genai.shared_config, 'api_key'): # Check if global key is accessible
                current_global_key = genai.shared_config.api_key

            if current_global_key != api_key_to_use:
                logger.info(f"ManagedApiKeyLlm ({self.actual_model_id}): Temporarily reconfiguring global API key from '{str(current_global_key)[:5]}...' to use '{selected_key_name}'.")
                genai.configure(api_key=api_key_to_use) # This is global, ensure it's handled or this instance is used sequentially.

            model_instance = genai.GenerativeModel(
                model_name=self.actual_model_id,
                system_instruction=llm_request.config.system_instruction if llm_request.config else None,
                generation_config=llm_request.config.generation_config if llm_request.config else None,
# THIS IS LINE 100
                safety_settings=llm_request.config.safety_settings if llm_request.config else None,
                tools=llm_request.config.tools if llm_request.config else None,
            )

            logger.info(f"ManagedApiKeyLlm: Calling {self.actual_model_id} with key '{selected_key_name}' ({selected_key_method}).")
            response: genai.types.GenerateContentResponse = await model_instance.generate_content_async(
                contents=llm_request.contents,
            )

            if current_global_key != api_key_to_use and current_global_key is not None: # Restore previous global key
                logger.info(f"ManagedApiKeyLlm ({self.actual_model_id}): Restoring global API key to '{str(current_global_key)[:5]}...'.")
                genai.configure(api_key=current_global_key)

            text_response = ""
            try:
                text_response = response.text
            except ValueError:
                logger.warning(f"ManagedApiKeyLlm ({self.actual_model_id}):ValueError extracting text. Feedback: {response.prompt_feedback}")
                text_response = "[ERROR EXTRACTING TEXT]"
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    text_response = f"[BLOCKED: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason.name}]"

            response_data = {"apiKeyLog": api_key_log_info}
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                response_data["isError"] = True
                error_details_serializable = {
                    "block_reason": response.prompt_feedback.block_reason.name if response.prompt_feedback.block_reason else "Unknown",
                    "block_reason_message": response.prompt_feedback.block_reason_message or ""
                }
                safety_ratings_serializable = []
                if response.prompt_feedback.safety_ratings:
                    for rating in response.prompt_feedback.safety_ratings:
                        safety_ratings_serializable.append({
                            "category": rating.category.name if rating.category else "Unknown",
                            "probability": rating.probability.name if rating.probability else "Unknown",
                            "severity": rating.severity.name if hasattr(rating, 'severity') and rating.severity else "NotSet"
                        })
                if safety_ratings_serializable: error_details_serializable["safety_ratings"] = safety_ratings_serializable
                response_data["error_details"] = error_details_serializable

            parsed_fc_calls = None
            if hasattr(response, 'function_calls') and response.function_calls:
                parsed_fc_calls = [FunctionCall(name=fc.name, args=dict(fc.args)) for fc in response.function_calls]

            return LlmResponse(text=text_response, function_calls=parsed_fc_calls, data=response_data)

        except Exception as e:
            logger.error(f"ManagedApiKeyLlm ({self.actual_model_id}): Error during generate_content_async: {e}", exc_info=True)
            if 'current_global_key' in locals() and current_global_key != api_key_to_use and current_global_key is not None: # Ensure restoration
                genai.configure(api_key=current_global_key)
            return LlmResponse(text=f"Error: {str(e)}", data={"error": str(e), "isError": True, "apiKeyLog": api_key_log_info})

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r".*"]

# --- MinionAdkAgent Class (Full Corrected Version) ---
class MinionAdkAgent(LlmAgent):
    def __init__(
        self, minion_id_internal: str, persona_prompt_template: str,
        initial_opinion_scores: Optional[Dict[str, int]] = None, **kwargs: Any
    ):
        if 'instruction' not in kwargs or not kwargs['instruction']: # Base instruction for LlmAgent
            kwargs['instruction'] = persona_prompt_template
        if 'model' not in kwargs or not isinstance(kwargs['model'], BaseLlm):
             raise ValueError("MinionAdkAgent requires a 'model' instance of BaseLlm (e.g., ManagedApiKeyLlm).")

        super().__init__(**kwargs)
        self.minion_id_internal = minion_id_internal
        self.persona_prompt_template = persona_prompt_template
        self.default_opinion_scores = {settings.LEGION_COMMANDER_NAME: 50}
        if initial_opinion_scores: self.default_opinion_scores.update(initial_opinion_scores)
        logger.info(f"Minion ADK Agent {self.name} (ID: {self.minion_id_internal}) initialized with instruction: {str(kwargs['instruction'])[:50]}...")

    async def _before_model_perception_and_plan(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        logger.info(f"Minion {self.name}: Entering _before_model_perception_and_plan.")

        if callback_context.invocation_context is None or callback_context.invocation_context.session is None:
            logger.error(f"Minion {self.name}: InvocationContext or Session is None in _before_model_perception_and_plan. Critical error.")
            return LlmResponse(text="Error: Critical context missing.", data={"isError": True})
        session_id = callback_context.invocation_context.session.id

        user_message_content, chat_history_string = "", ""
        if llm_request.contents:
            if llm_request.contents[-1].parts: user_message_content = llm_request.contents[-1].parts[0].text or ""
            if len(llm_request.contents) > 1: # Check if there are preceding content objects for history
                history_content_list = llm_request.contents[:-1]
                history_texts = []
                for hist_content in history_content_list:
                    for part_obj in hist_content.parts:
                        if part_obj.text:
                             # Simple role guessing; ADK content usually has role.
                             role_for_hist = hist_content.role if hist_content.role else "model"
                             history_texts.append(f"[{role_for_hist.upper()}]: {part_obj.text}")
                chat_history_string = "\n".join(history_texts)

            # Override with specific history part if sent by main_backend.py's design
            if len(llm_request.contents[-1].parts) > 1 and (llm_request.contents[-1].parts[1].text or "").strip():
                 chat_history_string = llm_request.contents[-1].parts[1].text or chat_history_string

        s_id = session_id
        channel_type = callback_context.state.get(f"{s_id}_current_channel_type", "user_minion_group")
        last_sender = callback_context.state.get(f"{s_id}_last_message_sender_name", settings.LEGION_COMMANDER_NAME)

        opinion_scores_key = OPINION_SCORES_KEY_TPL.format(session_id=s_id, minion_name=self.name)
        last_diary_key = LAST_DIARY_STATE_KEY_TPL.format(session_id=s_id, minion_name=self.name)
        current_opinions = callback_context.state.get(opinion_scores_key, self.default_opinion_scores.copy())
        last_diary_str = json.dumps(callback_context.state.get(last_diary_key, {})) # Default to empty obj if not found

        run_mode_key = RUN_MODE_KEY_TPL.format(session_id=s_id, minion_name=self.name)
        current_run_mode = callback_context.state.get(run_mode_key)
        active_plan_key = ACTIVE_PERCEPTION_PLAN_TPL.format(session_id=s_id, minion_name=self.name)

        plan_dict: Optional[Dict[str, Any]] = None
        perception_api_log: Optional[Dict[str, Any]] = None

        if current_run_mode == "speak_with_plan":
            plan_dict = callback_context.state.get(active_plan_key)
            if not plan_dict or not isinstance(plan_dict, dict): # Ensure plan_dict is a dict
                logger.error(f"Minion {self.name}: 'speak_with_plan' mode but no valid plan at '{active_plan_key}'. Found: {plan_dict}")
                return LlmResponse(text="Error: Missing or invalid plan for speaking.", data={"isError": True})

            logger.info(f"Minion {self.name}: Using provided plan for 'speak_with_plan' mode. Action: {plan_dict.get('action')}")

            # Update agent's internal state based on this provided plan (as if perception just happened for it)
            callback_context.state[opinion_scores_key] = plan_dict.get("finalOpinions", current_opinions)
            callback_context.state[last_diary_key] = plan_dict

            # Retrieve perceptionApiKeyLog if orchestrator embedded this within the plan_dict
            if isinstance(plan_dict, dict) and "perceptionApiKeyLog" in plan_dict:
                 perception_api_log = plan_dict["perceptionApiKeyLog"]
                 callback_context.state[API_KEY_LOG_PERCEPTION_TPL.format(session_id=s_id, minion_name=self.name)] = perception_api_log

            if plan_dict.get("action") == "STAY_SILENT":
                logger.info(f"Minion {self.name}: Plan is STAY_SILENT, but in speak_with_plan mode (unexpected).")
                return LlmResponse(text="[STAY_SILENT_UNEXPECTED]", data={"internalDiary": plan_dict, "isError": True, "error_message": "Instructed to speak with a silent plan.", "apiKeyLog": perception_api_log })
        else:
            prompt_str = settings.get_perception_and_planning_prompt(
                minionName=self.name, personaPrompt=self.persona_prompt_template,
                previousDiaryJSON=last_diary_str, currentOpinionScoresJSON=json.dumps(current_opinions),
                channelHistoryString=chat_history_string, lastMessageSenderName=last_sender,
                channelType=channel_type
            )

            # Ensure llm_request.config and its generation_config exist before trying to set temperature
            current_llm_config = llm_request.config if llm_request.config is not None else LlmRequest.Config()
            if current_llm_config.generation_config is None:
                current_llm_config.generation_config = GenerateContentConfig()

            if self.generate_content_config and self.generate_content_config.temperature is not None:
                 current_llm_config.generation_config.temperature = self.generate_content_config.temperature
            else: # Default if not set on agent
                 current_llm_config.generation_config.temperature = 0.7

            perception_req_for_model = LlmRequest(contents=[Content(parts=[Part(text=prompt_str)], role="user")], config=current_llm_config)

            logger.info(f"Minion {self.name}: Sending perception prompt (mode: {current_run_mode or 'initial'}).")
            perception_resp_obj: LlmResponse = await self.model.generate_content_async(perception_req_for_model)

            perception_api_log = perception_resp_obj.data.get("apiKeyLog") if perception_resp_obj.data else None
            if perception_api_log:
                callback_context.state[API_KEY_LOG_PERCEPTION_TPL.format(session_id=s_id, minion_name=self.name)] = perception_api_log

            if not perception_resp_obj.text or (perception_resp_obj.data and perception_resp_obj.data.get("isError")):
                logger.error(f"Minion {self.name}: Perception LLM call failed or returned error. Text: {perception_resp_obj.text}")
                error_data_for_resp = {"internalDiary": {"error": "Perception failed", "details": perception_resp_obj.text}, "isError": True, "apiKeyLog": perception_api_log}
                if perception_resp_obj.data and perception_resp_obj.data.get("error_details"): error_data_for_resp["error_details"] = perception_resp_obj.data.get("error_details")
                return LlmResponse(text="Error during perception.", data=error_data_for_resp)

            try:
                plan_dict = json.loads(perception_resp_obj.text)
                logger.info(f"Minion {self.name}: Received perception plan: {plan_dict.get('action')}")
            except json.JSONDecodeError as e:
                logger.error(f"Minion {self.name}: Failed to parse perception plan JSON: {e}. Response: {perception_resp_obj.text}")
                return LlmResponse(text="Error parsing perception plan.", data={"internalDiary": {"error": "Perception parsing error"}, "isError": True, "apiKeyLog": perception_api_log})

            callback_context.state[opinion_scores_key] = plan_dict.get("finalOpinions", current_opinions)
            callback_context.state[last_diary_key] = plan_dict

        callback_context.state[PERCEPTION_PLAN_KEY_TPL.format(session_id=s_id, minion_name=self.name)] = plan_dict

        if current_run_mode == "perception_only":
            logger.info(f"Minion {self.name}: Perception_only run complete. Action: {plan_dict.get('action')}")
            return LlmResponse(
                text=f"[PERCEPTION_COMPLETE_ACTION_{plan_dict.get('action')}]",
                data={"internalDiary": plan_dict, "perception_only_run": True, "apiKeyLog": perception_api_log}
            )

        if plan_dict.get("action") == "STAY_SILENT":
            logger.info(f"Minion {self.name}: Decided to STAY_SILENT.")
            return LlmResponse(text="[STAY_SILENT]", data={"internalDiary": plan_dict, "apiKeyLog": perception_api_log})

        elif plan_dict.get("action") == "SPEAK":
            logger.info(f"Minion {self.name}: Decided to SPEAK. Modifying llm_request for response generation.")
            response_prompt_str = settings.get_response_generation_prompt(
                minionName=self.name, personaPrompt=self.persona_prompt_template,
                channelHistoryString=chat_history_string, plan=plan_dict
            )
            llm_request.contents = [Content(parts=[Part(text=response_prompt_str)], role="user")]

            final_config_for_speak = llm_request.config if llm_request.config is not None else LlmRequest.Config()
            if final_config_for_speak.generation_config is None:
                final_config_for_speak.generation_config = GenerateContentConfig()

            if self.generate_content_config and self.generate_content_config.temperature is not None and final_config_for_speak.generation_config:
                final_config_for_speak.generation_config.temperature = self.generate_content_config.temperature
            llm_request.config = final_config_for_speak
            return None

        logger.error(f"Minion {self.name}: Invalid action '{plan_dict.get('action')}' in plan.")
        return LlmResponse(text="Error: Invalid action in plan.", data={"isError": True, "internalDiary": plan_dict, "apiKeyLog": perception_api_log})

    async def _after_model_modify_response(
        self, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        logger.info(f"Minion {self.name}: Entering _after_model_modify_response.")
        if callback_context.invocation_context is None or callback_context.invocation_context.session is None:
            logger.error(f"Minion {self.name}: InvocationContext or Session is None in _after_model_modify_response. Critical error.")
            error_data = llm_response.data if llm_response.data is not None else {}
            error_data["isError"] = True
            error_data["error"] = "Critical context missing in after_model_modify_response"
            return LlmResponse(text=llm_response.text or "Error: Critical context missing", data=error_data)

        session_id = callback_context.invocation_context.session.id

        current_data = llm_response.data if llm_response.data is not None else {}

        active_plan_key = PERCEPTION_PLAN_KEY_TPL.format(session_id=session_id, minion_name=self.name)
        active_plan = callback_context.state.get(active_plan_key)
        if active_plan:
            current_data["internalDiary"] = active_plan
        else:
            logger.warning(f"Minion {self.name}: No active plan at '{active_plan_key}' for _after_model_modify_response.")
            current_data["internalDiary"] = {"error": "Active perception plan missing for response."}

        if llm_response.data and "apiKeyLog" in llm_response.data:
            response_api_log = llm_response.data["apiKeyLog"]
            callback_context.state[API_KEY_LOG_RESPONSE_TPL.format(session_id=session_id, minion_name=self.name)] = response_api_log
            current_data["responseApiKeyLog"] = response_api_log

        perception_log_key = API_KEY_LOG_PERCEPTION_TPL.format(session_id=session_id, minion_name=self.name)
        perception_api_log = callback_context.state.get(perception_log_key)
        if perception_api_log:
            current_data["perceptionApiKeyLog"] = perception_api_log
            if perception_log_key in callback_context.state:
                 del callback_context.state[perception_log_key]

        llm_response.data = current_data
        logger.info(f"Minion {self.name}: Final LlmResponse.data for event: {llm_response.data}")
        return llm_response
