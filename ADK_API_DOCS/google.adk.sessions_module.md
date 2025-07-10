### google.adk.sessions module

**google.adk.sessions module**

**class** google.adk.sessions.**BaseSessionService**  
Bases: ABC

Base class for session services.

The service provides a set of methods for managing sessions and events.

**append\_event(session, event)**  
Appends an event to a session object.

RETURN TYPE:  
[Event](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.events.Event)

**close\_session(\*, session)**  
Closes a session.

**abstractmethod create\_session(\*, app\_name, user\_id, state=None, session\_id=None)**  
Creates a new session.

RETURN TYPE:  
[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)

PARAMETERS:

* **app\_name** – the name of the app.  
* **user\_id** – the id of the user.  
* **state** – the initial state of the session.  
* **session\_id** – the client-provided id of the session. If not provided, a generated ID will be used.

RETURNS:  
The newly created session instance.

RETURN TYPE:  
session

**abstractmethod delete\_session(\*, app\_name, user\_id, session\_id)**  
Deletes a session.

RETURN TYPE:  
None

**abstractmethod get\_session(\*, app\_name, user\_id, session\_id, config=None)**  
Gets a session.

RETURN TYPE:  
Optional\[[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)\]

**abstractmethod list\_events(\*, app\_name, user\_id, session\_id)**  
Lists events in a session.

RETURN TYPE:  
ListEventsResponse

**abstractmethod list\_sessions(\*, app\_name, user\_id)**  
Lists all the sessions.

RETURN TYPE:  
ListSessionsResponse

**class** google.adk.sessions.**DatabaseSessionService(db\_url)**  
Bases: [BaseSessionService](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.BaseSessionService)

A session service that uses a database for storage.

PARAMETERS:  
**db\_url** – The database URL to connect to.

**append\_event(session, event)**  
Appends an event to a session object.

RETURN TYPE:  
[Event](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.events.Event)

**create\_session(\*, app\_name, user\_id, state=None, session\_id=None)**  
Creates a new session.

RETURN TYPE:  
[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)

PARAMETERS:

* **app\_name** – the name of the app.  
* **user\_id** – the id of the user.  
* **state** – the initial state of the session.  
* **session\_id** – the client-provided id of the session. If not provided, a generated ID will be used.

RETURNS:  
The newly created session instance.

RETURN TYPE:  
session

**delete\_session(app\_name, user\_id, session\_id)**  
Deletes a session.

RETURN TYPE:  
None

**get\_session(\*, app\_name, user\_id, session\_id, config=None)**  
Gets a session.

RETURN TYPE:  
Optional\[[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)\]

**list\_events(\*, app\_name, user\_id, session\_id)**  
Lists events in a session.

RETURN TYPE:  
ListEventsResponse

**list\_sessions(\*, app\_name, user\_id)**  
Lists all the sessions.

RETURN TYPE:  
ListSessionsResponse

**class** google.adk.sessions.**InMemorySessionService**  
Bases: [BaseSessionService](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.BaseSessionService)

An in-memory implementation of the session service.

**append\_event(session, event)**  
Appends an event to a session object.

RETURN TYPE:  
[Event](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.events.Event)

**create\_session(\*, app\_name, user\_id, state=None, session\_id=None)**  
Creates a new session.

RETURN TYPE:  
[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)

PARAMETERS:

* **app\_name** – the name of the app.  
* **user\_id** – the id of the user.  
* **state** – the initial state of the session.  
* **session\_id** – the client-provided id of the session. If not provided, a generated ID will be used.

RETURNS:  
The newly created session instance.

RETURN TYPE:  
session

**delete\_session(\*, app\_name, user\_id, session\_id)**  
Deletes a session.

RETURN TYPE:  
None

**get\_session(\*, app\_name, user\_id, session\_id, config=None)**  
Gets a session.

RETURN TYPE:  
[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)

**list\_events(\*, app\_name, user\_id, session\_id)**  
Lists events in a session.

RETURN TYPE:  
ListEventsResponse

**list\_sessions(\*, app\_name, user\_id)**  
Lists all the sessions.

RETURN TYPE:  
ListSessionsResponse

**pydantic model** google.adk.sessions.**Session**  
Bases: BaseModel

Represents a series of interactions between a user and agents.

**id**  
The unique identifier of the session.

**app\_name**  
The name of the app.

**user\_id**  
The id of the user.

**state**  
The state of the session.

**events**  
The events of the session, e.g. user input, model response, function call/response, etc.

**last\_update\_time**  
The last update time of the session.

  
FIELDS:

* app\_name (str)  
* events (list\[google.adk.events.event.Event\])  
* id (str)  
* last\_update\_time (float)  
* state (dict\[str, Any\])  
* user\_id (str)

**field app\_name: str \[Required\]**  
The name of the app.

**field events: list\[[Event](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.events.Event)\] \[Optional\]**  
The events of the session, e.g. user input, model response, function call/response, etc.

**field id: str \[Required\]**  
The unique identifier of the session.

**field last\_update\_time: float \= 0.0**  
The last update time of the session.

**field state: dict\[str, Any\] \[Optional\]**  
The state of the session.

**field user\_id: str \[Required\]**  
The id of the user.

**class** google.adk.sessions.**State(value, delta)**  
Bases: object

A state dict that maintain the current value and the pending-commit delta.

PARAMETERS:

* **value** – The current value of the state dict.  
* **delta** – The delta change to the current value that hasn’t been committed.

**APP\_PREFIX \= 'app:'**  
**TEMP\_PREFIX \= 'temp:'**  
**USER\_PREFIX \= 'user:'**  
**get(key, default=None)**  
Returns the value of the state dict for the given key.

RETURN TYPE:  
Any

**has\_delta()**  
Whether the state has pending delta.

RETURN TYPE:  
bool

**to\_dict()**  
Returns the state dict.

RETURN TYPE:  
dict\[str, Any\]

**update(delta)**  
Updates the state dict with the given delta.

**class** google.adk.sessions.**VertexAiSessionService(project=None, location=None)**  
Bases: [BaseSessionService](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.BaseSessionService)

Connects to the managed Vertex AI Session Service.

**append\_event(session, event)**  
Appends an event to a session object.

RETURN TYPE:  
[Event](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.events.Event)

**create\_session(\*, app\_name, user\_id, state=None, session\_id=None)**  
Creates a new session.

RETURN TYPE:  
[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)

PARAMETERS:

* **app\_name** – the name of the app.  
* **user\_id** – the id of the user.  
* **state** – the initial state of the session.  
* **session\_id** – the client-provided id of the session. If not provided, a generated ID will be used.

RETURNS:  
The newly created session instance.

RETURN TYPE:  
session

**delete\_session(\*, app\_name, user\_id, session\_id)**  
Deletes a session.

RETURN TYPE:  
None

**get\_session(\*, app\_name, user\_id, session\_id, config=None)**  
Gets a session.

RETURN TYPE:  
[Session](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.sessions.Session)

**list\_events(\*, app\_name, user\_id, session\_id)**  
Lists events in a session.

RETURN TYPE:  
ListEventsResponse

**list\_sessions(\*, app\_name, user\_id)**  
Lists all the sessions.

RETURN TYPE:  
ListSessionsResponse

