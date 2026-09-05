from src.ai.llm import llm


response = llm.invoke(
    "Explain in one sentence what a stock candlestick represents."
)

print(response.content)