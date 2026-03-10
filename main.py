# -*- coding: UTF-8 -*-

from requests.exceptions import RequestsDependencyWarning
import warnings
import multiprocessing
import sys
import os

# 添加 src 目录到路径，确保模块能正确导入
script_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(script_dir, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

os.environ["PYTHONIOENCODING"] = "utf-8"

# 抑制版本警告和 noisy logs
warnings.filterwarnings("ignore", category=RequestsDependencyWarning)
try:
    import logging
    logging.getLogger("urllib3").setLevel(logging.ERROR)
except:
    pass

from aiforge import AIForgeEngine  # noqa


def run():
    """启动 GUI 应用程序"""
    try:
        from src.ai_write_x.core.license_stub import check_license_and_start

        # V23.0: 启动 HTTP/3 服务器 (可选 — 需要 aioquic)
        try:
            from src.ai_write_x.core.http3_server import HTTP3Server, HAS_AIOQUIC
            if HAS_AIOQUIC:
                import asyncio
                import threading

                async def start_http3_background():
                    try:
                        http3_server = HTTP3Server(
                            host='0.0.0.0',
                            port=4433,
                            enable_logging=True
                        )
                        await http3_server.start()
                    except Exception as e:
                        print(f"[V23.0] HTTP/3 server failed: {e}")

                http3_thread = threading.Thread(
                    target=lambda: asyncio.run(start_http3_background()),
                    daemon=True,
                    name="HTTP3_Background"
                )
                http3_thread.start()
        except ImportError:
            pass  # aioquic 未安装，跳过 HTTP/3

        check_license_and_start()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception:
        raise


if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn", force=True)

    if AIForgeEngine.handle_sandbox_subprocess(
        globals_dict=globals().copy(), sys_path=sys.path.copy()
    ):
        sys.exit(0)
    else:
        run()
