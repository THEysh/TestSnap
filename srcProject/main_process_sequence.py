import asyncio
from PIL import Image
from typing import List, Dict, Any
from tqdm.asyncio import tqdm_asyncio
from srcProject.config.constants import OCR_TEXT_VALUES, BlockType_MEMBER, BlockType
from srcProject.data_loaders.pdf_dataset import PDFDataset
from srcProject.models.layout_reader import find_reading_order_index
from srcProject.models.model_manager import ModelManager
from srcProject.models.reader_xy_cut import XY_CUT
from srcProject.utlis.aftertreatment import batch_preprocess_detections, normalize_polygons_to_bboxes, poly_to_bbox, \
    convert_html_tables_to_markdown
from srcProject.utlis.common import find_project_root, prepare_directory
from srcProject.utlis.visualization.visualize_document import visualize_document
import os

model_manager = ModelManager()

async def layout_prediction(input_path: str, bool_ocr = True) -> List[List[Dict[str, Any]]]:
    """
    处理单个文档，执行布局分析、文本提取和结构化，并进行可视化。
    """
    file_extension = os.path.splitext(input_path)[1].lower()
    all_page_images = []
    if file_extension == '.pdf':
        dataset = PDFDataset(input_path)
        for page_index in range(len(dataset)):
            page_image = dataset.get_page_image(page_index, dpi=300)
            all_page_images.append({"image": page_image, "page_size": dataset.get_page_dimensions(page_index)})
        dataset.close()
    elif file_extension in ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff']:
        image = Image.open(input_path).convert("RGB")
        all_page_images.append({"image": image, "page_size": (int(image.width), int(image.height))})
    else:
        raise ValueError(f"不支持的文件类型: {file_extension}")
    print(f"开始对 {len(all_page_images)} 页进行布局预测...")
    detections_per_page = model_manager.layout_detector.batch_predict(
        images=all_page_images,
        batch_size=4  # 根据你的GPU显存和图片大小调整批处理大小
    )
    for i in range(len(detections_per_page)):
        if isinstance(all_page_images[i], dict):
            this_page_image = all_page_images[i]['image']
        else:
            this_page_image = None
        for j in range(len(detections_per_page[i])):
            if isinstance(detections_per_page[i][j], dict):
                detections_per_page[i][j]['page_size'] = all_page_images[i]['page_size']
                if this_page_image is not None:
                    bbox = poly_to_bbox(detections_per_page[i][j]['poly'])
                    cropped_image = this_page_image.crop(bbox)
                    detections_per_page[i][j]['cropped_image'] = cropped_image
    print("布局预测完成。")
    filtered_detections = batch_preprocess_detections(detections_per_page, iou_threshold=0.05)
    print("布局预测iou过滤完成")
    # 调用异步OCR函数
    if bool_ocr:
        filtered_detections = await ocr_test(filtered_detections)
    return filtered_detections

async def ocr_test(data: List[List[Dict[str, Any]]], max_concurrent_tasks: int = 10):
    """
    处理 OCR 任务，并限制并发数量。
    Args:
        data: 包含检测结果的列表。
        max_concurrent_tasks: 允许同时运行的最大 OCR 任务数量。
    """

    ocr_tasks = []  # 用于存储所有的 OCR 任务
    # 创建一个信号量，用于控制并发任务的数量
    semaphore = asyncio.Semaphore(max_concurrent_tasks)
    async def run_ocr_task(image, i_idx, j_idx, inf:BlockType=None):
        """
        一个包装函数，用于在获取信号量许可后执行 OCR 预测。
        """
        async with semaphore:
            # 确保这里正确地 await 了异步的 predict 方法
            text = await model_manager.ocr_recognizer.predict(image, inf)
            return text, i_idx, j_idx
    for i in range(len(data)):
        for j in range(len(data[i])):
            if isinstance(data[i][j], dict) and data[i][j]['category_id'] in OCR_TEXT_VALUES:
                category_id = int(data[i][j]['category_id'])
                blockquote = BlockType_MEMBER[category_id]
                # 创建一个任务，这个任务会等待信号量许可
                task = asyncio.create_task(run_ocr_task(data[i][j]['cropped_image'], i, j, blockquote))
                ocr_tasks.append(task)
    # 并发地运行所有 OCR 任务，并等待它们全部完成
    # results 将是一个列表，包含所有任务的返回值 (text, i_idx, j_idx)
    # 使用 tqdm_asyncio.gather 来并发地运行任务并显示进度条
    if ocr_tasks:
        results = await tqdm_asyncio.gather(
            *ocr_tasks,
            total=len(ocr_tasks),  # 设置进度条的总数
            desc="OCR Progress"  # 进度条的描述信息
        )

        # 将 OCR 结果填充回原始数据结构
        for text, i_idx, j_idx in results:
            data[i_idx][j_idx]['text'] = text

    return data

