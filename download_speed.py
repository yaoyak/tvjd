import os
import cv2
import re
import time
import threading
from queue import Queue
import requests

# 线程安全的队列，用于存储下载任务
task_queue = Queue()

# 线程安全的列表，用于存储结果
results = []

channels = []

with open("hebei.txt", 'r', encoding='utf-8') as file:
    lines = file.readlines()
    for line in lines:
        line = line.strip()
        if line:
            channel_name, channel_url = line.split(',')
            channels.append((channel_name, channel_url))


# 定义工作线程函数
def worker():
    while True:
        # 从队列中获取一个任务
        channel_name, channel_url = task_queue.get()
        try:
            channel_url_t = channel_url.rstrip(channel_url.split('/')[-1])  # m3u8链接前缀
            lines = requests.get(channel_url).text.strip().split('\n')  # 获取m3u8文件内容
            ts_lists = [line.split('/')[-1] for line in lines if line.startswith('#') == False]  # 获取m3u8文件下视频流后缀
            ts_lists_0 = ts_lists[0].rstrip(ts_lists[0].split('.ts')[-1])  # m3u8链接前缀
            ts_url = channel_url_t + ts_lists[0]  # 拼接单个视频片段下载链接
            start_time = time.time()
            content = requests.get(ts_url).content
            end_time = time.time()
            response_time = (end_time - start_time) * 1
            with open(ts_lists_0, 'ab') as f:
                f.write(content)  # 写入文件
            file_size = len(content)
            #print(f"文件大小：{file_size} 字节")
            download_speed = file_size / response_time /1024
            #print(f"下载速度：{download_speed:.3f} kB/s")
            normalized_speed = min(max(download_speed / 1024, 0.001), 100)  # 将速率从kB/s转换为MB/s并限制在1~100之间
            print(f"标准化后的速率：{normalized_speed:.3f} MB/s")

            # 获取帧宽度和帧高度
            cap = cv2.VideoCapture(ts_lists_0)
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            print(f"视频分辨率：{frame_width}X{frame_height}")

            # 删除下载的文件
            os.remove(ts_lists_0)

            result = channel_name, channel_url, f"{normalized_speed:.3f} MB/s", f"{frame_width}X{frame_height}"
            results.append(result)
        except:
            pass

        # 标记任务完成
        task_queue.task_done()


# 创建多个工作线程
num_threads = 10
for _ in range(num_threads):
    t = threading.Thread(target=worker, daemon=True)  # 将工作线程设置为守护线程
    t.start()

# 添加下载任务到队列
for channel in channels:
    task_queue.put(channel)

# 等待所有任务完成
task_queue.join()


def channel_key(channel_name):
    match = re.search(r'\d+', channel_name)
    if match:
        return int(match.group())
    else:
        return float('inf')  # 返回一个无穷大的数字作为关键字

# 对频道进行排序
results.sort(key=lambda x: (x[0], -float(x[2].split()[0])))
results.sort(key=lambda x: channel_key(x[0]))

# 将结果写入文件
with open("download_results.txt", 'w', encoding='utf-8') as file:
    for result in results:
        channel_name, channel_url, speed, resolution = result
        file.write(f"{channel_name},{channel_url},{speed},{resolution}\n")

with open("download_speed.txt", 'w', encoding='utf-8') as file:
    for result in results:
        channel_name, channel_url, speed, resolution = result
        file.write(f"{channel_name},{channel_url}\n")