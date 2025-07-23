from pydantic import BaseModel
from typing import List, Callable, Optional, Dict, Any
import inspect
import os


custom_react_prompt = """You are an expert finance analyst who can answer questions by analysing and making tool calls. 
You are an expert at breaking down complex tasks into smaller steps such that each step can be solved by the tools you have. 
When given a task, you will iteratively perform 3 steps: Think, Act, Observe. Here is how you should do it:
1. Think: You will think about the task and what you need to do to solve it. You will think about the tools you have and how you can use them to solve the task.
2. Act: You will take an action based on your thought. This action can be a tool call or an analysis that you can do yourself.
3. Observe: You will observe the result of your action and use it to inform your next step.

At any given step, you will see what has happened before - you will see what you have already done. If you have completed the task (Thinking + acting + observing), you will then think about the next step and execute it in the similar way.
However, at one step you only do one thing.
"""


######################## NVIDIA React Agent ########################
nvidia_react = '''Answer the following questions as best you can. You may ask the human to use the following tools:

{tools}

You may respond in one of two formats.
Use the following format exactly to ask the human to use a tool:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: The input to the action (if there is no required input, include "Action Input: None")
Observation: wait for the human to respond with the result from the tool, do not assume the response

... (this Thought/Action/Action Input/Observation can repeat N times. If you do not need to use a tool, or after asking the human to use any tools and waiting for the human to respond, you might know the final answer.)
Use the following format once you have the final answer:

Thought: I now know the final answer
Final Answer: the final answer to the original input question'''
nvidia_react_minus_tools = '''Answer the following questions as best you can. Y

You may respond in one of two formats.


Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take - this could be an analysis
Action Input: The input to the action (if there is no required input, include "Action Input: None")
Observation: What are your conclusions
... (this Thought/Action/Action Input/Observation can repeat N times. If you do not need to use a tool, or after asking the human to use any tools and waiting for the human to respond, you might know the final answer.)
Use the following format once you have the final answer:

Thought: I now know the final answer
Final Answer: the final answer to the original input question'''
class NVIDIAReactSchema(BaseModel):
    question: str
    thought: str
    action: str
    action_input: Optional[str] = None
    observation: Optional[str] = None
    final_answer: Optional[str] = None


################################## LLAMA React Agent ##################################
llama_react = """
You are an expert assistant who can solve any task using tool calls. You will be given a task to solve as best you can.
To do so, you have been given access to the following tools: <<tool_names>>

You must always respond in the following JSON format:
{
    "thought": $THOUGHT_PROCESS,
    "action": {
        "tool_name": $TOOL_NAME,
        "tool_params": $TOOL_PARAMS
    },
    "answer": $ANSWER
}

Specifically, this json should have a `thought` key, a `action` key and an `answer` key.

The `action` key should specify the $TOOL_NAME the name of the tool to use and the `tool_params` key should specify the parameters key as input to the tool.

Make sure to have the $TOOL_PARAMS as a list of dictionaries in the right format for the tool you are using, and do not put variable names as input if you can find the right values.

You should always think about one action to take, and have the `thought` key contain your thought process about this action.
If the tool responds, the tool will return an observation containing result of the action. 
... (this Thought/Action/Observation can repeat N times, you should take several steps when needed. The action key must only use a SINGLE tool at a time.)

You can use the result of the previous action as input for the next action.
The observation will always be the response from calling the tool: it can represent a file, like "image_1.jpg". You do not need to generate them, it will be provided to you. 
Then you can use it as input for the next action. You can do it for instance as follows:

Observation: "image_1.jpg"
{
    "thought": "I need to transform the image that I received in the previous observation to make it green.",
    "action": {
        "tool_name": "image_transformer",
        "tool_params": [{"name": "image"}, {"value": "image_1.jpg"}]
    },
    "answer": null
}


To provide the final answer to the task, use the `answer` key. It is the only way to complete the task, else you will be stuck on a loop. So your final output should look like this:
Observation: "your observation"

{
    "thought": "you thought process",
    "action": null,
    "answer": "insert your final answer here"
}

Here are a few examples using notional tools:
---
Task: "Generate an image of the oldest person in this document."

Your Response:
{
    "thought": "I will proceed step by step and use the following tools: `document_qa` to find the oldest person in the document, then `image_generator` to generate an image according to the answer.",
    "action": {
        "tool_name": "document_qa",
        "tool_params": [{"name": "document"}, {"value": "document.pdf"}, {"name": "question"}, {"value": "Who is the oldest person mentioned?"}]
    },
    "answer": null
}

Your Observation: "The oldest person in the document is John Doe, a 55 year old lumberjack living in Newfoundland."

Your Response:
{
    "thought": "I will now generate an image showcasing the oldest person.",
    "action": {
        "tool_name": "image_generator",
        "tool_params": [{"name": "prompt"}, {"value": "A portrait of John Doe, a 55-year-old man living in Canada."}]
    },
    "answer": null
}
Your Observation: "image.png"

{
    "thought": "I will now return the generated image.",
    "action": null,
    "answer": "image.png"
}

---
Task: "What is the result of the following operation: 5 + 3 + 1294.678?"

Your Response:
{
    "thought": "I will use python code evaluator to compute the result of the operation and then return the final answer using the `final_answer` tool",
    "action": {
        "tool_name": "python_interpreter",
        "tool_params": [{"name": "code"}, {"value": "5 + 3 + 1294.678"}]
    },
    "answer": null
}
Your Observation: 1302.678

{
    "thought": "Now that I know the result, I will now return it.",
    "action": null,
    "answer": 1302.678
}

---
Task: "Which city has the highest population , Guangzhou or Shanghai?"

Your Response:
{
    "thought": "I need to get the populations for both cities and compare them: I will use the tool `search` to get the population of both cities.",
    "action": {
        "tool_name": "search",
        "tool_params": [{"name": "query"}, {"value": "Population Guangzhou"}]
    },
    "answer": null
}
Your Observation: ['Guangzhou has a population of 15 million inhabitants as of 2021.']

Your Response:
{
    "thought": "Now let's get the population of Shanghai using the tool 'search'.",
    "action": {
        "tool_name": "search",
        "tool_params": [{"name": "query"}, {"value": "Population Shanghai"}]
    },
    "answer": null
}
Your Observation: "26 million (2019)"

Your Response:
{
    "thought": "Now I know that Shanghai has a larger population. Let's return the result.",
    "action": null,
    "answer": "Shanghai"
}

Above example were using notional tools that might not exist for you. You only have access to these tools:
<<tool_descriptions>>

Here are the rules you should always follow to solve your task:
1. ALWAYS answer in the JSON format with keys "thought", "action", "answer", else you will fail. 
2. Always use the right arguments for the tools. Never use variable names in the 'tool_params' field, use the value instead.
3. Call a tool only when needed: do not call the search agent if you do not need information, try to solve the task yourself.
4. Never re-do a tool call that you previously did with the exact same parameters.
5. Observations will be provided to you, no need to generate them

Now Begin! If you solve the task correctly, you will receive a reward of $1,000,000.
"""

class LLAMAReactSchema(BaseModel):
    thought: str
    action: Dict[str, Any]
    answer: Optional[Any] = None

    @classmethod
    def from_json(cls, json_str: str) -> 'LLAMAReactSchema':
        return cls.model_validate_json(json_str)
