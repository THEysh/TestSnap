// src/utils/markdownUtils.js
import { ENDPOINTS } from '../constants/apiConfig';

// 更新图片路径，使其指向Flask API
export const updateImagePaths = (content, baseDir) => {
  const imgRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
  return content.replace(imgRegex, (match, alt, path) => {
    if (path.startsWith('http://') || path.startsWith('https://')) {
      return match;
    }
    if (path.startsWith('/api/files/')) {
      const relative = path.substring('/api/files/'.length);
      return `![${alt}](${ENDPOINTS.FILES}${relative})`;
    }
    if (path.startsWith('/api/')) {
      return match;
    }

    // 构建通过API访问的路径
    let newPath;
    if (baseDir && !path.startsWith('./') && !path.startsWith('../')) {
      // 相对于Markdown文件的路径
      newPath = `${ENDPOINTS.FILES}${baseDir}/${path}`;
    } else if (path.startsWith('./')) {
      // 当前目录相对路径
      newPath = `${ENDPOINTS.FILES}${baseDir}/${path.substring(2)}`;
    } else if (path.startsWith('../')) {
      // 上级目录相对路径，需要更复杂的处理
      const pathParts = baseDir.split('/').filter(p => p);
      const relativeParts = path.split('/').filter(p => p);

      // 处理../
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
      newPath = `${ENDPOINTS.FILES}${newBasePath ? newBasePath + '/' : ''}${remainingPath}`;
    } else {
      // 绝对路径（相对于项目根目录）
      newPath = `${ENDPOINTS.FILES}${path}`;
    }

    return `![${alt}](${newPath})`;
  });
};
