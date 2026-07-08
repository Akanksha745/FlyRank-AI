import os
import json
import pydantic
from typing import List, Dict, Any, Callable
from pydantic import BaseModel, Field
import psycopg2
from anthropic import Anthropic
from portkey_ai import Portkey  # <-- Fixed: Removed the missing config import

# 1. GATEWAY INTEGRATION (Example 6)
portkey = Portkey(
    api_key=os.environ.get("PORTKEY_API_KEY"),
    virtual_key=os.environ.get("PORTKEY_VIRTUAL_KEY"),
    metadata={"user_id": "usr_9481", "tenant": "enterprise_alpha"}
)
client = Anthropic(api_key="dummy")
# 2. DATA / TOOL CONTEXT & FACTORY (Example 2)
class ToolContext:
    def __init__(self, db_conn):
        self.db_conn = db_conn

def create_sql_tool(context: ToolContext) -> Callable:
    def execute_sql(query: str) -> List[Dict[str, Any]]:
        cursor = context.db_conn.cursor()
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    return execute_sql

# 3. GUARDRAIL (Example 5)
def validate_and_sanitize_sql(query: str) -> str:
    denylist = ["drop", "delete", "truncate", "update", "insert", "grant", "alter"]
    stripped_query = " ".join(query.lower().split())
    
    for word in denylist:
        if f" {word} " in f" {stripped_query} " or stripped_query.startswith(word):
            raise ValueError(f"Security Violated: Operation '{word}' is blocked by guardrails.")
    return query

# 4. STRUCTURED OUTPUT & WORKFLOW (Example 3)
class AgentDecision(BaseModel):
    plan: str = Field(description="Step-by-step logic")
    query: str = Field(description="The SQL query to execute")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")

def run_agent_workflow(user_prompt: str, db_connection) -> Dict[str, Any]:
    context = ToolContext(db_connection)
    tool_registry = {"execute_sql": create_sql_tool(context)}
    model_name = os.environ.get("AI_MODEL", "claude-3-5-sonnet-20241022")
    
    try:
        message = client.messages.create(
            model=model_name,
            max_tokens=1024,
            system="You are a data analyst. You must emit your plan and SQL as valid JSON.",
            messages=[{"role": "user", "content": user_prompt}],
            tools=[{
                "name": "execute_sql",
                "description": "Execute read-only queries over the local database",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query to run"}
                    },
                    "required": ["query"]
                }
            }]
        )
        
        tool_use = next((block for block in message.content if block.type == "tool_use"), None)
        if tool_use:
            unsafe_query = tool_use.input["query"]
            safe_query = validate_and_sanitize_sql(unsafe_query)
            result = tool_registry["execute_sql"](query=safe_query)
            return {"status": "success", "data": result}
        else:
            return {"status": "success", "text": message.content.text}
            
    except ValueError as e:
        return {"status": "error", "reason": str(e)}
    except Exception as e:
        return {"status": "error", "reason": f"System Failure: {str(e)}"}
