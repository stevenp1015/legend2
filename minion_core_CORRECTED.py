import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from google.adk.agents import LlmAgent, CallbackContext # InvocationContext is on callback_context.invocation_context
from google.adk.models import LlmRequest, LlmResponse, BaseLlm

import google.generativeai as genai
from google.generativeai.types import (
    GenerateContentConfig, Content, Part, FunctionCall,
    SafetySetting, HarmCategory, GenerateContentResponse as GenAI_GenerateContentResponse
)

from config import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constants for State Keys ---
OPINION_SCORES_KEY_TPL = "{session_id}_{minion_name}_opinion_scores"
LAST_DIARY_STATE_KEY_TPL = "{session_id}_{minion_name}_last_diary_state"
PERCEPTION_PLAN_KEY_TPL = "{session_id}_{minion_name}_perception_plan"
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
        self.api_key_pool: List[Dict[str, str]] = api_key_objects_pool if api_key_objects_pool is not None else []
        self.specific_api_key_id = specific_api_key_id
        self.round_robin_index = 0

        if not settings.GEMINI_API_KEY and not self.specific_api_key_id and not self.api_key_pool:
             logger.warning(f"ManagedApiKeyLlm for {model_id}: No API key strategy defined. Calls may fail if global key isn't set.")

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> LlmResponse:
        selected_key_value: Optional[str] = None
        selected_key_name: str = "Unknown"
        selected_key_method: str = "Unknown"

        if self.specific_api_key_id:
            key_obj_dict = next((k for k in self.api_key_pool if k.get("id") == self.specific_api_key_id), None)
            if key_obj_dict:
                selected_key_value = key_obj_dict.get("key")
                selected_key_name = key_obj_dict.get("name", "Specified ID")
                selected_key_method = "Assigned"
            else:
                logger.warning(f"ManagedApiKeyLlm: Specific API key ID '{self.specific_api_key_id}' not found in pool. Falling back.")

        if not selected_key_value and self.api_key_pool:
            key_info_obj_dict = self.api_key_pool[self.round_robin_index]
            selected_key_value = key_info_obj_dict.get("key")
            selected_key_name = key_info_obj_dict.get("name", f"PoolKey_{self.round_robin_index}")
            selected_key_method = "Load Balanced"
            self.round_robin_index = (self.round_robin_index + 1) % len(self.api_key_pool)

        if not selected_key_value:
            selected_key_value = settings.GEMINI_API_KEY
            selected_key_name = "Global Settings Key"
            selected_key_method = "Fallback (Global)"
            if not selected_key_value:
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
            # For per-call API key, google-generativeai typically uses a global config.
            # This is not ideal for true concurrent, isolated calls with different keys.
            # A more robust solution involves managing multiple genai.GenerativeModel instances,
            # each configured with its own client or transport if the library supports it.
            # For this implementation, we'll log a warning and use genai.configure if the key differs
            # from the current global one, acknowledging this isn't perfectly thread-safe for highly concurrent distinct key usage.
            current_global_key: Optional[str] = None
            if hasattr(genai, 'shared_config') and genai.shared_config and hasattr(genai.shared_config, 'api_key'):
                current_global_key = genai.shared_config.api_key

            key_needs_reconfigure = current_global_key != api_key_to_use

            if key_needs_reconfigure:
                logger.info(f"ManagedApiKeyLlm ({self.actual_model_id}): Temporarily reconfiguring global API key to use '{selected_key_name}'.")
                genai.configure(api_key=api_key_to_use)

            model_instance_config_args = {}
            if llm_request.config:
                if llm_request.config.system_instruction: model_instance_config_args['system_instruction'] = llm_request.config.system_instruction
                if llm_request.config.generation_config: model_instance_config_args['generation_config'] = llm_request.config.generation_config
                if llm_request.config.safety_settings: model_instance_config_args['safety_settings'] = llm_request.config.safety_settings
                if llm_request.config.tools: model_instance_config_args['tools'] = llm_request.config.tools

            model_instance = genai.GenerativeModel(self.actual_model_id, **model_instance_config_args)

            logger.info(f"ManagedApiKeyLlm: Calling {self.actual_model_id} with key '{selected_key_name}' ({selected_key_method}).")
            response: GenAI_GenerateContentResponse = await model_instance.generate_content_async(
                contents=llm_request.contents, # type: ignore
            )

            if key_needs_reconfigure and current_global_key is not None: # Restore previous global key
                logger.info(f"ManagedApiKeyLlm ({self.actual_model_id}): Restoring global API key.")
                genai.configure(api_key=current_global_key)

            text_response = ""
            try:
                text_response = response.text
            except ValueError:
                logger.warning(f"ManagedApiKeyLlm ({self.actual_model_id}): ValueError extracting text. Feedback: {response.prompt_feedback if hasattr(response, 'prompt_feedback') else 'N/A'}")
                text_response = "[ERROR EXTRACTING TEXT]"
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                    text_response = f"[BLOCKED: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason.name}]"

            response_data = {"apiKeyLog": api_key_log_info}
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and response.prompt_feedback.block_reason:
                response_data["isError"] = True
                error_details_serializable: Dict[str, Any] = {
                    "block_reason": response.prompt_feedback.block_reason.name if response.prompt_feedback.block_reason else "Unknown",
                    "block_reason_message": response.prompt_feedback.block_reason_message or ""
                }
                safety_ratings_serializable = []
                if response.prompt_feedback.safety_ratings:
                    for rating_obj in response.prompt_feedback.safety_ratings: # Corrected variable name
                        safety_ratings_serializable.append({
                            "category": rating_obj.category.name if rating_obj.category else "Unknown", # Corrected variable name
                            "probability": rating_obj.probability.name if rating_obj.probability else "Unknown", # Corrected variable name
                            "severity": rating_obj.severity.name if hasattr(rating_obj, 'severity') and rating_obj.severity else "NotSet" # Corrected variable name
                        })
                if safety_ratings_serializable: error_details_serializable["safety_ratings"] = safety_ratings_serializable
                response_data["error_details"] = error_details_serializable

            parsed_fc_calls: Optional[List[FunctionCall]] = None
            if hasattr(response, 'function_calls') and response.function_calls:
                parsed_fc_calls = [FunctionCall(name=fc.name, args=dict(fc.args)) for fc in response.function_calls]

            return LlmResponse(text=text_response, function_calls=parsed_fc_calls, data=response_data)

        except Exception as e:
            logger.error(f"ManagedApiKeyLlm ({self.actual_model_id}): Error during generate_content_async: {e}", exc_info=True)
            if 'key_needs_reconfigure' in locals() and key_needs_reconfigure and 'current_global_key' in locals() and current_global_key is not None: # Ensure restoration
                genai.configure(api_key=current_global_key)
            return LlmResponse(text=f"Error: {str(e)}", data={"error": str(e), "isError": True, "apiKeyLog": api_key_log_info})

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r".*"]

