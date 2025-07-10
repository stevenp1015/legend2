### google.adk.memory module

**google.adk.memory module**

**class** google.adk.memory.**BaseMemoryService**  
Bases: ABC

Base class for memory services.

The service provides functionalities to ingest sessions into memory so that the memory can be used for user queries.

**abstractmethod async add\_session\_to\_memory(session)**  
Adds a session to the memory service.

A session may be added multiple times during its lifetime.

PARAMETERS:  
**session** – The session to add.

**abstractmethod async search\_memory(\*, app\_name, user\_id, query)**  
Searches for sessions that match the query.

RETURN TYPE:  
SearchMemoryResponse

PARAMETERS:

* **app\_name** – The name of the application.  
* **user\_id** – The id of the user.  
* **query** – The query to search for.

RETURNS:  
A SearchMemoryResponse containing the matching memories.

**class** google.adk.memory.**InMemoryMemoryService**  
Bases: [BaseMemoryService](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.memory.BaseMemoryService)

An in-memory memory service for prototyping purpose only.

Uses keyword matching instead of semantic search.

**async add\_session\_to\_memory(session)**  
Adds a session to the memory service.

A session may be added multiple times during its lifetime.

PARAMETERS:  
**session** – The session to add.

**async search\_memory(\*, app\_name, user\_id, query)**  
Prototyping purpose only.

RETURN TYPE:  
SearchMemoryResponse

**session\_events: dict\[str, list\[[Event](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.events.Event)\]\]**  
keys are app\_name/user\_id/session\_id

**class** google.adk.memory.**VertexAiRagMemoryService(rag\_corpus=None, similarity\_top\_k=None, vector\_distance\_threshold=10)**  
Bases: [BaseMemoryService](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.memory.BaseMemoryService)

A memory service that uses Vertex AI RAG for storage and retrieval.

Initializes a VertexAiRagMemoryService.

PARAMETERS:

* **rag\_corpus** – The name of the Vertex AI RAG corpus to use. Format: projects/{project}/locations/{location}/ragCorpora/{rag\_corpus\_id} or {rag\_corpus\_id}  
* **similarity\_top\_k** – The number of contexts to retrieve.  
* **vector\_distance\_threshold** – Only returns contexts with vector distance smaller than the threshold..

**async add\_session\_to\_memory(session)**  
Adds a session to the memory service.

A session may be added multiple times during its lifetime.

PARAMETERS:  
**session** – The session to add.

**async search\_memory(\*, app\_name, user\_id, query)**  
Searches for sessions that match the query using rag.retrieval\_query.

RETURN TYPE:  
SearchMemoryResponse

