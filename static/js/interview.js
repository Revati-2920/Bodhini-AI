document.addEventListener('DOMContentLoaded', function () {
    const chatBox = document.getElementById('chat-box');
    const answerForm = document.getElementById('answer-form');

    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    if (answerForm) {
        answerForm.addEventListener('submit', function () {
            const button = answerForm.querySelector('button');
            const typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            typingIndicator.innerHTML = '<span></span><span></span><span></span> Preparing feedback...';
            if (chatBox) {
                chatBox.appendChild(typingIndicator);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
            if (button) {
                button.disabled = true;
                button.textContent = 'Preparing feedback...';
            }
        });
    }
});
