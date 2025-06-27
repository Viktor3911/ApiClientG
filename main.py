import g_api_view

print(g_api_view.reg())
# Simple use of library, make sure to fill core/settings.py and run
print(g_api_view.generate(message_text='ку'))
g_api_view.clear_context()