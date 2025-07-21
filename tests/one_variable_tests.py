import sys
import os
import json
# Add the parent directory to the Python path to import from agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import agent classes
from agents.groq_agent import GroqAgent
from agents.basic_openai_agent import OpenAIAgent
from agents.agent_openrouter import OpenRouterAgent
from pydantic import BaseModel
from typing import Dict


def main():
    # Define the Possible options for variables
    # Quarter years in the format of 1Q2025 for last 5 years
    quarters_year = [f"{i}Q{year}" for year in range(2025, 2020, -1) for i in range(1, 5)]
    print("Possible quarter years:", quarters_year)

    # Possible Companies: 
    possible_companies = ["Citi", "JPMC", "Goldman Sachs", "Bank of America", "Wells Fargo"]
    print("Possible companies:", possible_companies)

    # Possible Metrics: 
    possible_metrics = ["Total Revenue", "Net Income", "EPS", "Assets", "Liabilities", "Net Revenue", "Operating Income", "Net Interest Income", "Non-Interest Income"]
    print("Possible metrics:", possible_metrics)

    # Start designing the prompt
    role = "You are an Expert Finance Analyst who excels in constructing questions based on variables which to base the question on"
    task = "Construct a finance question based on Finance metrics for a particular company, metric, quarterYear based on the provided variables."
    instructions_one_var_test = """Here are the values that the allowed variables are allowed to take:
    Company: {possible_companies}
    Metric: {possible_metrics}
    Quarter Year: {quarters_year}

    Now, combine these variables to construct a question. you can change the values mentioned slightly but not largely. 
    For example, Revenue can become Rev. Wells Fargo can become Wells. Let the questions have some variation in phrasing. 
    
    Some examples:
    1. How did JPMC perform in terms of Revenue in 1Q2025?
    2. Can you tell me the Earnings per share of Goldman Sachs for 3Q2023?
    3. How did Wells fare in Assets in 4Q2022?
    4. What are the Liabilities of Wells in 1Q2021?

    Provide 50 such questions in JSON format with the keys as question1, question2, ..., question25.
    """

    instructions_multiple_metrics_test = """Here are the values that the allowed variables are allowed to take:
    Company: {possible_companies}
    Metric: {possible_metrics}
    Quarter Year: {quarters_year}

    Now, combine these variables to construct a question. you can change the values mentioned slightly but not largely. 
    For example, Revenue can become Rev. Wells Fargo can become Wells. Let the questions have some variation in phrasing. 
    In each question that you make, use at least 2 metrics or/and 2 companies or/and 2 quarters. Try a mix. Sometimes, include multiple companies, metrics and quarters in the same question sometimes. 
    If using 2 Quarters, prefer for the quarters to be either consecutive or exactly one year apart.
    Some examples:
    1. How did JPMC and Citi perform in terms of Revenue in 1Q2025?
    2. Can you compare the Earnings per share, Revenue of Goldman Sachs vs Wells for 3Q2023?
    3. How did Wells fare in Assets in 4Q2022 compared to JPMC?
    4. What are the Liabilities of Wells in 1Q2021? Did it perform better than Citi and JPMorgan?

    Provide 50 such questions in JSON format with the keys as question1, question2, ..., question25.
    """
    prompt_one_var_test = f"{role}\n\n{task}\n\n{instructions_one_var_test.format(possible_companies=possible_companies, possible_metrics=possible_metrics, quarters_year=quarters_year)}"
    prompt_multi_metrics_test = f"{role}\n\n{task}\n\n{instructions_multiple_metrics_test.format(possible_companies=possible_companies, possible_metrics=possible_metrics, quarters_year=quarters_year)}"

    # Write the Pydantic model for the output schema - for 50 Questions
    class FinanceQuestions(BaseModel):
        question1: str
        question2: str
        question3: str
        question4: str
        question5: str
        question6: str
        question7: str
        question8: str
        question9: str
        question10: str
        question11: str
        question12: str
        question13: str
        question14: str
        question15: str
        question16: str
        question17: str
        question18: str
        question19: str
        question20: str
        question21: str
        question22: str
        question23: str
        question24: str
        question25: str
        question26: str
        question27: str
        question28: str
        question29: str
        question30: str
        question31: str
        question32: str
        question33: str
        question34: str
        question35: str
        question36: str
        question37: str
        question38: str
        question39: str
        question40: str
        question41: str
        question42: str
        question43: str
        question44: str
        question45: str
        question46: str
        question47: str
        question48: str
        question49: str
        question50: str

    # Instantiate the agent with the model and tools (if any)
    '''agent = OpenAIAgent(
        model_name="gpt-4.1-mini",
        tools=[],
        output_schema=FinanceQuestions
    )   '''    

    # Define the Groq Agent
    agent = GroqAgent(
        model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
        tools=[],
        output_schema=FinanceQuestions
    )
    # Invoke the agent with the prompt
    print("Invoking agent with prompt...")
    result_one_var = agent.invoke(prompt_one_var_test)
    result_multi_var = agent.invoke(prompt_multi_metrics_test)
    print("Raw Result (one Var):", result_one_var, type(result_one_var), "\n\n\n")
    print("Raw Result (multi Var):", result_multi_var, type(result_multi_var))

    # Save structured output as json

    if 'structured_output' in result_one_var:
        # Convert Pydantic model to dict for JSON serialization
        structured_data = result_one_var['structured_output'].model_dump()
        with open("finance_questions_structured_one_var.json", "w") as f:
            json.dump(structured_data, f, indent=4)
        print("Structured output saved to finance_questions_result_one_var.json")

    if 'structured_output' in result_multi_var:
        # Convert Pydantic model to dict for JSON serialization
        structured_data = result_multi_var['structured_output'].model_dump()
        with open("finance_questions_structured_result_multi_var.json", "w") as f:
            json.dump(structured_data, f, indent=4)
        print("Structured output saved to finance_questions_result_multi_var.json")

if __name__ == "__main__":
    main()