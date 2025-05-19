from .core.request import list_models_api
from .core.settings import BASE_SERVER_URL
import json

def main():
    models_response = list_models_api(BASE_SERVER_URL)

    if models_response:
        if models_response.get('status_code') == 200:
            models_list = models_response.get('models')
            if models_list:
                print("Список доступных моделей:")
                for model in models_list:
                    print(f"{model.get('model_name')}")
            else:
                print("Список моделей пуст.")
        else:
            print(f"Ошибка при получении списка моделей: Статус {models_response.get('status_code')}, Детали: {models_response.get('detail', 'Нет деталей')}")

if __name__ == '__main__':
    main()