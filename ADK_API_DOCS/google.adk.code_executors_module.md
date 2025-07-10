### google.adk.code\_executors module

**google.adk.code\_executors module**

**pydantic model** google.adk.code\_executors.**BaseCodeExecutor**  
Bases: BaseModel

Abstract base class for all code executors.

The code executor allows the agent to execute code blocks from model responses and incorporate the execution results into the final response.

**optimize\_data\_file**  
If true, extract and process data files from the model request and attach them to the code executor. Supported data file MimeTypes are \[text/csv\]. Default to False.

**stateful**  
Whether the code executor is stateful. Default to False.

**error\_retry\_attempts**  
The number of attempts to retry on consecutive code execution errors. Default to 2\.

**code\_block\_delimiters**  
The list of the enclosing delimiters to identify the code blocks.

**execution\_result\_delimiters**  
The delimiters to format the code execution result.

  
FIELDS:

* code\_block\_delimiters (List\[tuple\[str, str\]\])  
* error\_retry\_attempts (int)  
* execution\_result\_delimiters (tuple\[str, str\])  
* optimize\_data\_file (bool)  
* stateful (bool)

**field code\_block\_delimiters: List\[tuple\[str, str\]\] \= \[('\`\`\`tool\_code\\n', '\\n\`\`\`'), ('\`\`\`python\\n', '\\n\`\`\`')\]**  
The list of the enclosing delimiters to identify the code blocks. For example, the delimiter (’[\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id1)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id3)python

