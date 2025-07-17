// Auto-scroll chat container to bottom
function scrollToBottom() {
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        setTimeout(() => {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }, 100);
    }
}

// Show coming soon modal
function showComingSoon() {
    // Create modal if it doesn't exist
    if (!document.getElementById('coming-soon-modal')) {
        const modal = document.createElement('div');
        modal.id = 'coming-soon-modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <span class="close" onclick="closeModal()">&times;</span>
                <h3 style="color: var(--pleasant-red); margin-bottom: 15px;">Coming Soon</h3>
                <p style="margin-bottom: 20px;">This feature is under development.</p>
                <button class="submit-button" onclick="closeModal()" style="padding: 8px 16px; font-size: 14px;">OK</button>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    document.getElementById('coming-soon-modal').style.display = 'block';
}

// Close modal
function closeModal() {
    const modal = document.getElementById('coming-soon-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('coming-soon-modal');
    if (event.target === modal) {
        modal.style.display = 'none';
    }
}

// Handle file upload
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-upload');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                // Add loading indicator
                const chatContainer = document.getElementById('chat-container');
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'bot-message';
                loadingDiv.innerHTML = '<strong>Assistant:</strong> <span class="loading"></span> Processing upload...';
                chatContainer.appendChild(loadingDiv);
                scrollToBottom();
                
                // The actual upload is handled by HTMX
                // Remove loading indicator after upload completes
                setTimeout(() => {
                    loadingDiv.remove();
                }, 2000);
            }
        });
    }
});

// Handle form submission with Enter key
document.addEventListener('DOMContentLoaded', function() {
    const textInput = document.querySelector('.text-input');
    if (textInput) {
        textInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                const form = this.closest('form');
                if (form && this.value.trim()) {
                    // Add loading indicator
                    const chatContainer = document.getElementById('chat-container');
                    const loadingDiv = document.createElement('div');
                    loadingDiv.className = 'bot-message';
                    loadingDiv.innerHTML = '<strong>Assistant:</strong> <span class="loading"></span> Thinking...';
                    chatContainer.appendChild(loadingDiv);
                    scrollToBottom();
                    
                    // Submit form
                    form.dispatchEvent(new Event('submit'));
                    
                    // Remove loading indicator after response
                    setTimeout(() => {
                        loadingDiv.remove();
                    }, 1000);
                }
            }
        });
    }
});

// Mobile menu toggle
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('active');
}

// Add mobile menu button if needed
document.addEventListener('DOMContentLoaded', function() {
    if (window.innerWidth <= 768) {
        const navbar = document.querySelector('.navbar');
        const menuButton = document.createElement('button');
        menuButton.innerHTML = '☰';
        menuButton.style.cssText = `
            background: none;
            border: none;
            color: white;
            font-size: 24px;
            cursor: pointer;
            margin-right: 15px;
        `;
        menuButton.onclick = toggleSidebar;
        navbar.insertBefore(menuButton, navbar.firstChild);
    }
});

// Handle window resize
window.addEventListener('resize', function() {
    if (window.innerWidth > 768) {
        document.querySelector('.sidebar').classList.remove('active');
    }
});

// HTMX event handlers
document.addEventListener('htmx:afterRequest', function(event) {
    // Auto-scroll after HTMX requests
    scrollToBottom();
    
    // Remove any loading indicators
    const loadingIndicators = document.querySelectorAll('.loading');
    loadingIndicators.forEach(indicator => {
        const parent = indicator.closest('.bot-message');
        if (parent) {
            parent.remove();
        }
    });
});

document.addEventListener('htmx:beforeRequest', function(event) {
    // Add loading indicator for requests
    if (event.target.tagName === 'FORM') {
        const chatContainer = document.getElementById('chat-container');
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'bot-message loading-message';
        loadingDiv.innerHTML = '<strong>Assistant:</strong> <span class="loading"></span> Processing...';
        chatContainer.appendChild(loadingDiv);
        scrollToBottom();
    }
});

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Initial scroll to bottom
    scrollToBottom();
    
    // Focus on input
    const textInput = document.querySelector('.text-input');
    if (textInput) {
        textInput.focus();
    }
    
    // Initialize calendar
    initializeCalendar();
    
    // Set initial active state (chat is active by default)
    updateActiveNavItem('chat');
    
    // Add fullscreen button
    addFullscreenButton();
});

// Earnings Calendar Variables
let currentDate = new Date();
let earningsData = {};

// Load earnings data
async function loadEarningsData() {
    try {
        const response = await fetch('/static/data/earnings_calendar.json');
        earningsData = await response.json();
    } catch (error) {
        console.error('Error loading earnings data:', error);
        earningsData = {};
    }
}

// Initialize calendar
async function initializeCalendar() {
    await loadEarningsData();
    renderCalendar();
}

