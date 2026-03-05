import multiprocessing as mp
import time
import random
from typing import List, Callable


class ParallelTaskManager:
    """使用进程池管理多个并行任务"""

    def __init__(self, num_processes: int = 4):
        self.num_processes = num_processes
        self.pool = mp.Pool(processes=num_processes)
        self.results = []
        self.callbacks = []

    def submit_tasks(self, tasks: List[tuple], callback: Callable = None):
        """
        提交多个任务
        tasks: [(task_id, params), ...]
        callback: 每个任务完成后的回调函数
        """
        async_results = []
        for task_id, params in tasks:
            # 异步执行任务
            async_result = self.pool.apply_async(
                self._worker_function,
                args=(task_id, params),
                callback=lambda result: self._handle_result(result, callback)
            )
            async_results.append(async_result)

        return async_results

    @staticmethod
    def _worker_function(task_id: int, params: dict):
        """工作函数（在子进程中运行）"""
        result = []
        total_steps = params.get('steps', 10)

        for i in range(total_steps):
            # 模拟计算
            time.sleep(random.uniform(0.2, 0.8))

            # 这里无法实时传递中间结果给主进程
            # 如果需要实时更新，需要配合Queue
            intermediate = i / total_steps * 100

            # 可以通过共享内存或Queue实现实时通信
            # 但为了简洁，这里只返回最终结果

        return {
            'task_id': task_id,
            'result': [random.random() * 100 for _ in range(total_steps)],
            'params': params
        }

    def _handle_result(self, result, callback):
        """处理每个任务的结果"""
        if callback:
            callback(result)
        self.results.append(result)

    def close(self):
        """关闭进程池"""
        self.pool.close()
        self.pool.join()


# 使用示例
def task_callback(result):
    print(f"任务 {result['task_id']} 完成！结果长度: {len(result['result'])}")


def main_pool():
    manager = ParallelTaskManager(num_processes=3)

    # 准备任务
    tasks = [(i + 1, {'steps': random.randint(5, 10)}) for i in range(5)]

    # 提交任务
    manager.submit_tasks(tasks, callback=task_callback)

    # 等待所有任务完成
    manager.close()

    print("\n所有任务结果:")
    for result in manager.results:
        print(f"任务 {result['task_id']}: {result['result'][:3]}...")  # 只显示前3个结果


if __name__ == "__main__":
    main_pool()