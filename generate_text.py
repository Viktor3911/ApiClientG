from core.request import send_request_to_gemini_api
from core.settings import USER_ID, PASSWORD, GENERATE_ENDPOINT_URL
import json

flag_search_generate = False
system_instruction_generate = ""
model_name = "Gemini 2 Flash"

message_text_generate = "привет, ты кто"
file_paths_generate = []

generate_result = send_request_to_gemini_api(
    server_url=GENERATE_ENDPOINT_URL, 
    user_id=USER_ID, 
    password=PASSWORD,
    model_name=model_name,
    text=message_text_generate, 
    system_instruction=system_instruction_generate, 
    flag_search=flag_search_generate, 
    file_paths=file_paths_generate
)

if generate_result and generate_result.get("answer"):
    print("Результат /generate:")
    print(json.dumps(generate_result, indent=2, ensure_ascii=False))
else:
    print("/generate не удался или произошла ошибка.")
    if generate_result: 
        print(json.dumps(generate_result, indent=2, ensure_ascii=False))
