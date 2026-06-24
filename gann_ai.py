import os
import google.generativeai as genai
from pathlib import Path

env_path = Path(".env")
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
# Load System Prompt
SKILL_PATH = Path("stock_analyzer_skill.md")
SYSTEM_PROMPT = ""
if SKILL_PATH.exists():
    SYSTEM_PROMPT = SKILL_PATH.read_text(encoding="utf-8")

def generate_fundamental_analysis(symbol: str, company_name: str, query: str) -> str:
    """
    Calls Gemini API with the Stock Analyzer Skill system prompt.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Error: GEMINI_API_KEY environment variable is not set. Please set it to use the AI Fundamental Analyzer."

    try:
        genai.configure(api_key=api_key)
        
        # Determine if it's a Deep Dive request to inject the template
        user_prompt = f"Target Stock: {symbol} ({company_name})\n\nUser Request: {query}"
        
        if "deep dive" in query.lower() or "detailed" in query.lower():
            template_path = Path("assets/deep-dive-template.html")
            if template_path.exists():
                template = template_path.read_text(encoding="utf-8")
                user_prompt += f"\n\nFor Deep Dive, output ONLY the HTML using this template:\n{template}"

        # Initialize the model with system instruction
        model = genai.GenerativeModel(
            model_name='gemini-2.5-pro',
            system_instruction=SYSTEM_PROMPT
        )
        
        # We can enable Google Search grounding for live data
        response = model.generate_content(
            user_prompt,
            tools='google_search_retrieval'
        )
        
        return response.text
    except Exception as e:
        return f"Error communicating with Gemini AI: {str(e)}"
