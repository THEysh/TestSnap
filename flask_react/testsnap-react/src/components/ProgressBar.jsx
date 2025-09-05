// 进度条组件
import './ProgressBar.css';

const ProgressBar = ({ progress, message }) => {
  if (progress <= 0) return null;
  
  return (
    <div className="progress-container">
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${progress}%` }} 
        />
      </div>
      <div className="progress-text">
        {message || `${progress.toFixed(2)}%`}
      </div>
    </div>
  );
};

export default ProgressBar;