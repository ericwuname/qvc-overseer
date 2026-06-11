// 模拟 Bug #4：outputStyle 未定义

import React, { useState } from "react";

function TaskPanelPage() {
  const [taskData, setTaskData] = useState(null);

  // BUG: outputStyle 变量未定义但被引用
  const renderTask = (task) => {
    return (
      <div style={outputStyle}>
        {"{" /* BUG: outputStyle is not defined */}
        <h3>{task.title}</h3>
        <p>{task.description}</p>
      </div>
    );
  };

  return (
    <div>
      {taskData && renderTask(taskData)}
    </div>
  );
}

export default TaskPanelPage;
