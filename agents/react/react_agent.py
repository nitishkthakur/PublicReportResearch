import os
from dotenv import load_dotenv
import sys
import os.path as path
from pydantic import BaseModel, Field
from typing import List, Callable, Optional, Dict, Any
import react_prompts
# Add the parent agents directory to the path
sys.path.append(path.join(path.dirname(__file__), '..'))
# Add the rag directory to the path (go up two levels from agents/react/)
sys.path.append(path.join(path.dirname(__file__), '..', '..', 'rag'))
# Add the root directory to the path
sys.path.append(path.join(path.dirname(__file__), '..', '..'))

from rag.excel_rag import FinancialDataTools
from utils import undo_sec_quarterly_cumulative, process_sec_quarterly_data

from groq_agent import GroqAgent
GROQ_MODELS = ["meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.3-70b-versatile", "meta-llama/llama-4-maverick-17b-128e-instruct",
          "deepseek-r1-distill-llama-70b", "llama-3.3-70b-versatile", "qwen/qwen3-32b"]

class ReactStateGeneric(BaseModel):
    Task: str = Field(..., description="The main task or goal that the agent needs to accomplish")
    Action: str = Field(..., description="The specific action the agent will take in this iteration")
    Observation: Optional[str] = Field(None, description="The result or feedback from the previous action or tool call taken which will be useful for the next steps")
    Final: bool = Field(..., description="Whether this is the final iteration and the task is complete")
    CurrentIterationNumber: int = Field(..., description="The current iteration number in the ReAct cycle", ge=0)

class ReactStateBasic(BaseModel):
    Task: str = Field(..., description="The main task or goal that the agent needs to accomplish in this step")
    


    
financial_tools = FinancialDataTools("12_metrics.xlsx")
financial_tools.load_data()
tools_list = [financial_tools.compare_companies_metric, financial_tools.get_metric_trends, 
            financial_tools.get_metric_for_company_quarter_year]

# Configuration - Define your preferred agent provider and model here

bank_name_mapping = {'AMERICAN EXPRESS COMPANY': 'American Express',
    'Bank of America Corporation': 'Bank of America',
    'CAPITAL\xa0ONE\xa0FINANCIAL\xa0CORP': 'Capital One',
    'Citigroup\xa0Inc': 'Citi',
    'Fifth Third Bancorp': 'Fifth Third',
    'Huntington Bancshares Incorporated': 'Huntington Bank',
    'JPMorgan Chase & Co': 'JPMorgan Chase',
    'KeyCorp': 'KeyBank',
    'NORTHERN TRUST CORPORATION': 'Northern Trust',
    'PNC Financial Services Group, Inc.': 'PNC Bank',
    "People's United Financial, Inc.": 'Peoples United',
    'SCHWAB CHARLES CORP': 'Charles Schwab',
    'STATE STREET CORPORATION': 'State Street',
    'TEGNA INC.': 'Tegna',
    'THE BANK OF NEW YORK MELLON CORPORATION': 'BNY Mellon',
    'TRUIST FINANCIAL CORPORATION': 'Truist',
    'The Goldman Sachs Group, Inc.': 'Goldman Sachs',
    'US BANCORP \\DE\\': 'US Bancorp',
    'WELLS FARGO & COMPANY/MN': 'Wells Fargo'

}

financial_tools.df['CompanyName'] = financial_tools.df['CompanyName'].replace(bank_name_mapping)
financial_tools.df['CompanyName'] = financial_tools.df['CompanyName'].str.strip()
# Filter only jp morgan and citi
financial_tools.df = financial_tools.df[financial_tools.df['CompanyName'].isin(['JPMorgan Chase', 'Citi'])]

# Convert data to json
financial_tools.df_json = financial_tools.df.to_json(orient="records")

#financial_tools.df = process_sec_quarterly_data(financial_tools.df)
tools_list = [financial_tools.compare_companies_metric, financial_tools.get_metric_trends, 
            financial_tools.get_metric_for_company_quarter_year]


output_schema = ReactStateBasic

agent = GroqAgent(
    model_name=GROQ_MODELS[0],
    tools=[],
    output_schema=output_schema
)

class ReactAgent:
    def __init__(self, react_prompt, agent, model = "meta-llama/llama-4-maverick-17b-128e-instruct", max_iterations: int = 5):
        self.react_prompt = react_prompt
        self.agent = agent
        self.model = model
        self.max_iterations = max_iterations

    def invoke(self, task: str) -> Dict[str, Any]:
        print(f"🚀 ReactAgent started with task: {task[:100]}...")
        
        # Add the react prompt to conversation history of the agent
        self.react_prompt_populated = self.react_prompt.format(
            tools=", ".join([tool.__name__ for tool in self.agent.tools]),
            tool_names=", ".join([tool.__name__ for tool in self.agent.tools])
        )

        self.agent.conversation_history.append({"role": "system", "content": self.react_prompt_populated})
        print("📋 React prompt added to conversation history")

        # Initialize with the task
        current_input = f"Task: {task}\nIteration: 1"
        print(f"🔄 Starting ReAct loop with max {self.max_iterations} iterations")
        
        for iteration in range(self.max_iterations):
            print(f"\n--- Iteration {iteration + 1}/{self.max_iterations} ---")
            print(f"📝 Current input: {current_input[:150]}...")
            
            # Get response from agent
            print("🤖 Invoking agent...")
            agent = GroqAgent(
                    model_name=self.model,
                    tools=[],
                    output_schema=output_schema
                )
            response = agent.invoke(current_input)
            print("\n\n\n Response is: ", response, type(response), "\n\n\n")

            if response:
                print(f"Agent response received")
                if hasattr(response, 'Task'):
                    print(f"   Task: {getattr(response, 'Task', 'N/A')}")
                if hasattr(response, 'Action'):
                    print(f"   Action: {getattr(response, 'Action', 'N/A')}")
                if hasattr(response, 'Observation'):
                    obs = getattr(response, 'Observation', 'N/A')
                    print(f"   Observation: {obs[:100] if obs else 'None'}...")
                if hasattr(response, 'Final'):
                    print(f"   Final: {getattr(response, 'Final', 'N/A')}")
            else:
                print("❌ No response from agent")
            
            # Check if task is complete
            if hasattr(response, 'Final') and response.Final:
                print("🎯 Task marked as complete (Final=True)")
                return response
            
            # Prepare next iteration input with observation
            observation = getattr(response, 'Observation', '') or "No observation available"
            current_input = f"Previous action completed. Observation: {observation}\nIteration: {iteration + 2}"
            print(f"🔄 Preparing next iteration with observation")
        
        print("⏰ Max iterations reached, returning final response")
        return response
    

reactor = ReactAgent(react_prompt = react_prompts.custom_react_prompt, agent = agent)
print("🎬 Starting ReactAgent execution...")
result = reactor.invoke(f"How did Citi Bank do in Q1 2025 compared to JP Morgan ? Comment on the most important metrics and prepare a full report. Format your final answer in markdown. Here is the data {financial_tools.df_json}")
print("\n🏁 ReactAgent execution completed!")
print("📊 Final result:")
print(result)