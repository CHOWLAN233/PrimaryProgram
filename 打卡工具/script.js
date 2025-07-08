// 获取DOM元素
const punchForm = document.getElementById('punchForm');
const punchInput = document.getElementById('punchInput');
const punchList = document.getElementById('punchList');
const exportBtn = document.getElementById('exportBtn');
const clearAllBtn = document.getElementById('clearAllBtn');

// 读取本地存储的打卡数据
function getPunchData() {
    const data = localStorage.getItem('punchData');
    return data ? JSON.parse(data) : [];
}

// 保存打卡数据到本地
function savePunchData(data) {
    localStorage.setItem('punchData', JSON.stringify(data));
}

// 渲染打卡记录，带删除按钮
function renderPunchList() {
    const data = getPunchData();
    punchList.innerHTML = '';
    data.slice().reverse().forEach((item, idx) => {
        const li = document.createElement('li');
        li.innerHTML = `<span>${item.text}</span><span class="date">${item.date}</span>`;
        // 删除按钮
        const delBtn = document.createElement('button');
        delBtn.textContent = '删除';
        delBtn.style.marginLeft = '10px';
        delBtn.onclick = function() {
            // 计算原始索引
            const originIdx = data.length - 1 - idx;
            data.splice(originIdx, 1);
            savePunchData(data);
            renderPunchList();
        };
        li.appendChild(delBtn);
        punchList.appendChild(li);
    });
}

// 提交打卡
punchForm.addEventListener('submit', function(e) {
    e.preventDefault();
    const text = punchInput.value.trim();
    if (!text) return;
    const now = new Date();
    const dateStr = now.toLocaleString('zh-CN', { hour12: false });
    const data = getPunchData();
    data.push({ text, date: dateStr });
    savePunchData(data);
    punchInput.value = '';
    renderPunchList();
});

// 页面加载时渲染打卡记录
renderPunchList();

exportBtn.addEventListener('click', function() {
    const data = getPunchData();
    if (data.length === 0) {
        alert('暂无打卡数据可导出！');
        return;
    }
    let content = '';
    data.forEach((item, idx) => {
        content += `【${idx+1}】${item.date}：${item.text}\n`;
    });
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'punch.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

// 清空全部打卡数据
clearAllBtn.addEventListener('click', function() {
    if (confirm('确定要清空全部打卡数据吗？此操作不可恢复！')) {
        savePunchData([]);
        renderPunchList();
    }
});  
