document.addEventListener('DOMContentLoaded', function() {
    const inputField = document.getElementById('question');
    const submitButton = document.getElementById('submit-btn');
    const chatContainer = document.querySelector('.chat-center');
    const form = document.getElementById('chat-form');
    const input = document.getElementById('question');
    let isBotTyping = false; // Track if bot is currently typing
    let userHasScrolled = false; // Track if user has manually scrolled up

    let fetchController = null;

    input.addEventListener('input', toggleSubmitButton);

    function toggleSubmitButton() {

    if (isBotTyping) {
        submitButton.style.opacity = "1";
        submitButton.style.visibility = "visible";
        submitButton.disabled = false;
    } else if (inputField.value.trim() !== "") {
        submitButton.style.opacity = "1";
        submitButton.style.visibility = "visible";
        submitButton.disabled = false;
    } else {
        submitButton.style.opacity = "0";
        submitButton.style.visibility = "hidden";
        submitButton.disabled = true;
    }
}

input.addEventListener('keypress', function(e) {
    if (e.key === 'Enter' && !e.shiftKey)  {
    e.preventDefault();
    if (isBotTyping) {
        stopBotTyping();
    } else if (input.value.trim() !== "") {
        form.requestSubmit(); // ✅ More reliable
    }
}
});
    // Stop bot typing function
    function stopBotTyping() {
        isBotTyping = false;
        userHasScrolled = false; // Reset scroll tracking
        if (fetchController) {
        fetchController.abort();
        fetchController = null;
        }
        // Change button back to send
        submitButton.textContent = '→';
        submitButton.style.background = 'linear-gradient(135deg, #009b7c 0%, #00b894 100%)';
        submitButton.disabled = false;
        submitButton.style.opacity = "1";
        
        // Remove any loading bubble
        const loadingBubbles = document.querySelectorAll('.loading');
        loadingBubbles.forEach(bubble => bubble.remove());

        // Remove the blinking cursor from the last bot bubble
        const botBubbles = document.querySelectorAll('.bot-bubble');
        if (botBubbles.length > 0) {
            const lastBotBubble = botBubbles[botBubbles.length - 1];
            const cursor = lastBotBubble.querySelector('.typing-cursor');
            if (cursor) {
                cursor.remove();
            }
        }
    }

    // Auto-scroll to bottom when new message is added
    function scrollToBottom() {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'auto' });
    }

    // Smart scroll that respects user intervention
    function smartScrollToBottom() {
        if (!userHasScrolled) {
            scrollToBottom();
        }
    }

    // Detect user scroll intervention
    window.addEventListener('scroll', function() {
        // How far from the bottom is the user?
        const scrollBuffer = 50; // px, how close to bottom counts as "at bottom"
        const atBottom = (window.innerHeight + window.scrollY) >= (document.body.offsetHeight - scrollBuffer);

        if (atBottom) {
            userHasScrolled = false; // User is at the bottom, allow autoscroll
        } else {
            userHasScrolled = true; // User scrolled up, disable autoscroll
        }
    });

    // Handle form submission
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        if(submitButton.disabled && !isBotTyping) {
            return;  // Prevent multiple submissions
        }

        if (isBotTyping) {
            stopBotTyping();
            return;
        }

        submitButton.disabled = true;
        submitButton.style.opacity = "0.5";
        const userMessage = input.value.trim();

        if (userMessage) {
            // Add user message to chat
            const userBubble = document.createElement('div');
            userBubble.classList.add('chat-bubble', 'user-bubble');
            userBubble.textContent = userMessage;
            chatContainer.appendChild(userBubble);

            // Clear the input field
            input.value = '';

            // Show animated typing indicator instead of static 'Processing...'
            const loadingBubble = document.createElement('div');
            loadingBubble.classList.add('chat-bubble', 'bot-bubble', 'loading');
       
            loadingBubble.innerHTML = '<span class="typing-indicator"><span></span><span></span><span></span></span>';
            
            chatContainer.appendChild(loadingBubble);
            setTimeout(scrollToBottom, 50);

            // Fetch bot response from the server
            fetchController = new AbortController();
            fetch("/get-bot-response", {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: userMessage}),
                signal: fetchController.signal
            })
