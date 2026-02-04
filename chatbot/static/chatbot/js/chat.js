// Global variables
let currentRoom = '';
let typingTimer;
let chatSocket = null;
const typingDelay = 1000;

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    currentRoom = document.body.dataset.roomName || '';
    
    // Tab switching
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById(this.dataset.tab + '-tab').classList.add('active');
        });
    });
    
    // Chat item click
    document.querySelectorAll('.chat-item').forEach(item => {
        item.addEventListener('click', function() {
            const roomName = this.dataset.room;
            window.location.href = `/room/${roomName}/`;
        });
    });
    
    // Theme toggle
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Load messages if in a room
    if (currentRoom) {
        loadMessages();
        connectWebSocket();
        setInterval(getOnlineUsers, 10000);
    }
    
    // Message input events
    const messageInput = document.getElementById('message-input');
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        messageInput.addEventListener('input', function() {
            // Send typing indicator
            clearTimeout(typingTimer);
            sendTypingIndicator(true);
            
            typingTimer = setTimeout(function() {
                sendTypingIndicator(false);
            }, typingDelay);
        });
    }
    
    // Search users
    const searchUsersInput = document.getElementById('search-users-input');
    if (searchUsersInput) {
        const debouncedSearch = debounce(function() {
            searchUsers(this.value);
        }, 300);
        
        searchUsersInput.addEventListener('input', debouncedSearch);
    }
});

// WebSocket functions
function connectWebSocket() {
    if (currentRoom) {
        // Close existing connection if any
        if (chatSocket) {
            chatSocket.close();
        }

        // Create new WebSocket connection
        const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsPath = wsScheme + '//' + window.location.host + '/ws/chat/' + currentRoom + '/';
        
        console.log('Connecting to WebSocket:', wsPath);
        
        chatSocket = new WebSocket(wsPath);

        chatSocket.onopen = function(e) {
            console.log('WebSocket connected successfully');
        };

        chatSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
    
            if (data.type === 'chat_message') {
                addMessageToUI(data);
            } else if (data.type === 'typing') {
                handleTypingIndicator(data);
            }
        };

        chatSocket.onclose = function(e) {
            console.log('Chat socket closed, reconnecting...');
            setTimeout(connectWebSocket, 2000);
        };

        chatSocket.onerror = function(e) {
            console.error('WebSocket error:', e);
        };
    }
}

function sendTypingIndicator(isTyping) {
    if (!currentRoom || !chatSocket || chatSocket.readyState !== WebSocket.OPEN) return;
    
    chatSocket.send(JSON.stringify({
        'type': 'typing',
        'is_typing': isTyping
    }));
}

function handleTypingIndicator(data) {
    const typingIndicator = document.getElementById('typing-indicator-text');
    if (data.is_typing && data.username !== window.currentUsername) {
        typingIndicator.textContent = `${data.username} is typing...`;
        typingIndicator.style.display = 'block';
    } else {
        typingIndicator.style.display = 'none';
    }
}

// Message functions
function addMessageToUI(data) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    const messageEl = document.createElement('div');
    const isCurrentUser = data.username === window.currentUsername;
    messageEl.className = `message ${isCurrentUser ? 'user' : 'other'}`;
    messageEl.dataset.messageId = data.message_id;

    messageEl.innerHTML = `
        ${escapeHtml(data.message)}
        <div class="message-info">
            <span>${data.timestamp}</span>
        </div>
    `;

    messagesContainer.appendChild(messageEl);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function loadMessages() {
    if (!currentRoom) return;
    
    fetch(`/api/messages/${currentRoom}/`)
        .then(response => response.json())
        .then(data => {
            const messagesContainer = document.getElementById('chat-messages');
            if (!messagesContainer) return;
            
            messagesContainer.innerHTML = '';
            
            data.messages.forEach(msg => {
                const messageEl = document.createElement('div');
                messageEl.className = `message ${msg.is_current_user ? 'user' : 'other'}`;
                messageEl.dataset.messageId = msg.id;
                
                let messageHtml = escapeHtml(msg.message);
                if (msg.file_url) {
                    if (msg.file_type === 'image') {
                        messageHtml += `<div><img src="${msg.file_url}" style="max-width: 200px; border-radius: 10px; margin-top: 5px;"></div>`;
                    } else {
                        messageHtml += `<div><a href="${msg.file_url}" target="_blank">Download file</a></div>`;
                    }
                }
                
                messageHtml += `<div class="message-info">
                    <span>${msg.timestamp}</span>
                    ${msg.edited ? '<span>(edited)</span>' : ''}
                    ${msg.is_current_user && msg.read_by.length > 1 ? '<span>✓✓ Read</span>' : 
                      msg.is_current_user ? '<span>✓ Sent</span>' : ''}
                </div>`;
                
                if (msg.is_current_user) {
                    messageHtml += `<div class="message-actions">
                        <button class="message-action-btn" onclick="editMessage(${msg.id})"><i class="fas fa-edit"></i></button>
                        <button class="message-action-btn" onclick="deleteMessage(${msg.id})"><i class="fas fa-trash"></i></button>
                    </div>`;
                }
                
                messageEl.innerHTML = messageHtml;
                messagesContainer.appendChild(messageEl);
            });
            
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        })
        .catch(error => {
            console.error('Error loading messages:', error);
            showNotification('Failed to load messages', true);
        });
}

