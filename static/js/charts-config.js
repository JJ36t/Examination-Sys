// ملف إعدادات الرسومات البيانية للنظام

// الإعدادات العامة لجميع الرسومات البيانية
const defaultChartOptions = {
    responsive: true,
    maintainAspectRatio: false, // للسماح بالتحكم الكامل في الحجم
    animation: {
        duration: 1000 // تقليل مدة الرسوم المتحركة
    },
    hover: {
        animationDuration: 0, // إلغاء التحريك عند مرور الماوس
        mode: null // إلغاء وضع التحويم
    },
    plugins: {
        legend: {
            display: true,
            position: 'top',
            labels: {
                boxWidth: 15,
                padding: 15,
                font: {
                    size: 12
                }
            }
        },
        tooltip: {
            enabled: true,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleFont: {
                size: 14
            },
            bodyFont: {
                size: 13
            },
            padding: 10,
            cornerRadius: 4,
            displayColors: true
        }
    }
};

// إعدادات إضافية للرسومات البيانية الدائرية
const pieChartOptions = {
    ...defaultChartOptions,
    cutout: '0%', // مخطط دائري كامل
    radius: '90%', // حجم أصغر قليلا من المساحة المتاحة
    plugins: {
        ...defaultChartOptions.plugins,
        legend: {
            ...defaultChartOptions.plugins.legend,
            position: 'right' // وضع وسيلة الإيضاح على اليمين للمخططات الدائرية
        },
        tooltip: {
            ...defaultChartOptions.plugins.tooltip,
            callbacks: {
                label: function(context) {
                    const value = context.parsed;
                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                    const percentage = ((value / total) * 100).toFixed(1);
                    return `${context.label}: ${value} (${percentage}%)`;
                }
            }
        }
    }
};

// إعدادات إضافية للرسومات البيانية الشريطية
const barChartOptions = {
    ...defaultChartOptions,
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                font: {
                    size: 12
                }
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: 'rgba(0, 0, 0, 0.1)'
            },
            ticks: {
                font: {
                    size: 12
                }
            }
        }
    },
    barPercentage: 0.7, // عرض الأشرطة
    categoryPercentage: 0.7 // المسافة بين مجموعات الأشرطة
};

// إعدادات إضافية لرسومات المتوسطات
const lineChartOptions = {
    ...defaultChartOptions,
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                font: {
                    size: 12
                }
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: 'rgba(0, 0, 0, 0.1)'
            },
            ticks: {
                font: {
                    size: 12
                }
            }
        }
    },
    elements: {
        line: {
            tension: 0.4, // جعل الخط أكثر انسيابية
            borderWidth: 2
        },
        point: {
            radius: 4,
            hitRadius: 10,
            hoverRadius: 4 // عدم تغيير حجم النقاط عند التحويم
        }
    }
};

// مجموعة ألوان جميلة ومتناسقة للرسومات البيانية
const colorsScheme = {
    backgroundColors: [
        'rgba(28, 200, 138, 0.7)',   // أخضر
        'rgba(54, 185, 204, 0.7)',   // أزرق فاتح
        'rgba(78, 115, 223, 0.7)',   // أزرق
        'rgba(246, 194, 62, 0.7)',   // أصفر
        'rgba(246, 128, 62, 0.7)',   // برتقالي
        'rgba(231, 74, 59, 0.7)',    // أحمر
        'rgba(153, 102, 255, 0.7)',  // بنفسجي
        'rgba(255, 159, 64, 0.7)'    // برتقالي فاتح
    ],
    borderColors: [
        'rgba(28, 200, 138, 1)',
        'rgba(54, 185, 204, 1)',
        'rgba(78, 115, 223, 1)',
        'rgba(246, 194, 62, 1)',
        'rgba(246, 128, 62, 1)',
        'rgba(231, 74, 59, 1)',
        'rgba(153, 102, 255, 1)',
        'rgba(255, 159, 64, 1)'
    ]
};

// دالة مساعدة لتكوين الرسم البياني حسب النوع
function getChartConfig(type) {
    switch(type) {
        case 'pie':
        case 'doughnut':
            return pieChartOptions;
        case 'bar':
        case 'horizontalBar':
            return barChartOptions;
        case 'line':
            return lineChartOptions;
        default:
            return defaultChartOptions;
    }
}

// دالة مساعدة لضبط حجم لوحة الرسم البياني حسب حجم الحاوية
function resizeChartCanvas(chartId) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    
    const container = canvas.parentElement;
    
    // ضبط ارتفاع قماش الرسم البياني حسب حجم الحاوية
    canvas.style.height = container.offsetHeight + 'px';
    canvas.height = container.offsetHeight;
    
    // إذا كان هناك رسم بياني موجود بالفعل، قم بتحديثه
    if (window[chartId + 'Chart']) {
        window[chartId + 'Chart'].resize();
    }
}

// إعداد حجم كل لوحات الرسوم البيانية
function setupChartCanvases() {
    const chartCanvases = document.querySelectorAll('canvas[id]');
    chartCanvases.forEach(canvas => {
        resizeChartCanvas(canvas.id);
    });
}

// إضافة مستمع لتغيير حجم النافذة لإعادة ضبط الرسومات البيانية
window.addEventListener('resize', function() {
    setupChartCanvases();
});

// مستمع لوقت تحميل المستند
document.addEventListener('DOMContentLoaded', function() {
    // إعداد أحجام كل الرسومات البيانية
    setupChartCanvases();
});
