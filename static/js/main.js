// Main JavaScript file for the examination committee system

// Apply animations to elements when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Animate elements with fade-in class
    const fadeElements = document.querySelectorAll('.fade-in');
    fadeElements.forEach((element, index) => {
        element.style.opacity = 0;
        setTimeout(() => {
            element.style.transition = 'opacity 0.5s ease';
            element.style.opacity = 1;
        }, 100 * index);
    });

    // Animate elements with slide-in class
    const slideElements = document.querySelectorAll('.slide-in');
    slideElements.forEach((element, index) => {
        element.style.opacity = 0;
        element.style.transform = 'translateY(20px)';
        setTimeout(() => {
            element.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            element.style.opacity = 1;
            element.style.transform = 'translateY(0)';
        }, 100 * index);
    });

    // Add hover effects to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Add hover effects to buttons
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Add hover effects to sidebar links
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link');
    sidebarLinks.forEach(link => {
        link.addEventListener('mouseenter', function() {
            this.style.paddingRight = '25px';
        });
        link.addEventListener('mouseleave', function() {
            this.style.paddingRight = '16px';
        });
    });

    // إدارة السايد بار على جميع أحجام الشاشات
    const sidebarToggle = document.querySelector('#sidebarToggle');
    const sidebar = document.querySelector('#sidebar');
    const mainContent = document.querySelector('#mainContent');
    const overlay = document.querySelector('.overlay');
    const toggleIcon = document.querySelector('#toggleIcon');
    
    if (sidebarToggle && sidebar && mainContent) {
        // تهيئة السايد بار بناءً على حجم الشاشة
        function initSidebarState() {
            if (window.innerWidth <= 767) {
                sidebar.classList.add('collapsed');
                mainContent.classList.add('expanded');
                if (toggleIcon) toggleIcon.classList.replace('fa-bars', 'fa-chevron-left');
            } else {
                sidebar.classList.remove('collapsed');
                mainContent.classList.remove('expanded');
                if (toggleIcon) toggleIcon.classList.replace('fa-chevron-left', 'fa-bars');
            }
        }

        // تنفيذ التهيئة عند تحميل الصفحة
        initSidebarState();
        
        // تبديل حالة السايد بار عند النقر على الزر
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
            
            if (overlay) {
                overlay.classList.toggle('show');
            }
            
            // تغيير أيقونة الزر
            if (toggleIcon) {
                if (sidebar.classList.contains('collapsed')) {
                    toggleIcon.classList.replace('fa-bars', 'fa-chevron-left');
                } else {
                    toggleIcon.classList.replace('fa-chevron-left', 'fa-bars');
                }
            }
        });
        
        // إغلاق السايد بار عند النقر على الخلفية
        if (overlay) {
            overlay.addEventListener('click', function() {
                sidebar.classList.add('collapsed');
                mainContent.classList.add('expanded');
                overlay.classList.remove('show');
                if (toggleIcon) toggleIcon.classList.replace('fa-bars', 'fa-chevron-left');
            });
        }
        
        // تحديث حالة السايد بار عند تغيير حجم النافذة
        window.addEventListener('resize', function() {
            initSidebarState();
        });
    }

    // Handle search input animation
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('focus', function() {
            this.style.boxShadow = '0 0 0 0.25rem rgba(13, 110, 253, 0.25)';
        });
        searchInput.addEventListener('blur', function() {
            this.style.boxShadow = 'none';
        });
    }

    // Add Enter key support for search
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const searchBtn = document.getElementById('searchBtn');
                if (searchBtn) {
                    searchBtn.click();
                }
            }
        });
    }

    // Add animation to grade inputs
    const gradeInputs = document.querySelectorAll('.grade-input');
    gradeInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.style.backgroundColor = '#f8f9fa';
            this.style.transform = 'scale(1.05)';
        });
        input.addEventListener('blur', function() {
            this.style.backgroundColor = '';
            this.style.transform = 'scale(1)';
        });
    });

    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href');
            if (targetId !== '#') {
                e.preventDefault();
                document.querySelector(targetId).scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});

