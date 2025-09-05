// src/utils/initExternalLibs.js

export const initExternalLibs = () => {
  if (typeof document === 'undefined') return;
  
  // 检查并加载marked.js
  if (!document.getElementById('marked-js')) {
    const markedScript = document.createElement('script');
    markedScript.id = 'marked-js';
    markedScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js';
    document.head.appendChild(markedScript);
  }

  // 检查并加载MathJax配置
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

  // 检查并加载MathJax脚本
  if (!document.getElementById('mathjax-script')) {
    const mathJaxScript = document.createElement('script');
    mathJaxScript.id = 'mathjax-script';
    mathJaxScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/mathjax/3.2.2/es5/tex-svg.js';
    mathJaxScript.async = true;
    document.head.appendChild(mathJaxScript);
  }
};