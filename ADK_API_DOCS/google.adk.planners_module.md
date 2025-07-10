### google.adk.planners module

**google.adk.planners module**

**class** google.adk.planners.**BasePlanner**  
Bases: ABC

Abstract base class for all planners.

The planner allows the agent to generate plans for the queries to guide its action.

**abstractmethod build\_planning\_instruction(readonly\_context, llm\_request)**  
Builds the system instruction to be appended to the LLM request for planning.

RETURN TYPE:  
Optional\[str\]

PARAMETERS:

* **readonly\_context** – The readonly context of the invocation.  
* **llm\_request** – The LLM request. Readonly.

RETURNS:  
The planning system instruction, or None if no instruction is needed.

**abstractmethod process\_planning\_response(callback\_context, response\_parts)**  
Processes the LLM response for planning.

RETURN TYPE:  
Optional\[List\[Part\]\]

PARAMETERS:

* **callback\_context** – The callback context of the invocation.  
* **response\_parts** – The LLM response parts. Readonly.

RETURNS:  
The processed response parts, or None if no processing is needed.

**class** google.adk.planners.**BuiltInPlanner(\*, thinking\_config)**  
Bases: [BasePlanner](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.planners.BasePlanner)

The built-in planner that uses model’s built-in thinking features.

**thinking\_config**  
Config for model built-in thinking features. An error will be returned if this field is set for models that don’t support thinking.

Initializes the built-in planner.

PARAMETERS:  
**thinking\_config** – Config for model built-in thinking features. An error will be returned if this field is set for models that don’t support thinking.

**apply\_thinking\_config(llm\_request)**  
Applies the thinking config to the LLM request.

RETURN TYPE:  
None

PARAMETERS:  
**llm\_request** – The LLM request to apply the thinking config to.

**build\_planning\_instruction(readonly\_context, llm\_request)**  
Builds the system instruction to be appended to the LLM request for planning.

RETURN TYPE:  
Optional\[str\]

PARAMETERS:

* **readonly\_context** – The readonly context of the invocation.  
* **llm\_request** – The LLM request. Readonly.

RETURNS:  
The planning system instruction, or None if no instruction is needed.

**process\_planning\_response(callback\_context, response\_parts)**  
Processes the LLM response for planning.

RETURN TYPE:  
Optional\[List\[Part\]\]

PARAMETERS:

* **callback\_context** – The callback context of the invocation.  
* **response\_parts** – The LLM response parts. Readonly.

RETURNS:  
The processed response parts, or None if no processing is needed.

**thinking\_config: ThinkingConfig**  
Config for model built-in thinking features. An error will be returned if this field is set for models that don’t support thinking.

**class** google.adk.planners.**PlanReActPlanner**  
Bases: [BasePlanner](https://google.github.io/adk-docs/api-reference/python/google-adk.html#google.adk.planners.BasePlanner)

Plan-Re-Act planner that constrains the LLM response to generate a plan before any action/observation.

Note: this planner does not require the model to support built-in thinking features or setting the thinking config.

**build\_planning\_instruction(readonly\_context, llm\_request)**  
Builds the system instruction to be appended to the LLM request for planning.

RETURN TYPE:  
str

PARAMETERS:

* **readonly\_context** – The readonly context of the invocation.  
* **llm\_request** – The LLM request. Readonly.

RETURNS:  
The planning system instruction, or None if no instruction is needed.

**process\_planning\_response(callback\_context, response\_parts)**  
Processes the LLM response for planning.

RETURN TYPE:  
Optional\[List\[Part\]\]

PARAMETERS:

* **callback\_context** – The callback context of the invocation.  
* **response\_parts** – The LLM response parts. Readonly.

RETURNS:  
The processed response parts, or None if no processing is needed.

