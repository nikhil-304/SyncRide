document.addEventListener('DOMContentLoaded', function() {
    // Only run if user is logged in (check for notifications dropdown)
    const notificationsDropdown = document.getElementById('notificationsDropdown');
    if (!notificationsDropdown) return;

    const notificationBadge = document.getElementById('notification-badge');
    const notificationsContainer = document.getElementById('notifications-container');
    const noNotifications = document.getElementById('no-notifications');

    // Function to fetch unread notification count
    function fetchUnreadCount() {
        fetch('/api/notifications/unread')
            .then(response => response.json())
            .then(data => {
                if (data.unread_count > 0) {
                    notificationBadge.textContent = data.unread_count;
                    notificationBadge.classList.remove('d-none');
                } else {
                    notificationBadge.classList.add('d-none');
                }
            })
            .catch(error => console.error('Error fetching notifications count:', error));
    }

    // Function to fetch and display notifications
    function fetchNotifications() {
        fetch('/api/notifications')
            .then(response => response.json())
            .then(data => {
                // Clear existing notification items (except header and divider)
                const items = notificationsContainer.querySelectorAll('.notification-item');
                items.forEach(item => item.remove());
                
                if (data.notifications && data.notifications.length > 0) {
                    noNotifications.classList.add('d-none');
                    
                    // Add notifications
                    data.notifications.forEach(notification => {
                        const li = document.createElement('li');
                        li.className = 'notification-item';
                        
                        const a = document.createElement('a');
                        a.className = 'dropdown-item d-flex align-items-center';
                        a.href = notification.link;
                        
                        const icon = document.createElement('div');
                        icon.className = 'me-3';
                        icon.innerHTML = `<i class="fas ${notification.icon}"></i>`;
                        
                        const content = document.createElement('div');
                        content.className = 'small';
                        
                        const text = document.createElement('div');
                        text.textContent = notification.text;
                        
                        const time = document.createElement('div');
                        time.className = 'text-muted';
                        time.textContent = new Date(notification.timestamp).toLocaleString();
                        
                        content.appendChild(text);
                        content.appendChild(time);
                        a.appendChild(icon);
                        a.appendChild(content);
                        li.appendChild(a);
                        
                        // Insert before the "No notifications" item
                        notificationsContainer.insertBefore(li, noNotifications.parentNode);
                    });
                } else {
                    noNotifications.classList.remove('d-none');
                }
            })
            .catch(error => console.error('Error fetching notifications:', error));
    }

    // Initial fetch
    fetchUnreadCount();
    
    // Fetch notifications when dropdown is opened
    notificationsDropdown.addEventListener('click', function() {
        fetchNotifications();
    });
    
    // Set up periodic refresh (every 30 seconds)
    setInterval(fetchUnreadCount, 30000);

    // Set up Socket.IO for real-time notifications
    if (typeof io !== 'undefined') {
        const socket = io();
        
        // Join user's notification room
        socket.on('connect', function() {
            socket.emit('join', {room: `user_${currentUserId}_notifications`});
        });
        
        // Listen for new message notifications
        socket.on('new_message_notification', function(data) {
            // Update badge count
            fetchUnreadCount();
            
            // Show browser notification if supported
            if ("Notification" in window && Notification.permission === "granted") {
                new Notification(`New message from ${data.sender_name}`, {
                    body: data.content_preview,
                    icon: '/static/img/logo.png'
                });
            }
        });
    }
});