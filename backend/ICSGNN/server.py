#!/usr/bin/env python
"""兼容入口，转调 run_api.py（推荐直接使用: python run_api.py）"""

if __name__ == "__main__":
    import runpy

    runpy.run_module("run_api", run_name="__main__")
