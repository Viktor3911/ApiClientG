import requests
import os
from typing import List, Optional, Dict, Any


def send_request_to_gemini_api(
    server_url: str,
    user_id: int,
    password: str,
    model_name: str,
    text: Optional[str],
    system_instruction: Optional[str],
    flag_search: Optional[bool],
    file_paths: List[str]
) -> Optional[Dict[str, Any]]:
    """
    Отправляет POST-запрос с текстом и файлами на FastAPI сервер (/generate).

    Args:
        server_url: Полный URL эндпоинта /generate.
        user_id: ID пользователя.
        password: Пароль пользователя.
        text: Текстовое сообщение (может быть None).
        system_instruction: Системная инструкция (может быть None).
        flag_search: Флаг поиска Google (может быть None).
        file_paths: Список путей к локальным файлам для отправки.

    Returns:
        Словарь с JSON-ответом сервера или None в случае ошибки.
    """
    # print(f"Отправка запроса на {server_url} для User ID: {user_id}")
    # print(f"Текст: {text}")
    # print(f"Файлы: {file_paths}")

    request_data: Dict[str, Any] = {'user_id': str(user_id), 'password': str(password), 'model_name': str(model_name)} 
    if text is not None: # Проверяем на None, чтобы пустая строка тоже отправлялась
        request_data['user_message_text'] = text
    if system_instruction is not None:
        request_data['system_instruction'] = system_instruction
    if flag_search is not None: # Отправляем bool значение как есть, Form() его обработает
        request_data['flag_search'] = flag_search 

    files_to_send = []
    opened_files = [] 

    try:
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"Предупреждение: Файл не найден и будет пропущен: {file_path}")
                continue
            try:
                file_obj = open(file_path, 'rb')
                opened_files.append(file_obj)
                file_name = os.path.basename(file_path)
                files_to_send.append(('files', (file_name, file_obj)))
            except Exception as e:
                print(f"Ошибка открытия файла {file_path}: {e}")
                # Закрываем уже открытые файлы перед возвратом None
                for f_obj in opened_files:
                    f_obj.close()
                return None

        if not text and not files_to_send and system_instruction is None and flag_search is None:
            # Если нет ни текста, ни файлов, и другие опциональные поля тоже None,
            # то запрос может быть некорректным с точки зрения логики сервера (/generate требует текст ИЛИ файлы)
            # Однако, сам FastAPI может обработать такой запрос, если поля user_message_text и files опциональны.
            # Оставим проверку на стороне сервера, здесь просто формируем запрос.
            pass


        # print(f"Отправка данных формы на {server_url}: {request_data}")
        # print(f"Отправляемые файлы: {files_to_send}")
        
        response = requests.post(
            server_url,
            data=request_data, 
            files=files_to_send 
        )
        # print(f"Статус ответа от {server_url}: {response.status_code}")
        # print(f"Тело ответа от {server_url}: {response.text}")

        try:
            response_json = response.json()
            return response_json
        except requests.exceptions.JSONDecodeError:
            print(f"Ошибка: Не удалось декодировать JSON из ответа сервера {server_url}.")
            print("Текст ответа:", response.text)
            # Возвращаем структуру с ошибкой, чтобы клиент мог ее обработать
            return {"error": "JSONDecodeError", "detail": response.text, "status_code": response.status_code}

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса на {server_url}: {e}")
        return None # Или можно вернуть {"error": str(e)}
    finally:
        for f in opened_files:
            try:
                f.close()
            except Exception as e:
                print(f"Ошибка закрытия файла: {e}")


def register_user_api(base_url: str, user_id: int, password: str) -> Optional[Dict[str, Any]]:
    """
    Отправляет POST-запрос для регистрации пользователя (/register).

    Args:
        base_url: Базовый URL сервера (например, "http://127.0.0.1:8000").
        user_id: ID пользователя.
        password: Пароль пользователя.

    Returns:
        Словарь с JSON-ответом сервера или None/словарь с ошибкой.
    """
    payload = {"user_id": user_id, "password": password}
    endpoint = "/register"
    url = f"{base_url}{endpoint}"
    try:
        # print(f"Отправка запроса на регистрацию: {url} с данными {payload}")
        response = requests.post(url, json=payload) # Отправляем как JSON
        # print(f"Статус ответа регистрации: {response.status_code}")
        # print(f"Тело ответа регистрации: {response.text}")
        
        return response.json()
    except requests.exceptions.JSONDecodeError:
        # Если JSON не декодируется, но статус, например, 200 (что маловероятно для ошибки)
        print(f"Ошибка декодирования JSON от {url}, хотя статус {response.status_code}. Текст: {response.text}")
        return {"error": "JSONDecodeError", "detail": response.text, "status_code": response.status_code}
    except requests.exceptions.HTTPError as http_err: # Этот блок может не сработать без raise_for_status
        print(f"HTTP ошибка при регистрации пользователя на {url}: {http_err}")
        print(f"Ответ сервера (текст): {http_err.response.text}")
        try:
            return http_err.response.json() 
        except requests.exceptions.JSONDecodeError:
            return {"error": http_err.response.text, "status_code": http_err.response.status_code}
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса на регистрацию на {url}: {e}")
        return None


