from openai import OpenAI

client = OpenAI(
  api_key="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"
)

response = client.responses.create(
  model="gpt-4o-mini",
  input="write a haiku about ai",
  store=True,
)

print(response.output_text)
