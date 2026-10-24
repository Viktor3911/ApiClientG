from g_api_view import Client, GApiError

with Client() as client:
    try:
        print("Пользователь:", client.me())
        print("Модели:")
        for model in client.list_models():
            print(f"  {model.index}. {model.name} ({model.code})")

        result = client.generate(
            text="Расскажи о Python в двух предложениях",
            model="gemini-3.5-flash-lite"
        )
        print("Ответ:", result.answer)
        print("Токенов:", result.tokens_used)
        for source in result.sources:
            print("Источник:", source.title, source.url)

        client.clear_context()
    except GApiError as error:
        print("Ошибка:", error)