// Show earnings calendar
function showEarningsCalendar() {
    document.getElementById('chat-section').style.display = 'none';
    document.getElementById('earnings-calendar-container').style.display = 'block';
    renderCalendar();
    
    // Update active state
    updateActiveNavItem('earnings-calendar');
}

// Show chat section (back to main view)
function showChatSection() {
    document.getElementById('earnings-calendar-container').style.display = 'none';
    document.getElementById('chat-section').style.display = 'block';
    
    // Update active state
    updateActiveNavItem('chat');
}

// Update active navigation item
function updateActiveNavItem(activeItem) {
    // Remove active class from all items
    document.querySelectorAll('.sidebar-item, .quick-actions-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Add active class to current item
    if (activeItem === 'chat') {
        document.querySelector('.sidebar-item[onclick*="showChatSection"]').classList.add('active');
    } else if (activeItem === 'earnings-calendar') {
        document.querySelector('.earnings-calendar-item').classList.add('active');
    }
}

// Reset chat function
function resetChat() {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = `
        <div class="bot-message">
            <strong>Assistant:</strong> Hello! I'm your Earnings Research assistant. Ask me anything about financial data, earnings analysis, or request charts and reports.
        </div>
    `;
    scrollToBottom();
}

// Fullscreen chat functionality
let isFullscreen = false;

function toggleFullscreenChat() {
    const mainContent = document.querySelector('.main-content');
    const sidebar = document.querySelector('.sidebar');
    const navbar = document.querySelector('.navbar');
    const fullscreenBtn = document.getElementById('fullscreen-btn');
    
    isFullscreen = !isFullscreen;
    
    if (isFullscreen) {
        // Enter fullscreen mode
        mainContent.classList.add('fullscreen-chat');
        sidebar.style.display = 'none';
        navbar.style.display = 'none';
        fullscreenBtn.innerHTML = '🗗'; // Exit fullscreen icon
        fullscreenBtn.title = 'Exit Fullscreen';
    } else {
        // Exit fullscreen mode
        mainContent.classList.remove('fullscreen-chat');
        sidebar.style.display = 'block';
        navbar.style.display = 'flex';
        fullscreenBtn.innerHTML = '🗖'; // Fullscreen icon
        fullscreenBtn.title = 'Enter Fullscreen';
    }
    
    // Scroll to bottom after layout change
    setTimeout(scrollToBottom, 100);
}

// Add fullscreen toggle button
function addFullscreenButton() {
    const inputContainer = document.querySelector('.input-container');
    if (inputContainer && !document.getElementById('fullscreen-btn')) {
        const fullscreenBtn = document.createElement('button');
        fullscreenBtn.id = 'fullscreen-btn';
        fullscreenBtn.type = 'button';
        fullscreenBtn.className = 'submit-button';
        fullscreenBtn.innerHTML = '🗖'; // Fullscreen icon
        fullscreenBtn.title = 'Enter Fullscreen';
        fullscreenBtn.onclick = toggleFullscreenChat;
        fullscreenBtn.style.minWidth = '50px';
        fullscreenBtn.style.padding = '12px 15px';
        
        // Insert before the download button
        const downloadLink = inputContainer.querySelector('.download-link');
        inputContainer.insertBefore(fullscreenBtn, downloadLink);
    }
}

// Handle ESC key to exit fullscreen
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape' && isFullscreen) {
        toggleFullscreenChat();
    }
});

// Calendar navigation
function previousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderCalendar();
}

function nextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderCalendar();
}

function previousYear() {
    currentDate.setFullYear(currentDate.getFullYear() - 1);
    renderCalendar();
}

function nextYear() {
    currentDate.setFullYear(currentDate.getFullYear() + 1);
    renderCalendar();
}

function changeYear(year) {
    currentDate.setFullYear(parseInt(year));
    renderCalendar();
}

// Render calendar
function renderCalendar() {
    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    
    // Update month/year display
    document.getElementById('current-month-year').textContent = 
        `${monthNames[currentDate.getMonth()]} ${currentDate.getFullYear()}`;
    
    // Clear existing calendar
    const calendarGrid = document.getElementById('calendar-grid');
    calendarGrid.innerHTML = '';
    
    // Add day headers
    dayNames.forEach(day => {
        const dayHeader = document.createElement('div');
        dayHeader.className = 'calendar-day-header';
        dayHeader.textContent = day;
        calendarGrid.appendChild(dayHeader);
    });
    
    // Calculate first day of month and days in month
    const firstDay = new Date(currentDate.getFullYear(), currentDate.getMonth(), 1);
    const lastDay = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();
    
    // Calculate previous month's last days
    const prevMonth = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 0);
    const prevMonthDays = prevMonth.getDate();
    
    // Add previous month's trailing days
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
        const dayElement = createDayElement(prevMonthDays - i, true);
        calendarGrid.appendChild(dayElement);
    }
    
    // Add current month's days
    for (let day = 1; day <= daysInMonth; day++) {
        const dayElement = createDayElement(day, false);
        calendarGrid.appendChild(dayElement);
    }
    
    // Add next month's leading days
    const totalCells = calendarGrid.children.length - 7; // Subtract header row
    const remainingCells = 42 - totalCells; // 6 rows × 7 days = 42 cells
    
    for (let day = 1; day <= remainingCells; day++) {
        const dayElement = createDayElement(day, true);
        calendarGrid.appendChild(dayElement);
    }
}

