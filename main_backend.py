
```markdown
```python
# main_backend.py
import uvicorn
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timezone
import logging

from config import settings
from minion_core import MinionAgent

# Configure logging for main_backend
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Gemini Legion C&C Backend",
    description="The Python ADK-powered backend for managing the Legion of AI Minions.",
    version="0.1.1" # Incremented version
)

# --- Data Models (Pydantic) ---
# These should mirror the TypeScript types for API consistency

class MinionParams(BaseModel):
    temperature: float = Field(default=0.7, ge=0, le=1.0) # Max 1.0 for Gemini

class MinionConfigPayload(BaseModel): # For POST/PUT requests
    id: Optional[str] = None
    name: str
    # provider: str = "google" # This is implicit by using this backend
    model_id: str
    system_prompt_persona: str # This is the 'persona_prompt' for MinionAgent
    params: MinionParams = Field(default_factory=MinionParams)
    # opinionScores are managed internally by MinionAgent instances
    status: Optional[str] = "Idle"
    currentTask: Optional[str] = None

class MinionConfigResponse(BaseModel): # For GET responses
    id: str
    name: str
    provider: str = "google" # Constant for this backend
    model_id: str
    system_prompt_persona: str
    params: MinionParams
    opinionScores: Dict[str, int] = {}
    status: str
    currentTask: Optional[str] = None

    @field_validator('id', mode='before')
    @classmethod
    def ensure_id_is_string(cls, value): # Ensure ID is always string, even if UUID obj
        return str(value)


class ChannelPayload(BaseModel): # For POST/PUT requests
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    type: str = Field(default="user_minion_group", pattern="^(user_minion_group|user_minion_dm|minion_minion_group|system_log)$")
    members: Optional[List[str]] = Field(default_factory=list) # List of Minion names or User name
    isPrivate: Optional[bool] = False

class ChannelResponse(ChannelPayload): # For GET responses
    id: str
    
    @field_validator('id', mode='before')
    @classmethod
    def ensure_id_is_string_ch(cls, value):
        return str(value)


class MessageSenderType(BaseModel): # Equivalent to enum MessageSender
    User: str = "User"
    AI: str = "AI"
    System: str = "System"

SENDER_TYPE = MessageSenderType()

class ChatMessageBase(BaseModel):
    channelId: str
    senderType: str # "User", "AI", "System"
    senderName: str
    content: str
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    internalDiary: Optional[str] = None
    isError: Optional[bool] = False
    replyToMessageId: Optional[str] = None

class ChatMessageResponse(ChatMessageBase): # For GET responses
    id: str

    @field_validator('id', mode='before')
    @classmethod
    def ensure_id_is_string_msg(cls, value):
        return str(value)


class UserMessageToChannel(BaseModel): # Payload from Frontend for new message
    channelId: str
    userInput: str # Renamed from 'content' to distinguish from ChatMessageData.content
    # current_messages_for_context: Optional[List[ChatMessageBase]] = None # Frontend might send this if context window is small

# --- In-memory storage (temporary - will be replaced by DB/ADK services) ---
# MinionAgent instances, not just configs
minion_agents: Dict[str, MinionAgent] = {}

# Channel data
channels_db: Dict[str, ChannelResponse] = {}

# Messages, keyed by channel_id
messages_db: Dict[str, List[ChatMessageResponse]] = {}


# --- Initialization ---
def initialize_default_data():
    global channels_db, messages_db, minion_agents

    logger.info("Initializing default backend data...")
    
    # Default Channels
    default_channels_data = [
        {"id": "general", "name": "#general", "description": "General discussion with all Minions.", "type": "user_minion_group", "members": [settings.LEGION_COMMANDER_NAME]},
        {"id": "random", "name": "#random_bullshit", "description": "Off-topic banter and delightful chaos.", "type": "user_minion_group", "members": [settings.LEGION_COMMANDER_NAME]},
        {"id": "legion_ops_log", "name": "#legion_ops_log", "description": "Automated Legion operational logs.", "type": "system_log", "members": []},
    ]
    for ch_data in default_channels_data:
        ch_id = ch_data["id"]
        channels_db[ch_id] = ChannelResponse(**ch_data) #type: ignore
        if ch_id not in messages_db:
            messages_db[ch_id] = []

    if "legion_ops_log" in messages_db and not messages_db["legion_ops_log"]:
         messages_db["legion_ops_log"].append(ChatMessageResponse(
            id=str(uuid.uuid4()), channelId="legion_ops_log", senderType=SENDER_TYPE.System,
            senderName="LegionOS", content="Legion Command Interface Backend Initialized.",
            timestamp=datetime.now(timezone.utc).timestamp()
        ))

    # Default Minion (for testing, if none exist)
    if not minion_agents:
        logger.info("No Minions found. Initializing a default 'Alpha' Minion...")
        alpha_config_payload = MinionConfigPayload(
            id="alpha-default", # Specify ID for predictability in testing
            name="Alpha",
            model_id="gemini-2.5-flash-preview-04-17",
            system_prompt_persona="You are Alpha, a highly efficient and slightly sarcastic Minion. You get things done with precision and a witty remark. You secretly enjoy puns.",
            params=MinionParams(temperature=0.7)
        )
        try:
            alpha_agent = MinionAgent(
                minion_id=alpha_config_payload.id, # type: ignore
                name=alpha_config_payload.name,
                model_id=alpha_config_payload.model_id,
                persona_prompt=alpha_config_payload.system_prompt_persona,
                temperature=alpha_config_payload.params.temperature
            )
            minion_agents[alpha_agent.minion_id] = alpha_agent
            
            # Add Alpha to general channel members
            if "general" in channels_db and channels_db["general"].members:
                if "Alpha" not in channels_db["general"].members: # type: ignore
                     channels_db["general"].members.append("Alpha") # type: ignore
            logger.info(f"Default Minion '{alpha_agent.name}' initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize default Minion Alpha: {e}")

    logger.info("Default data initialization complete.")
    logger.info(f"Channels loaded: {list(channels_db.keys())}")
    logger.info(f"Minions loaded: {list(minion_agents.keys())}")


