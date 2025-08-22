// Multilingual support for PF Creative AI Studio
const translations = {
    en: {
        "head.title": "PF Creative AI Studio - The Director-Grade AI",
        "nav.title": "PF Creative AI Studio",
        "nav.home": "Home",
        "nav.solution": "Solution",
        "nav.features": "Features",
        "nav.video": "Our Work",
        "nav.contact": "Contact",
        "nav.cta": "Get Started",
        
        "hero.title1": "The Director-Grade AI.",
        "hero.title2": "Go Beyond Prompts, Get Production-Ready Scripts.",
        "hero.subtitle": "Stop wrestling with inconsistent AI outputs. Our advanced system delivers complete, multi-scene script packages with professional cinematography controls and error-prevention technology.",
        "hero.cta1": "See How It Works",
        "hero.cta2": "Try Director-Grade AI",
        
        "solution.title1": "Stop Fixing AI Errors.",
        "solution.title2": "Start Directing.",
        "solution.subtitle": "Traditional AI video tools leave you frustrated with inconsistent results. Our Director-Grade AI eliminates common problems before they happen.",
        
        "problem1.title": "Problem: Inconsistent Characters",
        "problem1.description": "Characters change appearance between scenes, breaking narrative continuity and making videos look unprofessional.",
        "problem1.solution.title": "Our Solution: Advanced Production Strategies",
        "problem1.solution.description": "The \"Faceless Expert\" and \"Single Scene Presenter\" techniques ensure visual consistency across all scenes.",
        
        "problem2.title": "Problem: Glitches & Visual Artifacts",
        "problem2.description": "Mangled hands, extra fingers, unwanted text overlays, and other AI artifacts ruin professional presentations.",
        "problem2.solution.title": "Our Solution: Comprehensive Negative Prompt Library",
        "problem2.solution.description": "Automatically prevents common AI errors with our extensive database of negative prompts and quality controls.",
        
        "features.title": "Director-Grade Features",
        "features.subtitle": "Professional tools that give you complete creative control over your AI video production",
        
        "feature1.title": "Production-Ready Blueprints",
        "feature1.description": "Don't just get a prompt. Receive a complete, multi-scene script package that's ready for professional production.",
        "feature1.item1": "Complete VEO Prompt Blueprint for every scene",
        "feature1.item2": "Detailed shot descriptions and camera angles",
        "feature1.item3": "Scene-by-scene narrative structure",
        "feature1.item4": "Professional formatting for immediate use",
        "feature1.example.title": "Example Output:",
        "feature1.example.text": "\"Scene 1: Medium shot of confident presenter in modern office, natural lighting, camera slowly zooms in, professional attire, clean background...\"",
        
        "feature2.title": "Professional Creative Control",
        "feature2.description": "Choose from a library of cinematic styles and define specific cinematography like a real director.",
        "feature2.styles.title": "Cinematic Styles",
        "feature2.styles.item1": "Film Noir",
        "feature2.styles.item2": "Documentary",
        "feature2.styles.item3": "Corporate",
        "feature2.styles.item4": "Cinematic",
        "feature2.controls.title": "Camera Controls",
        "feature2.controls.item1": "Lens Choices",
        "feature2.controls.item2": "Camera Movements",
        "feature2.controls.item3": "Lighting Setup",
        "feature2.controls.item4": "Shot Composition",
        "feature2.item1": "Professional cinematography library",
        "feature2.item2": "Customizable camera movements and angles",
        "feature2.item3": "Industry-standard lighting techniques",
        "feature2.item4": "Director-level creative control",
        
        "video.title": "See Director-Grade AI in Action",
        "video.subtitle": "Experience the difference between amateur prompts and professional production",
        "video.description": "Watch how our Director-Grade AI transforms simple ideas into production-ready video scripts",
        
        "cta.title": "Ready to Direct Like a Pro?",
        "cta.subtitle": "Stop settling for amateur AI outputs. Get production-ready scripts that deliver professional results every time.",
        "cta.button1": "Start Creating Director-Grade Scripts",
        "cta.button2": "Book Professional Consultation",
        "cta.join": "Join hundreds of creators who've upgraded to Director-Grade AI",
        
        "footer.copyright": "© 2025 Pyrofractal Tech. All Rights Reserved.",
        "footer.terms": "Terms of Service",
        "footer.privacy": "Privacy Policy",
        "footer.contact": "Contact Us",
        "footer.social": "Follow us on social media"
    },
    
    bm: {
        "head.title": "PF Creative AI Studio - AI Gred Pengarah",
        "nav.title": "PF Creative AI Studio",
        "nav.home": "Utama",
        "nav.solution": "Penyelesaian",
        "nav.features": "Ciri-ciri",
        "nav.video": "Karya Kami",
        "nav.contact": "Hubungi",
        "nav.cta": "Mula Sekarang",
        
        "hero.title1": "AI Gred Pengarah.",
        "hero.title2": "Melampaui Prompt, Dapatkan Skrip Siap Produksi.",
        "hero.subtitle": "Berhenti bergelut dengan output AI yang tidak konsisten. Sistem canggih kami menyampaikan pakej skrip multi-adegan lengkap dengan kawalan sinematografi profesional dan teknologi pencegahan ralat.",
        "hero.cta1": "Lihat Cara Ia Berfungsi",
        "hero.cta2": "Cuba AI Gred Pengarah",
        
        "solution.title1": "Berhenti Membetulkan Ralat AI.",
        "solution.title2": "Mula Mengarah.",
        "solution.subtitle": "Alat video AI tradisional membuatkan anda kecewa dengan hasil yang tidak konsisten. AI Gred Pengarah kami menghapuskan masalah biasa sebelum ia berlaku.",
        
        "problem1.title": "Masalah: Watak Tidak Konsisten",
        "problem1.description": "Watak berubah penampilan antara adegan, memecahkan kesinambungan naratif dan menjadikan video kelihatan tidak profesional.",
        "problem1.solution.title": "Penyelesaian Kami: Strategi Produksi Lanjutan",
        "problem1.solution.description": "Teknik \"Pakar Tanpa Wajah\" dan \"Penyampai Adegan Tunggal\" memastikan konsistensi visual merentas semua adegan.",
        
        "problem2.title": "Masalah: Gangguan & Artifak Visual",
        "problem2.description": "Tangan yang rosak, jari tambahan, tindihan teks yang tidak diingini, dan artifak AI lain merosakkan persembahan profesional.",
        "problem2.solution.title": "Penyelesaian Kami: Perpustakaan Prompt Negatif Komprehensif",
        "problem2.solution.description": "Secara automatik mencegah ralat AI biasa dengan pangkalan data prompt negatif dan kawalan kualiti yang luas.",
        
        "features.title": "Ciri-ciri Gred Pengarah",
        "features.subtitle": "Alat profesional yang memberikan anda kawalan kreatif penuh ke atas produksi video AI anda",
        
        "feature1.title": "Pelan Tindakan Siap Produksi",
        "feature1.description": "Jangan hanya dapatkan prompt. Terima pakej skrip multi-adegan lengkap yang siap untuk produksi profesional.",
        "feature1.item1": "Pelan Tindakan Prompt VEO Lengkap untuk setiap adegan",
        "feature1.item2": "Penerangan tangkapan terperinci dan sudut kamera",
        "feature1.item3": "Struktur naratif adegan demi adegan",
        "feature1.item4": "Pemformatan profesional untuk kegunaan segera",
        "feature1.example.title": "Contoh Output:",
        "feature1.example.text": "\"Adegan 1: Tangkapan sederhana penyampai yakin di pejabat moden, pencahayaan semula jadi, kamera perlahan-lahan zum masuk, pakaian profesional, latar belakang bersih...\"",
        
        "feature2.title": "Kawalan Kreatif Profesional",
        "feature2.description": "Pilih dari perpustakaan gaya sinematik dan tentukan sinematografi khusus seperti pengarah sebenar.",
        "feature2.styles.title": "Gaya Sinematik",
        "feature2.styles.item1": "Film Noir",
        "feature2.styles.item2": "Dokumentari",
        "feature2.styles.item3": "Korporat",
        "feature2.styles.item4": "Sinematik",
        "feature2.controls.title": "Kawalan Kamera",
        "feature2.controls.item1": "Pilihan Lensa",
        "feature2.controls.item2": "Pergerakan Kamera",
        "feature2.controls.item3": "Persediaan Pencahayaan",
        "feature2.controls.item4": "Komposisi Tangkapan",
        "feature2.item1": "Perpustakaan sinematografi profesional",
        "feature2.item2": "Pergerakan kamera dan sudut yang boleh disesuaikan",
        "feature2.item3": "Teknik pencahayaan standard industri",
        "feature2.item4": "Kawalan kreatif peringkat pengarah",
        
        "video.title": "Lihat AI Gred Pengarah dalam Tindakan",
        "video.subtitle": "Alami perbezaan antara prompt amatur dan produksi profesional",
        "video.description": "Tonton bagaimana AI Gred Pengarah kami mengubah idea mudah menjadi skrip video siap produksi",
        
        "cta.title": "Bersedia untuk Mengarah Seperti Pro?",
        "cta.subtitle": "Berhenti berpuas hati dengan output AI amatur. Dapatkan skrip siap produksi yang memberikan hasil profesional setiap kali.",
        "cta.button1": "Mula Mencipta Skrip Gred Pengarah",
        "cta.button2": "Tempah Perundingan Profesional",
        "cta.join": "Sertai beratus-ratus pencipta yang telah menaik taraf kepada AI Gred Pengarah",
        
        "footer.copyright": "© 2025 Pyrofractal Tech. Semua Hak Terpelihara.",
        "footer.terms": "Terma Perkhidmatan",
        "footer.privacy": "Dasar Privasi",
        "footer.contact": "Hubungi Kami",
        "footer.social": "Ikuti kami di media sosial"
    },
    
    zh: {
        "head.title": "PF Creative AI Studio - 导演级AI",
        "nav.title": "PF Creative AI Studio",
        "nav.home": "首页",
        "nav.solution": "解决方案",
        "nav.features": "功能特色",
        "nav.video": "我们的作品",
        "nav.contact": "联系我们",
        "nav.cta": "开始使用",
        
        "hero.title1": "导演级AI。",
        "hero.title2": "超越提示词，获得制作就绪的脚本。",
        "hero.subtitle": "停止与不一致的AI输出作斗争。我们的先进系统提供完整的多场景脚本包，配备专业的电影摄影控制和错误预防技术。",
        "hero.cta1": "了解工作原理",
        "hero.cta2": "试用导演级AI",
        
        "solution.title1": "停止修复AI错误。",
        "solution.title2": "开始导演。",
        "solution.subtitle": "传统的AI视频工具让您对不一致的结果感到沮丧。我们的导演级AI在问题发生之前就消除了常见问题。",
        
        "problem1.title": "问题：角色不一致",
        "problem1.description": "角色在场景之间改变外观，破坏叙事连续性，使视频看起来不专业。",
        "problem1.solution.title": "我们的解决方案：先进的制作策略",
        "problem1.solution.description": "\"无脸专家\"和\"单场景演示者\"技术确保所有场景的视觉一致性。",
        
        "problem2.title": "问题：故障和视觉伪影",
        "problem2.description": "扭曲的手、多余的手指、不需要的文字覆盖和其他AI伪影破坏了专业演示。",
        "problem2.solution.title": "我们的解决方案：综合负面提示库",
        "problem2.solution.description": "通过我们广泛的负面提示数据库和质量控制自动防止常见的AI错误。",
        
        "features.title": "导演级功能",
        "features.subtitle": "专业工具让您完全掌控AI视频制作的创意控制",
        
        "feature1.title": "制作就绪蓝图",
        "feature1.description": "不只是获得提示词。接收完整的多场景脚本包，为专业制作做好准备。",
        "feature1.item1": "每个场景的完整VEO提示蓝图",
        "feature1.item2": "详细的镜头描述和摄像机角度",
        "feature1.item3": "逐场景叙事结构",
        "feature1.item4": "专业格式化，可立即使用",
        "feature1.example.title": "示例输出：",
        "feature1.example.text": "\"场景1：现代办公室中自信演示者的中景镜头，自然光照，摄像机缓慢拉近，专业着装，干净背景...\"",
        
        "feature2.title": "专业创意控制",
        "feature2.description": "从电影风格库中选择，像真正的导演一样定义特定的电影摄影。",
        "feature2.styles.title": "电影风格",
        "feature2.styles.item1": "黑色电影",
        "feature2.styles.item2": "纪录片",
        "feature2.styles.item3": "企业风格",
        "feature2.styles.item4": "电影风格",
        "feature2.controls.title": "摄像机控制",
        "feature2.controls.item1": "镜头选择",
        "feature2.controls.item2": "摄像机运动",
        "feature2.controls.item3": "灯光设置",
        "feature2.controls.item4": "镜头构图",
        "feature2.item1": "专业电影摄影库",
        "feature2.item2": "可定制的摄像机运动和角度",
        "feature2.item3": "行业标准照明技术",
        "feature2.item4": "导演级创意控制",
        
        "video.title": "观看导演级AI的实际应用",
        "video.subtitle": "体验业余提示词与专业制作之间的差异",
        "video.description": "观看我们的导演级AI如何将简单想法转化为制作就绪的视频脚本",
        
        "cta.title": "准备像专业人士一样导演？",
        "cta.subtitle": "停止满足于业余AI输出。获得每次都能提供专业结果的制作就绪脚本。",
        "cta.button1": "开始创建导演级脚本",
        "cta.button2": "预约专业咨询",
        "cta.join": "加入数百名已升级到导演级AI的创作者",
        
        "footer.copyright": "© 2025 Pyrofractal Tech. 保留所有权利。",
        "footer.terms": "服务条款",
        "footer.privacy": "隐私政策",
        "footer.contact": "联系我们",
        "footer.social": "在社交媒体上关注我们"
    }
};

