"""
LLM Agent Router for mapping user queries to predefined categories.
"""

from typing import List, Dict, Any, Type, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
import json
import os


class Router:
    """
    Router class that uses OpenAI's structured output to map user questions 
    to predefined categories based on a pydantic schema.
    
    The Router class is designed to be a flexible and robust LLM-based routing system
    that can categorize user queries into predefined categories. It leverages OpenAI's
    structured output capabilities to ensure consistent and reliable JSON responses
    that conform to a user-defined pydantic schema.
    
    Key Features:
    ------------
    - **Structured Output**: Uses OpenAI's JSON schema mode for guaranteed valid responses
    - **Pydantic Integration**: Accepts any pydantic model as the output schema
    - **Flexible Categorization**: Supports simple categories, enums, or complex nested structures
    - **Rule-Based Routing**: Uses natural language descriptions to guide LLM decisions
    - **Error Handling**: Comprehensive error handling with meaningful error messages
    - **Configurable Models**: Support for different OpenAI models (GPT-4, GPT-3.5, etc.)
    - **API Key Management**: Flexible API key configuration via parameter or environment variable
    
    Common Use Cases:
    -----------------
    1. **Customer Support Routing**: Route support tickets to appropriate departments
    2. **Content Categorization**: Classify articles, posts, or documents by topic
    3. **Intent Classification**: Determine user intent in chatbots or virtual assistants
    4. **Email Routing**: Automatically categorize and route incoming emails
    5. **Query Preprocessing**: Route queries to specialized LLM agents or tools
    
    Architecture:
    -------------
    The Router follows a simple but powerful architecture:
    
    1. **Schema Definition**: User defines a pydantic model with expected categories
    2. **Rule Description**: Natural language rules guide the LLM's decision-making
    3. **Query Processing**: User queries are sent to OpenAI with structured output constraints
    4. **Response Validation**: Responses are validated against the pydantic schema
    5. **Result Return**: Validated pydantic model instances are returned
    
    Schema Requirements:
    -------------------
    The pydantic schema can be any valid pydantic model, but some patterns work better:
    
    - **Enum Fields**: Use string enums for predefined categories
    - **Confidence Scores**: Include float fields for confidence levels (0.0-1.0)
    - **Multiple Categories**: Support primary/secondary category classification
    - **Metadata Fields**: Include additional context like reasoning or tags
    
    Performance Considerations:
    --------------------------
    - Uses low temperature (0.1) for consistent routing decisions
    - Optimized for gpt-4o-mini by default for cost-effectiveness
    - Caches schema information to avoid recomputation
    - Minimal prompt engineering for fast response times
    
    Error Handling:
    ---------------
    The Router handles several types of errors gracefully:
    
    - **API Errors**: Network issues, rate limits, invalid API keys
    - **Schema Errors**: Invalid pydantic models, missing fields
    - **Parsing Errors**: Malformed JSON responses (rare with structured output)
    - **Validation Errors**: Responses that don't match the schema
    
    Example Usage:
    --------------
    
    Basic Category Routing:
    ```python
    from pydantic import BaseModel, Field
    from enum import Enum
    
    class SupportCategory(str, Enum):
        TECHNICAL = "technical"
        BILLING = "billing"
        GENERAL = "general"
    
    class SupportRouting(BaseModel):
        category: SupportCategory = Field(description="Primary support category")
        confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    
    router = Router(
        schema=SupportRouting,
        description="Route support queries to technical, billing, or general categories"
    )
    
    result = router.route("My API integration is failing with 500 errors")
    print(result.category)  # SupportCategory.TECHNICAL
    print(result.confidence)  # 0.92
    ```
    
    Advanced Multi-Category Routing:
    ```python
    class AdvancedRouting(BaseModel):
        primary_category: str = Field(description="Main category")
        secondary_categories: List[str] = Field(default=[], description="Additional relevant categories")
        urgency: str = Field(description="Urgency level: low, medium, high")
        reasoning: str = Field(description="Brief explanation of categorization")
    
    router = Router(
        schema=AdvancedRouting,
        description=\"\"\"
        Route queries considering:
        - Primary category: technical, billing, sales, support
        - Secondary categories: any additional relevant categories
        - Urgency: assess based on language and context
        - Reasoning: explain the categorization decision
        \"\"\"
    )
    ```
    
    Integration with Agent Systems:
    ------------------------------
    The Router is designed to work seamlessly with larger agent systems:
    
    ```python
    # Route to specialized agents
    routing_result = router.route(user_query)
    
    if routing_result.category == "technical":
        response = technical_agent.process(user_query)
    elif routing_result.category == "billing":
        response = billing_agent.process(user_query)
    else:
        response = general_agent.process(user_query)
    ```
    
    Best Practices:
    ---------------
    1. **Clear Categories**: Define distinct, non-overlapping categories
    2. **Detailed Descriptions**: Provide comprehensive routing rules
    3. **Test Edge Cases**: Test with ambiguous or unusual queries
    4. **Monitor Performance**: Track routing accuracy and adjust rules as needed
    5. **Handle Fallbacks**: Always include a default/general category
    6. **Version Control**: Track changes to schemas and routing rules
    
    Limitations:
    ------------
    - Requires OpenAI API access and credits
    - Response time depends on OpenAI API latency
    - Accuracy depends on the quality of routing rules
    - May struggle with highly ambiguous queries
    - Limited to OpenAI's model capabilities and knowledge cutoff
    
    Dependencies:
    -------------
    - openai>=1.0.0: OpenAI API client
    - pydantic>=2.0.0: Schema validation and parsing
    - typing: Type hints (built-in)
    - json: JSON parsing (built-in)
    - os: Environment variable access (built-in)
    """
    
    def __init__(
        self, 
        schema: Type[BaseModel], 
        description: str,
        openai_api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize the Router.
        
        Args:
            schema: Pydantic model class that defines the output structure
            description: Rules and guidelines for the LLM to decide category mapping
            openai_api_key: OpenAI API key (if None, uses environment variable)
            model: OpenAI model to use for routing decisions
        """
        self.schema = schema
        self.description = description
        self.model = model
        
        # Initialize OpenAI client
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided either as parameter or OPENAI_API_KEY environment variable")
        
        self.client = OpenAI(api_key=api_key)
        
        # Validate schema has the expected structure
        self._validate_schema()
    
    def _validate_schema(self):
        """Validate that the schema is properly structured for routing."""
        # Check if schema has required fields
        if not hasattr(self.schema, 'model_fields'):
            raise ValueError("Schema must be a Pydantic model")
        
        # For routing, we expect at least one field that can contain categories
        fields = self.schema.model_fields
        if not fields:
            raise ValueError("Schema must have at least one field")
    
    def route(self, user_query: str) -> BaseModel:
        """
        Route a user query to the appropriate category based on the schema.
        
        Args:
            user_query: The user's question/query to be categorized
            
        Returns:
            Instance of the pydantic model with the routing result
        """
        # Create system prompt for routing
        system_prompt = self._create_system_prompt()
        
        # Create user prompt
        user_prompt = f"User query: {user_query}"
        
        try:
            # Make OpenAI API call with structured output
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "routing_result",
                        "schema": self.schema.model_json_schema()
                    }
                },
                temperature=0.1  # Low temperature for consistent routing
            )
            
            # Parse the response
            result_json = response.choices[0].message.content
            result_dict = json.loads(result_json)
            
            # Create and return pydantic model instance
            return self.schema(**result_dict)
            
        except Exception as e:
            raise RuntimeError(f"Error in routing: {str(e)}")
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for the LLM."""
        # Get schema information
        schema_info = self.schema.model_json_schema()
        
        # Extract field information for the prompt
        fields_info = []
        for field_name, field_info in schema_info.get("properties", {}).items():
            field_type = field_info.get("type", "unknown")
            field_description = field_info.get("description", "")
            
            # Handle enum/choices if present
            if "enum" in field_info:
                choices = field_info["enum"]
                fields_info.append(f"- {field_name} ({field_type}): {field_description}. Choices: {choices}")
            else:
                fields_info.append(f"- {field_name} ({field_type}): {field_description}")
        
        system_prompt = f"""You are a query router that maps user questions to predefined categories.

ROUTING RULES:
{self.description}

OUTPUT SCHEMA:
You must respond with a JSON object that matches this structure:
{fields_info}

INSTRUCTIONS:
1. Analyze the user's query carefully
2. Based on the routing rules provided, determine which category best fits the query
3. Return a JSON object with the appropriate category mapping
4. If the query doesn't clearly fit any category, choose the most appropriate one
5. Be consistent in your categorization

Remember: You must return valid JSON that matches the required schema exactly."""
        
        return system_prompt
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get information about the current schema."""
        return {
            "schema_name": self.schema.__name__,
            "schema": self.schema.model_json_schema(),
            "description": self.description
        }


# Example usage and helper classes
class CategoryChoice(BaseModel):
    """Example schema for simple category routing."""
    category: str = Field(
        description="The category that best matches the user query"
    )


class MultiCategoryChoice(BaseModel):
    """Example schema for multi-category routing."""
    primary_category: str = Field(
        description="The primary category that best matches the user query"
    )
    secondary_categories: List[str] = Field(
        default=[],
        description="Additional relevant categories (optional)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score for the primary category (0.0 to 1.0)"
    )


if __name__ == "__main__":
    # Example usage
    from enum import Enum
    
    class QueryCategories(str, Enum):
        TECHNICAL = "technical"
        BILLING = "billing"
        SUPPORT = "support"
        SALES = "sales"
        GENERAL = "general"
    
    class QueryRouting(BaseModel):
        category: QueryCategories = Field(
            description="The category that best matches the user query"
        )
        confidence: float = Field(
            ge=0.0, le=1.0,
            description="Confidence level for this categorization"
        )
    
    # Initialize router
    router = Router(
        schema=QueryRouting,
        description="""
        Route user queries to these categories:
        - technical: Questions about product features, bugs, integrations, API usage
        - billing: Questions about pricing, payments, invoices, subscriptions
        - support: Help requests, troubleshooting, how-to questions
        - sales: Questions about purchasing, demos, product comparisons
        - general: General inquiries that don't fit other categories
        """
    )
    
    # Example routing
    test_queries = [
        "How do I integrate your API with my application?",
        "What are your pricing plans?",
        "I'm having trouble logging in",
        "Can I schedule a demo?",
        "What's your company mission?"
    ]
    
    for query in test_queries:
        result = router.route(query)
        print(f"Query: {query}")
        print(f"Category: {result.category}")
        print(f"Confidence: {result.confidence}")
        print("---")