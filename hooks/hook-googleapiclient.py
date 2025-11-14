from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('googleapiclient') + \
                collect_submodules('google.generativeai') + \
                collect_submodules('google.api_core') + \
                collect_submodules('google')