‘, ‘ [\`\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id5)[\`](https://google.github.io/adk-docs/api-reference/python/google-adk.html#id7)’) can be

used to identify code blocks with the following format:

\`python print("hello") \`

**field error\_retry\_attempts: int \= 2**  
The number of attempts to retry on consecutive code execution errors. Default to 2\.

**field execution\_result\_delimiters: tuple\[str, str\] \= ('\`\`\`tool\_output\\n', '\\n\`\`\`')**  
The delimiters to format the code execution result.

**field optimize\_data\_file: bool \= False**  
If true, extract and process data files from the model request and attach them to the code executor. Supported data file MimeTypes are \[text/csv\].

Default to False.

**field stateful: bool \= False**  
Whether the code executor is stateful. Default to False.

**abstractmethod execute\_code(invocation\_context, code\_execution\_input)**  
Executes code and return the code execution result.

RETURN TYPE:  
CodeExecutionResult

PARAMETERS:

* **invocation\_context** – The invocation context of the code execution.  
* **code\_execution\_input** – The code execution input.

RETURNS:  
The code execution result.

**class** google.adk.code\_executors.**CodeExecutorContext(session\_state)**  
Bases: object

The persistent context used to configure the code executor.

Initializes the code executor context.

PARAMETERS:  
**session\_state** – The session state to get the code executor context from.

**add\_input\_files(input\_files)**  
Adds the input files to the code executor context.

PARAMETERS:  
**input\_files** – The input files to add to the code executor context.

**add\_processed\_file\_names(file\_names)**  
Adds the processed file name to the session state.

PARAMETERS:  
**file\_names** – The processed file names to add to the session state.

**clear\_input\_files()**  
Removes the input files and processed file names to the code executor context.

**get\_error\_count(invocation\_id)**  
Gets the error count from the session state.

RETURN TYPE:  
int

PARAMETERS:  
**invocation\_id** – The invocation ID to get the error count for.

RETURNS:  
The error count for the given invocation ID.

**get\_execution\_id()**  
Gets the session ID for the code executor.

RETURN TYPE:  
Optional\[str\]

RETURNS:  
The session ID for the code executor context.

**get\_input\_files()**  
Gets the code executor input file names from the session state.

RETURN TYPE:  
list\[File\]

RETURNS:  
A list of input files in the code executor context.

**get\_processed\_file\_names()**  
Gets the processed file names from the session state.

RETURN TYPE:  
list\[str\]

RETURNS:  
A list of processed file names in the code executor context.

**get\_state\_delta()**  
Gets the state delta to update in the persistent session state.

RETURN TYPE:  
dict\[str, Any\]

RETURNS:  
The state delta to update in the persistent session state.

**increment\_error\_count(invocation\_id)**  
Increments the error count from the session state.

PARAMETERS:  
**invocation\_id** – The invocation ID to increment the error count for.

**reset\_error\_count(invocation\_id)**  
Resets the error count from the session state.

PARAMETERS:  
**invocation\_id** – The invocation ID to reset the error count for.

**set\_execution\_id(session\_id)**  
Sets the session ID for the code executor.

PARAMETERS:  
**session\_id** – The session ID for the code executor.

**update\_code\_execution\_result(invocation\_id, code, result\_stdout, result\_stderr)**  
Updates the code execution result.

PARAMETERS:

* **invocation\_id** – The invocation ID to update the code execution result for.  
* **code** – The code to execute.  
* **result\_stdout** – The standard output of the code execution.  
* **result\_stderr** – The standard error of the code execution.

**pydantic model** google.adk.code\_executors.**ContainerCodeExecutor**  
Bases: [BaseCodeExecutor](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.code_executors.BaseCodeExecutor)

A code executor that uses a custom container to execute code.

**base\_url**  
Optional. The base url of the user hosted Docker client.

**image**  
The tag of the predefined image or custom image to run on the container. Either docker\_path or image must be set.

**docker\_path**  
The path to the directory containing the Dockerfile. If set, build the image from the dockerfile path instead of using the predefined image. Either docker\_path or image must be set.

Initializes the ContainerCodeExecutor.

PARAMETERS:

* **base\_url** – Optional. The base url of the user hosted Docker client.  
* **image** – The tag of the predefined image or custom image to run on the container. Either docker\_path or image must be set.  
* **docker\_path** – The path to the directory containing the Dockerfile. If set, build the image from the dockerfile path instead of using the predefined image. Either docker\_path or image must be set.  
* **\*\*data** – The data to initialize the ContainerCodeExecutor.

  
FIELDS:

* base\_url (str | None)  
* docker\_path (str)  
* image (str)  
* optimize\_data\_file (bool)  
* stateful (bool)

**field base\_url: Optional\[str\] \= None**  
Optional. The base url of the user hosted Docker client.

**field docker\_path: str \= None**  
The path to the directory containing the Dockerfile. If set, build the image from the dockerfile path instead of using the predefined image. Either docker\_path or image must be set.

**field image: str \= None**  
The tag of the predefined image or custom image to run on the container. Either docker\_path or image must be set.

**field optimize\_data\_file: bool \= False**  
If true, extract and process data files from the model request and attach them to the code executor. Supported data file MimeTypes are \[text/csv\].

Default to False.

**field stateful: bool \= False**  
Whether the code executor is stateful. Default to False.

**execute\_code(invocation\_context, code\_execution\_input)**  
Executes code and return the code execution result.

RETURN TYPE:  
CodeExecutionResult

PARAMETERS:

* **invocation\_context** – The invocation context of the code execution.  
* **code\_execution\_input** – The code execution input.

RETURNS:  
The code execution result.

**model\_post\_init(context, /)**  
This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

RETURN TYPE:  
None

PARAMETERS:

* **self** – The BaseModel instance.  
* **context** – The context.

**pydantic model** google.adk.code\_executors.**UnsafeLocalCodeExecutor**  
Bases: [BaseCodeExecutor](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.code_executors.BaseCodeExecutor)

A code executor that unsafely execute code in the current local context.

Initializes the UnsafeLocalCodeExecutor.

  
FIELDS:

* optimize\_data\_file (bool)  
* stateful (bool)

**field optimize\_data\_file: bool \= False**  
If true, extract and process data files from the model request and attach them to the code executor. Supported data file MimeTypes are \[text/csv\].

Default to False.

**field stateful: bool \= False**  
Whether the code executor is stateful. Default to False.

**execute\_code(invocation\_context, code\_execution\_input)**  
Executes code and return the code execution result.

RETURN TYPE:  
CodeExecutionResult

PARAMETERS:

* **invocation\_context** – The invocation context of the code execution.  
* **code\_execution\_input** – The code execution input.

RETURNS:  
The code execution result.

**pydantic model** google.adk.code\_executors.**VertexAiCodeExecutor**  
Bases: [BaseCodeExecutor](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.code_executors.BaseCodeExecutor)

A code executor that uses Vertex Code Interpreter Extension to execute code.

**resource\_name**  
If set, load the existing resource name of the code interpreter extension instead of creating a new one. Format: projects/123/locations/us-central1/extensions/456

Initializes the VertexAiCodeExecutor.

PARAMETERS:

* **resource\_name** – If set, load the existing resource name of the code interpreter extension instead of creating a new one. Format: projects/123/locations/us-central1/extensions/456  
* **\*\*data** – Additional keyword arguments to be passed to the base class.

  
FIELDS:

* resource\_name (str)

**field resource\_name: str \= None**  
If set, load the existing resource name of the code interpreter extension instead of creating a new one. Format: projects/123/locations/us-central1/extensions/456

**execute\_code(invocation\_context, code\_execution\_input)**  
Executes code and return the code execution result.

RETURN TYPE:  
CodeExecutionResult

PARAMETERS:

* **invocation\_context** – The invocation context of the code execution.  
* **code\_execution\_input** – The code execution input.

RETURNS:  
The code execution result.

**model\_post\_init(context, /)**  
This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

RETURN TYPE:  
None

PARAMETERS:

* **self** – The BaseModel instance.  
* **context** – The context.

