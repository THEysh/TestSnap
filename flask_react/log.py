import threading
import time
import logging
# 存储任务进度的字典，键为任务ID，值包含进度信息
TASK_PROCESS = {}
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TextSnapServer')

def update_task_progress(task_id, progress, status='processing', message=None, result=None):
    """
    更新任务进度
    :param task_id: 任务ID
    :param progress: 进度百分比 (0-100)
    :param status: 任务状态 ('processing', 'completed', 'failed')
    :param message: 状态消息
    :param result: 任务结果（任务完成时）
    """
    if task_id in TASK_PROCESS:
        TASK_PROCESS[task_id].update({
            'progress': progress,
            'status': status,
            'message': message,
            'updated_at': time.time()
        })
        if result:
            TASK_PROCESS[task_id]['result'] = result
        logger.info(f"任务 {task_id} 进度更新: {progress}% - {status} - {message or ''}")


def complete_task(task_id, result=None, error=None):
    """
    完成任务并清理进度信息
    :param task_id: 任务ID
    :param result: 成功结果
    :param error: 错误信息
    """
    if task_id not in TASK_PROCESS:
        logger.warning(f"尝试完成不存在的任务: {task_id}")
        return

    if error:
        TASK_PROCESS[task_id].update({
            'progress': 0,
            'status': 'failed',
            'message': error,
            'updated_at': time.time()
        })
        logger.error(f"任务 {task_id} 失败: {error}")
    else:
        TASK_PROCESS[task_id].update({
            'progress': 100,
            'status': 'completed',
            'message': '处理完成',
            'result': result,
            'updated_at': time.time()
        })
        logger.info(f"任务 {task_id} 成功完成")

    # 延迟删除任务信息（给客户端时间获取最终状态）
    def cleanup_task():
        time.sleep(100)  # 100秒后清理
        if task_id in TASK_PROCESS:
            del TASK_PROCESS[task_id]
            logger.info(f"任务 {task_id} 信息已清理")

    cleanup_thread = threading.Thread(target=cleanup_task)
    cleanup_thread.daemon = True
    cleanup_thread.start()

# 用于处理进度的函数
async def handle_progress(task_id, completed_count, total_tasks):
    process = 10+(completed_count/total_tasks)*100*0.8
    if task_id:
        update_task_progress(task_id, round(process, 2), 'processing', f'OCR处理中...{completed_count}/{total_tasks}')