import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO


def convert_html_tables_to_markdown(content):
    """
    从字符串中提取所有 HTML 表格，将其转换为 Markdown 格式，
    然后将修改后的内容返回。

    Args:
        content (str): 包含 HTML 表格的原始字符串。

    Returns:
        str: 替换了表格内容的新字符串。
    """
    soup = BeautifulSoup(content, 'lxml')
    tables = soup.find_all('table')

    # 遍历所有找到的表格，并进行替换
    for table in tables:
        # 将表格内容转换为 pandas DataFrame
        df = pd.read_html(StringIO(str(table)))[0]
        # 将 DataFrame 转换为 Markdown 字符串
        markdown_table = df.to_markdown(index=False)

        # 将原始 HTML 表格替换为 Markdown 表格
        table.replace_with(markdown_table)

    # 返回修改后的字符串
    return str(soup)


# 示例使用
html_content = """
<table>
  <thead>
    <tr>
      <th>Project</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>My Cool Project</td>
      <td>Complete ✅</td>
    </tr>
    <tr>
      <td>Website | Backend</td>
      <td>In Progress</td>
    </tr>
    <tr>
      <td>Documentation</td>
      <td><a href="https://example.com">Read More</a></td>
    </tr>
  </tbody>
</table>
"""

content_fix = convert_html_tables_to_markdown(html_content)
print(content_fix)