@app.on_event("startup")
async def startup_event():
    initialize_default_data()

# --- Helper Functions ---
def get_channel_history_string(channel_id: str, max_messages: int = 20) -> str:
    channel_messages = messages_db.get(channel_id, [])
    history_slice = channel_messages[-max_messages:] # Get the most recent N messages
    lines = []
    for msg in history_slice:
        prefix = f"[{msg.senderName}]"
        if msg.senderType == SENDER_TYPE.User:
            prefix = f"[COMMANDER {msg.senderName}]"
        elif msg.senderType == SENDER_TYPE.AI:
             prefix = f"[MINION {msg.senderName}]"
        lines.append(f"{prefix}: {msg.content}")
    if not lines:
        return f"This is the beginning of the conversation in channel {channels_db.get(channel_id, ChannelResponse(id=channel_id, name='Unknown', description=None)).name}."
    return "\n".join(lines)

# --- API Endpoints ---

@app.get("/")
async def root():
    return {"message": f"Welcome to the Gemini Legion C&C Backend, Commander {settings.LEGION_COMMANDER_NAME}!",
            "active_minions": list(minion_agents.keys()),
            "available_channels": list(channels_db.keys())}

# --- Minion Management Endpoints ---
@app.post("/api/minions", response_model=MinionConfigResponse, status_code=201)
async def create_minion(payload: MinionConfigPayload):
    minion_id = payload.id or str(uuid.uuid4())
    if minion_id in minion_agents:
        raise HTTPException(status_code=409, detail=f"Minion with ID '{minion_id}' already exists.")
    if any(agent.name == payload.name for agent in minion_agents.values()):
        raise HTTPException(status_code=409, detail=f"Minion with name '{payload.name}' already exists.")

    try:
        new_agent = MinionAgent(
            minion_id=minion_id,
            name=payload.name,
            model_id=payload.model_id,
            persona_prompt=payload.system_prompt_persona,
            temperature=payload.params.temperature
        )
        minion_agents[minion_id] = new_agent
        
        # Add Minion to default user_minion_group channels members list
        for ch_id in channels_db:
            if channels_db[ch_id].type == "user_minion_group":
                if channels_db[ch_id].members is None: channels_db[ch_id].members = []
                if payload.name not in channels_db[ch_id].members: # type: ignore
                     channels_db[ch_id].members.append(payload.name) # type: ignore

        logger.info(f"Deployed new Minion: {payload.name} (ID: {minion_id})")
        return MinionConfigResponse(
            id=minion_id, name=new_agent.name, model_id=new_agent.model_id,
            system_prompt_persona=new_agent.persona_prompt, params=MinionParams(temperature=new_agent.temperature),
            opinionScores=new_agent.opinion_scores, status=payload.status or "Idle", currentTask=payload.currentTask
        )
    except Exception as e:
        logger.error(f"Failed to create Minion {payload.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create Minion: {str(e)}")


@app.get("/api/minions", response_model=List[MinionConfigResponse])
async def get_all_minions_api(): # Renamed to avoid conflict with outer scope variable
    response_list = []
    for agent_id, agent in minion_agents.items():
        response_list.append(MinionConfigResponse(
            id=agent_id, name=agent.name, model_id=agent.model_id,
            system_prompt_persona=agent.persona_prompt,
            params=MinionParams(temperature=agent.temperature),
            opinionScores=agent.opinion_scores,
            status="Idle", # Needs dynamic status
            currentTask=None # Needs dynamic status
        ))
    return response_list