function sendMessage() {
    const messageInput = document.getElementById('message-input');
    if (!messageInput || !messageInput.value.trim()) return;

    // Send via WebSocket for real-time delivery
    if (chatSocket && chatSocket.readyState === WebSocket.OPEN) {
        chatSocket.send(JSON.stringify({
            'type': 'chat_message',
            'message': messageInput.value.trim()
        }));
    }

    // Also send via HTTP for persistence
    fetch(`/api/send-message/${currentRoom}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: messageInput.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            messageInput.value = '';
            messageInput.style.height = 'auto';
        } else {
            showNotification(data.message, true);
        }
    })
    .catch(error => {
        console.error('Error sending message:', error);
        showNotification('Failed to send message', true);
    });
}

function uploadFile() {
    const fileInput = document.getElementById('file-input');
    if (!fileInput.files.length) return;
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('message', 'File shared');
    
    fetch(`/api/send-message/${currentRoom}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            fileInput.value = '';
            loadMessages();
        } else {
            showNotification(data.message, true);
        }
    })
    .catch(error => {
        console.error('Error uploading file:', error);
        showNotification('Failed to upload file', true);
    });
}

function editMessage(messageId) {
    const newMessage = prompt('Edit your message:');
    if (newMessage !== null && newMessage.trim()) {
        fetch(`/api/edit-message/${messageId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: newMessage
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                loadMessages();
                showNotification('Message edited successfully');
            } else {
                showNotification(data.message, true);
            }
        })
        .catch(error => {
            console.error('Error editing message:', error);
            showNotification('Failed to edit message', true);
        });
    }
}

function deleteMessage(messageId) {
    if (confirm('Are you sure you want to delete this message?')) {
        fetch(`/api/delete-message/${messageId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                loadMessages();
                showNotification('Message deleted successfully');
            } else {
                showNotification(data.message, true);
            }
        })
        .catch(error => {
            console.error('Error deleting message:', error);
            showNotification('Failed to delete message', true);
        });
    }
}

// Friend functions
function addFriend(username) {
    fetch(`/add-friend/${username}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.status !== 'success');
        if (data.status === 'success') {
            setTimeout(() => location.reload(), 1000);
        }
    })
    .catch(error => {
        console.error('Error adding friend:', error);
        showNotification('Failed to send friend request', true);
    });
}

function acceptFriend(friendshipId) {
    fetch(`/accept-friend/${friendshipId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.status !== 'success');
        if (data.status === 'success') {
            setTimeout(() => location.reload(), 1000);
        }
    })
    .catch(error => {
        console.error('Error accepting friend:', error);
        showNotification('Failed to accept friend request', true);
    });
}

function rejectFriend(friendshipId) {
    fetch(`/reject-friend/${friendshipId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.status !== 'success');
        if (data.status === 'success') {
            setTimeout(() => location.reload(), 1000);
        }
    })
    .catch(error => {
        console.error('Error rejecting friend:', error);
        showNotification('Failed to reject friend request', true);
    });
}

function removeFriend(username) {
    if (confirm(`Are you sure you want to remove ${username} from your friends?`)) {
        fetch(`/remove-friend/${username}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => response.json())
        .then(data => {
            showNotification(data.message, data.status !== 'success');
            if (data.status === 'success') {
                setTimeout(() => location.reload(), 1000);
            }
        })
        .catch(error => {
            console.error('Error removing friend:', error);
            showNotification('Failed to remove friend', true);
        });
    }
}

function createPrivateChat(username) {
    fetch(`/create-private-chat/${username}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            window.location.href = `/room/${data.room_name}/`;
        } else {
            showNotification(data.message, true);
        }
    })
    .catch(error => {
        console.error('Error creating private chat:', error);
        showNotification('Failed to create private chat', true);
    });
}

// Search functions
function searchUsers(query) {
    if (query.length < 2) {
        document.getElementById('search-results').innerHTML = '';
        document.getElementById('suggested-users').style.display = 'block';
        return;
    }

    fetch(`/api/search-users/?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            const resultsContainer = document.getElementById('search-results');
            const suggestedContainer = document.getElementById('suggested-users');
    
            suggestedContainer.style.display = 'none';
            resultsContainer.innerHTML = '';
    
            if (data.users.length === 0) {
                resultsContainer.innerHTML = '<div class="empty-chat" style="padding: 20px; text-align: center;"><p>No users found</p></div>';
                return;
            }
    
            data.users.forEach(user => {
                const userEl = document.createElement('div');
                userEl.className = 'friend-item';
                userEl.innerHTML = `
                    <div class="avatar-container">
                        <div class="friend-avatar">${user.username[0].toUpperCase()}</div>
                        ${user.is_online ? '<div class="online-dot"></div>' : ''}
                    </div>
                    <div class="friend-info">
                        <div class="friend-name">${user.username}</div>
                    </div>
                    <div class="friend-actions">
                        <button class="friend-btn btn-primary" onclick="addFriend('${user.username}')">
                            <i class="fas fa-user-plus"></i> Add
                        </button>
                    </div>
                `;
                resultsContainer.appendChild(userEl);
            });
        })
        .catch(error => {
            console.error('Error searching users:', error);
            showNotification('Failed to search users', true);
        });
}

// Theme functions
function toggleTheme() {
    fetch("/api/toggle-theme/", {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            document.body.setAttribute('data-theme', data.theme);
            const icon = document.querySelector('#theme-toggle i');
            if (icon) {
                icon.className = data.theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
            }
            showNotification(data.message);
        }
    });
}

// Online users
function getOnlineUsers() {
    fetch('/api/online-users/')
        .then(response => response.json())
        .then(data => {
            document.querySelectorAll('.friend-item, .chat-item').forEach(item => {
                const username = item.querySelector('.friend-name, .chat-name')?.textContent;
                const onlineDot = item.querySelector('.online-dot');
                
                if (username && data.online_users.some(user => user.username === username)) {
                    if (onlineDot) onlineDot.style.display = 'block';
                } else {
                    if (onlineDot) onlineDot.style.display = 'none';
                }
            });
        })
        .catch(error => {
            console.error('Error getting online users:', error);
        });
}