class MinionAdkAgent(LlmAgent):
    def __init__(
        self, minion_id_internal: str, persona_prompt_template: str,
        initial_opinion_scores: Optional[Dict[str, int]] = None, **kwargs: Any
    ):
        if 'instruction' not in kwargs or not kwargs['instruction']:
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
            logger.error(f"Minion {self.name}: InvocationContext or Session is None. Critical error.")
            return LlmResponse(text="Error: Critical context missing.", data={"isError": True})
        session_id = callback_context.invocation_context.session.id

        user_message_content, chat_history_string = "", ""
        if llm_request.contents: # ADK LlmRequest.contents is List[Content]
            last_content_obj = llm_request.contents[-1]
            if last_content_obj.parts:
                user_message_content = last_content_obj.parts[0].text or ""
                if len(last_content_obj.parts) > 1 and (last_content_obj.parts[1].text or "").strip(): # History passed as second part
                    chat_history_string = last_content_obj.parts[1].text or ""

            if not chat_history_string and len(llm_request.contents) > 1: # Fallback: construct history from prior Content objects
                history_texts = []
                for hist_content in llm_request.contents[:-1]:
                    for part_obj in hist_content.parts:
                        if part_obj.text:
                             role_for_hist = hist_content.role if hist_content.role else "model"
                             history_texts.append(f"[{role_for_hist.upper()}]: {part_obj.text}")
                chat_history_string = "\n".join(history_texts)

        s_id = session_id
        channel_type = callback_context.state.get(f"{s_id}_current_channel_type", "user_minion_group")
        last_sender = callback_context.state.get(f"{s_id}_last_message_sender_name", settings.LEGION_COMMANDER_NAME)

        opinion_scores_key = OPINION_SCORES_KEY_TPL.format(session_id=s_id, minion_name=self.name)
        last_diary_key = LAST_DIARY_STATE_KEY_TPL.format(session_id=s_id, minion_name=self.name)
        current_opinions = callback_context.state.get(opinion_scores_key, self.default_opinion_scores.copy())
        last_diary_str = json.dumps(callback_context.state.get(last_diary_key, {}))

        run_mode_key = RUN_MODE_KEY_TPL.format(session_id=s_id, minion_name=self.name)
        current_run_mode = callback_context.state.get(run_mode_key)
        active_plan_key = ACTIVE_PERCEPTION_PLAN_TPL.format(session_id=s_id, minion_name=self.name)

        plan_dict: Optional[Dict[str, Any]] = None
        perception_api_log: Optional[Dict[str, Any]] = None # To store apiKeyLog from the perception call

        if current_run_mode == "speak_with_plan":
            plan_dict = callback_context.state.get(active_plan_key)
            if not plan_dict or not isinstance(plan_dict, dict):
                logger.error(f"Minion {self.name}: 'speak_with_plan' mode but no valid plan at '{active_plan_key}'. Found: {plan_dict}")
                return LlmResponse(text="Error: Missing or invalid plan for speaking.", data={"isError": True})

            logger.info(f"Minion {self.name}: Using provided plan for 'speak_with_plan' mode. Action: {plan_dict.get('action')}")
            callback_context.state[opinion_scores_key] = plan_dict.get("finalOpinions", current_opinions)
            callback_context.state[last_diary_key] = plan_dict

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

            req_config: LlmRequest.Config = llm_request.config if llm_request.config is not None else LlmRequest.Config()
            if req_config.generation_config is None: req_config.generation_config = GenerateContentConfig()

            agent_temp = self.generate_content_config.temperature if self.generate_content_config and self.generate_content_config.temperature is not None else 0.7
            if req_config.generation_config: # Should exist now
                 req_config.generation_config.temperature = agent_temp # Use agent's configured default for perception

            perception_req_for_model = LlmRequest(contents=[Content(parts=[Part(text=prompt_str)], role="user")], config=req_config)

            logger.info(f"Minion {self.name}: Sending perception prompt (mode: {current_run_mode or 'initial'}).")
            perception_resp_obj: LlmResponse = await self.model.generate_content_async(perception_req_for_model)

            perception_api_log = perception_resp_obj.data.get("apiKeyLog") if perception_resp_obj.data else None
            if perception_api_log:
                callback_context.state[API_KEY_LOG_PERCEPTION_TPL.format(session_id=s_id, minion_name=self.name)] = perception_api_log

            if not perception_resp_obj.text or (perception_resp_obj.data and perception_resp_obj.data.get("isError")):
                logger.error(f"Minion {self.name}: Perception LLM call failed. Text: {perception_resp_obj.text}, Data: {perception_resp_obj.data}")
                error_data = {"internalDiary": {"error": "Perception failed", "details": perception_resp_obj.text}, "isError": True, "apiKeyLog": perception_api_log}
                if perception_resp_obj.data and perception_resp_obj.data.get("error_details"): error_data["error_details"] = perception_resp_obj.data.get("error_details")
                return LlmResponse(text="Error during perception.", data=error_data)

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

            # Ensure the main LlmAgent call uses the correct temperature from MinionAdkAgent's config
            # The original llm_request.config might be from the Runner or a previous callback.
            # We want this agent's specific temperature for the speak call.
            speak_llm_config = llm_request.config if llm_request.config is not None else LlmRequest.Config()
            if speak_llm_config.generation_config is None:
                speak_llm_config.generation_config = GenerateContentConfig()

            if self.generate_content_config and self.generate_content_config.temperature is not None and speak_llm_config.generation_config:
                speak_llm_config.generation_config.temperature = self.generate_content_config.temperature
            llm_request.config = speak_llm_config # Ensure modified/created config is set back
            return None

        logger.error(f"Minion {self.name}: Invalid action '{plan_dict.get('action')}' in plan.")
        return LlmResponse(text="Error: Invalid action in plan.", data={"isError": True, "internalDiary": plan_dict, "apiKeyLog": perception_api_log})

    async def _after_model_modify_response(
        self, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        logger.info(f"Minion {self.name}: Entering _after_model_modify_response.")
        if callback_context.invocation_context is None or callback_context.invocation_context.session is None:
            logger.error(f"Minion {self.name}: InvocationContext or Session is None in _after_model_modify_response.")
            current_data_err = llm_response.data if llm_response.data is not None else {}
            current_data_err["isError"] = True
            current_data_err["error"] = "Critical context missing in after_model_modify_response"
            return LlmResponse(text=(llm_response.text or "Error: Critical context missing"), data=current_data_err)

        session_id = callback_context.invocation_context.session.id
        current_data = llm_response.data.copy() if llm_response.data is not None else {} # Make a copy to modify

        active_plan_key = PERCEPTION_PLAN_KEY_TPL.format(session_id=session_id, minion_name=self.name)
        active_plan = callback_context.state.get(active_plan_key)
        if active_plan:
            current_data["internalDiary"] = active_plan
        else:
            logger.warning(f"Minion {self.name}: No active plan at '{active_plan_key}' for _after_model_modify_response.")
            current_data["internalDiary"] = {"error": "Active perception plan missing for response."}

        # The llm_response.data["apiKeyLog"] here is from the SPEAK LLM call (via ManagedApiKeyLlm)
        if llm_response.data and "apiKeyLog" in llm_response.data:
            response_api_log = llm_response.data["apiKeyLog"]
            # Store it in state for the orchestrator/main_backend to potentially pick up for logging
            callback_context.state[API_KEY_LOG_RESPONSE_TPL.format(session_id=session_id, minion_name=self.name)] = response_api_log
            current_data["responseApiKeyLog"] = response_api_log # Ensure it's in the data being returned

        # Retrieve perception API key log from state (set by _before_model_perception_and_plan)
        perception_log_key = API_KEY_LOG_PERCEPTION_TPL.format(session_id=session_id, minion_name=self.name)
        perception_api_log = callback_context.state.get(perception_log_key)
        if perception_api_log:
            current_data["perceptionApiKeyLog"] = perception_api_log
            # Clean up from state as it's now part of the event data
            if perception_log_key in callback_context.state:
                 del callback_context.state[perception_log_key]

        llm_response.data = current_data # Assign the modified dictionary back
        logger.info(f"Minion {self.name}: Final LlmResponse.data for event: {llm_response.data}")
        return llm_response
