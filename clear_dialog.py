from core.request import clear_user_context_api
from core.settings import USER_ID, BASE_SERVER_URL, PASSWORD
import json

clear_result_correct_pass = clear_user_context_api(
    base_url=BASE_SERVER_URL, 
    user_id=USER_ID, 
    password=PASSWORD)

if clear_result_correct_pass:
    print("Результат очистки контекста:")
    print(json.dumps(clear_result_correct_pass, indent=2, ensure_ascii=False))
else:
    print("Очистка контекста не удалась или произошла ошибка.")
