### google.adk.examples module

**google.adk.examples module**

**class** google.adk.examples.**BaseExampleProvider**  
Bases: ABC

Base class for example providers.

This class defines the interface for providing examples for a given query.

**abstractmethod get\_examples(query)**  
Returns a list of examples for a given query.

RETURN TYPE:  
list\[[Example](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.examples.Example)\]

PARAMETERS:  
**query** – The query to get examples for.

RETURNS:  
A list of Example objects.

**pydantic model** google.adk.examples.**Example**  
Bases: BaseModel

A few-shot example.

**input**  
The input content for the example.

**output**  
The expected output content for the example.

  
FIELDS:

* input (google.genai.types.Content)  
* output (list\[google.genai.types.Content\])

**field input: Content \[Required\]**  
**field output: list\[Content\] \[Required\]**  
**class** google.adk.examples.**VertexAiExampleStore(examples\_store\_name)**  
Bases: [BaseExampleProvider](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.examples.BaseExampleProvider)

Provides examples from Vertex example store.

Initializes the VertexAiExampleStore.

PARAMETERS:  
**examples\_store\_name** – The resource name of the vertex example store, in the format of projects/{project}/locations/{location}/exampleStores/{example\_store}.

**get\_examples(query)**  
Returns a list of examples for a given query.

RETURN TYPE:  
list\[[Example](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.examples.Example)\]

PARAMETERS:  
**query** – The query to get examples for.

RETURNS:  
A list of Example objects.

