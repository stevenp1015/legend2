# minion_core.py
import re
import logging
import json
from typing import Dict, Any, Optional, Tuple, Union, cast

from google.adk.agents import LlmAgent, BaseAgent, ReadonlyContext, CallbackContext
from google.adk.models import LlmRequest, LlmResponse, BaseLlm
# Corrected import: google.generativeai.types is the module, then specific classes
from google.generativeai import types as genai_types
from google.generativeai.types import Content, Part, GenerateContentConfig, FunctionCall # Added FunctionCall

from config import settings


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Placeholder for the custom LLM that will handle API key management
# This will be fully implemented in a later step.
class ManagedApiKeyLlm(BaseLlm):
    def __init__(self, model_id: str, api_key_pool: list = None, specific_key: str = None):
        super().__init__(model=model_id)
        self.actual_model_id = model_id
        self.api_key_pool = api_key_pool or []
        self.specific_key = specific_key
        self.round_robin_index = 0
        
        if not settings.GEMINI_API_KEY and not self.specific_key and not self.api_key_pool:
             logger.warning(f"ManagedApiKeyLlm for {model_id}: No API key configured (global, specific, or pool). Calls may fail.")
        # Initialize the genai model instance here if a key is available,
        # or do it per call in generate_content_async.
        # For now, we'll try to configure it per call to be more flexible.


    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> LlmResponse:
        selected_key = self.specific_key
        if not selected_key and self.api_key_pool:
            # Basic round-robin for now if a pool is provided
            if self.api_key_pool:
                 selected_key = self.api_key_pool[self.round_robin_index]
                 self.round_robin_index = (self.round_robin_index + 1) % len(self.api_key_pool)
        
        api_key_to_use = selected_key or settings.GEMINI_API_KEY # Fallback to global settings

        if not api_key_to_use:
            logger.error(f"ManagedApiKeyLlm ({self.actual_model_id}): No API key available for LLM call.")
            return LlmResponse(text_content="Error: No API key available for LLM call.", is_final_response=True, data={"error": "No API Key", "isError": True})

        try:
            # It's generally safer to create a new GenerativeModel instance or use a ServiceClient
            # per call if the API key needs to change, as genai.configure() is global.
            # For this step, we'll simplify and assume one key is used for the model instance's lifetime,
            # or that the key is passed in a way that genai handles it correctly for this call.
            # The ideal solution is to pass a configured client to GenerativeModel.

            # Simplified: Using the globally configured key or the first one from pool for this call.
            # Full API key management logic will be in Step 4.

            model_instance = genai_types.GenerativeModel(
                model_name=self.actual_model_id,
                # system_instruction can be part of llm_request.config
                system_instruction=llm_request.config.system_instruction,
                generation_config=llm_request.config.generation_config,
                safety_settings=llm_request.config.safety_settings,
                # tools=llm_request.config.tools # Not used directly here, handled by LlmAgent
            )

            # The google-generativeai library uses the globally configured API key by default.
            # If specific_key or a key from pool is to be used, genai.configure would need
            # to be called, but this is not ideal for concurrent requests.
            # A better approach (for Step 4) is to use a client:
            # client = google.generativeai.GenerativeServiceClient(api_key=api_key_to_use)
            # model_instance = genai_types.GenerativeModel(..., client=client)
            # For now, we rely on the global key from settings if no specific/pool key is designated
            # and used in a more sophisticated way.
            if selected_key and selected_key != settings.GEMINI_API_KEY:
                 logger.warning(f"ManagedApiKeyLlm ({self.actual_model_id}): Attempting to use specific/pool key '{selected_key[:5]}...' but current simplified genai call uses global config. Full logic in Step 4.")

            logger.info(f"ManagedApiKeyLlm: Calling {self.actual_model_id} for request: {llm_request.contents[-1].parts[0].text[:50]}... Temp: {llm_request.config.generation_config.temperature if llm_request.config.generation_config else 'default'}")

            response = await model_instance.generate_content_async(
                contents=llm_request.contents,
                # stream=stream # ADK LlmAgent handles streaming part, this call is for one-shot response
            )

            # Construct LlmResponse from google.generativeai.types.GenerateContentResponse
            # This needs to handle potential function calls if tools were used, though this
            # specific agent design uses callbacks before the main model call for planning.

            text_response = ""
            try:
                text_response = response.text
            except ValueError: # Handle cases where response might not have direct .text (e.g. blocked)
                logger.warning(f"ManagedApiKeyLlm ({self.actual_model_id}):ValueError extracting text from response. Prompt Feedback: {response.prompt_feedback}")
                text_response = "[ERROR EXTRACTING TEXT]" # Or handle more gracefully
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    text_response = f"[BLOCKED: {response.prompt_feedback.block_reason_message or response.prompt_feedback.block_reason.name}]"
                    return LlmResponse(text_content=text_response, is_final_response=True, data={"isError": True, "error_details": response.prompt_feedback})


            # For this phase, we assume no tool calls from this direct invocation.
            # Tool calls would be in response.function_calls
            return LlmResponse(
                text_content=text_response,
                is_final_response=True, # This is a single call, so it's final
                # data field can be used to pass along other response parts if needed
            )

        except Exception as e:
            logger.error(f"ManagedApiKeyLlm ({self.actual_model_id}): Error during actual generate_content_async: {e}", exc_info=True)
            return LlmResponse(text_content=f"Error: {str(e)}", is_final_response=True, data={"error": str(e)})

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r".*"] # Supports all models by acting as a wrapper


