from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFont

from srcProject.models.model_base import BaseModel


class XY_CUT(BaseModel):
    """
    负责对页面上的文本块进行排序，实现一个基于 XY-Cut 的文档版面分析算法。
    该算法通过识别文本块间的水平和垂直间隙来构建一个布局树，并对页面内容进行逻辑排序。
    """
    def __init__(self, model_path: str = None):
        """初始化 PageSorter 实例。"""
        super().__init__(model_path)

    def _load_model(self):
        """
        从预训练路径加载 LayoutLMv3ForTokenClassification 模型。
        """
        print(f"加载 XY_CUT 算法成功")

    def _get_bbox(self, item: Dict) -> tuple:
        """
        根据文本块的坐标多边形（poly）计算其轴对齐的边界框（Bounding Box）。

        Args:
            item (Dict): 包含 'poly' 键的字典，'poly' 的值是一个列表，表示多边形顶点的扁平化坐标 [x0, y0, x1, y1, ...]。

        Returns:
            tuple: 边界框坐标 (x0, y0, x1, y1)。
        """
        # 从扁平化列表中分别提取 x 和 y 坐标
        poly = item['poly']
        x0, y0 = min(poly[0::2]), min(poly[1::2])
        x1, y1 = max(poly[0::2]), max(poly[1::2])
        return (x0, y0, x1, y1)

    def sort_page(self, text_blocks: List[Dict]) -> List[Dict]:
        """
        对给定页面的文本块列表进行排序。
        这是排序算法的主入口点，它协调了所有子步骤。

        Args:
            text_blocks (List[Dict]): 页面上所有文本块的列表。每个文本块是一个字典，至少包含 'poly' 键。

        Returns:
            List[Dict]: 按照阅读顺序排序后的文本块列表。
        """
        if not text_blocks:
            return []

        units = []
        page_l, page_r = float("inf"), -1
        # 1. 计算每个文本块的边界框，并记录页面的左右边界
        for tb in text_blocks:
            bbox = self._get_bbox(tb)
            units.append((bbox, tb))
            if bbox[0] < page_l: page_l = bbox[0]
            if bbox[2] > page_r: page_r = bbox[2]

        # 2. 按文本块的顶部坐标对它们进行排序，以便按行处理
        units.sort(key=lambda a: a[0][1])

        # 3. 计算页面上的垂直切割线（cuts）和文本行（rows）
        cuts, rows = self._get_cuts_rows(units, page_l, page_r)

        # 4. 根据切割线和行构建布局树
        root = self._get_layout_tree(cuts, rows)

        # 5. 对布局树进行前序遍历，得到排序后的节点列表
        nodes = self._preorder_traversal(root)

        # 6. 从排序后的节点中提取原始文本块数据
        new_text_blocks = self._get_text_blocks(nodes)

        return new_text_blocks

    def get_sorted_indices(self, text_blocks: List[Dict]) -> List[int]:
        """
        处理排序后的文本块列表，并返回它们在原始输入列表中的索引。
        这是一个便捷方法，用于获取排序结果的索引。

        Args:
            text_blocks (List[Dict]): 页面上所有文本块的列表。每个文本块是一个字典，至少包含 'poly' 键。

        Returns:
            List[int]: 按照阅读顺序排序后的文本块索引列表。
        """
        if not text_blocks:
            return []

        # 在排序前，为每个文本块添加一个临时的 'original_index' 键
        # 这样在排序后我们仍然可以找到其原始位置
        indexed_text_blocks = [dict(tb, original_index=i) for i, tb in enumerate(text_blocks)]
        # 调用现有的排序方法
        sorted_text_blocks = self.sort_page(indexed_text_blocks)
        # 提取并返回排序后的索引
        return [tb['original_index'] for tb in sorted_text_blocks]

    def batch_predict(self, pages:List[List[Dict[str, Any]]]) -> List[List[int]]:
        """
        对多个页面的文本块进行批处理排序，并返回每个页面的排序索引列表。

        Args:
            pages (List[List[Dict]]): 包含多个页面的列表。每个页面是 text_blocks 的列表。

        Returns:
            List[List[int]]: 每个页面的排序后的文本块索引列表。
        """
        return [self.get_sorted_indices(page) for page in pages]

    def _update_gaps(self, gaps1: List, gaps2: List):
        """
        更新和合并水平间隙。此函数用于在处理每一行时，将当前行的间隙与累积的间隙进行合并。

        Args:
            gaps1 (List): 累积的间隙列表。
            gaps2 (List): 当前行的间隙列表。

        Returns:
            tuple: 包含两个列表的元组 (new_gaps1, del_gaps1)。
                   - new_gaps1: 更新和合并后的新间隙列表。
                   - del_gaps1: 在合并过程中被 '关闭' 或 '完成' 的间隙列表。
        """
        flags1, flags2 = [True] * len(gaps1), [True] * len(gaps2)
        new_gaps1 = []
        # 查找间隙的重叠部分，这些重叠部分形成了新的、更窄的间隙
        for i1, g1 in enumerate(gaps1):
            for i2, g2 in enumerate(gaps2):
                inter_l = max(g1[0], g2[0])
                inter_r = min(g1[1], g2[1])
                if inter_l <= inter_r:
                    new_gaps1.append((inter_l, inter_r, g1[2]))
                    flags1[i1] = flags2[i2] = False
        # 将 gaps2 中未与 gaps1 重叠的部分添加到 new_gaps1
        for i2, f2 in enumerate(flags2):
            if f2: new_gaps1.append(gaps2[i2])
        # 提取在合并过程中未被任何新间隙覆盖的旧间隙，它们代表垂直切割线
        del_gaps1 = [gaps1[i1] for i1, f1 in enumerate(flags1) if f1]
        return new_gaps1, del_gaps1

    def _get_cuts_rows(self, units: List, page_l: float, page_r: float):
        """
        根据排序后的文本块，识别页面上的垂直切割线和逻辑文本行。

        Args:
            units (List): 包含 (bbox, text_block) 的元组列表，已按 y 坐标排序。
            page_l (float): 页面的左边界。
            page_r (float): 页面的右边界。

        Returns:
            tuple: 包含两个列表的元组 (completed_cuts, rows)。
                   - completed_cuts: 所有已识别的垂直切割线。
                   - rows: 包含按行分组的文本块。
        """
        page_l -= 1;
        page_r += 1
        rows, completed_cuts, gaps = [], [], []
        row_index = unit_index = 0
        while unit_index < len(units):
            unit = units[unit_index]
            u_bottom = unit[0][3]
            row = [unit]
            next_idx = unit_index
            # 识别同一行中的所有文本块
            for i in range(unit_index + 1, len(units)):
                if units[i][0][1] > u_bottom: break
                row.append(units[i])
                next_idx = i
            unit_index = next_idx

            row.sort(key=lambda x: x[0][0])
            row_gaps = []
            search_start = page_l
            # 识别当前行中的水平间隙
            for u in row:
                l, r = u[0][0], u[0][2]
                if l > search_start: row_gaps.append((search_start, l, row_index))
                if r > search_start: search_start = r
            row_gaps.append((search_start, page_r, row_index))

            # 更新和合并间隙
            gaps, del_gaps = self._update_gaps(gaps, row_gaps)
            # 将 '关闭' 的间隙视为垂直切割线
            for dg1 in del_gaps: completed_cuts.append((*dg1, row_index - 1))
            rows.append(row)
            unit_index += 1;
            row_index += 1

        # 将页面末尾未关闭的间隙也视为切割线
        for g in gaps: completed_cuts.append((*g, len(rows) - 1))
        completed_cuts.sort(key=lambda c: c[0])
        return completed_cuts, rows

    def _get_layout_tree(self, cuts: List, rows: List):
        """
        根据垂直切割线和文本行构建一个布局树。
        布局树的节点代表逻辑区域，子节点表示其内部的子区域。

        Args:
            cuts (List): 垂直切割线列表。
            rows (List): 文本行列表。

        Returns:
            Dict: 布局树的根节点。
        """
        if not cuts: return None

        # 将切割线与它们所跨越的行关联起来
        rows_gaps = [[] for _ in rows]
        for cut in cuts:
            for r_i in range(cut[2], cut[3] + 1): rows_gaps[r_i].append((cut[0], cut[1]))

        root = {"x_left": cuts[0][0] - 1, "x_right": cuts[-1][1] + 1, "r_top": -1, "r_bottom": -1, "units": [],
                "children": []}
        completed_nodes, now_nodes = [root], []

        def complete(node):
            """将节点与其父节点关联并标记为完成。"""
            node_r, max_r = node["x_right"] - 2, -2
            max_nodes = []
            for com_node in completed_nodes:
                if not (com_node["x_left"] <= node_r < com_node["x_right"] + 1e-4): continue
                if com_node["r_bottom"] >= node["r_top"]: continue
                if com_node["r_bottom"] > max_r:
                    max_r, max_nodes = com_node["r_bottom"], [com_node]
                elif com_node["r_bottom"] == max_r:
                    max_nodes.append(com_node)
            if max_nodes:
                max(max_nodes, key=lambda n: n["x_right"])["children"].append(node)
                completed_nodes.append(node)

        # 遍历每一行来构建树
        for r_i, row in enumerate(rows):
            row_gaps = rows_gaps[r_i]
            new_nodes = []
            # 检查当前节点是否被新的间隙“切断”，如果是则完成它
            for node in now_nodes:
                l_flag, r_flag, completed_flag = False, False, False
                for gap in row_gaps:
                    if abs(gap[1] - node["x_left"]) < 1e-4: l_flag = True
                    if abs(gap[0] - node["x_right"]) < 1e-4: r_flag = True
                    if node["x_left"] < gap[0] < node["x_right"] or node["x_left"] < gap[1] < node["x_right"]:
                        completed_flag = True
                        break
                if not l_flag or not r_flag: completed_flag = True
                if completed_flag:
                    complete(node)
                else:
                    node["r_bottom"] = r_i
                    new_nodes.append(node)
            now_nodes = new_nodes

            u_i = g_i = 0
            # 为当前行的每个文本块创建新的节点或添加到现有节点
            while u_i < len(row):
                unit = row[u_i]
                if g_i >= len(row_gaps) - 1: u_i += 1; continue
                x_l, x_r = row_gaps[g_i][1], row_gaps[g_i + 1][0]
                if unit[0][0] + 1e-4 > x_r: g_i += 1; continue
                flag = False
                for node in now_nodes:
                    if abs(node["x_left"] - x_l) < 1e-4 and abs(node["x_right"] - x_r) < 1e-4:
                        node["units"].append(unit)
                        flag = True
                        break
                if flag: u_i += 1; continue
                now_nodes.append(
                    {"x_left": x_l, "x_right": x_r, "r_top": r_i, "r_bottom": r_i, "units": [unit], "children": []})
                u_i += 1

        for node in now_nodes: complete(node)
        for node in completed_nodes:
            node["children"].sort(key=lambda n: n["x_left"])
            node["units"].sort(key=lambda u: u[0][1])
        return root

    def _preorder_traversal(self, root: Dict) -> List[Dict]:
        """
        对布局树进行前序遍历（根-左-右），这是生成阅读顺序的关键步骤。

        Args:
            root (Dict): 布局树的根节点。

        Returns:
            List[Dict]: 按前序遍历顺序排列的节点列表。
        """
        if not root: return []
        stack, result = [root], []
        while stack:
            node = stack.pop()
            result.append(node)
            # 子节点按 x_left 排序，但要反向压入栈，以保证遍历时按从左到右的顺序
            stack.extend(reversed(node["children"]))
        return result

    def _get_text_blocks(self, nodes: List[Dict]) -> List[Dict]:
        """
        从排序后的节点列表中提取原始的文本块数据。

        Args:
            nodes (List[Dict]): 排序后的节点列表。

        Returns:
            List[Dict]: 按照最终阅读顺序排列的文本块列表。
        """
        return [unit[1] for node in nodes for unit in node["units"]]

    def names(self) -> Dict[int, str]:
        """
        LayoutReader 模型不预测类别，因此此属性返回一个空字典。
        """
        return {}