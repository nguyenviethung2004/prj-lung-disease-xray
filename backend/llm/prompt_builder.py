from llm.llm_client import generate_groq_response
import asyncio
import json



def build_summary_prompt(history_str: str) -> str:
    
    if len(history_str) > 8000:
        history_str = history_str[-8000:]

    prompt = f"""
            You are an AI assistant that summarizes conversations between a user and a chatbot.

            Please read the conversation below and summarize it concisely and clearly.
            Automatically detect the language (Vietnamese or English) 
            and respond in the same language as the conversation.

            ---------------------
            {history_str}
            ---------------------

            Your summary should include:
            1. **Main topic** — what the user is asking about.
            2. **Key questions** — list the main questions from the user.
            3. **Important information provided** — key answers or facts from the assistant.
            4. **Context to remember** — any details useful for future questions.

            Keep the summary short (3–5 sentences), focusing only on essential information.
            """
    return prompt.strip()



def summarize_conversation(conversation_history: str):
    try:
        prompt = build_summary_prompt(conversation_history)
        summary = generate_groq_response(prompt)
        return summary.strip()
    except Exception as e:
        print("❌ Error summarizing conversation:", e)
        return "Unable to summarize this conversation."
    

async def build_answer_prompt(
    user_query,
    retrieved_context,
    conversation_summary=None,
    messages_recently=None,
    detected_language="English"
):
    context = retrieved_context.strip() if retrieved_context else "NO_CONTEXT"

    prompt = f"""
You are a medical AI assistant specializing in respiratory diseases.

ROLE:
- Explain respiratory/lung diseases using ONLY provided medical documents.
- Educational information only.
- You are NOT a doctor.

LANGUAGE:
- Detected language: {detected_language}
- Respond ONLY in {detected_language}
- Never mix languages
- Never output bilingual text
- Translate English medical context fully into {detected_language} when needed

SAFETY:
- Never diagnose definitively
- Never prescribe treatment
- For emergency symptoms (severe shortness of breath, chest pain, coughing blood):
  advise immediate medical attention

GROUNDING RULES (STRICT):
- Use ONLY facts explicitly present in Medical Context
- DO NOT use prior/internal medical knowledge
- DO NOT guess
- DO NOT infer missing facts
- DO NOT fabricate numbers
- DO NOT fabricate symptom lists
- DO NOT complete missing tables
- DO NOT reconstruct omitted images/figures
- If context is insufficient, say exactly:
"I don't have enough information in the provided documents to answer this."

USER QUESTION:
{user_query}

MEDICAL CONTEXT:
{context}

CONVERSATION SUMMARY:
{conversation_summary or "NONE"}

RECENT CHAT:
{messages_recently or "NONE"}

ANSWER FORMAT:
- concise
- structured
- bullet points preferred
- explain medical terms simply
- mention uncertainty if evidence is incomplete
- no markdown tables unless exact values exist in context

ANSWER:
"""
    return prompt.strip()

async def generate_answer(user_query, retrieved_context, conversation_summary=None, messages_recently=None, detected_language="English"):
    try:
        prompt = await build_answer_prompt(user_query, retrieved_context, conversation_summary, messages_recently, detected_language)
        response = await asyncio.to_thread(generate_groq_response, prompt)  
        return response.strip()
    except Exception as e:
        print("❌ Error while calling LLM:", e)
        return "Sorry, I'm unable to generate a response at the moment."


async def build_translate_query_prompt(user_query: str) -> str:
    prompt = f"""
        You are a language detection and translation assistant.
        Analyze the following text and determine if it is in "Vietnamese" or "English".
        Then, if it is in Vietnamese, translate it accurately to English. If it is already in English, return it exactly as it is without any translation.

        You MUST return your response as a valid JSON object in the exact format below, without any other text or markdown:
        {{
            "language": "Vietnamese" or "English",
            "english_query": "the translated or original english text"
        }}

        Text: "{user_query}"
    """
    return prompt.strip()

async def translate_query_to_english(user_query: str) -> tuple[str, str]:
    try:
        prompt = await build_translate_query_prompt(user_query)
        response_text = await asyncio.to_thread(generate_groq_response, prompt)
        
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned_text)
        
        language = data.get("language", data.get("Language", "English"))
        english_query = data.get("english_query", data.get("English_query", user_query))
        
        # Normalize language name
        if "viet" in language.lower():
            language = "Vietnamese"
        elif "eng" in language.lower():
            language = "English"
        else:
            language = "English" # Default fallback
            
        return language, english_query.strip()
    except Exception as e:
        print("❌ Error translating query:", e)
        return "Unknown", user_query    