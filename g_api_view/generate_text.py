from .core.request import send_request_to_gemini_api
from .core.settings import USER_ID, PASSWORD, GENERATE_ENDPOINT_URL
import json

def main():
    flag_search_generate = False
    system_instruction_generate = ""
    model_name = "Gemini 2 Flash"

    message_text_generate = "напиши историю про МАшу"
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
        return generate_result.get("answer")
    else:
        print("/generate не удался или произошла ошибка.")
        if generate_result: 
            print(json.dumps(generate_result, indent=2, ensure_ascii=False))

def generate(
    message_text: str,
    file_paths: list = None,
    flag_search: bool = False,
    system_instruction: str = "",
    model_name: str = "Gemini 2 Flash"
) -> dict:
    """Генерирует ответ с помощью Gemini API.
    
    Args:
        message_text: Текст сообщения для обработки
        file_paths: Список путей к файлам (по умолчанию [])
        flag_search: Флаг поиска (по умолчанию False)
        system_instruction: Системная инструкция (по умолчанию "")
        model_name: Название модели (по умолчанию "Gemini 2 Flash")
    
    Returns:
        Ответ от API в виде словаря
    """
    if file_paths is None:
        file_paths = []
        
    return send_request_to_gemini_api(
        server_url=GENERATE_ENDPOINT_URL,
        user_id=USER_ID,
        password=PASSWORD,
        model_name=model_name,
        text=message_text,
        system_instruction=system_instruction,
        flag_search=flag_search,
        file_paths=file_paths
    )

if __name__ == '__main__':
    main()