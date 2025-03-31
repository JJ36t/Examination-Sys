/**
 * ملف JavaScript خاص بالأجهزة المحمولة
 * نظام اللجان الامتحانية
 */

document.addEventListener('DOMContentLoaded', function() {
    // التعامل مع تجاوب الجداول
    makeTablesResponsive();
    
    // إضافة طبقة الخلفية للشريط الجانبي إذا لم تكن موجودة
    if (document.querySelector('.sidebar-backdrop') === null) {
        const backdropElement = document.createElement('div');
        backdropElement.className = 'sidebar-backdrop';
        document.body.appendChild(backdropElement);
    }
    
    // تحسين العناصر التفاعلية على الأجهزة المحمولة
    enhanceMobileInteraction();
});

/**
 * تحسين تجاوب الجداول على الأجهزة المحمولة
 */
function makeTablesResponsive() {
    // التأكد من أن جميع الجداول لديها table-responsive
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        // البحث عن أقرب div
        let parent = table.parentElement;
        
        // إذا لم يكن الأب table-responsive، ثم قم بإضافة الفئة
        if (!parent.classList.contains('table-responsive')) {
            // إذا كان الجدول بالفعل في div.table-responsive، لا تفعل شيئًا
            if (!(parent.tagName === 'DIV' && parent.classList.contains('table-responsive'))) {
                // إنشاء عنصر div جديد مع فئة table-responsive
                const responsiveWrapper = document.createElement('div');
                responsiveWrapper.className = 'table-responsive';
                
                // وضع الجدول داخل العنصر الجديد
                table.parentElement.insertBefore(responsiveWrapper, table);
                responsiveWrapper.appendChild(table);
            }
        }
    });
}

/**
 * تحسين التفاعل على الأجهزة المحمولة
 */
function enhanceMobileInteraction() {
    // زيادة مساحة النقر للروابط في القائمة الجانبية
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link');
    sidebarLinks.forEach(link => {
        link.style.padding = '12px 15px';
    });
    
    // تحسين أداء الأزرار على الشاشات الصغيرة
    if (window.innerWidth <= 768) {
        const buttons = document.querySelectorAll('.btn');
        buttons.forEach(button => {
            // تكبير المساحة القابلة للنقر قليلاً
            button.style.minHeight = '38px';
            button.style.display = 'inline-flex';
            button.style.alignItems = 'center';
            button.style.justifyContent = 'center';
        });
    }
    
    // إصلاح مشكلة التمرير للصفحات الطويلة
    if (window.innerWidth <= 992) {
        // منع التمرير السلس الذي قد يسبب مشاكل
        document.documentElement.style.scrollBehavior = 'auto';
        
        // تحسين سرعة الاستجابة للنقر من خلال إزالة التأخير
        const clickableElements = document.querySelectorAll('a, button, .btn, [role="button"]');
        clickableElements.forEach(element => {
            element.style.touchAction = 'manipulation';
        });
    }
}

/**
 * تحسين الروابط عند النقر على الهواتف
 */
function fixMobileTapDelay() {
    // إضافة استجابة فورية عند النقر على أي عنصر تفاعلي
    document.addEventListener('touchstart', function() {}, {passive: true});
}

// تنفيذ الوظيفة عند تغيير حجم النافذة
window.addEventListener('resize', function() {
    // تحسين التفاعل إذا كان حجم الشاشة من فئة الهواتف المحمولة
    if (window.innerWidth <= 992) {
        enhanceMobileInteraction();
    }
});