@app.get("/api/minions/{minion_id}", response_model=MinionConfigResponse)
async def get_minion_details(minion_id: str):
    if minion_id not in minion_agents:
        raise HTTPException(status_code=404, detail=f"Minion ID '{minion_id}' not found.")
    agent = minion_agents[minion_id]
    return MinionConfigResponse(
        id=minion_id, name=agent.name, model_id=agent.model_id,
        system_prompt_persona=agent.persona_prompt,
        params=MinionParams(temperature=agent.temperature),
        opinionScores=agent.opinion_scores,
        status="Idle", currentTask=None # Dynamic status needed
    )

@app.put("/api/minions/{minion_id}", response_model=MinionConfigResponse)
async def update_minion_api(minion_id: str, payload: MinionConfigPayload):
    if minion_id not in minion_agents:
        raise HTTPException(status_code=404, detail=f"Minion ID '{minion_id}' not found to update.")
    
    # Check for name collision if name is being changed
    existing_agent = minion_agents[minion_id]
    if payload.name != existing_agent.name and any(agent.name == payload.name for agent_id, agent in minion_agents.items() if agent_id != minion_id):
        raise HTTPException(status_code=409, detail=f"Minion name '{payload.name}' already exists.")

    try:
        # Re-initialize or update agent. For simplicity, re-initialize.
        # A more sophisticated update would preserve state like opinion scores if not meant to be reset.
        updated_agent = MinionAgent(
            minion_id=minion_id, # Keep original ID
            name=payload.name,
            model_id=payload.model_id,
            persona_prompt=payload.system_prompt_persona,
            temperature=payload.params.temperature
        )
        updated_agent.opinion_scores = existing_agent.opinion_scores # Preserve opinion scores
        updated_agent.last_diary = existing_agent.last_diary # Preserve last diary
        minion_agents[minion_id] = updated_agent

        # Update name in channel member lists if changed
        if payload.name != existing_agent.name:
            for ch_id in channels_db:
                if channels_db[ch_id].members and existing_agent.name in channels_db[ch_id].members: # type: ignore
                    channels_db[ch_id].members = [m if m != existing_agent.name else payload.name for m in channels_db[ch_id].members] # type: ignore

        logger.info(f"Updated Minion: {payload.name} (ID: {minion_id})")
        return MinionConfigResponse(
            id=minion_id, name=updated_agent.name, model_id=updated_agent.model_id,
            system_prompt_persona=updated_agent.persona_prompt, params=MinionParams(temperature=updated_agent.temperature),
            opinionScores=updated_agent.opinion_scores, status=payload.status or "Idle", currentTask=payload.currentTask
        )
    except Exception as e:
        logger.error(f"Failed to update Minion {payload.name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update Minion: {str(e)}")

@app.delete("/api/minions/{minion_id}", status_code=204)
async def delete_minion_api(minion_id: str):
    if minion_id not in minion_agents:
        raise HTTPException(status_code=404, detail=f"Minion ID '{minion_id}' not found to delete.")
    
    deleted_agent_name = minion_agents[minion_id].name
    del minion_agents[minion_id]

    # Remove Minion from channel member lists
    for ch_id in channels_db:
        if channels_db[ch_id].members and deleted_agent_name in channels_db[ch_id].members: # type: ignore
            channels_db[ch_id].members.remove(deleted_agent_name) # type: ignore
            
    logger.info(f"Decommissioned Minion: {deleted_agent_name} (ID: {minion_id})")
    return None


# --- Channel Management Endpoints ---
@app.get("/api/channels", response_model=List[ChannelResponse])
async def get_all_channels_api():
    return list(channels_db.values())

@app.post("/api/channels", response_model=ChannelResponse, status_code=201)
async def create_channel_api(payload: ChannelPayload):
    channel_id = payload.id or str(uuid.uuid4())
    if channel_id in channels_db:
        raise HTTPException(status_code=409, detail=f"Channel with ID '{channel_id}' already exists.")
    if any(ch.name == payload.name for ch in channels_db.values()):
        raise HTTPException(status_code=409, detail=f"Channel with name '{payload.name}' already exists.")

    # Ensure Commander is always a member of user-facing channels
    members = set(payload.members or [])
    if payload.type in ["user_minion_group", "user_minion_dm"]:
        members.add(settings.LEGION_COMMANDER_NAME)

    new_channel = ChannelResponse(
        id=channel_id, name=payload.name, description=payload.description or "",
        type=payload.type, members=list(members), isPrivate=payload.isPrivate or False
    )
    channels_db[channel_id] = new_channel
    if channel_id not in messages_db:
        messages_db[channel_id] = []
    
    logger.info(f"Created new channel: {new_channel.name} (ID: {channel_id})")
    return new_channel

