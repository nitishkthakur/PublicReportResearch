from langchain.agents import initialize_agent, AgentType
from langchain.prompts import load_prompt
from langchain_community.chat_models import ChatOpenAI, ChatOllama
from typing import List, Optional, Literal
import importlib

class ReActAgent:
    def __init__(
        self,
        tools: Optional[List] = None,
        llm: Optional[object] = None,
        prompt: Optional[str] = None,
        prompt_from_hub: Optional[str] = None,
        output_format: Literal["markdown", "html"] = "markdown"
    ):
        """
        Initialize a ReAct agent with tool binding, LLM selection, and prompt configuration.

        Args:
            tools: List of LangChain tool objects to bind to the agent.
            llm: ChatOllama or ChatOpenAI object from langchain_community.chat_models.
            prompt: Custom prompt string (default: react_prompt_meta from prompts.py).
            prompt_from_hub: If provided, loads prompt from LangChain's prompt hub.
            output_format: Output format for answers ("markdown" or "html").
        """
        # Load default prompt if not provided
        if prompt_from_hub:
            self.prompt = load_prompt(prompt_from_hub)
        else:
            if prompt is None:
                prompts_mod = importlib.import_module("prompts")
                self.prompt = getattr(prompts_mod, "react_prompt_meta")
            else:
                self.prompt = prompt

        self.llm = llm
        self.tools = tools or []
        self.output_format = output_format
        self.agent = None

    def bind_tools(self, tools: List):
        """Bind a new list of tools to the agent."""
        self.tools = tools

    def set_output_format(self, fmt: Literal["markdown", "html"]):
        """Set the output format for answers."""
        self.output_format = fmt

    def set_llm(self, llm: object):
        """
        Set the LLM backend to use (should be a ChatOllama or ChatOpenAI object).
        """
        self.llm = llm
        self.agent = None  # Reset agent so it can be re-initialized with new LLM

    def initialize(self):
        """Initialize the LangChain agent with current settings."""
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.REACT_DESCRIPTION,
            verbose=True,
            agent_kwargs={"system_message": self.prompt}
        )

    def run(self, input_text: str):
        """Run the agent on the given input and return the output in the selected format."""
        if self.agent is None:
            self.initialize()
        result = self.agent.run(input_text)
        if self.output_format == "html":
            # Simple conversion, can be customized
            return f"<div>{result}</div>"
        return result
