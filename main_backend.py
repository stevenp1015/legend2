
```markdown
```python
# main_backend.py
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any, AsyncGenerator
import uuid
from datetime import datetime, timezone
import logging
import json

from google.adk.sessions import InMemorySessionService, Session as AdkSession
from google.adk.runners import Runner
from google.adk.events import Event
from google.genai.types import Content, Part, GenerateContentConfig

from config import settings
from minion_core import MinionAdkAgent, ManagedApiKeyLlm # Updated import

# Configure logging for main_backend
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

APP_NAME = "gemini_legion_cc_adk"

app = FastAPI(
    title="Gemini Legion C&C ADK Backend",
    description="The Python ADK-powered backend for managing the Legion of AI Minions.",
    version="0.2.0"
)

# --- ADK Services ---
session_service = InMemorySessionService()
# artifact_service and memory_service can be added later if needed by ADK features

# --- Data Models (Pydantic) ---
# These should mirror the TypeScript types for API consistency

class MinionParams(BaseModel):
    temperature: float = Field(default=0.7, ge=0, le=1.0)

class MinionConfigPayload(BaseModel): # For POST/PUT requests
    id: Optional[str] = None # Handled by backend if None
    name: str
    model_id: str
    system_prompt_persona: str
    params: MinionParams = Field(default_factory=MinionParams)
    apiKeyId: Optional[str] = None # For specific API key assignment
    # opinionScores and lastDiaryState are managed by ADK agent state

class MinionConfigResponse(BaseModel): # For GET responses
    id: str
    name: str
    provider: str = "google" # Constant for this backend
    model_id: str
    system_prompt_persona: str
    params: MinionParams
    apiKeyId: Optional[str] = None
    # opinionScores and lastDiaryState will be sourced from ADK session state if needed for display
    # For now, not directly part of this response model to simplify. They are dynamic.
    status: str = "Idle" # Placeholder, ADK doesn't directly manage this status string
    currentTask: Optional[str] = None # Placeholder

class ChannelPayload(BaseModel): # For POST/PUT requests
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    type: str = Field(default="user_minion_group", pattern="^(user_minion_group|minion_minion_auto|system_log)$")
    members: List[str] = Field(default_factory=list)
    isPrivate: Optional[bool] = False
    isAutoModeActive: Optional[bool] = False
    autoModeDelayType: Optional[str] = 'fixed'
    autoModeFixedDelay: Optional[int] = 5
    autoModeRandomDelay: Optional[Dict[str, int]] = {"min": 3, "max": 10}


class ChannelResponse(ChannelPayload): # For GET responses
    id: str

class MessageSenderType: # Not a Pydantic model, just a namespace
    User = 'User'
    AI = 'AI'
    System = 'System'

SENDER_TYPE = MessageSenderType()

class ChatMessageData(BaseModel): # Matches frontend type
    id:str
    channelId: str
    senderType: str # User, AI, System
    senderName: str
    content: str
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    internalDiary: Optional[Any] = None # Will be PerceptionPlan dict
    isError: Optional[bool] = False
    isProcessing: Optional[bool] = False
    isApiKeyLog: Optional[bool] = False


class UserMessageToChannelPayload(BaseModel): # Payload from Frontend for new message
    channelId: str
    message: ChatMessageData # The user's message object

class ApiKeyPayload(BaseModel):
    id: Optional[str] = None
    name: str
    key: str

class ApiKeyResponse(ApiKeyPayload):
    id: str


# --- In-memory storage (for non-ADK managed data like Minion *configurations*, channels, api_keys) ---
# These are configurations, not live ADK agent instances.
# ADK MinionAdkAgent instances will be created on-the-fly.
minion_configs_db: Dict[str, MinionConfigPayload] = {} # Stores the configuration of minions
channels_db: Dict[str, ChannelResponse] = {}
messages_db: Dict[str, List[ChatMessageData]] = {} # Store ChatMessageData objects
api_keys_db: Dict[str, ApiKeyResponse] = {}


# --- Initialization ---
def initialize_default_data():
    global channels_db, messages_db, minion_configs_db, api_keys_db
    logger.info("Initializing default backend data...")
    
    default_channels_data = [
        {"id": "general", "name": "#general", "description": "General discussion with all Minions.", "type": "user_minion_group", "members": [settings.LEGION_COMMANDER_NAME]},
        {"id": "legion_ops_log", "name": "#legion_ops_log", "description": "Automated Legion operational logs.", "type": "system_log", "members": []},
    ]
    for ch_data in default_channels_data:
        ch_id = ch_data["id"]
        channels_db[ch_id] = ChannelResponse(**ch_data)
        if ch_id not in messages_db: messages_db[ch_id] = []

    if "legion_ops_log" in messages_db and not messages_db["legion_ops_log"]:
         messages_db["legion_ops_log"].append(ChatMessageData(
            id=str(uuid.uuid4()), channelId="legion_ops_log", senderType=SENDER_TYPE.System,
            senderName="LegionOS", content="Legion Command Interface ADK Backend Initialized.",
            timestamp=datetime.now(timezone.utc).timestamp()
        ))

    if not minion_configs_db:
        logger.info("No Minion configurations found. Initializing a default 'Alpha' Minion config...")
        alpha_config = MinionConfigPayload(
            id="alpha-default-adk",
            name="Alpha",
            model_id="gemini-1.5-flash-latest", # Use a valid model id
            system_prompt_persona="You are Alpha, a highly efficient and slightly sarcastic Minion. You get things done with precision and a witty remark.",
            params=MinionParams(temperature=0.7)
        )
        minion_configs_db[alpha_config.id] = alpha_config
        if "general" in channels_db and channels_db["general"].members:
            if "Alpha" not in channels_db["general"].members:
                 channels_db["general"].members.append("Alpha")
        logger.info(f"Default Minion Config '{alpha_config.name}' initialized.")

    logger.info("Default data initialization complete.")