# --- Message History Endpoints ---
@app.get("/api/messages/{channel_id}", response_model=List[ChatMessageResponse])
async def get_messages_for_channel(channel_id: str):
    if channel_id not in channels_db:
        raise HTTPException(status_code=404, detail=f"Channel ID '{channel_id}' not found.")
    return messages_db.get(channel_id, [])


# --- Message Handling Endpoint ---
@app.post("/api/messages", response_model=List[ChatMessageResponse]) # Returns list of AI responses
async def send_message_to_channel_api(payload: UserMessageToChannel = Body(...)):
    logger.info(f"Received user message for channel '{payload.channelId}': '{payload.userInput}'")
    if payload.channelId not in channels_db:
        raise HTTPException(status_code=404, detail=f"Channel '{payload.channelId}' not found.")

    # 1. Store User Message
    user_msg_id = str(uuid.uuid4())
    user_timestamp = datetime.now(timezone.utc).timestamp()
    user_chat_message = ChatMessageResponse(
        id=user_msg_id, channelId=payload.channelId, senderType=SENDER_TYPE.User,
        senderName=settings.LEGION_COMMANDER_NAME, content=payload.userInput,
        timestamp=user_timestamp
    )
    if payload.channelId not in messages_db: messages_db[payload.channelId] = []
    messages_db[payload.channelId].append(user_chat_message)

    # 2. Determine relevant Minions & get channel history
    current_channel_info = channels_db[payload.channelId]
    responding_minion_agents: List[MinionAgent] = []
    
    if current_channel_info.members:
        for member_name in current_channel_info.members:
            # Find agent by name. This assumes Minion names are unique.
            found_agent = next((agent for agent in minion_agents.values() if agent.name == member_name), None)
            if found_agent:
                responding_minion_agents.append(found_agent)
    
    if not responding_minion_agents and current_channel_info.type != SENDER_TYPE.System+"_log": # Adjust check
         logger.warning(f"No Minions configured or found to respond in channel {payload.channelId}")

    channel_history_for_llm = get_channel_history_string(payload.channelId) 
    ai_responses_for_frontend: List[ChatMessageResponse] = []

    # 3. Trigger Minion responses
    for agent in responding_minion_agents:
        logger.info(f"Triggering Minion: {agent.name} (ID: {agent.minion_id}) for channel {payload.channelId}")
        
        spoken_response, full_llm_response = await agent.process_message(
            user_message_content_for_task=payload.userInput,
            channel_history_string=channel_history_for_llm,
            channel_name=current_channel_info.name,
            last_message_sender_name=user_chat_message.senderName # User is the sender of the triggering message
        )

        if spoken_response != "[SILENT]":
            ai_msg_id = str(uuid.uuid4())
            ai_timestamp = datetime.now(timezone.utc).timestamp()
            
            # The agent.last_diary is updated internally by process_message if a diary was extracted
            # from full_llm_response.
            extracted_diary_for_response = agent.last_diary # Use the latest diary stored in the agent
            
            ai_chat_message = ChatMessageResponse(
                id=ai_msg_id, channelId=payload.channelId, senderType=SENDER_TYPE.AI,
                senderName=agent.name, content=spoken_response, timestamp=ai_timestamp,
                internalDiary=extracted_diary_for_response
            )
            messages_db[payload.channelId].append(ai_chat_message)
            ai_responses_for_frontend.append(ai_chat_message)
        else:
            logger.info(f"Minion {agent.name} remained silent.")
            # Optionally, create a system message for the frontend about silence
            system_silent_msg = ChatMessageResponse(
                id=str(uuid.uuid4()), channelId=payload.channelId, senderType=SENDER_TYPE.System,
                senderName="LegionOS", content=f"Minion {agent.name} chose to remain silent.",
                timestamp=datetime.now(timezone.utc).timestamp()
            )
            # Decide if frontend wants these: The legionApiService mock handles this.
            # If frontend expects it, add to ai_responses_for_frontend. For now, just log.
            # ai_responses_for_frontend.append(system_silent_msg) # If desired for UI

    # This endpoint currently returns all AI responses generated in this turn.
    # Streaming responses would require a different approach (e.g., FastAPI StreamingResponse).
    return ai_responses_for_frontend

# Note: DELETE and PUT for messages are not implemented here as they are handled by App.tsx
# calling the legionApiService which directly manipulates its local storage mock.
# If these were true backend operations, endpoints would be needed.


if __name__ == "__main__":
    logger.info(f"Starting Gemini Legion C&C Backend on {settings.HOST}:{settings.PORT}")
    logger.info(f"Legion Commander: {settings.LEGION_COMMANDER_NAME}")
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        logger.critical("CRITICAL WARNING: GEMINI_API_KEY is not set or is the default placeholder. Minions will NOT function correctly.")
    
    uvicorn.run("main_backend:app", host=settings.HOST, port=settings.PORT, reload=True)