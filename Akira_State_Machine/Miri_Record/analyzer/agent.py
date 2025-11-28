from openai import OpenAI

client = OpenAI(
    api_key="",
    base_url="",
)

def chat_with_agent(messages, model="gpt-5-chat-latest"):
    """
    与大模型agent对话。
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
    返回：模型回复内容字符串
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content.strip()

