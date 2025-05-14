import asyncio
import aiohttp
import re
from urllib.parse import urlparse
from collections import defaultdict

# 原始URL列表（此处已缩短，实际使用时替换为完整列表）
urls = [
    "http://example1.com:9901",
    "http://example2.com:9901",
]

async def generate_modified_urls(original_url):
    """生成修改后的IP地址序列"""
    parsed = urlparse(original_url)
    base_ip = '.'.join(parsed.hostname.split('.')[:-1])
    return [
      f"{parsed.scheme}://{base_ip}.{i}:{parsed.port}/iptv/live/1000.json?key=txiptv"
        for i in range(1, 256)
    ]

async def check_node(session, url, semaphore):
    """异步检查节点可用性"""
    async with semaphore:
        try:
            async with session.get(url, timeout=2) as response:
                if response.status == 200:
                    print(f"✅ Valid node: {url}")
                    return url
        except Exception as e:
            return None

async def fetch_channels(session, node_url, semaphore):
  """获取频道列表"""
    async with semaphore:
        try:
            async with session.get(node_url, timeout=2) as response:
                data = await response.json()
                base_url = f"{urlparse(node_url).scheme}://{urlparse(node_url).hostname}:{urlparse(node_url).port}"
                
                channels = []
                for item in data.get('data', []):
                  name = re.sub(r'\s+', '', item.get('name', ''))
                    stream_url = item.get('url', '')
                    
                    # 标准化处理
                    name = re.sub(r'CCTV(\d+)台', r'CCTV\1', name)
                    name = re.sub(r'高清|标清|超清|HD', '', name)
                    
                    if not stream_url.startswith('http'):
                        stream_url = f"{base_url}{stream_url}"
                    
                    channels.append((name, stream_url))
                  return channels
        except Exception as e:
            return []

async def speed_test(session, channel_name, channel_url, semaphore):
    """异步测速"""
    async with semaphore:
        try:
            # 获取m3u8内容
            async with session.get(channel_url, timeout=5) as response:
                if response.status != 200:
                  return None
                
                m3u8_text = await response.text()
                ts_list = [line for line in m3u8_text.split('\n') 
                          if line.strip() and not line.startswith('#')]
                
                if not ts_list:
                    return None
                
                # 测试第一个片段
                ts_url = f"{channel_url.rsplit('/', 1)[0]}/{ts_list[0]}"
                start_time = asyncio.get_event_loop().time()
              async with session.get(ts_url, timeout=5) as ts_response:
                    content = await ts_response.read()
                    elapsed = asyncio.get_event_loop().time() - start_time
                
                speed = len(content) / elapsed / 1024  # KB/s
                return (channel_name, channel_url, speed)
                
        except Exception as e:
            return None

async def main():
  # 初始化连接池
    connector = aiohttp.TCPConnector(limit=0)  # 不限制连接数
    async with aiohttp.ClientSession(connector=connector) as session:
        # 阶段1：发现有效节点
        print("🚀 Starting node discovery...")
        discovery_sem = asyncio.Semaphore(100)
        all_urls = []
        for url in urls:
            all_urls.extend(await generate_modified_urls(url))
        
        nodes = await asyncio.gather(*[
            check_node(session, url, discovery_sem) 
      for url in all_urls
        ])
        valid_nodes = [n for n in nodes if n]
        print(f"🎯 Found {len(valid_nodes)} valid nodes")
        
        # 阶段2：收集频道
        print("📡 Fetching channels...")
        fetch_sem = asyncio.Semaphore(50)
        channels = await asyncio.gather(*[
            fetch_channels(session, node, fetch_sem) 
      for node in valid_nodes
        ])
        all_channels = [c for sublist in channels for c in sublist if sublist]
        print(f"📺 Total channels found: {len(all_channels)}")
        
        # 阶段3：测速筛选
        print("⏱️ Speed testing...")
        speed_sem = asyncio.Semaphore(20)
        results = await asyncio.gather(*[
            speed_test(session, name, url, speed_sem)
            for name, url in all_channels
        ])
        valid_channels = [r for r in results if r]
      # 分类整理
        category = defaultdict(list)
        for name, url, speed in valid_channels:
            if speed < 500:  # 过滤低速源
                continue
            key = 'CCTV' if 'CCTV' in name else ('卫视' if '卫视' in name else '其他')
            category[key].append((name, url, speed))
        
        # 排序去重（每个频道保留最快8个）
        final = defaultdict(list)
        for key, items in category.items():
            groups = defaultdict(list)
            for name, url, speed in items:
                groups[name].append((speed, url))
              
            for name, candidates in groups.items():
                sorted_candidates = sorted(candidates, reverse=True)[:8]
                final[key].extend([
                    (name, url) for _, url in sorted_candidates
                ])
              
        # 生成结果文件
        with open("itvlist.txt", "w", encoding="utf-8") as f:
            for cat in ['CCTV', '卫视', '其他']:
                f.write(f"{cat}频道,#genre#\n")
                for name, url in final.get(cat, []):
                    f.write(f"{name},{url}\n")
                f.write("\n")
        print("🎉 Done! Results saved to itvlist.txt")
      
if __name__ == "__main__":
    asyncio.run(main())
      
      
