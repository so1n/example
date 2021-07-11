import sys
from hook_aiomysql import MetaPathFinder

sys.meta_path.insert(0, MetaPathFinder())
