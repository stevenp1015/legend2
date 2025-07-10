### google.adk.models module

**google.adk.models module**

Defines the interface to support a model.

**pydantic model** google.adk.models.**BaseLlm**  
Bases: BaseModel

The BaseLLM class.

**model**  
The name of the LLM, e.g. gemini-1.5-flash or gemini-1.5-flash-001.

  
FIELDS:

* model (str)

**field model: str \[Required\]**  
The name of the LLM, e.g. gemini-1.5-flash or gemini-1.5-flash-001.

**classmethod supported\_models()**  
Returns a list of supported models in regex for LlmRegistry.

RETURN TYPE:  
list\[str\]

**connect(llm\_request)**  
Creates a live connection to the LLM.

RETURN TYPE:  
BaseLlmConnection

PARAMETERS:  
**llm\_request** – LlmRequest, the request to send to the LLM.

RETURNS:  
BaseLlmConnection, the connection to the LLM.

**abstractmethod async generate\_content\_async(llm\_request, stream=False)**  
Generates one content from the given contents and tools.

RETURN TYPE:  
AsyncGenerator\[LlmResponse, None\]

PARAMETERS:

* **llm\_request** – LlmRequest, the request to send to the LLM.  
* **stream** – bool \= False, whether to do streaming call.

YIELDS:  
a generator of types.Content.

For non-streaming call, it will only yield one Content.

For streaming call, it may yield more than one content, but all yielded contents should be treated as one content by merging the parts list.

**pydantic model** google.adk.models.**Gemini**  
Bases: [BaseLlm](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.models.BaseLlm)

Integration for Gemini models.

**model**  
The name of the Gemini model.

  
FIELDS:

* model (str)

**field model: str \= 'gemini-1.5-flash'**  
The name of the LLM, e.g. gemini-1.5-flash or gemini-1.5-flash-001.

**static supported\_models()**  
Provides the list of supported models.

RETURN TYPE:  
list\[str\]

RETURNS:  
A list of supported models.

**connect(llm\_request)**  
Connects to the Gemini model and returns an llm connection.

RETURN TYPE:  
BaseLlmConnection

PARAMETERS:  
**llm\_request** – LlmRequest, the request to send to the Gemini model.

YIELDS:  
BaseLlmConnection, the connection to the Gemini model.

**async generate\_content\_async(llm\_request, stream=False)**  
Sends a request to the Gemini model.

RETURN TYPE:  
AsyncGenerator\[LlmResponse, None\]

PARAMETERS:

* **llm\_request** – LlmRequest, the request to send to the Gemini model.  
* **stream** – bool \= False, whether to do streaming call.

YIELDS:  
*LlmResponse* – The model response.

**property api\_client: Client**  
Provides the api client.

RETURNS:  
The api client.

**class** google.adk.models.**LLMRegistry**  
Bases: object

Registry for LLMs.

**static new\_llm(model)**  
Creates a new LLM instance.

RETURN TYPE:  
[BaseLlm](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.models.BaseLlm)

PARAMETERS:  
**model** – The model name.

RETURNS:  
The LLM instance.

**static register(llm\_cls)**  
Registers a new LLM class.

PARAMETERS:  
**llm\_cls** – The class that implements the model.

**static resolve(model)**  
Resolves the model to a BaseLlm subclass.

RETURN TYPE:  
type\[[BaseLlm](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.models.BaseLlm)\]

PARAMETERS:  
**model** – The model name.

RETURNS:  
The BaseLlm subclass.

RAISES:  
**ValueError** – If the model is not found.

