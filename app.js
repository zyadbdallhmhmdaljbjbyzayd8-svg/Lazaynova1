document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:8787';
    const sendBtn = document.getElementById('sendBtn');
    const userInput = document.getElementById('userInput');
    const welcomeScreen = document.getElementById('welcomeScreen');
    const messagesContainer = document.getElementById('messagesContainer');
    let chatHistory = [];

    async function handleSendMessage() {
        const text = userInput.value.trim();
        if (!text) return;
        if (welcomeScreen) welcomeScreen.style.display = 'none';
        appendMessage(text, 'user');
        userInput.value = '';

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, language: 'ar', history: chatHistory })
            });
            const data = await response.json();
            if (response.ok && data.reply) {
                appendMessage(data.reply, 'assistant');
                chatHistory.push({ role: 'user', content: text });
                chatHistory.push({ role: 'assistant', content: data.reply });
            } else {
                appendMessage('عذراً، حدث خطأ في استجابة الخادم.', 'assistant');
            }
        } catch (error) {
            appendMessage('تعذر الاتصال بالخادم المحلي.', 'assistant');
        }
    }

    if (sendBtn) sendBtn.addEventListener('click', handleSendMessage);
    if (userInput) userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') handleSendMessage(); });

    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message-bubble ${sender}`;
        msgDiv.textContent = text;
        messagesContainer.appendChild(msgDiv);
    }
});
