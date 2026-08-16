'''
总程序
负责运行整个携程爬虫流程
'''
import os
import sys
import glob

# 添加当前目录到Python路径，确保可以导入其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ctrip_spider0 import get_spot
from ctrip_spider1 import get_url
from ctrip_spider2 import mainc2


def select_existing_city_file():
    """列出当前目录下的 *_携程景点.csv 文件供选择"""
    city_files = glob.glob("*_携程景点.csv")
    if not city_files:
        print("⚠️ 当前目录下未找到任何携程景点文件。")
        return None

    print("\n检测到以下已有城市景点文件：")
    for i, f in enumerate(city_files, 1):
        print(f"{i}. {f}")

    try:
        idx = int(input("\n请输入要使用的文件序号（或按回车取消）: ").strip() or 0)
        if 1 <= idx <= len(city_files):
            city_file = city_files[idx - 1]
            city = city_file.replace("_携程景点.csv", "")
            return city
    except ValueError:
        pass
    return None

def full_process():
    """完整流程：获取景点列表 → 获取详情页URL → 爬取评论"""
    print("\n" + "=" * 60)
    print("开始完整爬虫流程")
    print("=" * 60)

    # 1. 获取景点列表
    print("\n步骤1: 获取景点列表")
    print("-" * 30)
    city = get_spot()
    if not city:
        print("获取景点列表失败，流程终止")
        return

    # 2. 获取详情页URL
    print("\n步骤2: 获取详情页URL")
    print("-" * 40)
    detail_urls = get_url(city)
    if not detail_urls:
        print("❌ 获取详情页URL失败，流程终止。")
        return

    # 3. 爬取评论
    print("\n步骤3: 爬取景点评论")
    print("-" * 30)
    mainc2()

def only_url_process():
    print("\n步骤1: 获取详情页URL")
    print("-" * 40)
    city = select_existing_city_file()
    if not city:
        print("未选择城市文件，流程终止。")
        return

    csv_file = f"{city}_携程景点.csv"
    if not os.path.exists(csv_file):
        print(f"❌ 未找到文件 {csv_file}。")
        return

    print(f"\n使用已有文件: {csv_file}")
    print("\n开始爬取详情页URL...\n")

    detail_urls = get_url(city)
    if not detail_urls:
        print("❌ 获取详情页URL失败。")
    else:
        print(f"✅ 已更新 {csv_file} 中的详情页URL。")


def comment_only_process():
    """仅爬取评论流程"""
    print("\n" + "=" * 60)
    print("开始仅爬取评论流程")
    print("=" * 60)
    mainc2()


def main():
    """主程序"""
    print("携程景点评论爬虫系统")
    print("=" * 40)

    while True:
        print("\n请选择运行模式:")
        print("1. 完整流程（输入城市，获取景点列表 → 获取详情页URL → 爬取景点评论）")
        print("2. 仅获取详情页URL")
        print("3. 仅爬取评论（需要已存在景点数据文件）")
        print("4. 退出程序")

        choice = input("\n请输入选择 (1-4): ").strip()

        if choice == '1':
            full_process()
        elif choice == '2':
            only_url_process()
        elif choice == '3':
            comment_only_process()
        elif choice == '4':
            print("程序退出，再见！")
            break
        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    # 忽略pandas的FutureWarning
    import warnings

    warnings.simplefilter(action='ignore', category=FutureWarning)

    main()
