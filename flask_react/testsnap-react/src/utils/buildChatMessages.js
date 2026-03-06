// 负责将历史记录、用户输入和附件拼成后端要求的 messages 数组
// 接口示例参见后端说明：支持 content 文本 + image_url/image_base64/images
export function extractImageUrlsFromHtml(html) {
  try {
    if (!html) return [];
    const div = document.createElement('div');
    div.innerHTML = html;
    const imgs = Array.from(div.querySelectorAll('img'));
    const urls = imgs
      .map(img => (img.getAttribute('src') || '').trim())
      .filter(Boolean)
      .map(src => {
        // 绝对 http(s)
        if (/^https?:\/\//i.test(src) || /^data:/i.test(src)) return src;
        // 绝对路径（以 / 开头），拼成同源绝对URL
        if (src.startsWith('/')) {
          try {
            const origin = typeof window !== 'undefined' ? window.location.origin : '';
            return origin ? origin + src : src;
          } catch {
            return src;
          }
        }
        // 相对路径：尽力拼到同源下
        try {
          const origin = typeof window !== 'undefined' ? window.location.origin : '';
          const pathname = typeof window !== 'undefined' ? window.location.pathname.replace(/\/+$/, '') : '';
          return origin ? `${origin}/${src}` : `${pathname}/${src}`;
        } catch {
          return src;
        }
      });
    return urls;
  } catch {
    return [];
  }
}

function buildUserContentWithTextAttachments(input, attachments) {
  const texts = (attachments || [])
    .filter(a => a && a.type !== 'image')
    .map(a => a?.rawMd || a?.text || '')
    .filter(Boolean);
  if (texts.length === 0) return input || '';
  const attachText = texts.join('\n\n---\n\n');
  const base = input || '';
  return `${base}${base ? '\n\n' : ''}参考内容：\n\n${attachText}\n\n用户的提问可能与参考内容相关，请结合参考内容作答。`;
}

export function buildMessages(history, input, attachments) {
  const messages = (history || []).map(m => ({
    role: m.role,
    content: m.content || ''
  }));
  const userMsg = {
    role: 'user',
    content: buildUserContentWithTextAttachments(input, attachments)
  };
  const imageUrls = [];
  (attachments || []).forEach(a => {
    if (a && a.type === 'image') {
      const urls = extractImageUrlsFromHtml(a.html || '');
      urls.forEach(u => {
        if (u && !imageUrls.includes(u)) imageUrls.push(u);
      });
    }
  });
  if (imageUrls.length === 1) {
    userMsg.image_url = imageUrls[0];
  } else if (imageUrls.length > 1) {
    userMsg.images = imageUrls;
  }
  messages.push(userMsg);
  return messages;
}
