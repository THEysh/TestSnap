import React, { useState, useEffect, useRef } from 'react';
import './MarkdownViewer.css';

const MarkdownViewer = ({ autoLoadPath }) => {


  // 添加CDN链接到head
  useEffect(() => {
    if (typeof document !== 'undefined') {
      // 检查是否已添加script标签
      if (!document.getElementById('marked-js')) {
        const markedScript = document.createElement('script');
        markedScript.id = 'marked-js';
        markedScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js';
        document.head.appendChild(markedScript);
      }

      if (!document.getElementById('mathjax-config')) {
        const mathJaxConfig = document.createElement('script');
        mathJaxConfig.id = 'mathjax-config';
        mathJaxConfig.textContent = `
          window.MathJax = {
            tex: {
              inlineMath: [['$', '$']],
              displayMath: [['$$', '$$']],
              processEscapes: true,
              processEnvironments: true,
              tags: 'ams'
            },
            svg: {
              fontCache: 'global',
              scale: 1.1
            },
            options: {
              renderActions: {
                findScript: [10, function (doc) {
                  for (const node of document.querySelectorAll('script[type^="math/tex"]')) {
                    const display = !!node.type.match(/; *mode=display/);
                    const math = new doc.options.MathItem(node.textContent, doc.inputJax[0], display);
                    const text = document.createTextNode('');
                    node.parentNode.replaceChild(text, node);
                    math.start = {node: text, delim: '', n: 0};
                    math.end = {node: text, delim: '', n: 0};
                    doc.math.push(math);
                  }
                }, '']
              }
            }
          };
        `;
        document.head.appendChild(mathJaxConfig);
      }

      if (!document.getElementById('mathjax-script')) {
        const mathJaxScript = document.createElement('script');
        mathJaxScript.id = 'mathjax-script';
        mathJaxScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg.js';
        mathJaxScript.async = true;
        document.head.appendChild(mathJaxScript);
      }
    }
  }, []);
  const [filePath, setFilePath] = useState('');
  const [markdownContent, setMarkdownContent] = useState('');
  const [statusMessage, setStatusMessage] = useState('');
  const [statusType, setStatusType] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [currentFileDir, setCurrentFileDir] = useState('');
  const [apiBaseUrl, setApiBaseUrl] = useState('http://localhost:7861/api/files');
  
  const previewRef = useRef(null);
  const timeoutRef = useRef(null);

  // 配置 marked
  useEffect(() => {
    if (typeof window !== 'undefined' && window.marked) {
      const renderer = new window.marked.Renderer();
      window.marked.setOptions({
        renderer: renderer,
        highlight: function(code, lang) {
          return code;
        },
        pedantic: false,
        gfm: true,
        breaks: true,
        sanitize: true, // 启用HTML特殊字符转义
        smartLists: true,
        smartypants: false,
        xhtml: false
      });
    }
  }, []);

  // 显示状态消息
  const showStatus = (message, type = 'info') => {
    setStatusMessage(message);
    setStatusType(type);
    
    if (type === 'success') {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(() => {
        setStatusMessage('');
        setStatusType('');
      }, 3000);
    }
  };

  // 更新图片路径，使其指向Flask API
  const updateImagePaths = (content, baseDir, apiUrl) => {
    const imgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
    return content.replace(imgRegex, (match, alt, path) => {
      // 检查路径是否已经是绝对路径或包含 http
      if (path.startsWith('http://') || path.startsWith('https://') || path.startsWith('/api/')) {
        return match;
      }

      // 构建通过API访问的路径
      let newPath;
      if (baseDir && !path.startsWith('./') && !path.startsWith('../')) {
        // 相对于Markdown文件的路径
        newPath = `${apiUrl}/${baseDir}/${path}`;
      } else if (path.startsWith('./')) {
        // 当前目录相对路径
        newPath = `${apiUrl}/${baseDir}/${path.substring(2)}`;
      } else if (path.startsWith('../')) {
        // 上级目录相对路径，需要更复杂的处理
        const pathParts = baseDir.split('/').filter(p => p);
        const relativeParts = path.split('/').filter(p => p);

        // 处理 ../
        let upLevels = 0;
        for (let part of relativeParts) {
          if (part === '..') {
            upLevels++;
          } else {
            break;
          }
        }

        // 构建新路径
        const remainingPath = relativeParts.slice(upLevels).join('/');
        const newBasePath = pathParts.slice(0, -upLevels).join('/');
        newPath = `${apiUrl}/${newBasePath ? newBasePath + '/' : ''}${remainingPath}`;
      } else {
        // 绝对路径（相对于项目根目录）
        newPath = `${apiUrl}/${path}`;
      }

      return `![${alt}](${newPath})`;
    });
  };

  // 渲染Markdown
  const renderMarkdown = (input) => {
    if (!previewRef.current || !window.marked) {
      return;
    }

    // 保护数学公式不被 Markdown 解析器处理
    let tempStorage = [];
    let tempIndex = 0;

    // 保护块级公式
    let protectedInput = input.replace(/\$\$[\s\S]*?\$\$/g, function(match) {
      const placeholder = `MATH_BLOCK_${tempIndex}`;
      tempStorage[tempIndex] = match;
      tempIndex++;
      return placeholder;
    });

    // 保护行内公式
    protectedInput = protectedInput.replace(/\$(?!\$)([^\$\n]+?)\$/g, function(match) {
      const placeholder = `MATH_INLINE_${tempIndex}`;
      tempStorage[tempIndex] = match;
      tempIndex++;
      return placeholder;
    });

    // 使用 marked 解析 Markdown
    let html = window.marked.parse(protectedInput);

    // 恢复数学公式
    html = html.replace(/MATH_BLOCK_(\d+)/g, function(match, index) {
      return tempStorage[parseInt(index)];
    });

    html = html.replace(/MATH_INLINE_(\d+)/g, function(match, index) {
      return tempStorage[parseInt(index)];
    });

    // 更新预览
    previewRef.current.innerHTML = html;

    // 触发 MathJax 重新渲染
    if (window.MathJax) {
      MathJax.typesetPromise([previewRef.current]).catch(function(err) {
        console.log('MathJax 渲染错误: ', err);
      });
    }
  };

  // 防抖函数
  const debounce = (func, wait) => {
    return function executedFunction(...args) {
      const later = () => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        func(...args);
      };
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      timeoutRef.current = setTimeout(later, wait);
    };
  };

  // 从后端加载Markdown文件
  const loadMarkdownFile = async (path) => {
    if (!path.trim()) {
      showStatus('请输入文件路径', 'error');
      return;
    }

    try {
      setIsLoading(true);
      showStatus('正在加载文件...', 'loading');

      // 直接使用正确的API路径，不依赖apiBaseUrl变量
      const response = await fetch('http://localhost:7861/api/markdown', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          path: path
        })
      });

      // 增强错误处理：检查响应状态和类型
      if (!response.ok) {
        const text = await response.text();
        throw new Error(`服务器返回错误状态码: ${response.status}\n响应内容: ${text.substring(0, 100)}...`);
      }

      // 尝试解析JSON，但增加额外检查
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const text = await response.text();
        throw new Error(`期望JSON响应，但收到: ${contentType || '未知类型'}\n内容: ${text.substring(0, 100)}...`);
      }

      const result = await response.json();

      if (result.success) {
        setCurrentFileDir(result.file_dir);
        // 更新API URL用于图片加载
        setApiBaseUrl('http://localhost:7861/api/files');

        // 处理图片路径并更新内容
        const updatedContent = updateImagePaths(result.content, result.file_dir, 'http://localhost:7861/api/files');

        setMarkdownContent(updatedContent);
        renderMarkdown(updatedContent);

        showStatus(`文件加载成功: ${result.file_path}`, 'success');
      } else {
        showStatus(`加载失败: ${result.error}`, 'error');
      }

    } catch (error) {
      console.error('请求失败:', error);
      // 显示更具体的错误信息
      let errorMessage = '网络请求失败，请检查服务器是否启动';
      if (error.message.includes('Unexpected token < in JSON')) {
        errorMessage = 'JSON解析错误: 服务器可能未启动或返回了HTML错误页面';
      } else if (error.message.includes('Failed to fetch')) {
        errorMessage = '无法连接到服务器: 请确认后端服务已在运行';
      } else {
        errorMessage = `请求失败: ${error.message}`;
      }
      showStatus(errorMessage, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // 处理内容变化
  const handleContentChange = (e) => {
    setMarkdownContent(e.target.value);
    debouncedRender(e.target.value);
  };

  // 防抖渲染
  const debouncedRender = debounce((content) => {
    renderMarkdown(content);
  }, 300);

  // 处理文件路径变化
  const handleFilePathChange = (e) => {
    setFilePath(e.target.value);
  };

  // 处理加载按钮点击
  const handleLoadButtonClick = () => {
    loadMarkdownFile(filePath);
  };

  // 处理回车键加载文件
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      loadMarkdownFile(filePath);
    }
  };

  // 组件卸载时清除定时器
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // 当autoLoadPath发生变化时，自动加载Markdown文件
  useEffect(() => {
    if (autoLoadPath) {
      setFilePath(autoLoadPath); 
      loadMarkdownFile(autoLoadPath);
    }
  }, [autoLoadPath]);

  return (
    <div className="markdown-container">
      <div className="header">
        <p>支持image,LaTeX数学公式的实时 Markdown 渲染</p>
        <p>    计算结果3小时后自动删除</p>

      </div>

      <div className="controls">
        <div className="path-input-group">
          <input
            type="text"
            id="file-path-input"
            placeholder="例如: srcProject/output/gae/gae.md"
            value={filePath}
            onChange={handleFilePathChange}
            onKeyPress={handleKeyPress}
          />
          <button 
            id="load-button"
            onClick={handleLoadButtonClick}
            disabled={isLoading}
          >
            加载文件
          </button>
        </div>
        {statusMessage && (
          <div className={`status-message status-${statusType}`}>
            {statusMessage}
          </div>
        )}
      </div>

      <div className="editor-container">
        <div className="editor-pane">
          <h2>Markdown 内容</h2>
          <textarea 
            id="markdown-input"
            value={markdownContent}
            onChange={handleContentChange}
            placeholder="在上方输入文件路径并点击加载，或直接在此处编辑Markdown内容..."
          />
        </div>
        <div className="preview-pane">
          <h2>渲染预览</h2>
          <div 
            id="preview"
            ref={previewRef}
          />
        </div>
      </div>
    </div>
  );
};

export default MarkdownViewer;