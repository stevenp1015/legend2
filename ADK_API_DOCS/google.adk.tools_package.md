### google.adk.tools package

**google.adk.tools package**

**class** google.adk.tools.**APIHubToolset(\*, apihub\_resource\_name, access\_token=None, service\_account\_json=None, name='', description='', lazy\_load\_spec=False, auth\_scheme=None, auth\_credential=None, apihub\_client=None)**  
Bases: object

APIHubTool generates tools from a given API Hub resource.

Examples:

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id42)\` apihub\_toolset \= APIHubToolset(

apihub\_resource\_name=”projects/test-project/locations/us-central1/apis/test-api”, service\_account\_json=”…”,

)

\# Get all available tools agent \= LlmAgent(tools=apihub\_toolset.get\_tools())

\# Get a specific tool agent \= LlmAgent(tools=\[

… apihub\_toolset.get\_tool(‘my\_tool’),

**\])**

**apihub\_resource\_name** is the resource name from API Hub. It must include  
API name, and can optionally include API version and spec name. \- If apihub\_resource\_name includes a spec resource name, the content of that

spec will be used for generating the tools.

* If apihub\_resource\_name includes only an api or a version name, the first spec of the first version of that API will be used.

Initializes the APIHubTool with the given parameters.

Examples: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id45)\` apihub\_toolset \= APIHubToolset(

apihub\_resource\_name=”projects/test-project/locations/us-central1/apis/test-api”, service\_account\_json=”…”,

)

\# Get all available tools agent \= LlmAgent(tools=apihub\_toolset.get\_tools())

\# Get a specific tool agent \= LlmAgent(tools=\[

… apihub\_toolset.get\_tool(‘my\_tool’),

**\])**

**apihub\_resource\_name** is the resource name from API Hub. It must include API name, and can optionally include API version and spec name. \- If apihub\_resource\_name includes a spec resource name, the content of that

spec will be used for generating the tools.

* If apihub\_resource\_name includes only an api or a version name, the first spec of the first version of that API will be used.

Example: \* projects/xxx/locations/us-central1/apis/apiname/… \* [https://console.cloud.google.com/apigee/api-hub/apis/apiname?project=xxx](https://console.cloud.google.com/apigee/api-hub/apis/apiname?project=xxx)

PARAM APIHUB\_RESOURCE\_NAME:  
The resource name of the API in API Hub. Example: *projects/test-project/locations/us-central1/apis/test-api*.

PARAM ACCESS\_TOKEN:  
Google Access token. Generate with gcloud cli *gcloud auth auth print-access-token*. Used for fetching API Specs from API Hub.

PARAM SERVICE\_ACCOUNT\_JSON:  
The service account config as a json string. Required if not using default service credential. It is used for creating the API Hub client and fetching the API Specs from API Hub.

PARAM APIHUB\_CLIENT:  
Optional custom API Hub client.

PARAM NAME:  
Name of the toolset. Optional.

PARAM DESCRIPTION:  
Description of the toolset. Optional.

PARAM AUTH\_SCHEME:  
Auth scheme that applies to all the tool in the toolset.

PARAM AUTH\_CREDENTIAL:  
Auth credential that applies to all the tool in the toolset.

PARAM LAZY\_LOAD\_SPEC:  
If True, the spec will be loaded lazily when needed. Otherwise, the spec will be loaded immediately and the tools will be generated during initialization.

**get\_tool(name)**  
Retrieves a specific tool by its name.

RETURN TYPE:  
Optional\[[RestApiTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.openapi_tool.RestApiTool)\]

Example: \` apihub\_tool \= apihub\_toolset.get\_tool('my\_tool') \`

PARAMETERS:  
**name** – The name of the tool to retrieve.

RETURNS:  
The tool with the given name, or None if no such tool exists.

**get\_tools()**  
Retrieves all available tools.

RETURN TYPE:  
List\[[RestApiTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.openapi_tool.RestApiTool)\]

RETURNS:  
A list of all available RestApiTool objects.

**pydantic model** google.adk.tools.**AuthToolArguments**  
Bases: BaseModel

the arguments for the special long running function tool that is used to

request end user credentials.

  
FIELDS:

* auth\_config (google.adk.auth.auth\_tool.AuthConfig)  
* function\_call\_id (str)

**field auth\_config: AuthConfig \[Required\]**  
**field function\_call\_id: str \[Required\]**  
**class** google.adk.tools.**BaseTool(\*, name, description, is\_long\_running=False)**  
Bases: ABC

The base class for all tools.

**description: str**  
The description of the tool.

**is\_long\_running: bool \= False**  
Whether the tool is a long running operation, which typically returns a resource id first and finishes the operation later.

**name: str**  
The name of the tool.

**async process\_llm\_request(\*, tool\_context, llm\_request)**  
Processes the outgoing LLM request for this tool.

Use cases: \- Most common use case is adding this tool to the LLM request. \- Some tools may just preprocess the LLM request before it’s sent out.

RETURN TYPE:  
None

PARAMETERS:

* **tool\_context** – The context of the tool.  
* **llm\_request** – The outgoing LLM request, mutable this method.

**async run\_async(\*, args, tool\_context)**  
Runs the tool with the given arguments and context.

NOTE :rtype: Any

* Required if this tool needs to run at the client side.  
* Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for Gemini.

PARAMETERS:

* **args** – The LLM-filled arguments.  
* **tool\_context** – The context of the tool.

RETURNS:  
The result of running the tool.

**class** google.adk.tools.**ExampleTool(examples)**  
Bases: [BaseTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.BaseTool)

A tool that adds (few-shot) examples to the LLM request.

**examples**  
The examples to add to the LLM request.

**async process\_llm\_request(\*, tool\_context, llm\_request)**  
Processes the outgoing LLM request for this tool.

Use cases: \- Most common use case is adding this tool to the LLM request. \- Some tools may just preprocess the LLM request before it’s sent out.

RETURN TYPE:  
None

PARAMETERS:

* **tool\_context** – The context of the tool.  
* **llm\_request** – The outgoing LLM request, mutable this method.

**class** google.adk.tools.**FunctionTool(func)**  
Bases: [BaseTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.BaseTool)

A tool that wraps a user-defined Python function.

**func**  
The function to wrap.

**async run\_async(\*, args, tool\_context)**  
Runs the tool with the given arguments and context.

NOTE :rtype: Any

* Required if this tool needs to run at the client side.  
* Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for Gemini.

PARAMETERS:

* **args** – The LLM-filled arguments.  
* **tool\_context** – The context of the tool.

RETURNS:  
The result of running the tool.

**class** google.adk.tools.**LongRunningFunctionTool(func)**  
Bases: [FunctionTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.FunctionTool)

A function tool that returns the result asynchronously.

This tool is used for long-running operations that may take a significant amount of time to complete. The framework will call the function. Once the function returns, the response will be returned asynchronously to the framework which is identified by the function\_call\_id.

Example: \`python tool \= LongRunningFunctionTool(a\_long\_running\_function) \`

**is\_long\_running**  
Whether the tool is a long running operation.

**class** google.adk.tools.**ToolContext(invocation\_context, \*, function\_call\_id=None, event\_actions=None)**  
Bases: CallbackContext

The context of the tool.

This class provides the context for a tool invocation, including access to the invocation context, function call ID, event actions, and authentication response. It also provides methods for requesting credentials, retrieving authentication responses, listing artifacts, and searching memory.

**invocation\_context**  
The invocation context of the tool.

**function\_call\_id**  
The function call id of the current tool call. This id was returned in the function call event from LLM to identify a function call. If LLM didn’t return this id, ADK will assign one to it. This id is used to map function call response to the original function call.

**event\_actions**  
The event actions of the current tool call.

**property actions: [EventActions](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.events.EventActions)**  
**get\_auth\_response(auth\_config)**  
RETURN TYPE:  
AuthCredential

**async list\_artifacts()**  
Lists the filenames of the artifacts attached to the current session.

RETURN TYPE:  
list\[str\]

**request\_credential(auth\_config)**  
RETURN TYPE:  
None

**async search\_memory(query)**  
Searches the memory of the current user.

RETURN TYPE:  
SearchMemoryResponse

**class** google.adk.tools.**VertexAiSearchTool(\*, data\_store\_id=None, search\_engine\_id=None)**  
Bases: [BaseTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.BaseTool)

A built-in tool using Vertex AI Search.

**data\_store\_id**  
The Vertex AI search data store resource ID.

**search\_engine\_id**  
The Vertex AI search engine resource ID.

Initializes the Vertex AI Search tool.

PARAMETERS:

* **data\_store\_id** – The Vertex AI search data store resource ID in the format of “projects/{project}/locations/{location}/collections/{collection}/dataStores/{dataStore}”.  
* **search\_engine\_id** – The Vertex AI search engine resource ID in the format of “projects/{project}/locations/{location}/collections/{collection}/engines/{engine}”.

RAISES:

* **ValueError** – If both data\_store\_id and search\_engine\_id are not specified  
* **or both are specified.** –

**async process\_llm\_request(\*, tool\_context, llm\_request)**  
Processes the outgoing LLM request for this tool.

Use cases: \- Most common use case is adding this tool to the LLM request. \- Some tools may just preprocess the LLM request before it’s sent out.

RETURN TYPE:  
None

PARAMETERS:

* **tool\_context** – The context of the tool.  
* **llm\_request** – The outgoing LLM request, mutable this method.

google.adk.tools.**exit\_loop(tool\_context)**  
Exits the loop.

Call this function only when you are instructed to do so.

google.adk.tools.**transfer\_to\_agent(agent\_name, tool\_context)**  
Transfer the question to another agent.

**class** google.adk.tools.application\_integration\_tool.**ApplicationIntegrationToolset(project, location, integration=None, triggers=None, connection=None, entity\_operations=None, actions=None, tool\_name='', tool\_instructions='', service\_account\_json=None)**  
Bases: object

ApplicationIntegrationToolset generates tools from a given Application

Integration or Integration Connector resource. Example Usage: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id48)\` \# Get all available tools for an integration with api trigger application\_integration\_toolset \= ApplicationIntegrationToolset(

project=”test-project”, location=”us-central1” integration=”test-integration”, trigger=”api\_trigger/test\_trigger”, service\_account\_credentials={…},

)

\# Get all available tools for a connection using entity operations and \# actions \# Note: Find the list of supported entity operations and actions for a connection \# using integration connector apis: \# [https://cloud.google.com/integration-connectors/docs/reference/rest/v1/projects.locations.connections.connectionSchemaMetadata](https://cloud.google.com/integration-connectors/docs/reference/rest/v1/projects.locations.connections.connectionSchemaMetadata) application\_integration\_toolset \= ApplicationIntegrationToolset(

project=”test-project”, location=”us-central1” connection=”test-connection”, entity\_operations=\[“EntityId1”: \[“LIST”,”CREATE”\], “EntityId2”: \[\]\], \#empty list for actions means all operations on the entity are supported actions=\[“action1”\], service\_account\_credentials={…},

)

\# Get all available tools agent \= LlmAgent(tools=\[

… [\*](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id50)application\_integration\_toolset.get\_tools(),

**\])**

Initializes the ApplicationIntegrationToolset.

Example Usage: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id53)\` \# Get all available tools for an integration with api trigger application\_integration\_toolset \= ApplicationIntegrationToolset(

project=”test-project”, location=”us-central1” integration=”test-integration”, triggers=\[“api\_trigger/test\_trigger”\], service\_account\_credentials={…},

)

\# Get all available tools for a connection using entity operations and \# actions \# Note: Find the list of supported entity operations and actions for a connection \# using integration connector apis: \# [https://cloud.google.com/integration-connectors/docs/reference/rest/v1/projects.locations.connections.connectionSchemaMetadata](https://cloud.google.com/integration-connectors/docs/reference/rest/v1/projects.locations.connections.connectionSchemaMetadata) application\_integration\_toolset \= ApplicationIntegrationToolset(

project=”test-project”, location=”us-central1” connection=”test-connection”, entity\_operations=\[“EntityId1”: \[“LIST”,”CREATE”\], “EntityId2”: \[\]\], \#empty list for actions means all operations on the entity are supported actions=\[“action1”\], service\_account\_credentials={…},

)

\# Get all available tools agent \= LlmAgent(tools=\[

… [\*](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id55)application\_integration\_toolset.get\_tools(),

**\])**

PARAM PROJECT:  
The GCP project ID.

PARAM LOCATION:  
The GCP location.

PARAM INTEGRATION:  
The integration name.

PARAM TRIGGERS:  
The list of trigger names in the integration.

PARAM CONNECTION:  
The connection name.

PARAM ENTITY\_OPERATIONS:  
The entity operations supported by the connection.

PARAM ACTIONS:  
The actions supported by the connection.

PARAM TOOL\_NAME:  
The name of the tool.

PARAM TOOL\_INSTRUCTIONS:  
The instructions for the tool.

PARAM SERVICE\_ACCOUNT\_JSON:  
The service account configuration as a dictionary. Required if not using default service credential. Used for fetching the Application Integration or Integration Connector resource.

RAISES VALUEERROR:  
If neither integration and trigger nor connection and (entity\_operations or actions) is provided.

RAISES EXCEPTION:  
If there is an error during the initialization of the integration or connection client.

**get\_tools()**  
RETURN TYPE:  
List\[[RestApiTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.openapi_tool.RestApiTool)\]

**class** google.adk.tools.application\_integration\_tool.**IntegrationConnectorTool(name, description, connection\_name, connection\_host, connection\_service\_name, entity, operation, action, rest\_api\_tool)**  
Bases: [BaseTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.BaseTool)

A tool that wraps a RestApiTool to interact with a specific Application Integration endpoint.

This tool adds Application Integration specific context like connection details, entity, operation, and action to the underlying REST API call handled by RestApiTool. It prepares the arguments and then delegates the actual API call execution to the contained RestApiTool instance.

* Generates request params and body  
* Attaches auth credentials to API call.

Example: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id58)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id60)

\# Each API operation in the spec will be turned into its own tool \# Name of the tool is the operationId of that operation, in snake case operations \= OperationGenerator().parse(openapi\_spec\_dict) tool \= \[RestApiTool.from\_parsed\_operation(o) for o in operations\]

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id62)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id64)

Initializes the ApplicationIntegrationTool.

PARAMETERS:

* **name** – The name of the tool, typically derived from the API operation. Should be unique and adhere to Gemini function naming conventions (e.g., less than 64 characters).  
* **description** – A description of what the tool does, usually based on the API operation’s summary or description.  
* **connection\_name** – The name of the Integration Connector connection.  
* **connection\_host** – The hostname or IP address for the connection.  
* **connection\_service\_name** – The specific service name within the host.  
* **entity** – The Integration Connector entity being targeted.  
* **operation** – The specific operation being performed on the entity.  
* **action** – The action associated with the operation (e.g., ‘execute’).  
* **rest\_api\_tool** – An initialized RestApiTool instance that handles the underlying REST API communication based on an OpenAPI specification operation. This tool will be called by ApplicationIntegrationTool with added connection and context arguments. tool \= \[RestApiTool.from\_parsed\_operation(o) for o in operations\]

**EXCLUDE\_FIELDS \= \['connection\_name', 'service\_name', 'host', 'entity', 'operation', 'action'\]**  
**OPTIONAL\_FIELDS \= \['page\_size', 'page\_token', 'filter'\]**  
**async run\_async(\*, args, tool\_context)**  
Runs the tool with the given arguments and context.

NOTE :rtype: Dict\[str, Any\]

* Required if this tool needs to run at the client side.  
* Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for Gemini.

PARAMETERS:

* **args** – The LLM-filled arguments.  
* **tool\_context** – The context of the tool.

RETURNS:  
The result of running the tool.

**class** google.adk.tools.mcp\_tool.**MCPTool(mcp\_tool, mcp\_session, mcp\_session\_manager, auth\_scheme=None, auth\_credential=None)**  
Bases: [BaseTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.BaseTool)

Turns a MCP Tool into a Vertex Agent Framework Tool.

Internally, the tool initializes from a MCP Tool, and uses the MCP Session to call the tool.

Initializes a MCPTool.

This tool wraps a MCP Tool interface and an active MCP Session. It invokes the MCP Tool through executing the tool from remote MCP Session.

EXAMPLE

tool \= MCPTool(mcp\_tool=mcp\_tool, mcp\_session=mcp\_session)

PARAMETERS:

* **mcp\_tool** – The MCP tool to wrap.  
* **mcp\_session** – The MCP session to use to call the tool.  
* **auth\_scheme** – The authentication scheme to use.  
* **auth\_credential** – The authentication credential to use.

RAISES:  
**ValueError** – If mcp\_tool or mcp\_session is None.

**async run\_async(\*, args, tool\_context)**  
Runs the tool asynchronously.

PARAMETERS:

* **args** – The arguments as a dict to pass to the tool.  
* **tool\_context** – The tool context from upper level ADK agent.

RETURNS:  
The response from the tool.

RETURN TYPE:  
Any

**class** google.adk.tools.mcp\_tool.**MCPToolset(\*, connection\_params, errlog=\<\_io.TextIOWrapper name='\<stderr\>' mode='w' encoding='utf-8'\>, exit\_stack=\<contextlib.AsyncExitStack object\>)**  
Bases: object

Connects to a MCP Server, and retrieves MCP Tools into ADK Tools.

Usage: Example 1: (using from\_server helper): [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id66)\` async def load\_tools():

return await MCPToolset.from\_server(  
connection\_params=StdioServerParameters(  
command=’npx’, args=\[“-y”, “@modelcontextprotocol/server-filesystem”\], )

)

\# Use the tools in an LLM agent tools, exit\_stack \= await load\_tools() agent \= LlmAgent(

tools=tools

**)**

await exit\_stack.aclose() [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id69)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id71)

Example 2: (using *async with*):

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id73)\` async def load\_tools():

async with MCPToolset(  
connection\_params=SseServerParams(url=”[http://0.0.0.0:8090/sse](http://0.0.0.0:8090/sse)”)

) as toolset:  
tools \= await toolset.load\_tools()

agent \= LlmAgent(  
… tools=tools

)

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id75)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id77)

Example 3: (provide AsyncExitStack): [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id79)\` async def load\_tools():

async\_exit\_stack \= AsyncExitStack() toolset \= MCPToolset(

connection\_params=StdioServerParameters(…),

) async\_exit\_stack.enter\_async\_context(toolset) tools \= await toolset.load\_tools() agent \= LlmAgent(

… tools=tools

await async\_exit\_stack.aclose()

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id81)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id83)

**connection\_params**  
The connection parameters to the MCP server. Can be either *StdioServerParameters* or *SseServerParams*.

**exit\_stack**  
The async exit stack to manage the connection to the MCP server.

**session**  
The MCP session being initialized with the connection.

Initializes the MCPToolset.

Usage: Example 1: (using from\_server helper): [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id85)\` async def load\_tools():

return await MCPToolset.from\_server(  
connection\_params=StdioServerParameters(  
command=’npx’, args=\[“-y”, “@modelcontextprotocol/server-filesystem”\], )

)

\# Use the tools in an LLM agent tools, exit\_stack \= await load\_tools() agent \= LlmAgent(

tools=tools

**)**

await exit\_stack.aclose() [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id88)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id90)

Example 2: (using *async with*):

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id92)\` async def load\_tools():

async with MCPToolset(  
connection\_params=SseServerParams(url=”[http://0.0.0.0:8090/sse](http://0.0.0.0:8090/sse)”)

) as toolset:  
tools \= await toolset.load\_tools()

agent \= LlmAgent(  
… tools=tools

)

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id94)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id96)

Example 3: (provide AsyncExitStack): [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id98)\` async def load\_tools():

async\_exit\_stack \= AsyncExitStack() toolset \= MCPToolset(

connection\_params=StdioServerParameters(…),

) async\_exit\_stack.enter\_async\_context(toolset) tools \= await toolset.load\_tools() agent \= LlmAgent(

… tools=tools

await async\_exit\_stack.aclose()

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id100)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id102)

PARAM CONNECTION\_PARAMS:  
The connection parameters to the MCP server. Can be: *StdioServerParameters* for using local mcp server (e.g. using *npx* or *python3*); or *SseServerParams* for a local/remote SSE server.

**async classmethod from\_server(\*, connection\_params, async\_exit\_stack=None, errlog=\<\_io.TextIOWrapper name='\<stderr\>' mode='w' encoding='utf-8'\>)**  
Retrieve all tools from the MCP connection.

RETURN TYPE:  
Tuple\[List\[[MCPTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.mcp_tool.MCPTool)\], AsyncExitStack\]

Usage: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id104)\` async def load\_tools():

tools, exit\_stack \= await MCPToolset.from\_server(  
connection\_params=StdioServerParameters(  
command=’npx’, args=\[“-y”, “@modelcontextprotocol/server-filesystem”\],

)

)

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id106)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id108)

PARAMETERS:

* **connection\_params** – The connection parameters to the MCP server.  
* **async\_exit\_stack** – The async exit stack to use. If not provided, a new AsyncExitStack will be created.

RETURNS:  
A tuple of the list of MCPTools and the AsyncExitStack. \- tools: The list of MCPTools. \- async\_exit\_stack: The AsyncExitStack used to manage the connection to

the MCP server. Use *await async\_exit\_stack.aclose()* to close the connection when server shuts down.

**async load\_tools()**  
Loads all tools from the MCP Server.

RETURN TYPE:  
List\[[MCPTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.mcp_tool.MCPTool)\]

RETURNS:  
A list of MCPTools imported from the MCP Server.

google.adk.tools.mcp\_tool.**adk\_to\_mcp\_tool\_type(tool)**  
Convert a Tool in ADK into MCP tool type.

This function transforms an ADK tool definition into its equivalent representation in the MCP (Model Context Protocol) system.

RETURN TYPE:  
Tool

PARAMETERS:  
**tool** – The ADK tool to convert. It should be an instance of a class derived from *BaseTool*.

RETURNS:  
An object of MCP Tool type, representing the converted tool.

EXAMPLES

\# Assuming ‘my\_tool’ is an instance of a BaseTool derived class mcp\_tool \= adk\_to\_mcp\_tool\_type(my\_tool) print(mcp\_tool)

google.adk.tools.mcp\_tool.**gemini\_to\_json\_schema(gemini\_schema)**  
Converts a Gemini Schema object into a JSON Schema dictionary.

RETURN TYPE:  
Dict\[str, Any\]

PARAMETERS:  
**gemini\_schema** – An instance of the Gemini Schema class.

RETURNS:  
A dictionary representing the equivalent JSON Schema.

RAISES:

* **TypeError** – If the input is not an instance of the expected Schema class.  
* **ValueError** – If an invalid Gemini Type enum value is encountered.

**class** google.adk.tools.openapi\_tool.**OpenAPIToolset(\*, spec\_dict=None, spec\_str=None, spec\_str\_type='json', auth\_scheme=None, auth\_credential=None)**  
Bases: object

Class for parsing OpenAPI spec into a list of RestApiTool.

Usage: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id110)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id112)

\# Initialize OpenAPI toolset from a spec string. openapi\_toolset \= OpenAPIToolset(spec\_str=openapi\_spec\_str,

spec\_str\_type=”json”)

\# Or, initialize OpenAPI toolset from a spec dictionary. openapi\_toolset \= OpenAPIToolset(spec\_dict=openapi\_spec\_dict)

\# Add all tools to an agent. agent \= Agent(

tools=\[[\*](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id114)openapi\_toolset.get\_tools()\]

) \# Or, add a single tool to an agent. agent \= Agent(

tools=\[openapi\_toolset.get\_tool(‘tool\_name’)\]

)

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id116)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id118)

Initializes the OpenAPIToolset.

Usage: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id120)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id122)

\# Initialize OpenAPI toolset from a spec string. openapi\_toolset \= OpenAPIToolset(spec\_str=openapi\_spec\_str,

spec\_str\_type=”json”)

\# Or, initialize OpenAPI toolset from a spec dictionary. openapi\_toolset \= OpenAPIToolset(spec\_dict=openapi\_spec\_dict)

\# Add all tools to an agent. agent \= Agent(

tools=\[[\*](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id124)openapi\_toolset.get\_tools()\]

) \# Or, add a single tool to an agent. agent \= Agent(

tools=\[openapi\_toolset.get\_tool(‘tool\_name’)\]

)

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id126)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id128)

PARAMETERS:

* **spec\_dict** – The OpenAPI spec dictionary. If provided, it will be used instead of loading the spec from a string.  
* **spec\_str** – The OpenAPI spec string in JSON or YAML format. It will be used when spec\_dict is not provided.  
* **spec\_str\_type** – The type of the OpenAPI spec string. Can be “json” or “yaml”.  
* **auth\_scheme** – The auth scheme to use for all tools. Use AuthScheme or use helpers in *google.adk.tools.openapi\_tool.auth.auth\_helpers*  
* **auth\_credential** – The auth credential to use for all tools. Use AuthCredential or use helpers in *google.adk.tools.openapi\_tool.auth.auth\_helpers*

**get\_tool(tool\_name)**  
Get a tool by name.

RETURN TYPE:  
Optional\[[RestApiTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.openapi_tool.RestApiTool)\]

**get\_tools()**  
Get all tools in the toolset.

RETURN TYPE:  
List\[[RestApiTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.openapi_tool.RestApiTool)\]

**class** google.adk.tools.openapi\_tool.**RestApiTool(name, description, endpoint, operation, auth\_scheme=None, auth\_credential=None, should\_parse\_operation=True)**  
Bases: [BaseTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.BaseTool)

A generic tool that interacts with a REST API.

* Generates request params and body  
* Attaches auth credentials to API call.

Example: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id130)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id132)

\# Each API operation in the spec will be turned into its own tool \# Name of the tool is the operationId of that operation, in snake case operations \= OperationGenerator().parse(openapi\_spec\_dict) tool \= \[RestApiTool.from\_parsed\_operation(o) for o in operations\]

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id134)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id136)

Initializes the RestApiTool with the given parameters.

To generate RestApiTool from OpenAPI Specs, use OperationGenerator. Example: [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id138)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id140)

\# Each API operation in the spec will be turned into its own tool \# Name of the tool is the operationId of that operation, in snake case operations \= OperationGenerator().parse(openapi\_spec\_dict) tool \= \[RestApiTool.from\_parsed\_operation(o) for o in operations\]

[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id142)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id144)

Hint: Use google.adk.tools.openapi\_tool.auth.auth\_helpers to construct auth\_scheme and auth\_credential.

PARAMETERS:

* **name** – The name of the tool.  
* **description** – The description of the tool.  
* **endpoint** – Include the base\_url, path, and method of the tool.  
* **operation** – Pydantic object or a dict. Representing the OpenAPI Operation object ([https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md\#operation-object](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#operation-object))  
* **auth\_scheme** – The auth scheme of the tool. Representing the OpenAPI SecurityScheme object ([https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md\#security-scheme-object](https://github.com/OAI/OpenAPI-Specification/blob/main/versions/3.1.0.md#security-scheme-object))  
* **auth\_credential** – The authentication credential of the tool.  
* **should\_parse\_operation** – Whether to parse the operation.

**call(\*, args, tool\_context)**  
Executes the REST API call.

RETURN TYPE:  
Dict\[str, Any\]

PARAMETERS:

* **args** – Keyword arguments representing the operation parameters.  
* **tool\_context** – The tool context (not used here, but required by the interface).

RETURNS:  
The API response as a dictionary.

**configure\_auth\_credential(auth\_credential=None)**  
Configures the authentication credential for the API call.

PARAMETERS:  
**auth\_credential** – AuthCredential|dict \- The authentication credential. The dict is converted to an AuthCredential object.

**configure\_auth\_scheme(auth\_scheme)**  
Configures the authentication scheme for the API call.

PARAMETERS:  
**auth\_scheme** – AuthScheme|dict \-: The authentication scheme. The dict is converted to a AuthScheme object.

**classmethod from\_parsed\_operation(parsed)**  
Initializes the RestApiTool from a ParsedOperation object.

RETURN TYPE:  
[RestApiTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.openapi_tool.RestApiTool)

PARAMETERS:  
**parsed** – A ParsedOperation object.

RETURNS:  
A RestApiTool object.

**classmethod from\_parsed\_operation\_str(parsed\_operation\_str)**  
Initializes the RestApiTool from a dict.

RETURN TYPE:  
[RestApiTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.openapi_tool.RestApiTool)

PARAMETERS:  
**parsed** – A dict representation of a ParsedOperation object.

RETURNS:  
A RestApiTool object.

**async run\_async(\*, args, tool\_context)**  
Runs the tool with the given arguments and context.

NOTE :rtype: Dict\[str, Any\]

* Required if this tool needs to run at the client side.  
* Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for Gemini.

PARAMETERS:

* **args** – The LLM-filled arguments.  
* **tool\_context** – The context of the tool.

RETURNS:  
The result of running the tool.

**class** google.adk.tools.retrieval.**BaseRetrievalTool(\*, name, description, is\_long\_running=False)**  
Bases: [BaseTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.BaseTool)

**class** google.adk.tools.retrieval.**FilesRetrieval(\*, name, description, input\_dir)**  
Bases: [LlamaIndexRetrieval](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.retrieval.LlamaIndexRetrieval)

**class** google.adk.tools.retrieval.**LlamaIndexRetrieval(\*, name, description, retriever)**  
Bases: [BaseRetrievalTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.retrieval.BaseRetrievalTool)

**async run\_async(\*, args, tool\_context)**  
Runs the tool with the given arguments and context.

NOTE :rtype: Any

* Required if this tool needs to run at the client side.  
* Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for Gemini.

PARAMETERS:

* **args** – The LLM-filled arguments.  
* **tool\_context** – The context of the tool.

RETURNS:  
The result of running the tool.

**class** google.adk.tools.retrieval.**VertexAiRagRetrieval(\*, name, description, rag\_corpora=None, rag\_resources=None, similarity\_top\_k=None, vector\_distance\_threshold=None)**  
Bases: [BaseRetrievalTool](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.tools.retrieval.BaseRetrievalTool)

A retrieval tool that uses Vertex AI RAG (Retrieval-Augmented Generation) to retrieve data.

**async process\_llm\_request(\*, tool\_context, llm\_request)**  
Processes the outgoing LLM request for this tool.

Use cases: \- Most common use case is adding this tool to the LLM request. \- Some tools may just preprocess the LLM request before it’s sent out.

RETURN TYPE:  
None

PARAMETERS:

* **tool\_context** – The context of the tool.  
* **llm\_request** – The outgoing LLM request, mutable this method.

**async run\_async(\*, args, tool\_context)**  
Runs the tool with the given arguments and context.

NOTE :rtype: Any

* Required if this tool needs to run at the client side.  
* Otherwise, can be skipped, e.g. for a built-in GoogleSearch tool for Gemini.

PARAMETERS:

* **args** – The LLM-filled arguments.  
* **tool\_context** – The context of the tool.

RETURNS:  
The result of running the tool.

