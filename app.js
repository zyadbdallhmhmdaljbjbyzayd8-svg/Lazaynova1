const API_BASE_URL = 'http://127.0.0.1:8788';
let currentEngineId = 'chat';

document.addEventListener('DOMContentLoaded', () => {
  const menuBtn = document.getElementById('menu-btn');
  const closeSidebar = document.getElementById('close-sidebar');
  const sidebar = document.getElementById('sidebar');
  const sidebarOverlay = document.getElementById('sidebar-overlay');
  
  const addBtn = document.getElementById('add-btn');
  const toolsModal = document.getElementById('tools-modal');
  const closeTools = document.getElementById('close-tools');
  
  const callBtn = document.getElementById('call-btn');
  const voiceCallOverlay = document.getElementById('voice-call-overlay');
  const endCall = document.getElementById('end-call');

  const sendBtn = document.getElementById('send-btn');
  const userInput = document.getElementById('user-input');
  const welcomeScreen = document.getElementById('welcome-screen');
  const chatContainer = document.getElementById('chat-container');

  // فتح وإغلاق القائمة الجانبية
  function toggleSidebar() {
    sidebar.classList.toggle('active');
    sidebarOverlay.classList.toggle('active');
  }
  menuBtn.addEventListener('click', toggleSidebar);
  closeSidebar.addEventListener('click', toggleSidebar);
  sidebarOverlay.addEventListener('click', toggleSidebar);

  // فتح نافذة الأدوات والمهام
  addBtn.addEventListener('click', () => {
    toolsModal.classList.add('active');
  });
  closeTools.addEventListener('click', () => {
    toolsModal.classList.remove('active');
  });

  // اختيار المحرك من القائمة
  document.querySelectorAll('.tool-card').forEach(card => {
    card.addEventListener('click', () => {
      currentEngineId = card.getAttribute('data-engine');
      toolsModal.classList.remove('active');
      userInput.placeholder = `اسأل محرك (${card.querySelector('.tool-name').textContent}) المحلي...`;
    });
  });

  // مكالمة صوتية
  callBtn.addEventListener('click', () => {
    voiceCallOverlay.classList.remove('hidden');
  });
  endCall.addEventListener('click', () => {
    voiceCallOverlay.classList.add('hidden');
  });

  // إرسال الرسالة إلى الخلفية السيادية
  async function handleSendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    if (welcomeScreen.style.display !== 'none') {
      welcomeScreen.style.display = 'none';
      chatContainer.classList.remove('hidden');
    }

    // إضافة رسالة المستخدم
    appendMessage(text, 'user');
    userInput.value = '';

    // إظهار مؤشر المعالجة المؤقتة
    const loadingId = appendMessage('جاري المعالجة محلياً عبر محركات Lazaynova...', 'assistant');

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          engineId: currentEngineId,
          useOrchestrator: true
        })
      });

      const data = await res.json();
      removeMessage(loadingId);
      
      if (data.response) {
        appendMessage(data.response, 'assistant');
      } else {
        appendMessage('[خطأ محلي]: لم يتم استلام رد من المحرك.', 'assistant');
      }
    } catch (err) {
      removeMessage(loadingId);
      appendMessage('[خطأ في الاتصال بالخادم المحلي]: تأكد أن خادم المنفذ 8788 يعمل.', 'assistant');
    }
  }

  sendBtn.addEventListener('click', handleSendMessage);
  userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleSendMessage();
  });

  function appendMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', sender);
    msgDiv.textContent = text;
    const msgId = 'msg-' + Date.now();
    msgDiv.id = msgId;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    return msgId;
  }

  function removeMessage(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }
});
