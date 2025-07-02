from setuptools import setup

APP = ['url_navigator.py']
DATA_FILES = [
    ('', ['xmum_logo.png']),
    ('', ['sites.json'])
]
OPTIONS = {
    'argv_emulation': True,
    'packages': ['tkinter', 'PIL'],
    # 'iconfile': 'xmum_logo.icns',  # 如有 icns 图标可取消注释
    'plist': {
        'CFBundleName': '妙妙工具',
        'CFBundleDisplayName': '妙妙工具',
        'CFBundleGetInfoString': '厦门大学马来西亚分校网址导航工具',
        'CFBundleIdentifier': 'com.xmum.urlnavigator',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHumanReadableCopyright': '© 2024 厦门大学马来西亚分校'
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
) 