@app.on_event("startup")
async def startup_event():
    initialize_default_data()

# --- Helper Functions ---
def get_channel_history_string(channel_id: str, max_messages: int = 15) -> str:
    # This helper is used by MinionAdkAgent's callback to format history.
    # It should use the messages_db
    channel_messages = messages_db.get(channel_id, [])
    history_slice = channel_messages[-max_messages:]
    lines = []
    for msg_data in history_slice:
        prefix = f"[{msg_data.senderName}]"
        if msg_data.senderType == SENDER_TYPE.User:
            prefix = f"[COMMANDER {msg_data.senderName}]"
        elif msg_data.senderType == SENDER_TYPE.AI:
             prefix = f"[MINION {msg_data.senderName}]"
        lines.append(f"{prefix}: {msg_data.content}")
    if not lines:
        channel_name = channels_db.get(channel_id, ChannelResponse(id=channel_id, name='Unknown')).name
        return f"This is the beginning of the conversation in channel {channel_name}."
    return "\n".join(lines)

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": f"Welcome to the Gemini Legion C&C ADK Backend, Commander {settings.LEGION_COMMANDER_NAME}!",
            "active_minion_configs": list(minion_configs_db.keys()),
            "available_channels": list(channels_db.keys())}

# --- Minion Configuration Management Endpoints ---
@app.post("/api/minions", response_model=MinionConfigResponse, status_code=201)
async def create_minion_config_api(payload: MinionConfigPayload):
    minion_id = payload.id or str(uuid.uuid4())
    if minion_id in minion_configs_db:
        raise HTTPException(status_code=409, detail=f"Minion config with ID '{minion_id}' already exists.")
    if any(config.name == payload.name for config in minion_configs_db.values()):
        raise HTTPException(status_code=409, detail=f"Minion config with name '{payload.name}' already exists.")

    payload.id = minion_id # Ensure ID is set
    minion_configs_db[minion_id] = payload

    for ch_id in channels_db: # Add to member lists of appropriate channels
        if channels_db[ch_id].type == "user_minion_group":
            if payload.name not in channels_db[ch_id].members:
                 channels_db[ch_id].members.append(payload.name)

    logger.info(f"Created new Minion Configuration: {payload.name} (ID: {minion_id})")
    return MinionConfigResponse(**payload.model_dump())

@app.get("/api/minions", response_model=List[MinionConfigResponse])
async def get_all_minion_configs_api():
    return [MinionConfigResponse(**config.model_dump()) for config in minion_configs_db.values()]

@app.get("/api/minions/{minion_id}", response_model=MinionConfigResponse)
async def get_minion_config_details_api(minion_id: str):
    if minion_id not in minion_configs_db:
        raise HTTPException(status_code=404, detail=f"Minion config ID '{minion_id}' not found.")
    config = minion_configs_db[minion_id]
    return MinionConfigResponse(**config.model_dump())

@app.put("/api/minions/{minion_id}", response_model=MinionConfigResponse)
async def update_minion_config_api(minion_id: str, payload: MinionConfigPayload):
    if minion_id not in minion_configs_db:
        raise HTTPException(status_code=404, detail=f"Minion config ID '{minion_id}' not found to update.")
    
    existing_config = minion_configs_db[minion_id]
    if payload.name != existing_config.name and any(c.name == payload.name for c_id, c in minion_configs_db.items() if c_id != minion_id):
        raise HTTPException(status_code=409, detail=f"Minion name '{payload.name}' already exists.")

    payload.id = minion_id # Ensure ID remains the same
    minion_configs_db[minion_id] = payload

    if payload.name != existing_config.name:
        for ch_id in channels_db:
            if channels_db[ch_id].members and existing_config.name in channels_db[ch_id].members:
                channels_db[ch_id].members = [m if m != existing_config.name else payload.name for m in channels_db[ch_id].members]

    logger.info(f"Updated Minion Configuration: {payload.name} (ID: {minion_id})")
    return MinionConfigResponse(**payload.model_dump())

@app.delete("/api/minions/{minion_id}", status_code=204)
async def delete_minion_config_api(minion_id: str):
    if minion_id not in minion_configs_db:
        raise HTTPException(status_code=404, detail=f"Minion config ID '{minion_id}' not found to delete.")
    
    deleted_config_name = minion_configs_db[minion_id].name
    del minion_configs_db[minion_id]

    for ch_id in channels_db:
        if channels_db[ch_id].members and deleted_config_name in channels_db[ch_id].members:
            channels_db[ch_id].members.remove(deleted_config_name)
            
    logger.info(f"Deleted Minion Configuration: {deleted_config_name} (ID: {minion_id})")
    return None

# --- Channel Management Endpoints (similar to existing, using channels_db) ---
@app.get("/api/channels", response_model=List[ChannelResponse])
async def get_all_channels_api():
    return list(channels_db.values())