// Create day element
function createDayElement(day, isOtherMonth) {
    const dayElement = document.createElement('div');
    dayElement.className = 'calendar-day';
    
    // Create date number element
    const dateNumber = document.createElement('div');
    dateNumber.className = 'calendar-date-number';
    dateNumber.textContent = day;
    dayElement.appendChild(dateNumber);
    
    if (isOtherMonth) {
        dayElement.classList.add('other-month');
    } else {
        // Check if it's today
        const today = new Date();
        if (currentDate.getFullYear() === today.getFullYear() &&
            currentDate.getMonth() === today.getMonth() &&
            day === today.getDate()) {
            dayElement.classList.add('today');
        }
        
        // Check if there's earnings data for this day
        const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        if (earningsData[dateStr]) {
            dayElement.classList.add('earnings-day');
            
            // Add earnings preview text
            const earningsText = earningsData[dateStr];
            const previewText = earningsText.length > 15 ? earningsText.substring(0, 15) + '...' : earningsText;

            const previewElement = document.createElement('div');
            previewElement.className = 'calendar-earnings-preview';
            previewElement.textContent = previewText;
            dayElement.appendChild(previewElement);
            
            // Add hover tooltip
            dayElement.addEventListener('mouseenter', function(e) {
                showTooltip(e, earningsData[dateStr]);
            });
            
            dayElement.addEventListener('mouseleave', function() {
                hideTooltip();
            });
        }
    }
    
    return dayElement;
}

// Show tooltip
function showTooltip(event, text) {
    const tooltip = document.createElement('div');
    tooltip.className = 'calendar-tooltip';
    tooltip.textContent = text;
    
    document.body.appendChild(tooltip);
    
    // Position tooltip
    const rect = event.target.getBoundingClientRect();
    tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
    tooltip.style.top = `${rect.top - tooltip.offsetHeight - 10}px`;
    
    // Store reference for cleanup
    event.target.tooltip = tooltip;
}

// Hide tooltip
function hideTooltip() {
    const tooltips = document.querySelectorAll('.calendar-tooltip');
    tooltips.forEach(tooltip => tooltip.remove());
}

// Add back button functionality to calendar
document.addEventListener('DOMContentLoaded', function() {
    // Add back button to calendar header
    setTimeout(() => {
        const calendarHeader = document.querySelector('.calendar-header');
        if (calendarHeader) {
            const backButton = document.createElement('button');
            backButton.className = 'calendar-nav-btn';
            backButton.innerHTML = '←';
            backButton.title = 'Back to Chat';
            backButton.onclick = showChatSection;
            backButton.style.marginRight = '10px';
            
            const controls = calendarHeader.querySelector('.calendar-controls');
            controls.insertBefore(backButton, controls.firstChild);
        }
    }, 100);
});

// Error handling for HTMX
document.addEventListener('htmx:responseError', function(event) {
    const chatContainer = document.getElementById('chat-container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'bot-message';
    errorDiv.innerHTML = '<strong>Assistant:</strong> Sorry, there was an error processing your request. Please try again.';
    chatContainer.appendChild(errorDiv);
    scrollToBottom();
});

// Handle network errors
document.addEventListener('htmx:sendError', function(event) {
    const chatContainer = document.getElementById('chat-container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'bot-message';
    errorDiv.innerHTML = '<strong>Assistant:</strong> Network error. Please check your connection and try again.';
    chatContainer.appendChild(errorDiv);
    scrollToBottom();
});

// Smooth animations for dynamic content
function addSmoothAnimation(element) {
    element.style.opacity = '0';
    element.style.transform = 'translateY(20px)';
    element.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    
    setTimeout(() => {
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
    }, 10);
}

// Apply animations to new messages
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
            if (node.nodeType === 1 && (node.classList.contains('user-message') || node.classList.contains('bot-message'))) {
                addSmoothAnimation(node);
            }
        });
    });
});

// Start observing
document.addEventListener('DOMContentLoaded', function() {
    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        observer.observe(chatContainer, { childList: true });
    }
});