// Function to show toast notification
function showToast(message, type = 'success') {
    // Remove existing toasts
    const existingToasts = document.querySelectorAll('.toast-container');
    existingToasts.forEach(toast => toast.remove());

    // Create toast container
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '5';

    // Create toast
    const toast = document.createElement('div');
    toast.className = 'toast show';
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');

    // Create toast header
    const toastHeader = document.createElement('div');
    toastHeader.className = `toast-header bg-${type} text-white`;

    // Create icon
    const icon = document.createElement('i');
    icon.className = type === 'success' ? 'fas fa-check-circle me-2' : 'fas fa-exclamation-circle me-2';

    // Create title
    const title = document.createElement('strong');
    title.className = 'me-auto';
    title.textContent = type === 'success' ? 'نجاح' : 'تنبيه';

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'toast');
    closeButton.setAttribute('aria-label', 'Close');

    // Create toast body
    const toastBody = document.createElement('div');
    toastBody.className = 'toast-body';
    toastBody.textContent = message;

    // Assemble toast
    toastHeader.appendChild(icon);
    toastHeader.appendChild(title);
    toastHeader.appendChild(closeButton);
    toast.appendChild(toastHeader);
    toast.appendChild(toastBody);
    toastContainer.appendChild(toast);

    // Add to document
    document.body.appendChild(toastContainer);

    // Auto hide after 3 seconds
    setTimeout(() => {
        toastContainer.remove();
    }, 3000);
}

// Function to update semester options based on selected stage
function updateSemesterOptions(stageId) {
    const semesterLinks = document.querySelectorAll('.semester-links');
    semesterLinks.forEach(link => {
        link.style.display = 'none';
    });

    const selectedSemesterLinks = document.getElementById(`semesterLinks${stageId}`);
    if (selectedSemesterLinks) {
        selectedSemesterLinks.style.display = 'block';
    }
}

// Function to calculate grade evaluation
function calculateGradeEvaluation(total) {
    if (total < 50) return 'ضعيف';
    if (total < 60) return 'مقبول';
    if (total < 70) return 'متوسط';
    if (total < 80) return 'جيد';
    if (total < 90) return 'جيد جدا';
    return 'امتياز';
}

// تحسين عرض الجداول ديناميكيًا
function optimizeTableDisplay() {
    const tables = document.querySelectorAll('table.table');
    
    tables.forEach(table => {
        // التأكد من أن الجدول موجود داخل عنصر table-responsive
        let parent = table.parentElement;
        if (!parent.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
        
        // إضافة فئة التجاوب لجميع الجداول
        if (!table.classList.contains('table-responsive-sm')) {
            table.classList.add('table-responsive-sm');
        }
    });
}

// تحسين المخططات البيانية
function optimizeCharts() {
    const chartContainers = document.querySelectorAll('.chart-container');
    
    chartContainers.forEach(container => {
        // تحسين حجم عرض المخططات
        container.style.minHeight = '300px';
        container.style.height = 'calc(100% - 40px)';
        
        // إضافة تأثير حركي عند التحويم
        container.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 8px 20px rgba(0, 0, 0, 0.12)';
        });
        
        container.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 3px 15px rgba(0, 0, 0, 0.08)';
        });
    });
}

// استدعاء وظائف التحسين عند تحميل الصفحة
document.addEventListener('DOMContentLoaded', function() {
    optimizeTableDisplay();
    optimizeCharts();
    
    // تنفيذ التحسينات مرة أخرى عند تغيير حجم النافذة
    window.addEventListener('resize', function() {
        setTimeout(function() {
            optimizeTableDisplay();
            optimizeCharts();
        }, 300);
    });
});

// Function to validate grade input
function validateGradeInput(input, min, max) {
    const value = parseInt(input.value);
    if (isNaN(value) || value < min || value > max) {
        input.classList.add('is-invalid');
        return false;
    }
    input.classList.remove('is-invalid');
    return true;
}
