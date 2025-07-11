import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime, timezone # Added missing imports

from google.adk.agents import BaseAgent, InvocationContext # Assuming InvocationContext is correctly here
from google.adk.events import Event
from google.adk.runners import Runner
from google.generativeai.types import Content, Part, GenerateContentConfig

from config import settings # Assuming access to LEGION_COMMANDER_NAME
from minion_core import MinionAdkAgent, ManagedApiKeyLlm
# Assuming main_backend's session_service and other DBs (minion_configs_db, api_keys_db, channels_db, messages_db)
# are accessible or passed appropriately if needed, though orchestrator should primarily use ADK session state.

logger = logging.getLogger(__name__)
APP_NAME = "gemini_legion_cc_adk" # Consistent with main_backend

class AutoChatOrchestratorAgent(BaseAgent):
    def __init__(
        self,
        session_service, # ADK SessionService instance
        minion_configs_map: Dict[str, Any], # {name: config_payload_dict}
        api_keys_list: List[Dict[str,str]], # List of {'id':.., 'name':.., 'key':..}
        **kwargs: Any
    ):
        super().__init__(**kwargs) # name, description if any
        self.session_service = session_service
        self.minion_configs_map = minion_configs_map # For instantiating MinionAdkAgents
        self.api_keys_list = api_keys_list         # For ManagedApiKeyLlm

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        logger.info(f"AutoChatOrchestratorAgent ({self.name}): Starting new auto chat turn.")

        channel_id = ctx.state.get("auto_chat_channel_id")
        if not channel_id:
            logger.error(f"Orchestrator: Missing 'auto_chat_channel_id' in session state.")
            yield Event(author=self.name, data={"error": "Missing channel_id for auto chat.", "isError": True})
            return

        channel_config = ctx.state.get(f"{ctx.session.id}_channel_config") # Sent by main_backend endpoint
        if not channel_config:
            logger.error(f"Orchestrator: Missing 'channel_config' for channel {channel_id} in session state.")
            yield Event(author=self.name, data={"error": "Missing channel_config for auto chat.", "isError": True})
            return

        # These would be passed into ctx.state by the calling endpoint in main_backend.py
        current_chat_history_str = ctx.state.get("auto_chat_history_str", "")
        last_message_sender_name = ctx.state.get("auto_chat_last_speaker", settings.LEGION_COMMANDER_NAME) # Default to commander if no last speaker

        minion_names_in_channel = channel_config.get("members", [])
        active_minions_for_turn: List[MinionAdkAgent] = []

        for name in minion_names_in_channel:
            if name == settings.LEGION_COMMANDER_NAME:
                continue
            min_config_dict = self.minion_configs_map.get(name)
            if min_config_dict:
                # Convert Pydantic model dict back to kwargs for MinionConfigPayload if necessary, or use directly
                # For ManagedApiKeyLlm, ensure api_keys_list is structured as list of dicts with id, name, key

                specific_api_key_id = min_config_dict.get("apiKeyId")

                model_for_agent = ManagedApiKeyLlm(
                    model_id=min_config_dict["model_id"],
                    api_key_objects_pool=self.api_keys_list,
                    specific_api_key_id=specific_api_key_id
                )
                agent_instance = MinionAdkAgent(
                    name=min_config_dict["name"],
                    minion_id_internal=min_config_dict["id"],
                    model=model_for_agent,
                    instruction=min_config_dict["system_prompt_persona"],
                    generate_content_config=GenerateContentConfig(temperature=min_config_dict["params"]["temperature"]),
                    before_model_callback=MinionAdkAgent._before_model_perception_and_plan,
                    after_model_callback=MinionAdkAgent._after_model_modify_response,
                )
                active_minions_for_turn.append(agent_instance)

        if len(active_minions_for_turn) < 1: # Needs at least 1 to speak, ideally 2 for conversation
            logger.warning(f"Orchestrator: Not enough minions ({len(active_minions_for_turn)}) in channel {channel_id} for auto chat.")
            yield Event(author=self.name, data={"text_content": "Auto-mode: Not enough minions to chat.", "isSystemMessage": True})
            return

        # 1. Perception Pass for all eligible minions
        perception_plans: Dict[str, Any] = {}
        logger.info(f"Orchestrator: --- Perception Pass for Auto Chat Channel {channel_id} ---")

        base_user_message_for_adk = Content(parts=[
            Part(text="This is an auto-chat turn."), # Placeholder, real trigger is implicit
            Part(text=current_chat_history_str)
        ])

        for minion_agent in active_minions_for_turn:
            if minion_agent.name == last_message_sender_name: # Minion cannot respond to itself immediately
                logger.info(f"Orchestrator: Skipping perception for {minion_agent.name} as they were the last speaker.")
                continue

            logger.info(f"Orchestrator: Running PERCEPTION for {minion_agent.name} in auto-chat.")

            # Set state for this minion's perception run
            perception_state_update = {
                f"{ctx.session.id}_{minion_agent.name}_run_mode": "perception_only",
                f"{ctx.session.id}_current_channel_type": channel_config.get("type", "minion_minion_auto"),
                f"{ctx.session.id}_last_message_sender_name": last_message_sender_name
            }
            ctx.state.update(perception_state_update) # Update orchestrator's view of session state
            # This state needs to be committed to ADK Session for the MinionAdkAgent to see it.
            await self.session_service.append_event(ctx.session, Event(author="orchestrator_system", actions={"state_delta": perception_state_update}))

            perception_runner = Runner(app_name=APP_NAME, agent=minion_agent, session_service=self.session_service)
            try:
                async for event in perception_runner.run_async(user_id=ctx.session.user_id, session_id=ctx.session.id, new_message=base_user_message_for_adk):
                    if event.author == minion_agent.name and event.is_final_response():
                        # The MinionAdkAgent's callback stores the plan in a namespaced state key
                        plan_key = f"{ctx.session.id}_{minion_agent.name}_perception_plan"
                        # Refresh session to get latest state after minion's run
                        refreshed_session = await self.session_service.get_session(app_name=APP_NAME, user_id=ctx.session.user_id, session_id=ctx.session.id)
                        plan = refreshed_session.state.get(plan_key)
                        if plan:
                            perception_plans[minion_agent.name] = plan
                            logger.info(f"Orchestrator: Got perception plan for {minion_agent.name}: Action {plan.get('action')}")
                            # Yield API key log if present in plan's LlmResponse data
                            if event.data and event.data.get("apiKeyLog"):
                                key_log = event.data.get("apiKeyLog")
                                log_content = f"{minion_agent.name} used key '{key_log.get('key_name', 'N/A')}' ({key_log.get('key_method', 'N/A')}) for Perception (Auto)."
                                yield Event(author="System", data={"text_content": log_content, "isApiKeyLog": True, "channelId": channel_id})

                        # Clean up run_mode for this minion
                        run_mode_cleanup_delta = {f"{ctx.session.id}_{minion_agent.name}_run_mode": None}
                        refreshed_session.state.update(run_mode_cleanup_delta)
                        await self.session_service.append_event(refreshed_session, Event(author="orchestrator_system", actions={"state_delta": run_mode_cleanup_delta}))
                        break
            except Exception as e:
                logger.error(f"Orchestrator: Error during PERCEPTION for {minion_agent.name} in auto-chat: {e}", exc_info=True)
                yield Event(author="System", data={"text_content": f"Error in {minion_agent.name}'s perception (auto-chat): {str(e)}", "isError": True, "channelId": channel_id})


        # 2. Select next speaker
        next_speaker_agent: Optional[MinionAdkAgent] = None
        next_speaker_plan: Optional[Dict[str, Any]] = None

        eligible_speakers = []
        for name, plan in perception_plans.items():
            if plan.get("action") == "SPEAK":
                eligible_speakers.append({"name": name, "plan": plan, "predictedResponseTime": plan.get("predictedResponseTime", float('inf'))})

        if eligible_speakers:
            eligible_speakers.sort(key=lambda x: x["predictedResponseTime"])
            selected_speaker_info = eligible_speakers[0]
            next_speaker_agent = next((m for m in active_minions_for_turn if m.name == selected_speaker_info["name"]), None)
            next_speaker_plan = selected_speaker_info["plan"]
            logger.info(f"Orchestrator: Next speaker selected: {next_speaker_agent.name if next_speaker_agent else 'None'}")
        else:
            logger.info("Orchestrator: No minions chose to speak this turn.")
            yield Event(author="System", data={"text_content": "Auto-chat: All minions chose to remain silent this turn.", "isSystemMessage": True, "channelId": channel_id})
            # Clean up all perception plans from state
            final_cleanup_delta = {}
            for name in perception_plans.keys():
                final_cleanup_delta[f"{ctx.session.id}_{name}_perception_plan"] = None
            if final_cleanup_delta:
                current_session_for_cleanup = await self.session_service.get_session(app_name=APP_NAME, user_id=ctx.session.user_id, session_id=ctx.session.id)
                current_session_for_cleanup.state.update(final_cleanup_delta)
                await self.session_service.append_event(current_session_for_cleanup, Event(author="orchestrator_system", actions={"state_delta": final_cleanup_delta}))
            return

        # 3. Execute speak pass for the selected minion
        if next_speaker_agent and next_speaker_plan:
            logger.info(f"Orchestrator: Running SPEAK pass for {next_speaker_agent.name} in auto-chat.")

            # Set state for this minion's speak run
            speak_state_update = {
                f"{ctx.session.id}_{next_speaker_agent.name}_run_mode": "speak_with_plan",
                f"{ctx.session.id}_{next_speaker_agent.name}_active_perception_plan": next_speaker_plan, # Pass the chosen plan
                f"{ctx.session.id}_current_channel_type": channel_config.get("type", "minion_minion_auto"),
                f"{ctx.session.id}_last_message_sender_name": last_message_sender_name
            }
            # Refresh session before update
            current_session_for_speak_setup = await self.session_service.get_session(app_name=APP_NAME, user_id=ctx.session.user_id, session_id=ctx.session.id)
            current_session_for_speak_setup.state.update(speak_state_update)
            await self.session_service.append_event(current_session_for_speak_setup, Event(author="orchestrator_system", actions={"state_delta": speak_state_update}))

            # Yield placeholder for typing indicator
            placeholder_msg_id = f"ai-auto-{next_speaker_agent.minion_id_internal}-{datetime.now(timezone.utc).timestamp()}"
            yield Event(
                author=next_speaker_agent.name,
                data={
                    "id": placeholder_msg_id, "channelId": channel_id, "senderType": "AI",
                    "senderName": next_speaker_agent.name, "content": "", "isProcessing": True,
                    "internalDiary": next_speaker_plan, "timestamp": datetime.now(timezone.utc).timestamp()
                },
                partial=True # Indicate this is not the final form of the message
            )

            speak_runner = Runner(app_name=APP_NAME, agent=next_speaker_agent, session_service=self.session_service)
            try:
                async for event in speak_runner.run_async(user_id=ctx.session.user_id, session_id=ctx.session.id, new_message=base_user_message_for_adk):
                    # Relay events from the speaking minion (chunks and final)
                    # Ensure event.data is serializable if it's directly yielded
                    event_data_dict = {
                        "id": placeholder_msg_id, # Use same ID for chunks
                        "channelId": channel_id,
                        "senderType": "AI",
                        "senderName": event.author,
                        "content": event.content.parts[0].text if event.content and event.content.parts else "",
                        "isProcessing": not event.is_final_response(),
                        "timestamp": datetime.now(timezone.utc).timestamp()
                    }
                    if event.data: # Merge MinionAdkAgent's event.data
                        if event.data.get("internalDiary"): event_data_dict["internalDiary"] = event.data.get("internalDiary")
                        if event.data.get("isError"): event_data_dict["isError"] = event.data.get("isError")
                        # Stream API key log for response if present
                        if event.data.get("responseApiKeyLog"):
                            key_log_resp = event.data.get("responseApiKeyLog")
                            log_content_resp = f"{event.author} used key '{key_log_resp.get('key_name', 'N/A')}' ({key_log_resp.get('key_method', 'N/A')}) for Response (Auto)."
                            yield Event(author="System", data={"text_content": log_content_resp, "isApiKeyLog": True, "channelId": channel_id})
                        elif event.data.get("apiKeyLog"): # Fallback if only general apiKeyLog is there
                            key_log_resp = event.data.get("apiKeyLog")
                            log_content_resp = f"{event.author} used key '{key_log_resp.get('key_name', 'N/A')}' ({key_log_resp.get('key_method', 'N/A')}) for Response (Auto)."
                            yield Event(author="System", data={"text_content": log_content_resp, "isApiKeyLog": True, "channelId": channel_id})


                    yield Event(author=event.author, data=event_data_dict, partial=not event.is_final_response())

                    if event.is_final_response():
                        logger.info(f"Orchestrator: {next_speaker_agent.name} finished speaking in auto-chat.")
                        # Update orchestrator's knowledge of last speaker
                        ctx.state["auto_chat_last_speaker"] = next_speaker_agent.name
                        # This change to ctx.state won't be auto-persisted by this agent,
                        # main_backend should handle persisting this if needed across orchestrator calls.
                        break
            except Exception as e:
                logger.error(f"Orchestrator: Error during SPEAK pass for {next_speaker_agent.name} in auto-chat: {e}", exc_info=True)
                yield Event(author="System", data={"text_content": f"Error in {next_speaker_agent.name}'s response (auto-chat): {str(e)}", "isError": True, "channelId": channel_id})

            # Clean up state for the speaker
            speaker_cleanup_delta = {
                f"{ctx.session.id}_{next_speaker_agent.name}_run_mode": None,
                f"{ctx.session.id}_{next_speaker_agent.name}_active_perception_plan": None,
                f"{ctx.session.id}_{next_speaker_agent.name}_perception_plan": None, # General perception plan
                f"{ctx.session.id}_{next_speaker_agent.name}_api_key_log_perception": None,
                f"{ctx.session.id}_{next_speaker_agent.name}_api_key_log_response": None
            }
            current_session_for_speaker_cleanup = await self.session_service.get_session(app_name=APP_NAME, user_id=ctx.session.user_id, session_id=ctx.session.id)
            current_session_for_speaker_cleanup.state.update(speaker_cleanup_delta)
            await self.session_service.append_event(current_session_for_speaker_cleanup, Event(author="orchestrator_system", actions={"state_delta": speaker_cleanup_delta}))

        # 4. Implement delay
        delay = 5 # default
        if channel_config.get("autoModeDelayType") == 'fixed':
            delay = channel_config.get("autoModeFixedDelay", 5)
        elif channel_config.get("autoModeDelayType") == 'random':
            min_delay = channel_config.get("autoModeRandomDelay", {}).get("min", 3)
            max_delay = channel_config.get("autoModeRandomDelay", {}).get("max", 10)
            delay = asyncio.to_thread(lambda: random.uniform(min_delay, max_delay)) # random.uniform is not async
            delay = await delay


        logger.info(f"Orchestrator: Auto chat turn finished. Next turn in {delay:.2f} seconds.")
        # The orchestrator itself doesn't loop. The frontend/main_backend will call it again after delay.
        # Yield a final event to signify end of this orchestrator turn.
        yield Event(author=self.name, data={"turn_complete": True, "next_turn_delay_estimate": delay, "last_speaker": ctx.state.get("auto_chat_last_speaker")}, is_final_response=True)

# Need to import random for the random delay
import random
