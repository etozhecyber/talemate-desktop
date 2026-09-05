from PyInstaller.utils.hooks import collect_data_files

# Collect only standard package data, do not collect external AppData/nltk_data corpora
datas = collect_data_files("nltk", False)
hiddenimports = ["nltk.chunk.named_entity"]