# Constants for state keys - updated for session_id namespacing
OPINION_SCORES_KEY_TPL = "{session_id}_{minion_name}_opinion_scores"
LAST_DIARY_STATE_KEY_TPL = "{session_id}_{minion_name}_last_diary_state"
PERCEPTION_PLAN_KEY_TPL = "{session_id}_{minion_name}_perception_plan" # Used by main_backend to store/retrieve specific plan
RUN_MODE_KEY_TPL = "{session_id}_{minion_name}_run_mode" # Used by main_backend to signal agent

# CURRENT_PERCEPTION_PLAN_KEY can be removed if plan is passed explicitly or namespaced for storage by callback

class MinionAdkAgent(LlmAgent):
    def __init__(
        self,
        minion_id_internal: str, # Keep internal ID for logging or specific non-ADK uses
        persona_prompt_template: str, # The minion's core persona string
        initial_opinion_scores: Optional[Dict[str, int]] = None,
        **kwargs: Any, # Standard LlmAgent arguments like name, model, instruction, generate_content_config
    ):
        # The 'instruction' for LlmAgent will be dynamic via callbacks,
        # so we pass a base instruction or the persona_prompt itself.
        # The actual prompts are constructed in callbacks.
        # The 'model' passed in kwargs should be an instance of ManagedApiKeyLlm.
        super().__init__(**kwargs)
        self.minion_id_internal = minion_id_internal # Store original minion ID if needed
        self.persona_prompt_template = persona_prompt_template # Store persona

        # Default opinion scores if not provided
        self.default_opinion_scores = {settings.LEGION_COMMANDER_NAME: 50}
        if initial_opinion_scores:
            self.default_opinion_scores.update(initial_opinion_scores)
        
        logger.info(f"Minion ADK Agent {self.name} (ID: {self.minion_id_internal}) initialized.")

    async def _before_model_perception_and_plan(
        self, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        logger.info(f"Minion {self.name}: Entering _before_model_perception_and_plan.")

        # 1. Get necessary data from llm_request and context state
        # Assuming user_message is the last content part, and history is penultimate if passed
        user_message_content = ""
        chat_history_string = ""

        if llm_request.contents:
            if len(llm_request.contents[-1].parts) > 0:
                 user_message_content = llm_request.contents[-1].parts[0].text or ""
            if len(llm_request.contents) > 1 and len(llm_request.contents[-2].parts) > 0: # Assuming history is second to last
                 chat_history_string = llm_request.contents[-2].parts[0].text or ""
        
        # TODO: Get channel_type and last_message_sender_name.
        # These might need to be passed in llm_request.contents or callback_context.state
        # For now, using placeholders.
        channel_type = callback_context.state.get("current_channel_type", "user_minion_group")
        last_message_sender_name = callback_context.state.get("last_message_sender_name", settings.LEGION_COMMANDER_NAME)

        # 2. Load opinion scores and last diary state from callback_context.state
        session_id = callback_context.session.id # Get session_id from context
        opinion_scores_key = OPINION_SCORES_KEY_TPL.format(session_id=session_id, minion_name=self.name)
        last_diary_state_key = LAST_DIARY_STATE_KEY_TPL.format(session_id=session_id, minion_name=self.name)

        current_opinion_scores = callback_context.state.get(opinion_scores_key, self.default_opinion_scores.copy())
        last_diary_json = json.dumps(callback_context.state.get(last_diary_state_key, {})) # Default to empty dict if not found
        
        current_opinion_scores_json = json.dumps(current_opinion_scores)

        # 3. Construct the PERCEPTION_AND_PLANNING_PROMPT
        # Assuming PERCEPTION_AND_PLANNING_PROMPT_TEMPLATE is available (e.g., from settings)
        perception_prompt_str = settings.PERCEPTION_AND_PLANNING_PROMPT_TEMPLATE(
            minionName=self.name,
            personaPrompt=self.persona_prompt_template, # Use stored persona
            previousDiaryJSON=last_diary_json,
            currentOpinionScoresJSON=current_opinion_scores_json,
            channelHistoryString=chat_history_string,
            lastMessageSenderName=last_message_sender_name, # This needs to be accurate
            channelType=channel_type # This needs to be accurate
        )
        
        perception_llm_request = LlmRequest(
            contents=[Content(parts=[Part(text=perception_prompt_str)], role="user")],
            config=llm_request.config # Use existing config for temperature etc.
        )

        logger.info(f"Minion {self.name}: Sending perception prompt: {perception_prompt_str[:200]}...")

        # 4. Make the direct LLM call for perception plan
        # The self.model is expected to be an instance of ManagedApiKeyLlm
        perception_response: LlmResponse = await self.model.generate_content_async(perception_llm_request)

        if not perception_response.text_content:
            logger.error(f"Minion {self.name}: Perception LLM call failed or returned empty content.")
            # Return an error response or allow main flow with error indication
            return LlmResponse(text_content="Error during perception.", is_final_response=True, data={"internalDiary": {"error": "Perception failed"}, "isError": True})

        try:
            plan_data = json.loads(perception_response.text_content)
            logger.info(f"Minion {self.name}: Received perception plan: {plan_data}")
        except json.JSONDecodeError as e:
            logger.error(f"Minion {self.name}: Failed to parse perception plan JSON: {e}. Response: {perception_response.text_content}")
            return LlmResponse(text_content="Error parsing perception plan.", is_final_response=True, data={"internalDiary": {"error": "Perception parsing failed"}, "isError": True})

        # 5. Update opinion scores and last diary state in callback_context.state
        new_opinions = plan_data.get("finalOpinions", current_opinion_scores)
        callback_context.state[opinion_scores_key] = new_opinions
        callback_context.state[last_diary_state_key] = plan_data # Store the whole plan as last diary

        # Store the perception plan in the namespaced key for main_backend to retrieve
        session_id = callback_context.session.id
        current_perception_plan_key = PERCEPTION_PLAN_KEY_TPL.format(session_id=session_id, minion_name=self.name)
        callback_context.state[current_perception_plan_key] = plan_data

        # 6. Decide action based on plan & current run_mode
        run_mode_key = RUN_MODE_KEY_TPL.format(session_id=session_id, minion_name=self.name)
        current_run_mode = callback_context.state.get(run_mode_key)

        active_perception_plan_key = f"{session_id}_{self.name}_active_perception_plan" # Key used by main_backend

        if current_run_mode == "speak_with_plan":
            # In this mode, the plan is already decided and provided by the orchestrator (main_backend.py)
            # It should be in callback_context.state[active_perception_plan_key]
            plan_data_for_speak = callback_context.state.get(active_perception_plan_key)
            if not plan_data_for_speak:
                logger.error(f"Minion {self.name}: In 'speak_with_plan' mode but no active_perception_plan found in state key '{active_perception_plan_key}'.")
                return LlmResponse(text_content="Error: Missing plan for speaking.", is_final_response=True, data={"isError": True})
            
            logger.info(f"Minion {self.name}: In 'speak_with_plan' mode. Using provided plan: {plan_data_for_speak.get('action')}")
            # Update opinion scores and last diary based on this provided plan (as if perception just happened)
            new_opinions = plan_data_for_speak.get("finalOpinions", current_opinion_scores)
            callback_context.state[opinion_scores_key] = new_opinions
            callback_context.state[last_diary_state_key] = plan_data_for_speak
            # Also store it in the key that _after_model_modify_response expects for attaching to the output
            callback_context.state[current_perception_plan_key] = plan_data_for_speak


            if plan_data_for_speak.get("action") == "STAY_SILENT":
                logger.info(f"Minion {self.name}: Plan is STAY_SILENT, but in speak_with_plan mode. This shouldn't happen if orchestrator filters.")
                # This case should ideally be filtered out by main_backend.py before calling this agent in "speak_with_plan" mode.
                return LlmResponse(
                    text_content="[STAY_SILENT_UNEXPECTED]",
                    is_final_response=True,
                    data={"internalDiary": plan_data_for_speak, "isError": True, "error_message": "Instructed to speak with a silent plan."}
                )
            # Proceed to SPEAK (construct response_gen_prompt_str)
            plan_data = plan_data_for_speak # Use this plan for response generation
            # Fall through to response generation logic below.
        
        # This part below is for "perception_only" or if "speak_with_plan" needs to generate response
        # If current_run_mode was "speak_with_plan", plan_data is already set from active_perception_plan.
        # Otherwise, it's from the fresh perception call made earlier in this callback.

        if current_run_mode == "perception_only":
            logger.info(f"Minion {self.name}: Perception_only run complete. Plan stored. Action: {plan_data.get('action')}")
            return LlmResponse(
                text_content=f"[PERCEPTION_COMPLETE_ACTION_{plan_data.get('action')}]",
                is_final_response=True,
                data={"internalDiary": plan_data, "perception_only_run": True}
            )

        # If it's not perception_only and action is SPEAK (or plan_data is set from speak_with_plan mode):
        if plan_data.get("action") == "STAY_SILENT": # This check is after speak_with_plan logic, so it's for initial perception deciding silence
            logger.info(f"Minion {self.name}: Chose to STAY_SILENT (initial perception).")
            return LlmResponse(
                text_content="[STAY_SILENT]",
                is_final_response=True,
                data={"internalDiary": plan_data} # Attach plan for frontend
            )
        else: # SPEAK
            logger.info(f"Minion {self.name}: Chose to SPEAK. Preparing response generation prompt.")
            response_gen_prompt_str = settings.RESPONSE_GENERATION_PROMPT_TEMPLATE(
                minionName=self.name,
                personaPrompt=self.persona_prompt_template,
                channelHistoryString=chat_history_string,
                plan=plan_data
            )
            llm_request.contents = [Content(parts=[Part(text=response_gen_prompt_str)], role="user")]

            if not llm_request.config.generation_config:
                llm_request.config.generation_config = GenerateContentConfig()
            if self.generate_content_config and hasattr(self.generate_content_config, 'temperature'):
                 llm_request.config.generation_config.temperature = self.generate_content_config.temperature

            return None # Proceed to main LLM call for response generation

    async def _after_model_modify_response(
        self, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        logger.info(f"Minion {self.name}: Entering _after_model_modify_response.")
        
        session_id = callback_context.session.id
        run_mode_key = RUN_MODE_KEY_TPL.format(session_id=session_id, minion_name=self.name)
        current_run_mode = callback_context.state.get(run_mode_key)

        # This callback primarily attaches the diary if it's a "speak" run.
        # If it was perception_only, the before_model_callback already returned an LlmResponse.
        if current_run_mode != "perception_only":
            perception_plan_key = PERCEPTION_PLAN_KEY_TPL.format(session_id=session_id, minion_name=self.name)
            perception_plan = callback_context.state.get(perception_plan_key)

            current_data = llm_response.data if llm_response.data is not None else {}
            if perception_plan:
                current_data["internalDiary"] = perception_plan
            else:
                logger.warning(f"Minion {self.name}: No perception plan found in state ({perception_plan_key}) for after_model_callback during speak phase.")
                current_data["internalDiary"] = {"error": "Perception plan missing for speak phase"}
            llm_response.data = current_data
            logger.info(f"Minion {self.name}: Modified LlmResponse to include internalDiary: {llm_response.data}")
        else:
            logger.info(f"Minion {self.name}: In perception_only mode, _after_model_modify_response is likely skipped or LlmResponse is already set.")
            # If for some reason it's called in perception_only mode, ensure diary is still there from before_model
            if llm_response.data and "internalDiary" not in llm_response.data:
                 perception_plan_key = PERCEPTION_PLAN_KEY_TPL.format(session_id=session_id, minion_name=self.name)
                 perception_plan = callback_context.state.get(perception_plan_key)
                 if perception_plan:
                     llm_response.data["internalDiary"] = perception_plan


        # It's generally safer for the orchestrator (main_backend.py) to clean up
        # the run_mode and perception_plan from state after it's done with them for that turn.
        # If we delete perception_plan_key here, main_backend might not be able to show it for silent minions.
        logger.info(f"Minion {self.name}: Exiting _after_model_modify_response.")
        return llm_response

    # The LlmAgent's _run_async_impl will be called by the Runner.
    # We are hooking into its process using before_model_callback and after_model_callback.
    # The 'instruction' parameter for LlmAgent is set during __init__ using self.persona_prompt_template.
    # The 'model' parameter for LlmAgent is set during __init__ with an instance of ManagedApiKeyLlm.
    # 'generate_content_config' can be passed in __init__ too.