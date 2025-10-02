##Creating by Pr1me_StRel0k##

from flask import Flask, request, redirect
import datetime
import dropbox
from dropbox.exceptions import ApiError
import json
import os
from user_agents import parse

app = Flask(__name__)


DROPBOX_TOKEN = os.environ.get("DROPBOX_TOKEN")

DROPBOX_PATH = "/tracking/logs.jsonl"


if not DROPBOX_TOKEN:
    raise ValueError("Не найден DROPBOX_TOKEN! Установите переменную окружения.")
dbx = dropbox.Dropbox(DROPBOX_TOKEN)


def append_to_dropbox_file(line: str):

    try:
        
        _, res = dbx.files_download(DROPBOX_PATH)
        existing_content = res.content.decode('utf-8')
    except ApiError as e:
        
        if e.error.is_path() and e.error.get_path().is_not_found():
            app.logger.info(f"Файл {DROPBOX_PATH} не найден. Будет создан новый.")
            existing_content = ""
        else:
           
            app.logger.error(f"Ошибка API Dropbox при скачивании: {e}")
            raise
    
    
    new_content = existing_content + line + "\n"
    
    try:
        
        dbx.files_upload(
            new_content.encode('utf-8'), 
            DROPBOX_PATH, 
            mode=dropbox.files.WriteMode.overwrite
        )
    except ApiError as e:
        app.logger.error(f"Ошибка API Dropbox при загрузке: {e}")
        raise


@app.route("/track")
def track():
    
    to_url = request.args.get("to", "/")
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    user_agent_string = request.headers.get("User-Agent", "")
    user_agent = parse(user_agent_string)
    os_info = user_agent.os.family
    browser_info = f"{user_agent.browser.family} {user_agent.browser.version_string}"
    device_info = user_agent.device.family
    
    
    record = {
        "timestamp_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "ip": ip_address,
        "os": os_info,
        "browser": browser_info,
        "device": device_info,
        "user_agent_full": user_agent_string,
        "destination_url": to_url,
        "referer": request.headers.get("Referer"),
    }
    
    
    log_line = json.dumps(record, ensure_ascii=False)
    
    
    try:
        append_to_dropbox_file(log_line)
    except Exception as e:

        app.logger.error(f"Не удалось загрузить лог в Dropbox: {e}")
        
   
    return redirect(to_url, code=302)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
