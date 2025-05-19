from .core.request import register_user_api
from .core.settings import USER_ID, BASE_SERVER_URL, PASSWORD
import json

def main():
    registration_result = register_user_api(base_url=BASE_SERVER_URL, user_id=USER_ID, password=PASSWORD)
    if registration_result:
        print("Результат регистрации:")
        print(json.dumps(registration_result, indent=2, ensure_ascii=False))
    else:
        print("Регистрация не удалась или произошла ошибка сети/сервера.")

if __name__ == '__main__':
    main()