let currentLanguage = 'en';

// Initialize language system
document.addEventListener('DOMContentLoaded', function() {
    // Load saved language preference
    const savedLang = localStorage.getItem('preferredLanguage') || 'en';
    currentLanguage = savedLang;
    
    // Set up language button event listeners
    const langBtn = document.getElementById('langBtn');
    const langMenu = document.getElementById('langMenu');
    const langOptions = document.querySelectorAll('.lang-option');
    
    if (langBtn && langMenu) {
        // Toggle language menu
        langBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            langMenu.classList.toggle('show');
            langMenu.classList.toggle('hidden');
        });
        
        // Close menu when clicking outside
        document.addEventListener('click', function() {
            langMenu.classList.remove('show');
            langMenu.classList.add('hidden');
        });
        
        // Handle language selection
        langOptions.forEach(option => {
            option.addEventListener('click', function(e) {
                e.preventDefault();
                const selectedLang = this.getAttribute('data-lang');
                changeLanguage(selectedLang);
                langMenu.classList.remove('show');
                langMenu.classList.add('hidden');
            });
        });
    }
    
    // Apply initial language
    changeLanguage(currentLanguage);
});

function changeLanguage(lang) {
    if (!translations[lang]) {
        console.error('Language not supported:', lang);
        return;
    }
    
    currentLanguage = lang;
    localStorage.setItem('preferredLanguage', lang);
    
    // Update current language display
    const currentLangSpan = document.getElementById('currentLang');
    if (currentLangSpan) {
        const langMap = {
            'en': 'EN',
            'bm': 'BM',
            'zh': '中文'
        };
        currentLangSpan.textContent = langMap[lang] || 'EN';
    }
    
    // Update active language option
    const langOptions = document.querySelectorAll('.lang-option');
    langOptions.forEach(option => {
        option.classList.remove('active');
        if (option.getAttribute('data-lang') === lang) {
            option.classList.add('active');
        }
    });
    
    // Apply translations to all elements with data-i18n attribute
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            if (element.tagName === 'TITLE') {
                element.textContent = translations[lang][key];
            } else {
                element.textContent = translations[lang][key];
            }
        }
    });
    
    console.log('Language changed to:', lang);
}

// Export for global access
window.changeLanguage = changeLanguage;
window.translations = translations;

