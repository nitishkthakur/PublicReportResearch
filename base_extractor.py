import os
from typing import Dict, Any
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain import hub

# os.environ["OPENAI_API_KEY"] = "your-api-key-here"

class SimpleMetricExtractor:
    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model_name, temperature=0)
        self.tools = self._create_tools()
        self.agent = self._create_agent()
        
    def _create_tools(self):
        @tool
        def load_pdf_content(file_path: str) -> str:
            """Load PDF content from file path and return as string"""
            try:
                # Replace with your actual PDF loading implementation
                return f"PDF content loaded from {file_path}. This contains the earnings report text."
            except Exception as e:
                return f"Error loading PDF: {str(e)}"
        
        @tool  
        def extract_specific_metric(text: str, metric_name: str) -> str:
            """Extract a specific financial metric from the earnings report text using LLM"""
            
            prompt_text = f"""
            You are a financial analyst. Extract the specific metric requested from this earnings report.
            
            METRIC TO FIND: {metric_name}
            
            EARNINGS REPORT TEXT:
            {text}
            
            INSTRUCTIONS:
            1. Find the exact value for "{metric_name}" in the text
            2. Include the numerical value with units (millions, billions, %, etc.)
            3. If found, also include any period comparison (YoY, QoQ)
            4. If not found, return "Metric not found in document"
            5. Be precise and include context if helpful
            
            Return format: "Metric: [value] [additional context if relevant]"
            """
            
            try:
                response = self.llm.invoke(prompt_text)
                return response.content
            except Exception as e:
                return f"Extraction failed: {str(e)}"
        
        return [load_pdf_content, extract_specific_metric]
    
    def _create_agent(self):
        prompt = hub.pull("hwchase17/react")
        agent = create_react_agent(self.llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent, 
            tools=self.tools, 
            verbose=True, 
            max_iterations=5
        )
    
    def extract_metric(self, pdf_file_path: str, metric_name: str, bank_name: str = "") -> Dict[str, Any]:
        """
        Extract a specific metric from a bank's earnings report
        
        Args:
            pdf_file_path (str): Path to the PDF earnings report
            metric_name (str): Name of the metric to extract (e.g., "Net Interest Income", "ROE", "EPS")
            bank_name (str): Name of the bank (optional)
            
        Returns:
            Dict with extraction results
        """
        
        query = f"""
        Extract the metric "{metric_name}" from {bank_name}'s earnings report.
        
        Steps:
        1. Load the PDF content from: {pdf_file_path}
        2. Extract the specific metric "{metric_name}" from the loaded content
        
        Focus on finding the exact value with proper context.
        """
        
        try:
            result = self.agent.invoke({"input": query})
            return {
                "success": True,
                "bank_name": bank_name,
                "metric_requested": metric_name,
                "result": result.get("output", ""),
                "file_path": pdf_file_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "bank_name": bank_name,
                "metric_requested": metric_name,
                "file_path": pdf_file_path
            }

# Example usage
def main():
    extractor = SimpleMetricExtractor()
    
    # User specifies what metric they want
    metrics_to_extract = [
        "Net Interest Income",
        "Return on Equity", 
        "Earnings Per Share",
        "Tier 1 Capital Ratio",
        "Net Income"
    ]
    
    pdf_path = "./reports/jpmorgan_q4_2024_earnings.pdf"
    bank = "JPMorgan Chase"
    
    print(f"🏦 Extracting metrics from {bank}'s earnings report\n")
    
    for metric in metrics_to_extract:
        print(f"🔍 Extracting: {metric}")
        result = extractor.extract_metric(pdf_path, metric, bank)
        
        if result["success"]:
            print(f"✅ {result['result']}")
        else:
            print(f"❌ Failed: {result['error']}")
        print("-" * 50)

if __name__ == "__main__":
    main()
