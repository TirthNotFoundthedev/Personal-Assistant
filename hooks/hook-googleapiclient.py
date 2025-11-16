from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# Collect all submodules for every google library being used
hiddenimports = (
    collect_submodules('google.generativeai') +
    collect_submodules('googleapiclient') +
    collect_submodules('google_auth_oauthlib') +
    collect_submodules('google.auth')
)

# Some google libraries need their metadata to work correctly
datas = copy_metadata('google-generativeai')
datas += copy_metadata('google-api-python-client')
datas += copy_metadata('google-auth')