from PyInstaller.utils.hooks.gi import GiModuleInfo

for ver in ("4.1", "4.0"):
    module_info = GiModuleInfo("JavaScriptCore", ver)
    if module_info.available:
        binaries, datas, hiddenimports = module_info.collect_typelib_data()
        break
else:
    binaries, datas, hiddenimports = [], [], []