.then(response => {
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Remove loading bubble immediately when we get response
    loadingBubble.remove();

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let responseText = '';

    const botBubble = document.createElement('div');
    botBubble.classList.add('chat-bubble', 'bot-bubble');
    chatContainer.appendChild(botBubble);

    isBotTyping = true;
    submitButton.textContent = '■';
    submitButton.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
    submitButton.disabled = false;
    submitButton.style.opacity = "1";

    function readStream() {
        return reader.read().then(({ done, value }) => {
            if (done) {
                // After streaming, render as markdown (no cursor)
                const formattedText = marked.parse(responseText);
                botBubble.innerHTML = formattedText;
                isBotTyping = false;
                submitButton.textContent = '→';
                submitButton.style.background = 'linear-gradient(135deg, #009b7c 0%, #00b894 100%)';
                submitButton.disabled = false;
                submitButton.style.opacity = "1";
                return;
            }

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    lines.forEach(line => {
        line = line.trim();

        if (line && line.startsWith('data:')) {
                const jsonStr = line.slice(6).trim(); // removes 'data:'
            try {
                const data = JSON.parse(jsonStr);
                if (!isBotTyping) {
                        return; // Stop processing this chunk
                    }
                if (data.content) {
                    
                    responseText += data.content;
                    const formattedText = marked.parse(responseText);
                    botBubble.innerHTML = formattedText + '<span class="typing-cursor"></span>';
                    smartScrollToBottom();
                }

                if (data.end) {
                    const formattedText = marked.parse(responseText);
                    botBubble.innerHTML = formattedText;
                    isBotTyping = false;
                    submitButton.textContent = '→';
                    submitButton.style.background = 'linear-gradient(135deg, #009b7c 0%, #00b894 100%)';
                    submitButton.disabled = false;
                    submitButton.style.opacity = "1";
                }

                if (data.error) {
                    botBubble.innerHTML = `Error: ${data.error}`;
                    isBotTyping = false;
                }
            } catch (e) {
                console.error('Error parsing stream data:', e, jsonStr);
            }
        }
    });


            if (isBotTyping) {
                return readStream();
            }
        });
    }

    return readStream();
})
            .catch(error => {
                if (error.name === 'AbortError') {
                    // User stopped the bot, do not show error bubble
                    return;
                }
                console.error('Error fetching bot response:', error);

                const errorBubble = document.createElement('div');
                errorBubble.classList.add('chat-bubble', 'error-bubble');
                errorBubble.textContent = "I'm having trouble connecting right now. This could be due to network issues or too many requests. Please try again shortly.";
                chatContainer.appendChild(errorBubble);
                setTimeout(scrollToBottom, 50);
            })
            .finally(() => {
                // Re-enable the submit button after the response is processed
                if (!isBotTyping) {
                    submitButton.style.opacity = "1";
                    submitButton.disabled = false;
                }
            });
        }
    });

    function toggleSubmitButton() {
        const inputField = document.getElementById('question');

        // Always show the button when bot is typing, regardless of input field content
        if (isBotTyping) {
            submitButton.style.opacity = "1";
            submitButton.style.visibility = "visible";
            submitButton.disabled = false;
        } else if (inputField.value.trim() !== "") {
            // Show send button when there's input and bot is not typing
            submitButton.style.opacity = "1";
            submitButton.style.visibility = "visible";
            submitButton.disabled = false;
        } else {
            // Hide button when no input and bot is not typing
            submitButton.style.opacity = "0";
            submitButton.style.visibility = "hidden";
            submitButton.disabled = true;
        }
    }

    // Auto-scroll on load
    setTimeout(scrollToBottom, 50);
});