def read_prediction(data:List[List[Dict[str, Any]]])->List[List[int]]:
    page_order = model_manager.read_model.batch_predict(data)
    order_in_list = find_reading_order_index(page_order)
    print(f'阅读顺序索引{order_in_list}')
    return order_in_list

def generate_markdown_document(data: List[List[Dict[str, Any]]], reading_order: List[List[int]],
                               output_path: str) -> str:
    """
    根据 OCR 结果和阅读顺序生成 Markdown 文档并保存。
    Args:
        data: 包含所有页面OCR结果的列表。
        reading_order: 一个列表，包含了每页元素的阅读顺序索引。
        output_path: 最终Markdown文件的保存路径。
    """
    # 检查并创建保存路径的父目录
    save_root_path = os.path.dirname(output_path)
    images_path = os.path.join(save_root_path, "images")
    prepare_directory(save_root_path)
    prepare_directory(images_path)
    markdown_content = []
    # 遍历每个页面的阅读顺序
    for page_index, order_list in enumerate(reading_order):
        page_data = data[page_index]
        sorted_data = []
        for index in range(len(page_data)):
            new_index = order_list.index(index)
            sorted_data.append(page_data[new_index])
        for element in sorted_data:
            category_id = int(element.get('category_id'))
            content = element.get('text', '')
            category_key_enum = BlockType_MEMBER.get(category_id)
            if category_key_enum is None:
                continue
            content = content.replace("```html", "").replace("```markdown", "").replace("```", "")
            # 根据键名拼接内容
            if category_key_enum == BlockType.TITLE:
                markdown_content.append(f"## {content}\n\n")
            elif category_key_enum in [BlockType.PLAIN_TEXT, BlockType.ISOLATE_FORMULA]:
                markdown_content.append(f"{content}\n\n")
            elif category_key_enum in [BlockType.FIGURE_CAPTION, BlockType.TABLE_CAPTION, BlockType.TABLE_FOOTNOTE]:
                markdown_content.append(f"_{content}_\n\n")
            elif category_key_enum ==BlockType.TABLE:
                content = convert_html_tables_to_markdown(content)
                markdown_content.append(f"{content}\n\n")
            elif category_key_enum == BlockType.FIGURE:
                # 生成一个UUID对象
                import uuid
                unique_uuid = str(uuid.uuid4())
                cropped_image = element.get('cropped_image')
                if cropped_image is not None and isinstance(cropped_image, Image.Image):
                    cropped_image_path = os.path.join(images_path, f"{unique_uuid}.png")
                    cropped_image.save(cropped_image_path)
                    markdown_content.append(f"![{unique_uuid}](images/{unique_uuid}.png)\n\n")
    final_markdown = "".join(markdown_content)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_markdown)
    print(f"Markdown文档已生成并保存到: {output_path}")
    return final_markdown

if __name__ == '__main__':
    sample_path = os.path.join(find_project_root(), 'tests/test_data/demo1_页面_3.png')
    # sample_path = os.path.join(find_project_root(), "tests/test_data/多智能体强化学习综述.pdf")
    file_name_without_extension, file_extension = os.path.splitext(os.path.basename(sample_path))
    detections = asyncio.run(layout_prediction(sample_path, bool_ocr=True))
    page_order = read_prediction(detections)
    output_directory = "srcProject/output/visualizations"
    visualize_document(
        input_path=sample_path,  # 传入原始输入路径
        detections_per_page=detections,
        category_names=model_manager.layout_category_names,
        output_directory = output_directory,
        page_order= page_order,
        file_prefix = file_name_without_extension,
        dpi_for_image_output=300  # 保持与加载图片DPI一致
    )
    md_save_path = os.path.join(find_project_root(), f"srcProject/output/visualizations/{file_name_without_extension}", f"{file_name_without_extension}.md")
    generate_markdown_document(detections,page_order,output_path= md_save_path)