@app.post("/api/channels", response_model=ChannelResponse, status_code=201)
async def create_channel_api(payload: ChannelPayload):
    channel_id = payload.id or str(uuid.uuid4())
    if channel_id in channels_db:
        raise HTTPException(status_code=409, detail=f"Channel with ID '{channel_id}' already exists.")
    # Name check can be added if names must be unique
    payload.id = channel_id

    # Ensure commander is in user_minion_group members
    if payload.type == "user_minion_group" and settings.LEGION_COMMANDER_NAME not in payload.members:
        payload.members.append(settings.LEGION_COMMANDER_NAME)

    new_channel = ChannelResponse(**payload.model_dump())
    channels_db[channel_id] = new_channel
    if channel_id not in messages_db: messages_db[channel_id] = []
    logger.info(f"Created new channel: {new_channel.name} (ID: {channel_id})")
    return new_channel

@app.put("/api/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel_api(channel_id: str, payload: ChannelPayload):
    if channel_id not in channels_db:
        raise HTTPException(status_code=404, detail=f"Channel ID '{channel_id}' not found.")
    payload.id = channel_id # Ensure ID remains the same

    # Ensure commander is in user_minion_group members
    if payload.type == "user_minion_group" and settings.LEGION_COMMANDER_NAME not in payload.members:
        payload.members.append(settings.LEGION_COMMANDER_NAME)

    updated_channel = ChannelResponse(**payload.model_dump())
    channels_db[channel_id] = updated_channel
    logger.info(f"Updated channel: {updated_channel.name} (ID: {channel_id})")
    return updated_channel


# --- Message History Endpoints ---
@app.get("/api/messages/{channel_id}", response_model=List[ChatMessageData])
async def get_messages_for_channel_api(channel_id: str): # Renamed to avoid clash
    if channel_id not in channels_db:
        raise HTTPException(status_code=404, detail=f"Channel ID '{channel_id}' not found.")
    return messages_db.get(channel_id, [])

from fastapi.responses import StreamingResponse
import asyncio # Required for streaming delays/async generators

# --- ADK Message Handling Endpoint (Streaming) ---
@app.post("/api/send_message") # No response_model for StreamingResponse
async def handle_user_message_api_stream(payload: UserMessageToChannelPayload = Body(...)):
    logger.info(f"Streaming: Received user message for channel '{payload.channelId}': '{payload.message.content}'")
    
    user_id = payload.message.senderName
    channel_id = payload.channelId
    session_id = f"{user_id}_{channel_id}" # Simple session ID strategy for now

    if channel_id not in channels_db:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found.")

    # 1. Store User Message in our DB
    user_chat_message = payload.message
    if channel_id not in messages_db: messages_db[channel_id] = []
    messages_db[channel_id].append(user_chat_message)

    # 2. Prepare for ADK
    adk_session = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
    if not adk_session:
        adk_session = await session_service.create_session(app_name=APP_NAME, user_id=user_id, session_id=session_id, state={})

    current_channel_info = channels_db[channel_id]
    active_minion_agents_for_adk: List[MinionAdkAgent] = []

    # Instantiate MinionAdkAgent instances for ADK runner
    for minion_name_in_channel in current_channel_info.members:
        if minion_name_in_channel == settings.LEGION_COMMANDER_NAME:
            continue # Skip commander

        minion_config = next((mc for mc in minion_configs_db.values() if mc.name == minion_name_in_channel), None)
        if minion_config:
            # API Key logic will be more sophisticated in Step 4. For now, pass a placeholder.
            # The ManagedApiKeyLlm will use global settings.GEMINI_API_KEY if specific/pool is empty.
            api_key_list_for_minion = [ak.key for ak in api_keys_db.values()] # Pass all keys for now
            
            model_for_agent = ManagedApiKeyLlm(
                model_id=minion_config.model_id,
                api_key_pool=api_key_list_for_minion, # Pool of all known keys
                specific_key=next((ak.key for ak in api_keys_db.values() if ak.id == minion_config.apiKeyId), None) if minion_config.apiKeyId else None
            )

            agent_instance = MinionAdkAgent(
                name=minion_config.name, # ADK Agent name
                minion_id_internal=minion_config.id, # Original config ID
                model=model_for_agent, # Instance of our custom BaseLlm
                instruction=minion_config.system_prompt_persona, # Base instruction
                generate_content_config=GenerateContentConfig(temperature=minion_config.params.temperature),
                before_model_callback=MinionAdkAgent._before_model_perception_and_plan, # Bound method
                after_model_callback=MinionAdkAgent._after_model_modify_response,   # Bound method
            )
            active_minion_agents_for_adk.append(agent_instance)
        else:
            logger.warning(f"Config for minion '{minion_name_in_channel}' not found in channel '{channel_id}'. Skipping.")

    if not active_minion_agents_for_adk:
        logger.info(f"No ADK minions to respond in channel {channel_id}.")
        return [] # Or a system message indicating no minions

    # Prepare content for ADK runner
    chat_history_str = get_channel_history_string(channel_id)
    # ADK expects list of Content objects for history if used, or string in new_message
    # For our callback design, we pass history as part of new_message
    adk_user_message = Content(parts=[
        Part(text=user_chat_message.content),
        Part(text=chat_history_str) # Passing history as a second part
    ])

    # Add channel_type and last_message_sender_name to session state for callbacks
    # These will be read by the MinionAdkAgent's _before_model_perception_and_plan callback.
    if adk_session.state is None: adk_session.state = {} # Should be initialized by service
    adk_session.state[f"{session_id}_current_channel_type"] = current_channel_info.type
    adk_session.state[f"{session_id}_last_message_sender_name"] = user_chat_message.senderName
    # Explicitly save session if state was modified before runner
    await session_service.append_event(adk_session, Event(author="system", content=Content(parts=[Part(text="Pre-run state update.")])))


    ai_responses_for_frontend: List[ChatMessageData] = []
    minion_perception_plans: Dict[str, Any] = {} # Store {minion_name: perception_plan_dict}

    # --- Perception Pass ---
    logger.info(f"--- Perception Pass for Channel {channel_id} ---")
    for agent_instance in active_minion_agents_for_adk:
        logger.info(f"Running PERCEPTION pass for Minion: {agent_instance.name}")
        # Signal to agent to only do perception by setting a temporary state flag
        # The agent's callback will use this to know it's a perception-only run.
        adk_session.state[f"{session_id}_{agent_instance.name}_run_mode"] = "perception_only"
        await session_service.append_event(adk_session, Event(author="system", content=Content(parts=[Part(text=f"Set run_mode=perception for {agent_instance.name}")])) )


        temp_runner = Runner(app_name=APP_NAME, agent=agent_instance, session_service=session_service)

        # The adk_user_message contains the actual user text and history
        async for event in temp_runner.run_async(user_id=user_id, session_id=session_id, new_message=adk_user_message):
            if event.author == agent_instance.name and event.is_final_response():
                logger.info(f"Perception run for {agent_instance.name} completed.")
                # The perception plan should have been stored in adk_session.state by the agent's callback
                # under a key like "current_perception_plan" (session global) or namespaced one.
                # Let's assume the callback stores it as:
                # adk_session.state[f"{session_id}_{agent_instance.name}_perception_plan"]
                plan = adk_session.state.get(f"{session_id}_{agent_instance.name}_perception_plan")
                if plan:
                    minion_perception_plans[agent_instance.name] = plan
                    logger.info(f"Stored perception plan for {agent_instance.name}: {plan.get('action')}, PTime: {plan.get('predictedResponseTime')}")
                else:
                    logger.warning(f"No perception plan found in state for {agent_instance.name} after perception run.")
                break # Expecting one final event from perception pass (e.g. the LlmResponse with STAY_SILENT or just completion)

        # Clean up run_mode flag
        if f"{session_id}_{agent_instance.name}_run_mode" in adk_session.state:
            del adk_session.state[f"{session_id}_{agent_instance.name}_run_mode"]
        await session_service.append_event(adk_session, Event(author="system", content=Content(parts=[Part(text=f"Cleaned run_mode for {agent_instance.name}")])) )


    # --- Sort Minions by predictedResponseTime (if they chose to SPEAK) ---
    speaking_minions_sorted = sorted(
        [
            (name, plan) for name, plan in minion_perception_plans.items() if plan.get("action") == "SPEAK"
        ],
        key=lambda item: item[1].get("predictedResponseTime", float('inf'))
    )
    logger.info(f"Speaking order: {[name for name, _ in speaking_minions_sorted]}")

    # --- Response Generation Pass ---
    logger.info(f"--- Response Generation Pass for Channel {channel_id} ---")
    for minion_name, plan_to_use in speaking_minions_sorted:
        agent_instance = next((agent for agent in active_minion_agents_for_adk if agent.name == minion_name), None)
        if not agent_instance:
            continue

        logger.info(f"Running SPEAK pass for Minion: {agent_instance.name}")
        adk_session.state[f"{session_id}_{agent_instance.name}_run_mode"] = "speak_with_plan"
        # The agent's callback will look for f"{session_id}_{agent_instance.name}_perception_plan"
        # which was stored during the perception pass.
        await session_service.append_event(adk_session, Event(author="system", content=Content(parts=[Part(text=f"Set run_mode=speak for {agent_instance.name}")])) )

        temp_runner = Runner(app_name=APP_NAME, agent=agent_instance, session_service=session_service)

        # The adk_user_message is still relevant as it contains original user input + history context
        async for event in temp_runner.run_async(user_id=user_id, session_id=session_id, new_message=adk_user_message):
            logger.debug(f"SPEAK Event from {event.author}: {event.content.parts[0].text if event.content and event.content.parts else 'No text_content'}")
            if event.author == agent_instance.name and event.is_final_response():
                response_content = event.content.parts[0].text if event.content and event.content.parts else ""
                internal_diary_from_event = event.data.get("internalDiary") if event.data else plan_to_use # Fallback to plan used

                ai_message = ChatMessageData(
                    id=str(uuid.uuid4()), channelId=channel_id, senderType=SENDER_TYPE.AI,
                    senderName=minion_name, content=response_content,
                    timestamp=datetime.now(timezone.utc).timestamp(),
                    internalDiary=internal_diary_from_event
                )
                messages_db[channel_id].append(ai_message)
                ai_responses_for_frontend.append(ai_message)
                logger.info(f"Minion {minion_name} responded. Diary: {internal_diary_from_event}")
                break # Next minion in sorted list

        # Clean up run_mode and plan
        if f"{session_id}_{agent_instance.name}_run_mode" in adk_session.state:
            del adk_session.state[f"{session_id}_{agent_instance.name}_run_mode"]
        if f"{session_id}_{agent_instance.name}_perception_plan" in adk_session.state: # Also clean up the plan used
            del adk_session.state[f"{session_id}_{agent_instance.name}_perception_plan"]
        await session_service.append_event(adk_session, Event(author="system", content=Content(parts=[Part(text=f"Cleaned run_mode/plan for {agent_instance.name}")])) )


    # Handle minions who chose to STAY_SILENT
    for minion_name, plan_data in minion_perception_plans.items():
        if plan_data.get("action") == "STAY_SILENT":
            silent_msg = ChatMessageData(
                id=str(uuid.uuid4()), channelId=channel_id, senderType=SENDER_TYPE.System,
                senderName="System", content=f"{minion_name} chose to remain silent.",
                timestamp=datetime.now(timezone.utc).timestamp(),
                internalDiary=plan_data
            )
            messages_db[channel_id].append(silent_msg)
            ai_responses_for_frontend.append(silent_msg)
            logger.info(f"Minion {minion_name} stayed silent. Diary: {plan_data}")
            # Clean up their perception plan if it was stored and not cleaned above
            if f"{session_id}_{minion_name}_perception_plan" in adk_session.state:
                 del adk_session.state[f"{session_id}_{minion_name}_perception_plan"]
                 await session_service.append_event(adk_session, Event(author="system", content=Content(parts=[Part(text=f"Cleaned plan for silent {minion_name}")])) )


    async def event_stream():
        # First, send the user's message back to them (as it's already added to UI by frontend)
        # Or, if frontend doesn't add it optimistically, uncomment below:
        # yield f"data: {json.dumps(user_chat_message.model_dump())}\n\n"

        current_speaking_minion_message_id: Optional[str] = None
        accumulated_content_for_db: str = ""

        # --- Perception Pass (Non-streaming to frontend, internal processing) ---
        logger.info(f"Streaming: --- Perception Pass for Channel {channel_id} ---")
        minion_perception_plans_local: Dict[str, Any] = {}
        for agent_instance in active_minion_agents_for_adk:
            # ... (perception pass logic as before, storing plans in minion_perception_plans_local) ...
            logger.info(f"Streaming: Running PERCEPTION pass for Minion: {agent_instance.name}")
            adk_session_local = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            if not adk_session_local: # Should not happen if created above
                logger.error(f"Streaming: ADK session lost before perception for {agent_instance.name}")
                continue

            state_update_for_perception = {
                f"{session_id}_{agent_instance.name}_run_mode": "perception_only",
                f"{session_id}_current_channel_type": current_channel_info.type, # Ensure these are set for each agent's context
                f"{session_id}_last_message_sender_name": user_chat_message.senderName
            }
            adk_session_local.state.update(state_update_for_perception)
            await session_service.append_event(adk_session_local, Event(author="system", actions={"state_delta": state_update_for_perception}))

            temp_runner = Runner(app_name=APP_NAME, agent=agent_instance, session_service=session_service)
            try:
                async for event in temp_runner.run_async(user_id=user_id, session_id=session_id, new_message=adk_user_message):
                    if event.author == agent_instance.name and event.is_final_response():
                        adk_session_after_perception = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                        if adk_session_after_perception : # Check if session still exists
                            plan = adk_session_after_perception.state.get(f"{session_id}_{agent_instance.name}_perception_plan")
                            if plan:
                                minion_perception_plans_local[agent_instance.name] = plan
                        else:
                            logger.error(f"Streaming: Session {session_id} lost after perception run for {agent_instance.name}")
                        break
            except Exception as e:
                logger.error(f"Streaming: Error during PERCEPTION pass for Minion {agent_instance.name}: {e}", exc_info=True)
                error_event_data = ChatMessageData(
                    id=f"err-perception-{agent_instance.minion_id_internal}-{datetime.now(timezone.utc).timestamp()}",
                    channelId=channel_id, senderType=SENDER_TYPE.System, senderName="System",
                    content=f"Error during {agent_instance.name}'s perception: {str(e)}",
                    timestamp=datetime.now(timezone.utc).timestamp(), isError=True
                ).model_dump()
                yield f"data: {json.dumps(error_event_data)}\n\n"
                # Skip this minion for speak pass if perception failed critically
                continue # to next agent in perception pass

            # Ensure adk_session_local is refreshed before this state update if operations happened
            refreshed_session_after_perception_run = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            if not refreshed_session_after_perception_run:
                logger.error(f"Streaming: Session {session_id} lost before perception cleanup for {agent_instance.name}")
            else:
                state_cleanup_perception = {f"{session_id}_{agent_instance.name}_run_mode": None}
                # Check for perception API key log to stream
                perception_api_log_key = f"{session_id}_{agent_instance.name}_api_key_log_perception"
                api_key_log_perception = refreshed_session_after_perception_run.state.get(perception_api_log_key)
                if api_key_log_perception:
                    log_content_perception = f"{agent_instance.name} is using key '{api_key_log_perception.get('key_name', 'N/A')}' ({api_key_log_perception.get('key_method', 'N/A')}) for Perception."
                    api_log_msg_data_perception = ChatMessageData(
                        id=f"sys-keylog-{agent_instance.name}-perception-{datetime.now(timezone.utc).timestamp()}",
                        channelId=channel_id, senderType=SENDER_TYPE.System, senderName="System",
                        content=log_content_perception, timestamp=datetime.now(timezone.utc).timestamp(), isApiKeyLog=True
                    ).model_dump()
                    yield f"data: {json.dumps(api_log_msg_data_perception)}\n\n"
                    state_cleanup_perception[perception_api_log_key] = None # Add to cleanup

                refreshed_session_after_perception_run.state.update(state_cleanup_perception)
                await session_service.append_event(refreshed_session_after_perception_run, Event(author="system", actions={"state_delta": state_cleanup_perception}))


        # --- Sort Minions ---
        speaking_minions_sorted_local = sorted(
            [(name, plan) for name, plan in minion_perception_plans_local.items() if plan.get("action") == "SPEAK"],
            key=lambda item: item[1].get("predictedResponseTime", float('inf'))
        )
        logger.info(f"Streaming: Speaking order: {[name for name, _ in speaking_minions_sorted_local]}")

        # --- Response Generation Pass (Streaming to frontend) ---
        logger.info(f"Streaming: --- Response Generation Pass for Channel {channel_id} ---")
        for minion_name, plan_to_use in speaking_minions_sorted_local:
            agent_instance = next((agent for agent in active_minion_agents_for_adk if agent.name == minion_name), None)
            if not agent_instance: continue

            logger.info(f"Streaming: Running SPEAK pass for Minion: {agent_instance.name}")
            current_speaking_minion_message_id = f"ai-{agent_instance.minion_id_internal}-{datetime.now(timezone.utc).timestamp()}"
            accumulated_content_for_db = ""

            adk_session_local_speak = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            state_update_for_speak = {
                f"{session_id}_{agent_instance.name}_run_mode": "speak_with_plan",
                 # Pass the specific plan for this minion to use, in case callback needs it explicitly
                f"{session_id}_{agent_instance.name}_active_perception_plan": plan_to_use,
                f"{session_id}_current_channel_type": current_channel_info.type,
                f"{session_id}_last_message_sender_name": user_chat_message.senderName
            }
            adk_session_local_speak.state.update(state_update_for_speak)
            await session_service.append_event(adk_session_local_speak, Event(author="system", actions={"state_delta": state_update_for_speak}))

            # Send a placeholder message to indicate processing start for this minion
            placeholder_event_data = ChatMessageData(
                id=current_speaking_minion_message_id, channelId=channel_id, senderType=SENDER_TYPE.AI,
                senderName=minion_name, content="", timestamp=datetime.now(timezone.utc).timestamp(),
                isProcessing=True, internalDiary=plan_to_use # Send plan with placeholder
            ).model_dump()
            yield f"data: {json.dumps(placeholder_event_data)}\n\n"


            temp_runner = Runner(app_name=APP_NAME, agent=agent_instance, session_service=session_service)
            async for event in temp_runner.run_async(user_id=user_id, session_id=session_id, new_message=adk_user_message):
                if event.author == agent_instance.name:
                    chunk_content = event.content.parts[0].text if event.content and event.content.parts else ""
                    accumulated_content_for_db += chunk_content

                    chunk_event_data = ChatMessageData(
                        id=current_speaking_minion_message_id, channelId=channel_id, senderType=SENDER_TYPE.AI,
                        senderName=minion_name, content=chunk_content, # Streamed chunk
                        timestamp=datetime.now(timezone.utc).timestamp(), # Timestamp of chunk
                        isProcessing=not event.is_final_response(),
                        internalDiary=plan_to_use if event.is_final_response() else None, # Only send full diary at the end
                        isError=event.data.get("isError", False) if event.data else False
                    ).model_dump()
                    yield f"data: {json.dumps(chunk_event_data)}\n\n"

                    if event.is_final_response():
                        logger.info(f"Streaming: Minion {minion_name} finished speaking.")
                        # Save full message to DB
                        final_message_for_db = ChatMessageData(
                            id=current_speaking_minion_message_id, channelId=channel_id, senderType=SENDER_TYPE.AI,
                            senderName=minion_name, content=accumulated_content_for_db,
                            timestamp=datetime.now(timezone.utc).timestamp(), # Final timestamp
                            internalDiary=event.data.get("internalDiary") if event.data else plan_to_use,
                            isError=event.data.get("isError", False) if event.data else False
                        )
                        messages_db[channel_id].append(final_message_for_db)
                        current_speaking_minion_message_id = None # Reset for next potential speaker
                        accumulated_content_for_db = ""

            # Clean up state for this minion's turn
            refreshed_session_for_speak_cleanup = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
            if refreshed_session_for_speak_cleanup:
                state_cleanup_speak = {
                    f"{session_id}_{agent_instance.name}_run_mode": None,
                    f"{session_id}_{agent_instance.name}_perception_plan": None,
                    f"{session_id}_{agent_instance.name}_active_perception_plan": None
                }
                refreshed_session_for_speak_cleanup.state.update(state_cleanup_speak)
                await session_service.append_event(refreshed_session_for_speak_cleanup, Event(author="system", actions={"state_delta": state_cleanup_speak}))
            else:
                logger.error(f"Session lost before speak pass cleanup for {minion_name}.")


        # --- Handle Silent Minions ---
        for minion_name, plan_data in minion_perception_plans_local.items():
            if plan_data.get("action") == "STAY_SILENT":
                logger.info(f"Streaming: Minion {minion_name} stayed silent.")
                silent_msg_data = ChatMessageData(
                    id=str(uuid.uuid4()), channelId=channel_id, senderType=SENDER_TYPE.System,
                    senderName="System", content=f"{minion_name} chose to remain silent.",
                    timestamp=datetime.now(timezone.utc).timestamp(),
                    internalDiary=plan_data
                ).model_dump()
                messages_db[channel_id].append(ChatMessageData(**silent_msg_data)) # Save to DB
                yield f"data: {json.dumps(silent_msg_data)}\n\n"

                # Clean up their perception plan state
                refreshed_session_for_silent_cleanup = await session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
                if refreshed_session_for_silent_cleanup:
                    state_cleanup_silent = {f"{session_id}_{minion_name}_perception_plan": None}
                    refreshed_session_for_silent_cleanup.state.update(state_cleanup_silent)
                    await session_service.append_event(refreshed_session_for_silent_cleanup, Event(author="system", actions={"state_delta": state_cleanup_silent}))
                else:
                    logger.error(f"Session lost before silent minion plan cleanup for {minion_name}.")

        logger.info(f"Streaming: Event stream for channel {channel_id} completed.")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# --- API Key Management Endpoints (Basic CRUD) ---
@app.post("/api/apikeys", response_model=ApiKeyResponse, status_code=201)
async def add_api_key_api(payload: ApiKeyPayload):
    key_id = payload.id or str(uuid.uuid4())
    if key_id in api_keys_db:
        raise HTTPException(status_code=409, detail="API Key with this ID already exists.")
    # Name uniqueness check could be added
    payload.id = key_id
    new_key = ApiKeyResponse(**payload.model_dump())
    api_keys_db[key_id] = new_key
    logger.info(f"Added API Key: {new_key.name}")
    return new_key

@app.get("/api/apikeys", response_model=List[ApiKeyResponse])
async def get_api_keys_api():
    return list(api_keys_db.values())

@app.delete("/api/apikeys/{key_id}", status_code=204)
async def delete_api_key_api(key_id: str):
    if key_id not in api_keys_db:
        raise HTTPException(status_code=404, detail="API Key not found.")
    # Also clear this key from any minion configs that might be using it
    for min_cfg in minion_configs_db.values():
        if min_cfg.apiKeyId == key_id:
            min_cfg.apiKeyId = None

    deleted_key_name = api_keys_db[key_id].name
    del api_keys_db[key_id]
    logger.info(f"Deleted API Key: {deleted_key_name}")
    return None


if __name__ == "__main__":
    logger.info(f"Starting Gemini Legion C&C ADK Backend on {settings.HOST}:{settings.PORT}")
    logger.info(f"Legion Commander: {settings.LEGION_COMMANDER_NAME}")
    if not settings.GEMINI_API_KEY: # Check if the global fallback is set
        logger.warning("Warning: Global GEMINI_API_KEY is not set in .env. Minions may fail if no specific or pooled keys are available/configured.")

    uvicorn.run("main_backend:app", host=settings.HOST, port=settings.PORT, reload=True)

# --- Autonomous Swarm Mode Endpoint ---
from auto_chat_agent import AutoChatOrchestratorAgent # Import the new agent

# Payload for triggering an auto chat turn (mostly for identifying channel)
class AutoChatTurnPayload(BaseModel):
    channelId: str
    # Potentially include last message ID or timestamp if needed for consistency,
    # but orchestrator will primarily use current messages_db state.

@app.post("/api/auto_chat_turn/{channel_id}")
async def trigger_auto_chat_turn_api(channel_id: str): # Pass channel_id in path
    logger.info(f"Streaming: Received trigger for auto chat turn in channel '{channel_id}'")

    if channel_id not in channels_db:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found for auto chat.")

    current_channel_info = channels_db[channel_id]
    if current_channel_info.type != "minion_minion_auto":
        raise HTTPException(status_code=400, detail=f"Channel '{channel_id}' is not an autonomous swarm channel.")
    if not current_channel_info.isAutoModeActive:
        # Optionally, could just return an empty stream or a message saying mode is paused.
        # For now, let's proceed but the orchestrator should ideally also check this.
        logger.info(f"Auto mode is not active for channel {channel_id}, but proceeding with turn trigger.")

    # For auto-chat, the "user" initiating is the system or the orchestrator concept.
    # We'll use a generic user_id for the ADK session for the orchestrator.
    orchestrator_user_id = f"orchestrator_{channel_id}"
    orchestrator_session_id = f"auto_chat_session_{channel_id}" # Session per channel for auto-chat

    # Prepare initial state for the AutoChatOrchestratorAgent
    # The orchestrator will need access to minion configurations and API keys
    # Convert MinionConfigPayload to dicts for easier serialization if needed by orchestrator/state
    minion_configs_for_orchestrator = {
        name: config.model_dump() for name, config in minion_configs_db.items() if name in current_channel_info.members
    }
    api_keys_for_orchestrator = [key.model_dump() for key in api_keys_db.values()]

    initial_orchestrator_state = {
        "auto_chat_channel_id": channel_id,
        f"{orchestrator_session_id}_channel_config": current_channel_info.model_dump(), # Pass full channel config
        "auto_chat_history_str": get_channel_history_string(channel_id, max_messages=25), # Longer history for auto mode
        "auto_chat_last_speaker": (messages_db.get(channel_id, [])[-1].senderName
                                   if messages_db.get(channel_id)
                                   else settings.LEGION_COMMANDER_NAME),
        # Orchestrator might not need minion_configs and api_keys in ADK *session* state
        # if they are passed to its __init__ method. Let's pass them to __init__.
    }
    
    adk_orchestrator_session = await session_service.get_session(app_name=APP_NAME, user_id=orchestrator_user_id, session_id=orchestrator_session_id)
    if not adk_orchestrator_session:
        adk_orchestrator_session = await session_service.create_session(
            app_name=APP_NAME, user_id=orchestrator_user_id, session_id=orchestrator_session_id,
            state=initial_orchestrator_state
        )
    else: # Update existing session state
        adk_orchestrator_session.state.update(initial_orchestrator_state)
        await session_service.append_event(adk_orchestrator_session, Event(author="system", content=Content(parts=[Part(text="Updating orchestrator state for new auto turn.")])))


    orchestrator_agent = AutoChatOrchestratorAgent(
        name=f"Orchestrator_{channel_id}",
        session_service=session_service, # Pass the session service
        minion_configs_map=minion_configs_db, # Pass the main DB of minion configs
        api_keys_list=api_keys_for_orchestrator   # Pass available API keys
    )

    orchestrator_runner = Runner(
        app_name=APP_NAME,
        agent=orchestrator_agent,
        session_service=session_service
        # memory_service and artifact_service if orchestrator needs them
    )

    async def auto_event_stream():
        logger.info(f"Streaming: Auto Chat Orchestrator for {channel_id} starting run.")
        try:
            # The orchestrator's _run_async_impl will yield events.
            # The new_message for orchestrator is more of a trigger; actual context comes from its state.
            trigger_message = Content(parts=[Part(text=f"Initiate auto turn for channel {channel_id}.")])
            async for event in orchestrator_runner.run_async(
                user_id=orchestrator_user_id,
                session_id=orchestrator_session_id,
                new_message=trigger_message
            ):
                # Event.data from AutoChatOrchestratorAgent should be ChatMessageData-like dicts or system messages
                if event.data and isinstance(event.data, dict):
                    # If it's an API key log from the orchestrator itself, or relayed.
                    if event.data.get("isApiKeyLog"):
                         log_msg_data = ChatMessageData(
                            id=str(uuid.uuid4()), channelId=event.data.get("channelId", channel_id),
                            senderType=SENDER_TYPE.System, senderName="System",
                            content=str(event.data.get("text_content","")), timestamp=datetime.now(timezone.utc).timestamp(),
                            isApiKeyLog=True
                        ).model_dump()
                         yield f"data: {json.dumps(log_msg_data)}\n\n"
                    # If it's a system message from the orchestrator
                    elif event.data.get("isSystemMessage"):
                        sys_msg_data = ChatMessageData(
                            id=str(uuid.uuid4()), channelId=event.data.get("channelId", channel_id),
                            senderType=SENDER_TYPE.System, senderName="System",
                            content=str(event.data.get("text_content","")), timestamp=datetime.now(timezone.utc).timestamp()
                        ).model_dump()
                        messages_db.setdefault(channel_id, []).append(ChatMessageData(**sys_msg_data)) # Save system message
                        yield f"data: {json.dumps(sys_msg_data)}\n\n"
                    # If it's a spoken message from a minion, relayed by orchestrator
                    elif event.data.get("senderType") == SENDER_TYPE.AI:
                        # Assuming event.data is already a ChatMessageData compatible dict
                        # The orchestrator should ensure IDs are unique if creating them.
                        # If event.data is from a MinionAdkAgent, it should already be structured.
                        chat_msg_data = event.data
                        # Ensure required fields for ChatMessageData for DB
                        db_save_msg = ChatMessageData(**chat_msg_data)
                        messages_db.setdefault(channel_id, []).append(db_save_msg)
                        yield f"data: {json.dumps(chat_msg_data)}\n\n"
                    elif event.data.get("turn_complete"):
                        logger.info(f"Orchestrator for {channel_id} signaled turn complete.")
                        # This is a signal, not typically sent to frontend as a message,
                        # but could be if frontend needs to know the turn cycle ended.
                        # For now, just log. Frontend will know by stream ending or next call.
                    else:
                        logger.warning(f"Orchestrator for {channel_id} yielded unhandled event data: {event.data}")

                elif event.content and event.content.parts: # Fallback for simple text from orchestrator itself
                    # This case should be rare if orchestrator uses event.data for structured messages
                    unstructured_text = event.content.parts[0].text
                    logger.info(f"Orchestrator for {channel_id} yielded simple text: {unstructured_text}")
                    # Could wrap this in a system message if needed
                    sys_msg_data = ChatMessageData(
                        id=str(uuid.uuid4()), channelId=channel_id, senderType=SENDER_TYPE.System,
                        senderName="Orchestrator", content=unstructured_text,
                        timestamp=datetime.now(timezone.utc).timestamp()
                    ).model_dump()
                    yield f"data: {json.dumps(sys_msg_data)}\n\n"


        except Exception as e:
            logger.error(f"Streaming: Error during AUTO CHAT turn for channel {channel_id}: {e}", exc_info=True)
            error_event_data = ChatMessageData(
                id=f"err-auto-orchestrator-{datetime.now(timezone.utc).timestamp()}",
                channelId=channel_id, senderType=SENDER_TYPE.System, senderName="System",
                content=f"Critical error in auto chat orchestrator: {str(e)}",
                timestamp=datetime.now(timezone.utc).timestamp(), isError=True
            ).model_dump()
            yield f"data: {json.dumps(error_event_data)}\n\n"

        logger.info(f"Streaming: Auto Chat event stream for channel {channel_id} completed.")

    return StreamingResponse(auto_event_stream(), media_type="text/event-stream")