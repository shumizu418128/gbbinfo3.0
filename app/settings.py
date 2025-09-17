import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# MARK: 世界地図初期化
def delete_world_map():
    """
    world_mapディレクトリ内の全てのHTMLファイルを削除します。

    app/templates配下の各年度ディレクトリ内に存在するworld_mapディレクトリを探索し、
    その中に含まれる全ての.htmlファイルを削除します。
    ディレクトリやファイルが存在しない場合は何も行いません。

    Raises:
        OSError: ファイルの削除に失敗した場合
    """
    templates_dir = os.path.join(BASE_DIR, "app", "templates")
    if os.path.exists(templates_dir):
        for year_dir in os.listdir(templates_dir):
            year_path = os.path.join(templates_dir, year_dir)
            if os.path.isdir(year_path):
                world_map_path = os.path.join(year_path, "world_map")
                if os.path.exists(world_map_path):
                    for file in os.listdir(world_map_path):
                        if file.endswith(".html"):
                            file_path = os.path.join(world_map_path, file)
                            os.remove(file_path)

