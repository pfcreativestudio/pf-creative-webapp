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
        
        "footer.copyright": "2025 Pyrofractal Tech. All Rights Reserved.",
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
        
        "footer.copyright": "2025 Pyrofractal Tech. Semua Hak Terpelihara.",
        "footer.terms": "Terma Perkhidmatan",
        "footer.privacy": "Dasar Privasi",
        "footer.contact": "Hubungi Kami",
        "footer.social": "Ikuti kami di media sosial"
    },
    
    zh: {
        "head.title": "PF Creative AI Studio - AI",
        "nav.title": "PF Creative AI Studio",
        "nav.home": "",
        "nav.solution": "",
        "nav.features": "",
        "nav.video": "",
        "nav.contact": "",
        "nav.cta": "",
        
        "hero.title1": "AI",
        "hero.title2": "",
        "hero.subtitle": "AI",
        "hero.cta1": "",
        "hero.cta2": "AI",
        
        "solution.title1": "AI",
        "solution.title2": "",
        "solution.subtitle": "AI AI",
        
        "problem1.title": "",
        "problem1.description": "",
        "problem1.solution.title": "",
        "problem1.solution.description": "\" \" \" \"",
        
        "problem2.title": "",
        "problem2.description": "AI",
        "problem2.solution.title": "",
        "problem2.solution.description": "AI",
        
        "features.title": "",
        "features.subtitle": "AI",
        
        "feature1.title": "",
        "feature1.description": "",
        "feature1.item1": "VEO",
        "feature1.item2": "",
        "feature1.item3": "",
        "feature1.item4": "",
        "feature1.example.title": "",
        "feature1.example.text": "\" 1 ...\"",
        
        "feature2.title": "",
        "feature2.description": "",
        "feature2.styles.title": "",
        "feature2.styles.item1": "",
        "feature2.styles.item2": "",
        "feature2.styles.item3": "",
        "feature2.styles.item4": "",
        "feature2.controls.title": "",
        "feature2.controls.item1": "",
        "feature2.controls.item2": "",
        "feature2.controls.item3": "",
        "feature2.controls.item4": "",
        "feature2.item1": "",
        "feature2.item2": "",
        "feature2.item3": "",
        "feature2.item4": "",
        
        "video.title": "AI",
        "video.subtitle": "",
        "video.description": "AI",
        
        "cta.title": "",
        "cta.subtitle": "AI",
        "cta.button1": "",
        "cta.button2": "",
        "cta.join": "AI",
        
        "footer.copyright": "2025 Pyrofractal Tech.",
        "footer.terms": "",
        "footer.privacy": "Privacy Policy",
        "footer.contact": "",
        "footer.social": ""
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
            'zh': 'Chinese'
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

