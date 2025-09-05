// 创建 src/hooks/useFileSelector.js
import { useState, useRef } from 'react';
import { validateFile } from '../utils/fileUtils';

const useFileSelector = () => {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);
  
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragover' || e.type === 'dragenter') {
      setDragActive(true);
    } else if (e.type === 'dragleave' || e.type === 'drop') {
      setDragActive(false);
    }
  };
  
  const handleFileChange = (e, onFileSelect) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const validation = validateFile(selectedFile);
      if (!validation.valid) {
        alert(validation.message);
        return;
      }
      onFileSelect(selectedFile);
    }
  };
  
  return {
    dragActive,
    fileInputRef,
    handleDrag,
    handleFileChange,
    openFileDialog: () => fileInputRef.current?.click()
  };
};

export default useFileSelector;