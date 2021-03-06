import json
import requests
from flask import current_app
from flask_babel import _


def translate(text, source_language, dest_language):
    if ('MS_TRANSLATOR_KEY' not in current_app.config or
            not current_app.config['MS_TRANSLATOR_KEY']):
        return _('Error: the translation service is not configured.')
    # Azure requires this header populated with API Key:
    auth = {'Ocp-Apim-Subscription-Key': current_app.config['MS_TRANSLATOR_KEY']}
    r = requests.get('https://api.microsofttranslator.com/v2/Ajax.svc'
                     '/Translate?text={}&from={}&to={}'.format(
                         text, source_language, dest_language),
                     headers=auth)
    if r.status_code != 200:
        return _('Error: the translation service failed.')
    # Decode byte string using UTF-8 with leading BOM (signature):
    return json.loads(r.content.decode('utf-8-sig'))

