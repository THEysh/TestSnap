// 创建 src/components/StatusMessage.jsx
import './StatusMessage.css';

const StatusMessage = ({ status, message }) => {
  if (!message) return null;
  
  return (
    <div className={`status-message status-${status}`}>
      {message}
    </div>
  );
};

export default StatusMessage;