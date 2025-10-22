# MMD 格式说明 (Multimodal Markdown)

## 📝 什么是 .mmd 文件?

`.mmd` 是 **Multimodal Markdown** 的缩写,是 DeepSeek OCR 输出的一种**扩展 Markdown 格式**。

## 🎯 为什么使用 .mmd 而不是 .md?

DeepSeek OCR 使用 `.mmd` 扩展名是因为它的输出包含了**标准 Markdown 之外的扩展元素**:

### 1. **图像引用标记** (`<|ref|>` 和 `<|det|>`)
```markdown
<|ref|>image<|/ref|><|det|>[[0, 0, 999, 1005]]<|/det|>
```
- `<|ref|>`: 引用标记,指示这是一个图像引用
- `<|det|>`: 检测坐标,包含边界框坐标 `[x1, y1, x2, y2]`

### 2. **内嵌图像处理**
模型会自动:
- 提取文档中的图像
- 保存到 `images/` 目录
- 在 MMD 文件中用标准 Markdown 图像语法引用:
  ```markdown
  ![](images/0.jpg)
  ![](images/1.jpg)
  ```

### 3. **数学公式和特殊符号**
自动处理特殊的 LaTeX 符号:
- `\coloneqq` → `:=`
- `\eqqcolon` → `=:`

## 📂 输出文件结构

DeepSeek OCR 解析后会生成以下文件:

```
output_path/
├── result.mmd                    # 主要的 MMD 格式输出
├── result_with_boxes.jpg         # 带有边界框标注的原图
├── images/                       # 提取的图像目录
│   ├── 0.jpg                     # 文档中的第一张图
│   ├── 1.jpg                     # 文档中的第二张图
│   └── ...
└── geo.jpg                       # (可选) 几何图形可视化
```

## 🔄 如何使用 .mmd 文件?

### 方案 1: 直接重命名为 .md

`.mmd` 文件的内容**基本上就是标准 Markdown**,可以直接重命名:

```bash
mv result.mmd result.md
```

然后用任何 Markdown 查看器打开。

### 方案 2: 转换为纯 Markdown

如果需要移除特殊标记,可以简单处理:

```python
def mmd_to_md(mmd_content: str) -> str:
    """将 MMD 格式转换为纯 Markdown"""
    import re
    
    # 移除 ref 和 det 标记
    content = re.sub(r'<\|ref\|>.*?<\|/ref\|>', '', mmd_content)
    content = re.sub(r'<\|det\|>.*?<\|/det\|>', '', content)
    
    # 清理多余的空行
    content = re.sub(r'\n\n+', '\n\n', content)
    
    return content.strip()

# 使用示例
with open('result.mmd', 'r', encoding='utf-8') as f:
    mmd_content = f.read()

md_content = mmd_to_md(mmd_content)

with open('result.md', 'w', encoding='utf-8') as f:
    f.write(md_content)
```

### 方案 3: 使用 Markdown 查看器

大多数 Markdown 查看器都能正确渲染 `.mmd` 文件中的标准 Markdown 部分:

- **VS Code**: 安装 Markdown 预览插件
- **Typora**: 直接打开
- **Obsidian**: 直接打开
- **网页查看器**: 如 [StackEdit](https://stackedit.io/)

## 📊 MMD 文件内容示例

```markdown
# 文档标题

这是一段普通的文本内容。

## 第一章

这里有一张图片:

![](images/0.jpg)

<|ref|>table<|/ref|><|det|>[[100, 200, 500, 400]]<|/det|>

| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 数据1 | 数据2 | 数据3 |

## 第二章

这里有数学公式: $E = mc^2$

更多内容...
```

## 🔧 在代码中处理 MMD 文件

### 读取并解析

```python
from pathlib import Path

def read_mmd_file(mmd_path: str) -> dict:
    """读取 MMD 文件并返回结构化数据"""
    mmd_path = Path(mmd_path)
    
    with open(mmd_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取图像路径
    import re
    images = re.findall(r'!\[\]\((images/\d+\.jpg)\)', content)
    
    # 提取引用标记
    refs = re.findall(r'<\|ref\|>(.*?)<\|/ref\|>', content)
    
    # 提取坐标
    coords = re.findall(r'<\|det\|>(.*?)<\|/det\|>', content)
    
    return {
        'content': content,
        'images': images,
        'references': refs,
        'coordinates': coords,
        'output_dir': mmd_path.parent
    }

# 使用示例
result = read_mmd_file('output/result.mmd')
print(f"文档包含 {len(result['images'])} 张图片")
print(f"文档包含 {len(result['references'])} 个引用")
```

### 转换为 HTML

```python
import markdown

def mmd_to_html(mmd_path: str, output_html: str):
    """将 MMD 转换为 HTML"""
    with open(mmd_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除特殊标记
    import re
    content = re.sub(r'<\|ref\|>.*?<\|/ref\|>', '', content)
    content = re.sub(r'<\|det\|>.*?<\|/det\|>', '', content)
    
    # 转换为 HTML
    html = markdown.markdown(content, extensions=['tables', 'fenced_code'])
    
    # 包装成完整的 HTML 页面
    html_page = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>文档</title>
        <style>
            body {{ 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px; 
                font-family: Arial, sans-serif;
            }}
            img {{ max-width: 100%; }}
            table {{ 
                border-collapse: collapse; 
                width: 100%; 
            }}
            th, td {{ 
                border: 1px solid #ddd; 
                padding: 8px; 
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """
    
    with open(output_html, 'w', encoding='utf-8') as f:
        f.write(html_page)
```

## 📖 技术细节

### 为什么不直接用 .md?

1. **避免混淆**: `.mmd` 明确表示这是多模态输出,包含特殊标记
2. **兼容性**: 某些 Markdown 解析器可能不正确处理 `<|ref|>` 等标记
3. **语义明确**: 表明这是 OCR 模型的原始输出,可能需要后处理

### 特殊标记的用途

- **`<|ref|>` 和 `<|det|>`**: 用于后处理,可以:
  - 重新定位文档中的元素
  - 生成带标注的可视化
  - 提取结构化数据
  - 进行版面分析

## 🎨 最佳实践

### 1. 对外分发时转换为 .md

```python
# 清理并重命名
import shutil
from pathlib import Path

def export_clean_markdown(mmd_path: str, output_md: str):
    """导出干净的 Markdown 文件"""
    with open(mmd_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除特殊标记
    import re
    content = re.sub(r'<\|ref\|>.*?<\|/ref\|><\|det\|>.*?<\|/det\|>', '', content)
    content = re.sub(r'\n\n+', '\n\n', content)
    
    with open(output_md, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    
    # 复制 images 目录
    mmd_dir = Path(mmd_path).parent
    output_dir = Path(output_md).parent
    
    if (mmd_dir / 'images').exists():
        shutil.copytree(
            mmd_dir / 'images', 
            output_dir / 'images',
            dirs_exist_ok=True
        )
```

### 2. 保留原始 .mmd 用于分析

保留 `.mmd` 文件和特殊标记,可以用于:
- 文档结构分析
- 重新布局
- 精确定位
- 质量评估

## 📚 参考资源

- [DeepSeek OCR GitHub](https://github.com/deepseek-ai/DeepSeek-OCR)
- [DeepSeek OCR 论文](https://arxiv.org/abs/2510.18234)
- [Markdown 规范](https://spec.commonmark.org/)

---

**总结**: `.mmd` 本质上就是**标准 Markdown + 少量元数据标记**,可以直接当作 `.md` 文件使用,或者简单清理后导出为纯 Markdown。

