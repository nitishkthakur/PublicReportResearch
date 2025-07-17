from basic_ollama_agent_with_post import OllamaAgent
from excel_rag import FinancialDataTools
from basic_openai_agent import OpenAIAgent


financial_tools = FinancialDataTools("12_metrics.xlsx")
financial_tools.load_data()
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

tools_list = [financial_tools.compare_companies_metric, financial_tools.get_metric_trends, 
              financial_tools.get_metric_for_company_quarter_year]

class FinancialRAGAgent:
    def __init__(self, model_name: str, agent_provider: str = "openai"):
        """
        Initialize the Financial RAG Agent.
        
        Args:
            model_name: Name of the model to use
            agent_provider: Either "openai" or "ollama" to specify which agent to use
        """
        self.model_name = model_name
        self.agent_provider = agent_provider.lower()
        self.df = financial_tools.df
        
        # Initialize the appropriate agent based on provider
        if self.agent_provider == "openai":
            self.agent = OpenAIAgent(
                model_name=self.model_name,
                tools=tools_list,
                output_schema=None
            )
        elif self.agent_provider == "ollama":
            self.agent = OllamaAgent(
                model_name=self.model_name,
                tools=tools_list,
                output_schema=None
            )
        else:
            raise ValueError(f"Unsupported agent provider: {agent_provider}. Choose 'openai' or 'ollama'.")

    def run_question(self, question: str):
        role = "You are an expert Earnings Data Extractor and Analyzer. "
        task = "Call the appropriate functions to extract the earnings data from the DataFrame and analyze it for the companies mentioned.\n"
        context_company_names = (
            "\nWhen the user asks to search for a company, try to map their mentioned name to a list of pre-defined companies. "
            "The allowed company names are as follows :" + f"{', '.join(self.df['CompanyName'].unique().tolist())}" + "\n"
        )
        Context = "\nHere are the metrics present in the data:" + f"{', '.join(self.df.columns.tolist()[2:])}" + ""
        first_prompt = role + task + context_company_names + Context + question
        overall_prompt = (
            "You are a helpful assistant that provides answers based on user queries. "
            "You will be provided with the conversation to follow which might consist of answers from a tool call. "
            "If any information you need is not present in the following conversation, you mention so."
        )
        second_prompt = "Now, write the final answer to the user questions based on the above conversation"

        result = self.agent.invoke_plus_next_call(
            first_prompt=first_prompt,
            second_prompt=second_prompt,
            overall_task_prompt=overall_prompt
        )
        return result


if __name__ == "__main__":
    # Configuration - Define your preferred agent provider and model here
    agent_provider = "openai"  # Choose: "openai" or "ollama"
    
    # Model selection based on provider
    if agent_provider == "openai":
        model_name = "gpt-4o-mini"  # Options: "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"
    else:  # ollama
        model_name = "qwen3:8b-q8_0"  # Options: "qwen3:8b-q8_0", "llama3:8b", "gemma2:9b"
    
    print(f"Using {agent_provider.upper()} agent with model: {model_name}")
    
    # Initialize the agent
    agent = FinancialRAGAgent(model_name=model_name, agent_provider=agent_provider)
    
    # Get user question
    print("\nExample questions:")
    print("- Compare Citi and Wells Fargo on some important metrics for the last few years")
    print("- What was JPMorgan Chase's revenue trend over the last 5 years?")
    print("- Show me Bank of America's total assets for Q1 2023")
    
    question = input("\nEnter your financial data question: ").strip()
    if not question:
        question = "Compare Citi and Wells Fargo on some important metrics for the last few years. Prepare a report for the same"
        print(f"Using default question: {question}")
    
    print(f"\nProcessing your question using {agent_provider.upper()} agent...")
    result = agent.run_question(question)
    
    print("\n" + "="*80)
    print("FINAL ANSWER:")
    print("="*80)
    print(result.get("final_message", "No final answer found."))
    
    print("\n" + "="*80)
    print("DETAILED RESULT:")
    print("="*80)
    print(result)

    '''# Use agent on 2 calls
    # Constructing the first prompt
    df = financial_tools.df
    role = "You are an expert Earnings Data Extractor and Analyzer. " 
    task = "Call the appropriate functions to extract the earnings data from the DataFrame and analyze it for the companies mentioned.\n"
    context_company_names = "\nWhen the user asks to search for a company, try to map their mentioned name to a list of pre-defined companies. The allowed company names are as follows :" + f"{', '.join(df['CompanyName'].unique().tolist())}" + "\n"
    Context = "\nHere are the metrics present in the data:" + f"{', '.join(df.columns.tolist()[2:])}" + ""
    question = "Compare Citi and Wells Fargo on their total revenue. Also, let me know the trend of revenue for Citi in the last 5 years. Finally, what was the revenue for Citi in Q1 2023?"
    question = "Compare Citi and Wells Fargo on some important metrics for the last few years. Prepare a report for the same"

    first_prompt = role + task + context_company_names + Context + question
    overall_prompt = "You are a helpful assistant that provides answers based on user queries. You will be provided with the conversation to follow which might consist of answers from a tool call. If any information you need is not present in the following conversation, you mention so."
    second_prompt = "Now, write the final answer to the user questions based on the above conversation"

    result = agent.invoke_plus_next_call(
        first_prompt=first_prompt,
        second_prompt=second_prompt,
        overall_task_prompt=overall_prompt
    )


    
    print(result, "\n\n\n\n")
    print(result.get("final_message", "No final answer found."))'''