def clear_user_context_api(base_url: str, user_id: int, password: str) -> Optional[Dict[str, Any]]:
    """
    Отправляет POST-запрос для очистки контекста пользователя (/clear_context) с аутентификацией.

    Args:
        base_url: Базовый URL сервера.
        user_id: ID пользователя.
        password: Пароль пользователя.

    Returns:
        Словарь с JSON-ответом сервера или None/словарь с ошибкой.
    """
    payload = {"user_id": user_id, "password": password}
    endpoint = "/clear_context"
    url = f"{base_url}{endpoint}"
    try:
        # print(f"Отправка запроса на очистку контекста: {url} для user_id {user_id} (с паролем)")
        response = requests.post(url, json=payload) # Отправляем как JSON
        # print(f"Статус ответа очистки контекста: {response.status_code}")
        # print(f"Тело ответа очистки контекста: {response.text}")
        
        # response.raise_for_status()
        
        return response.json()
    except requests.exceptions.JSONDecodeError:
        print(f"Ошибка декодирования JSON от {url}, хотя статус {response.status_code}. Текст: {response.text}")
        return {"error": "JSONDecodeError", "detail": response.text, "status_code": response.status_code}
    except requests.exceptions.HTTPError as http_err: # Этот блок может не сработать без raise_for_status
        print(f"HTTP ошибка при очистке контекста на {url}: {http_err}")
        print(f"Ответ сервера (текст): {http_err.response.text}")
        try:
            return http_err.response.json()
        except requests.exceptions.JSONDecodeError:
            return {"error": http_err.response.text, "status_code": http_err.response.status_code}
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке запроса на очистку контекста на {url}: {e}")
        return None


def list_models_api(base_url: str) -> Optional[Dict[str, Any]]:
    """
    Отправляет POST-запрос для получения списка доступных моделей (/list_models).
    Не требует аутентификации.

    Args:
        base_url: Базовый URL сервера (например, "http://127.0.0.1:8000").

    Returns:
        Словарь с JSON-ответом сервера (содержит список моделей в ключе 'models')
        или словарь с информацией об ошибке.
        Успешный ответ обычно имеет статус 200 и выглядит как {'models': [...], 'status_code': 200}.
        Ошибка может вернуть словарь с ключами 'error', 'detail', 'status_code'.
    """
    endpoint = "/list_models"
    url = f"{base_url}{endpoint}"

    try:
        # Сервер ожидает POST с пустым телом. requests.post без data/json/files отправляет пустой body.
        # Или можно явно послать json={}. Оба варианта допустимы для FastAPI endpoint без body/form/json параметров.
        # Давайте отправим json={} для явности, что это POST запрос с телом (пустым JSON).
        response = requests.post(url, json={})

        # print(f"Статус ответа списка моделей: {response.status_code}")
        # print(f"Тело ответа списка моделей: {response.text}") # Отладочный вывод

        try:
            # Пытаемся декодировать JSON независимо от статуса ответа
            response_json = response.json()
            # Добавляем статус код в ответ
            if isinstance(response_json, dict):
                response_json['status_code'] = response.status_code
            return response_json
        except requests.exceptions.JSONDecodeError:
            # Если ответ не в формате JSON, возвращаем ошибку
            # print(f"Ошибка: Не удалось декодировать JSON из ответа сервера {url} (статус {response.status_code}).")
            # print("Тело ответа:", response.text)
            return {"error": "JSONDecodeError", "detail": response.text, "status_code": response.status_code}

    except requests.exceptions.RequestException as e:
        # Ловим сетевые ошибки, ошибки таймаута и т.п.
        # print(f"Ошибка при отправке запроса на {url}: {e}")
        return {"error": "RequestException", "detail": str(e)}