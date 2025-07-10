### google.adk.events module

**google.adk.events module**

**pydantic model** google.adk.events.**Event**  
Bases: LlmResponse

Represents an event in a conversation between agents and users.

It is used to store the content of the conversation, as well as the actions taken by the agents like function calls, etc.

**invocation\_id**  
The invocation ID of the event.

**author**  
“user” or the name of the agent, indicating who appended the event to the session.

**actions**  
The actions taken by the agent.

**long\_running\_tool\_ids**  
The ids of the long running function calls.

**branch**  
The branch of the event.

**id**  
The unique identifier of the event.

**timestamp**  
The timestamp of the event.

**is\_final\_response**  
Whether the event is the final response of the agent.

**get\_function\_calls**  
Returns the function calls in the event.

  
FIELDS:

* actions (google.adk.events.event\_actions.EventActions)  
* author (str)  
* branch (str | None)  
* id (str)  
* invocation\_id (str)  
* long\_running\_tool\_ids (set\[str\] | None)  
* timestamp (float)

**field actions: EventActions \[Optional\]**  
The actions taken by the agent.

**field author: str \[Required\]**  
‘user’ or the name of the agent, indicating who appended the event to the session.

**field branch: Optional\[str\] \= None**  
The branch of the event.

The format is like agent\_1.agent\_2.agent\_3, where agent\_1 is the parent of agent\_2, and agent\_2 is the parent of agent\_3.

Branch is used when multiple sub-agent shouldn’t see their peer agents’ conversation history.

**field id: str \= ''**  
The unique identifier of the event.

**field invocation\_id: str \= ''**  
The invocation ID of the event.

**field long\_running\_tool\_ids: Optional\[set\[str\]\] \= None**  
Set of ids of the long running function calls. Agent client will know from this field about which function call is long running. only valid for function call event

**field timestamp: float \[Optional\]**  
The timestamp of the event.

**static new\_id()**  
**get\_function\_calls()**  
Returns the function calls in the event.

RETURN TYPE:  
list\[FunctionCall\]

**get\_function\_responses()**  
Returns the function responses in the event.

RETURN TYPE:  
list\[FunctionResponse\]

**has\_trailing\_code\_execution\_result()**  
Returns whether the event has a trailing code execution result.

RETURN TYPE:  
bool

**is\_final\_response()**  
Returns whether the event is the final response of the agent.

RETURN TYPE:  
bool

**model\_post\_init(\_Event\_\_context)**  
Post initialization logic for the event.

**pydantic model** google.adk.events.**EventActions**  
Bases: BaseModel

Represents the actions attached to an event.

  
FIELDS:

* artifact\_delta (dict\[str, int\])  
* escalate (bool | None)  
* requested\_auth\_configs (dict\[str, google.adk.auth.auth\_tool.AuthConfig\])  
* skip\_summarization (bool | None)  
* state\_delta (dict\[str, object\])  
* transfer\_to\_agent (str | None)

**field artifact\_delta: dict\[str, int\] \[Optional\]**  
Indicates that the event is updating an artifact. key is the filename, value is the version.

**field escalate: Optional\[bool\] \= None**  
The agent is escalating to a higher level agent.

**field requested\_auth\_configs: dict\[str, AuthConfig\] \[Optional\]**  
Authentication configurations requested by tool responses.

This field will only be set by a tool response event indicating tool request auth credential. \- Keys: The function call id. Since one function response event could contain multiple function responses that correspond to multiple function calls. Each function call could request different auth configs. This id is used to identify the function call. \- Values: The requested auth config.

**field skip\_summarization: Optional\[bool\] \= None**  
If true, it won’t call model to summarize function response.

Only used for function\_response event.

**field state\_delta: dict\[str, object\] \[Optional\]**  
Indicates that the event is updating the state with the given delta.

**field transfer\_to\_agent: Optional\[str\] \= None**  
If set, the event transfers to the specified agent.

