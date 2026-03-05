import sys
import os

# Ensure the root path is added so absolute imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))

from src.ai_write_x.tools.publishers.toutiao_publisher import ToutiaoPublisher
from src.ai_write_x.tools.publishers.xiaohongshu_publisher import XiaohongshuPublisher
from src.ai_write_x.tools.publishers.zhihu_publisher import ZhihuPublisher
from src.ai_write_x.tools.publishers.baijiahao_publisher import BaijiahaoPublisher

def test_login(platform: str):
    """
    Test logging in to a specific platform.
    This will open a visible browser window.
    """
    publisher = None
    if platform == "toutiao":
        publisher = ToutiaoPublisher(headless=False)
    elif platform == "xiaohongshu":
        publisher = XiaohongshuPublisher(headless=False)
    elif platform == "zhihu":
        publisher = ZhihuPublisher(headless=False)
    elif platform == "baijiahao":
        publisher = BaijiahaoPublisher(headless=False)
    else:
        print("❌ 未知的平台，支持: toutiao, xiaohongshu, zhihu, baijiahao")
        return

    print(f"🔄 准备启动 {platform} 平台登录测试流程...")
    print("👉 请在弹出的浏览器中手动扫描二维码或输入账号密码登录。登录成功后，系统会自动保存您的 Cookie 并关闭窗口。")
    publisher.check_and_login()
    print("✅ 登录验证脚本执行完毕。如果上面提示登录验证成功，您可以放心使用 AIWriteX 自动发布了。")


def test_publish(platform: str, commit: bool = False, images: list = None):
    """
    Test a dummy publish action to an account.
    """
    publisher = None
    if platform == "toutiao":
        publisher = ToutiaoPublisher(headless=False)
    elif platform == "xiaohongshu":
        publisher = XiaohongshuPublisher(headless=False)
    elif platform == "zhihu":
        publisher = ZhihuPublisher(headless=False)
    elif platform == "baijiahao":
        publisher = BaijiahaoPublisher(headless=False)
    else:
        print("❌ 未知的平台，支持: toutiao, xiaohongshu, zhihu, baijiahao")
        return

    print(f"📝 准备对 {platform} 平台执行发文测试...")
    test_title = f"AIWriteX 自动发布测试 - {platform}"
    test_content = "这是一篇由 AIWriteX 自动发布脚本测试生成的文章内容。\n\n请忽略此草稿。测试时间：" + __import__('time').strftime('%Y-%m-%d %H:%M:%S')
    
    # 允许测试时自动加载图片
    if images is None:
        # 尝试在当前目录下找几个 jpg/png
        import glob
        images = glob.glob("*.jpg")[:2] + glob.glob("*.png")[:2]
        if images:
            print(f"🖼️ 自动拾取到待测图片: {images}")

    success, msg = publisher.publish(title=test_title, content=test_content, images=images, commit=commit)
    if success:
        print(f"🎉 测试流程执行成功: {msg}")
    else:
        print(f"❌ 测试发布失败: {msg}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法:")
        print("  python test_publishers.py login [platform]")
        print("  python test_publishers.py publish [platform] [--commit] [--images=path1,path2]")
        sys.exit(1)
        
    action = sys.argv[1]
    plat = sys.argv[2]
    
    # 解析 args
    commit_flag = "--commit" in sys.argv
    image_paths = None
    for arg in sys.argv:
        if arg.startswith("--images="):
            image_paths = arg.split("=")[1].split(",")

    if action == "login":
        test_login(plat)
    elif action == "publish":
        test_publish(plat, commit=commit_flag, images=image_paths)
    else:
        print("❌ 未知的操作，只支持 login 或是 publish")
