from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('google.generativeai') + \
                collect_submodules('google.auth') + \
                collect_submodules('google_auth_oauthlib') + \
                collect_submodules('googleapiclient') + \
                collect_submodules('google.api_core')