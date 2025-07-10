### google.adk.evaluation module

**google.adk.evaluation module**

**class** google.adk.evaluation.**AgentEvaluator**  
Bases: object

An evaluator for Agents, mainly intended for helping with test cases.

**static evaluate(agent\_module, eval\_dataset\_file\_path\_or\_dir, num\_runs=2, agent\_name=None, initial\_session\_file=None)**  
Evaluates an Agent given eval data.

PARAMETERS:

* **agent\_module** – The path to python module that contains the definition of the agent. There is convention in place here, where the code is going to look for ‘root\_agent’ in the loaded module.  
* **eval\_dataset** – The eval data set. This can be either a string representing full path to the file containing eval dataset, or a directory that is recursively explored for all files that have a *.test.json* suffix.  
* **num\_runs** – Number of times all entries in the eval dataset should be assessed.  
* **agent\_name** – The name of the agent.  
* **initial\_session\_file** – File that contains initial session state that is needed by all the evals in the eval dataset.

**static find\_config\_for\_test\_file(test\_file)**  
Find the test\_config.json file in the same folder as the test file.

