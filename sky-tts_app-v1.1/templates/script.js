$(document).ready(function() {
    let isAuthenticated = false;
    const API_BASE_URL = 'http://127.0.0.1:5000';
    let mediaRecorder = null;
    let recordedChunks = [];

    // Preloader
    function hidePreloader() {
        gsap.to('.logo-animation', {
            rotation: 360,
            duration: 1.5,
            ease: 'power3.out'
        });
        
        gsap.to('#preloader', {
            opacity: 0,
            duration: 0.8,
            ease: 'power3.out',
            onComplete: () => $('#preloader').addClass('hidden')
        });
    }

    // Initialize
    function initApp() {
        hidePreloader();
        initDarkMode();
        checkAuthStatus();
        initSelect2();
        updateCharCount();
        initAnimations();
        initNavbar();
        initModals();
        initForms();
        initTippy();
    }

    // GSAP Animations
    function initAnimations() {
        gsap.registerPlugin(ScrollTrigger);

        // Hero Section
        gsap.from('.hero-title', { 
            opacity: 0, 
            y: 80, 
            duration: 1.2, 
            ease: 'power3.out', 
            delay: 0.3 
        });
        
        gsap.from('.hero-subtitle', { 
            opacity: 0, 
            y: 40, 
            duration: 1, 
            ease: 'power3.out', 
            delay: 0.6 
        });
        
        gsap.from('.hero-buttons .btn', { 
            opacity: 0, 
            y: 30, 
            duration: 0.8, 
            stagger: 0.15, 
            ease: 'power3.out', 
            delay: 0.9 
        });

        // Feature Cards
        gsap.utils.toArray('.feature-card').forEach((card, i) => {
            gsap.from(card, {
                opacity: 0,
                y: 100,
                duration: 0.8,
                ease: 'back.out(1.5)',
                delay: i * 0.1,
                scrollTrigger: {
                    trigger: card,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                }
            });
            
            $(card).hover(
                () => gsap.to(card, { 
                    y: -10, 
                    boxShadow: '0 20px 40px rgba(0,0,0,0.1)', 
                    duration: 0.3 
                }),
                () => gsap.to(card, { 
                    y: 0, 
                    boxShadow: '0 10px 20px rgba(0,0,0,0.05)', 
                    duration: 0.3 
                })
            );
        });

        // Pricing Cards
        gsap.utils.toArray('.pricing-card').forEach((card, i) => {
            gsap.from(card, {
                opacity: 0,
                y: 80,
                scale: 0.95,
                duration: 0.8,
                delay: i * 0.15,
                ease: 'back.out(1.5)',
                scrollTrigger: {
                    trigger: card,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                }
            });
            
            $(card).hover(
                () => gsap.to(card, { 
                    y: -5, 
                    boxShadow: '0 20px 40px rgba(0,0,0,0.1)', 
                    duration: 0.3 
                }),
                () => gsap.to(card, { 
                    y: 0, 
                    boxShadow: '0 10px 20px rgba(0,0,0,0.05)', 
                    duration: 0.3 
                })
            );
        });

        // Section Titles
        gsap.utils.toArray('.section-title').forEach(title => {
            gsap.from(title, {
                opacity: 0,
                y: 40,
                duration: 0.8,
                ease: 'back.out(1.5)',
                scrollTrigger: {
                    trigger: title,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                }
            });
        });

        // Buttons
        $('.btn-primary:not(.disabled-btn), .btn-outline, #dark-mode-toggle, #loginButton, #signupButton').each(function() {
            const btn = this;
            gsap.set(btn, { transformPerspective: 800 });
            
            $(btn).hover(
                () => gsap.to(btn, { 
                    scale: 1.05, 
                    boxShadow: '0 10px 25px rgba(0,0,0,0.15)', 
                    duration: 0.3 
                }),
                () => gsap.to(btn, { 
                    scale: 1, 
                    boxShadow: 'none', 
                    duration: 0.3 
                })
            );
            
            $(btn).click((e) => {
                gsap.to(btn, { 
                    scale: 0.95, 
                    duration: 0.1, 
                    yoyo: true, 
                    repeat: 1 
                });
                createRippleEffect(btn, e);
            });
        });

        // Logo Animation
        gsap.from('.logo-container', {
            opacity: 0,
            x: -40,
            duration: 1,
            ease: 'power3.out'
        });
        
        $('.logo-container').hover(
            () => gsap.to('.logo-container', { 
                scale: 1.05, 
                duration: 0.4 
            }),
            () => gsap.to('.logo-container', { 
                scale: 1, 
                duration: 0.4 
            })
        );

        // Scroll animations for other elements
        gsap.utils.toArray('.analytics-card').forEach((card, i) => {
            gsap.from(card, {
                opacity: 0,
                y: 60,
                duration: 0.8,
                delay: i * 0.1,
                ease: 'back.out(1.5)',
                scrollTrigger: {
                    trigger: card,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                }
            });
        });
    }

    // Ripple Effect
    function createRippleEffect(element, event) {
        const $ripple = $('<span class="ripple"></span>');
        const rect = element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;

        $ripple.css({ 
            width: size, 
            height: size, 
            top: y, 
            left: x 
        });
        
        $(element).append($ripple);
        
        gsap.to($ripple, {
            scale: 2,
            opacity: 0,
            duration: 0.7,
            ease: 'power3.out',
            onComplete: () => $ripple.remove()
        });
    }

    // Navbar
    function initNavbar() {
        // Smooth scrolling for nav links
        $('.nav-link').each(function() {
            const link = this;
            
            $(link).hover(
                () => gsap.to(link, { 
                    color: '#3b82f6', 
                    duration: 0.3 
                }),
                () => gsap.to(link, { 
                    color: 'var(--text-light)', 
                    duration: 0.3 
                })
            );
            
            $(link).click((e) => {
                gsap.to(link, { 
                    scale: 0.95, 
                    duration: 0.15, 
                    yoyo: true, 
                    repeat: 1 
                });
                createRippleEffect(link, e);
            });
            
            $(link).on('click', function(e) {
                e.preventDefault();
                const targetId = $(this).attr('href');
                
                gsap.to(window, {
                    scrollTo: { 
                        y: $(targetId).offset().top - 100,
                        autoKill: false
                    },
                    duration: 1,
                    ease: 'power3.out'
                });
                
                // Update active nav link
                $('.nav-link').removeClass('active');
                $(this).addClass('active');
            });
        });

        // Update active nav link on scroll
        gsap.utils.toArray('.nav-link').forEach(link => {
            const targetId = $(link).attr('href');
            
            ScrollTrigger.create({
                trigger: targetId,
                start: 'top center',
                end: 'bottom center',
                onEnter: () => {
                    $('.nav-link').removeClass('active');
                    $(link).addClass('active');
                },
                onEnterBack: () => {
                    $('.nav-link').removeClass('active');
                    $(link).addClass('active');
                }
            });
        });

        // Navbar background animation on scroll
        gsap.to('.navbar', {
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(12px)',
            boxShadow: '0 2px 10px rgba(0,0,0,0.1)',
            duration: 0.5,
            scrollTrigger: {
                trigger: 'body',
                start: 'top top',
                end: '+=100',
                scrub: true
            }
        });

        // User dropdown animation
        $('#userMenuBtn').click(function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            const $dropdown = $('#userDropdown');
            const isHidden = $dropdown.hasClass('hidden');
            
            if (isHidden) {
                $dropdown.removeClass('hidden');
                gsap.fromTo($dropdown, 
                    { scale: 0.95, opacity: 0, y: -10 },
                    { scale: 1, opacity: 1, y: 0, duration: 0.3, ease: 'power3.out' }
                );
            } else {
                gsap.to($dropdown, {
                    scale: 0.95,
                    opacity: 0,
                    y: -10,
                    duration: 0.2,
                    ease: 'power3.in',
                    onComplete: () => $dropdown.addClass('hidden')
                });
            }
        });

        // Close dropdown when clicking outside
        $(document).click(function(e) {
            if (!$(e.target).closest('#userMenu').length) {
                const $dropdown = $('#userDropdown');
                if (!$dropdown.hasClass('hidden')) {
                    gsap.to($dropdown, {
                        scale: 0.95,
                        opacity: 0,
                        y: -10,
                        duration: 0.2,
                        ease: 'power3.in',
                        onComplete: () => $dropdown.addClass('hidden')
                    });
                }
            }
        });
    }

    // Modals
    function initModals() {
        window.openModal = function(modalId) {
            $('.modal').not(`#${modalId}`).removeClass('show').addClass('hidden').attr('aria-hidden', 'true');
            
            const $modal = $(`#${modalId}`);
            $modal.removeClass('hidden').addClass('show').attr('aria-hidden', 'false');
            
            gsap.fromTo($modal.find('.modal-content'), 
                { scale: 0.95, opacity: 0, y: 20 },
                { scale: 1, opacity: 1, y: 0, duration: 0.4, ease: 'back.out(1.5)' }
            );
            
            gsap.from($modal.find('.modal-content > *'), { 
                opacity: 0, 
                y: 20, 
                duration: 0.3, 
                stagger: 0.1, 
                delay: 0.2 
            });
        };

        window.closeModal = function(modalId) {
            const $modal = $(`#${modalId}`);
            
            gsap.to($modal.find('.modal-content > *'), { 
                opacity: 0, 
                y: -10, 
                duration: 0.2, 
                stagger: 0.05 
            });
            
            gsap.to($modal.find('.modal-content'), {
                scale: 0.95,
                opacity: 0,
                y: 20,
                duration: 0.3,
                ease: 'power3.in',
                onComplete: () => {
                    $modal.removeClass('show').addClass('hidden').attr('aria-hidden', 'true');
                }
            });
        };

        $('.modal-close, .close').click(function(e) {
            e.preventDefault();
            closeModal($(this).data('modal'));
        });

        $('#switchToSignup').click(function(e) {
            e.preventDefault();
            closeModal('loginModal');
            setTimeout(() => openModal('signupModal'), 300);
        });

        $('#switchToLogin').click(function(e) {
            e.preventDefault();
            closeModal('signupModal');
            setTimeout(() => openModal('loginModal'), 300);
        });

        $(window).click(function(e) {
            if ($(e.target).hasClass('modal') && $(e.target).hasClass('show')) {
                closeModal(e.target.id);
            }
        });
    }

    // Tippy.js
    function initTippy() {
        tippy('[data-tippy-content]', {
            theme: 'light',
            allowHTML: true,
            animation: 'scale',
            duration: [300, 200],
            arrow: true,
            placement: 'top',
            interactive: true,
            appendTo: document.body
        });
    }

    // Dark Mode
    function initDarkMode() {
        const isDark = localStorage.getItem('darkMode') === 'enabled';
        $('body').toggleClass('dark', isDark);
        $('#darkModeIcon').toggleClass('fa-moon', !isDark).toggleClass('fa-sun', isDark);
        
        $('#dark-mode-toggle').click(function(e) {
            e.preventDefault();
            $('body').toggleClass('dark');
            const isDark = $('body').hasClass('dark');
            
            localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
            $('#darkModeIcon').toggleClass('fa-moon', !isDark).toggleClass('fa-sun', isDark);
            
            gsap.to('body', { 
                backgroundColor: isDark ? '#111827' : '#f9fafb', 
                duration: 0.5 
            });
        });
    }

    // Select2
    function initSelect2() {
        $('#language-select, #voice-select, #clone-voice-style').select2({
            placeholder: 'Select an option',
            width: '100%',
            templateResult: formatVoiceOption,
            templateSelection: formatVoiceSelection,
            dropdownParent: $('.modal.show').length ? $('.modal.show') : document.body
        });
    }

    function formatVoiceOption(voice) {
        if (!voice.id) return voice.text;
        
        return $(
            `<div class="flex justify-between items-center py-2">
                <span>${voice.text}</span>
                ${voice.element && $(voice.element).data('info') ? 
                    `<button class="play-voice-btn text-blue-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors" 
                     data-voice-id="${voice.id}" 
                     data-sample-text="${$(voice.element).data('info').sample_text}">
                        <i class="fas fa-play"></i>
                    </button>` : ''}
            </div>`
        );
    }

    function formatVoiceSelection(voice) {
        return voice.text;
    }

    // Voice Sample Playback
    $(document).on('click', '.play-voice-btn', function(e) {
        e.stopPropagation();
        const voiceId = $(this).data('voice-id');
        const sampleText = $(this).data('sample-text');
        const voice = $('#voice-select').find(`option[value="${voiceId}"]`).data('info');
        
        if (voice && sampleText) {
            playVoiceSample(voice, sampleText);
        }
    });

    function playVoiceSample(voice, text) {
        if (!isAuthenticated) {
            openModal('loginModal');
            showToast('error', 'Please log in to play voice samples');
            return;
        }

        const playBtn = $(`.play-voice-btn[data-voice-id="${voice.id}"]`);
        playBtn.html('<i class="fas fa-spinner fa-spin"></i>').prop('disabled', true);

        $.ajax({
            url: `${API_BASE_URL}/api/generate_tts`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                language: $('#language-select').val(),
                voice: voice.id,
                text: text || voice.sample_text,
                speed: 1,
                pitch: 1,
                use_ssml: false
            }),
            xhrFields: { withCredentials: true },
            success: function(data) {
                if (data.filename) {
                    const audioUrl = `${API_BASE_URL}/static/audio/Output/${data.filename}`;
                    const audioPlayer = $('#audioPlayer')[0];
                    
                    audioPlayer.src = audioUrl;
                    audioPlayer.classList.remove('hidden');
                    
                    audioPlayer.onplay = function() {
                        $('#audioPlayerControls').removeClass('hidden');
                        gsap.from('#audioPlayerControls', { 
                            opacity: 0, 
                            y: 20, 
                            duration: 0.5 
                        });
                    };
                    
                    audioPlayer.onended = function() {
                        $('#audioPlayerControls').addClass('hidden');
                        playBtn.html('<i class="fas fa-play"></i>').prop('disabled', false);
                    };
                    
                    audioPlayer.play().catch(e => {
                        showToast('error', 'Playback failed. Please try again.');
                        playBtn.html('<i class="fas fa-play"></i>').prop('disabled', false);
                    });
                    
                    $('#downloadBtn').attr('href', audioUrl).removeClass('hidden');
                    showToast('success', 'Voice sample generated successfully');
                } else {
                    showToast('error', 'Failed to generate voice sample');
                }
            },
            error: function(xhr) {
                showToast('error', xhr.responseJSON?.error || 'Failed to generate voice sample');
                playBtn.html('<i class="fas fa-play"></i>').prop('disabled', false);
            }
        });
    }

    // Stop Audio Playback
    $('#stopAudioBtn').click(function() {
        const audioPlayer = $('#audioPlayer')[0];
        audioPlayer.pause();
        audioPlayer.currentTime = 0;
        $('#audioPlayerControls').addClass('hidden');
    });

    // Auth Status
    function checkAuthStatus() {
        $('.auth-loading').removeClass('hidden');
        
        $.ajax({
            url: `${API_BASE_URL}/api/auth/status`,
            method: 'GET',
            xhrFields: { withCredentials: true },
            success: function(data) {
                isAuthenticated = data.authenticated;
                
                if (isAuthenticated) {
                    $('#userName, #dropdownName, #profileName').text(data.user.name);
                    $('#dropdownEmail, #profileEmail').text(data.user.email);
                    $('#dropdownPlan, #profilePlan').text(data.user.plan);
                    
                    $('#userMenu').removeClass('hidden');
                    $('#authButtons').addClass('hidden');
                    $('#analytics-content').removeClass('hidden');
                    $('#analytics-login-prompt').addClass('hidden');
                    
                    $('#charsUsed').text(data.user.chars_used);
                    $('#charLimit').text(data.user.char_limit);
                    
                    // Update usage bar
                    const usagePercent = Math.min(100, (data.user.chars_used / data.user.char_limit) * 100);
                    $('#charsUsedBar').css('width', `${usagePercent}%`);
                    
                    $.get(`${API_BASE_URL}/api/analytics`, function(analytics) {
                        $('#apiCalls').text(analytics.api_calls);
                        gsap.from('#apiCalls', { 
                            scale: 0.8, 
                            opacity: 0, 
                            duration: 0.6 
                        });
                    });
                    
                    loadLanguages();
                    
                    gsap.from('#userMenu', { 
                        opacity: 0, 
                        scale: 0.9, 
                        duration: 0.5, 
                        ease: 'back.out(1.5)' 
                    });
                } else {
                    $('#userMenu').addClass('hidden');
                    $('#authButtons').removeClass('hidden');
                    $('#analytics-content').addClass('hidden');
                    $('#analytics-login-prompt').removeClass('hidden');
                }
            },
            error: function(xhr) {
                showToast('error', 'Failed to check authentication status');
            },
            complete: function() {
                $('.auth-loading').addClass('hidden');
            }
        });
    }

    // Languages
    function loadLanguages() {
        $.get(`${API_BASE_URL}/api/languages`, function(data) {
            const langSelect = $('#language-select');
            langSelect.empty().append('<option value="">Select Language</option>');
            
            data.languages.forEach(lang => {
                langSelect.append(`<option value="${lang.id}">${lang.text}</option>`);
            });
        }).fail(function() {
            showToast('error', 'Failed to load languages');
        });
    }

    // Forms
    function initForms() {
        // Language select change handler
        $('#language-select').on('change', function() {
            const lang = $(this).val();
            const voiceSelect = $('#voice-select');
            voiceSelect.empty().append('<option value="">Select Voice</option>');
            
            if (lang) {
                $.get(`${API_BASE_URL}/api/voices?language=${lang}`, function(data) {
                    data.voices.forEach(voice => {
                        const option = new Option(
                            `${voice.text} - ${voice.style} (${voice.gender})`,
                            voice.id
                        );
                        $(option).data('info', voice);
                        voiceSelect.append(option);
                    });
                    voiceSelect.trigger('change');
                }).fail(function() {
                    showToast('error', 'Failed to load voices');
                });
            }
        });

        // Voice select change handler
        $('#voice-select').on('change', function() {
            const voice = $(this).find('option:selected').data('info');
            
            if (voice) {
                $('#voiceDescription').text(voice.description || 'Natural voice');
                $('#voiceStyle').text(voice.style || 'Neutral');
                $('#voiceUseCases').text(voice.use_cases || 'Narration, audiobooks');
                $('#voiceAge').text(voice.age || 'Adult');
                $('#voiceMood').text(voice.mood || 'Calm');
                $('#voiceSample').text(voice.sample_text || 'Hello, this is a sample.');
                
                $('#voiceInfo').removeClass('hidden');
                gsap.from('#voiceInfo', { 
                    opacity: 0, 
                    y: 20, 
                    duration: 0.4 
                });
            } else {
                $('#voiceInfo').addClass('hidden');
            }
        });

        // Play sample button
        $('#playSampleBtn').click(function(e) {
            e.preventDefault();
            const voice = $('#voice-select').find('option:selected').data('info');
            
            if (!voice) {
                showToast('error', 'Please select a voice');
                return;
            }
            
            playVoiceSample(voice, $('#voiceSample').text());
        });

        // TTS Form submission
        $('#ttsForm').submit(function(e) {
            e.preventDefault();
            
            if (!isAuthenticated) {
                openModal('loginModal');
                showToast('error', 'Please log in to generate speech');
                return;
            }

            const language = $('#language-select').val();
            const voice = $('#voice-select').val();
            const text = $('#tts-text').val().trim();
            const speed = $('#speed').val();
            const pitch = $('#pitch').val();
            const useSSML = $('#use_ssml').prop('checked');

            if (!language || !voice || !text) {
                showToast('error', 'Please fill all required fields');
                return;
            }

            $('#generateLoader').removeClass('hidden');
            $('#generate-btn').prop('disabled', true);

            $.ajax({
                url: `${API_BASE_URL}/api/generate_tts`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    language,
                    voice,
                    text,
                    speed: parseFloat(speed),
                    pitch: parseFloat(pitch),
                    use_ssml: useSSML
                }),
                xhrFields: { withCredentials: true },
                success: function(data) {
                    if (data.filename) {
                        const audioUrl = `${API_BASE_URL}/static/audio/Output/${data.filename}`;
                        const audioPlayer = $('#audioPlayer')[0];
                        
                        audioPlayer.src = audioUrl;
                        audioPlayer.classList.remove('hidden');
                        $('#audioPlayerControls').removeClass('hidden');
                        $('#downloadBtn').attr('href', audioUrl).removeClass('hidden');
                        
                        showToast('success', 'Speech generated successfully');
                        
                        gsap.from('#audioPlayerControls', { 
                            opacity: 0, 
                            y: 20, 
                            duration: 0.5 
                        });
                        
                        // Update character count
                        checkAuthStatus();
                    } else {
                        showToast('error', 'Failed to generate speech');
                    }
                },
                error: function(xhr) {
                    showToast('error', xhr.responseJSON?.error || 'Failed to generate speech');
                },
                complete: function() {
                    $('#generateLoader').addClass('hidden');
                    $('#generate-btn').prop('disabled', false);
                }
            });
        });

        // File upload handler
        $('#file-upload').change(function(e) {
            const file = e.target.files[0];
            
            if (file) {
                $('#fileName').text(file.name);
                $('#fileLoader').removeClass('hidden');
                
                const formData = new FormData();
                formData.append('file', file);

                $.ajax({
                    url: `${API_BASE_URL}/api/upload_text`,
                    method: 'POST',
                    data: formData,
                    processData: false,
                    contentType: false,
                    xhrFields: { withCredentials: true },
                    success: function(data) {
                        if (data.text) {
                            $('#tts-text').val(data.text);
                            updateCharCount();
                            showToast('success', 'File uploaded successfully');
                        } else {
                            showToast('error', 'Failed to process file');
                        }
                    },
                    error: function(xhr) {
                        showToast('error', xhr.responseJSON?.error || 'Failed to upload file');
                    },
                    complete: function() {
                        $('#fileLoader').addClass('hidden');
                    }
                });
            }
        });

        // Speed slider
        $('#speed').on('input', function() {
            $('#speedValue').text(`${$(this).val()}x`);
        });

        // Pitch slider
        $('#pitch').on('input', function() {
            $('#pitchValue').text(`${$(this).val()}x`);
        });

        // STT Form submission
        $('#sttForm').submit(function(e) {
            e.preventDefault();
            
            if (!isAuthenticated) {
                openModal('loginModal');
                showToast('error', 'Please log in to transcribe audio');
                return;
            }

            const blob = $('#audio-upload').data('blob');
            
            if (!blob) {
                showToast('error', 'Please upload or record audio');
                return;
            }

            $('#transcribeLoader').removeClass('hidden');
            $('#transcribe-btn').prop('disabled', true);

            const formData = new FormData();
            formData.append('audio', blob, 'audio.wav');

            $.ajax({
                url: `${API_BASE_URL}/api/transcribe`,
                method: 'POST',
                data: formData,
                processData: false,
                contentType: false,
                xhrFields: { withCredentials: true },
                success: function(data) {
                    if (data.transcription) {
                        $('#transcription').val(data.transcription);
                        showToast('success', 'Transcription completed');
                        
                        // Update character count
                        checkAuthStatus();
                    } else {
                        showToast('error', 'Failed to transcribe audio');
                    }
                },
                error: function(xhr) {
                    showToast('error', xhr.responseJSON?.error || 'Failed to transcribe audio');
                },
                complete: function() {
                    $('#transcribeLoader').addClass('hidden');
                    $('#transcribe-btn').prop('disabled', false);
                }
            });
        });

        // Copy transcription button
        $('#copyTranscriptionBtn').click(function() {
            const transcription = $('#transcription').val();
            
            if (transcription) {
                navigator.clipboard.writeText(transcription).then(() => {
                    showToast('success', 'Transcription copied to clipboard');
                }).catch(() => {
                    showToast('error', 'Failed to copy transcription');
                });
            } else {
                showToast('error', 'No transcription to copy');
            }
        });

        // Start recording button
        $('#startRecordBtn').click(function(e) {
            e.preventDefault();
            
            if (!isAuthenticated) {
                openModal('loginModal');
                showToast('error', 'Please log in to record audio');
                return;
            }

            $('#transcribeLoader').addClass('hidden');
            
            navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                recordedChunks = [];

                mediaRecorder.ondataavailable = function(e) {
                    recordedChunks.push(e.data);
                };

                mediaRecorder.onstop = function() {
                    const blob = new Blob(recordedChunks, { type: 'audio/wav' });
                    const url = URL.createObjectURL(blob);
                    
                    $('#transcribe-btn').prop('disabled', false);
                    $('#audioFileName').text('Recorded Audio');
                    $('#audio-upload').data('blob', blob);
                    
                    // Stop all tracks in the stream
                    stream.getTracks().forEach(track => track.stop());
                };

                mediaRecorder.start();
                $('#startRecordBtn').addClass('hidden');
                $('#stopRecordBtn').removeClass('hidden');
                
                showToast('info', 'Recording started...');
            }).catch(err => {
                showToast('error', 'Failed to access microphone: ' + err.message);
                $('#transcribeLoader').addClass('hidden');
            });
        });

        // Stop recording button
        $('#stopRecordBtn').click(function(e) {
            e.preventDefault();
            
            if (mediaRecorder) {
                mediaRecorder.stop();
                $('#transcribeLoader').addClass('hidden');
                $('#transcribe-btn').prop('disabled', false);
                
                showToast('success', 'Recording stopped');
            }
        });

        // Audio upload handler
        $('#audio-upload').change(function(e) {
            const file = e.target.files[0];
            
            if (file) {
                $('#audioFileName').text(file.name);
                $('#transcribe-btn').prop('disabled', false);
                $('#transcribeLoader').addClass('hidden');
                $('#audio-upload').data('blob', file);
            } else {
                $('#transcribe-btn').prop('disabled', true);
            }
        });

        // Clone form submission
        $('#cloneForm').submit(function(e) {
            e.preventDefault();
            showToast('info', 'Voice cloning is coming soon. Join our waitlist to get notified when it launches.');
        });

        // Login form submission
        $('#loginForm').submit(function(e) {
            e.preventDefault();
            
            const email = $('#loginEmail').val().trim();
            const password = $('#loginPassword').val();
            
            if (!email || !password) {
                showToast('error', 'Please enter email and password');
                return;
            }
            
            $('.auth-loading').removeClass('hidden');
            
            $.ajax({
                url: `${API_BASE_URL}/api/auth/login`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ email, password }),
                xhrFields: { withCredentials: true },
                success: function(data) {
                    if (data.error) {
                        showToast('error', data.error);
                    } else {
                        showToast('success', 'Login successful');
                        
                        setTimeout(() => {
                            closeModal('loginModal');
                            checkAuthStatus();
                        }, 1500);
                    }
                },
                error: function(xhr) {
                    const errorMsg = xhr.status === 401 ? 'Invalid email or password' : 
                                    xhr.responseJSON?.error || 'Login failed';
                    
                    showToast('error', errorMsg);
                },
                complete: function() {
                    $('.auth-loading').addClass('hidden');
                }
            });
        });

        // Signup form submission
        $('#signupForm').submit(function(e) {
            e.preventDefault();
            
            const name = $('#signupName').val().trim();
            const email = $('#signupEmail').val().trim();
            const password = $('#signupPassword').val();
            const confirmPassword = $('#signupConfirmPassword').val();
            
            if (!name || !email || !password || !confirmPassword) {
                showToast('error', 'Please fill all fields');
                return;
            }
            
            if (password !== confirmPassword) {
                showToast('error', 'Passwords do not match');
                return;
            }
            
            if (!/^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/.test(password)) {
                showToast('error', 'Password must be at least 8 characters with 1 number');
                return;
            }
            
            if (!$('#terms').prop('checked')) {
                showToast('error', 'Please agree to the terms and conditions');
                return;
            }
            
            $('.auth-loading').removeClass('hidden');
            
            $.ajax({
                url: `${API_BASE_URL}/api/auth/signup`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ name, email, password }),
                xhrFields: { withCredentials: true },
                success: function(data) {
                    if (data.error) {
                        showToast('error', data.error);
                    } else {
                        showToast('success', 'Account created successfully');
                        
                        setTimeout(() => {
                            closeModal('signupModal');
                            openModal('loginModal');
                        }, 1500);
                    }
                },
                error: function(xhr) {
                    const errorMsg = xhr.status === 409 ? 'Account already exists' : 
                                    xhr.responseJSON?.error || 'Signup failed';
                    
                    showToast('error', errorMsg);
                },
                complete: function() {
                    $('.auth-loading').addClass('hidden');
                }
            });
        });

        // Settings form submission
        $('#settingsForm').submit(function(e) {
            e.preventDefault();
            
            const currentPassword = $('#currentPassword').val();
            const newPassword = $('#newPassword').val();
            const confirmPassword = $('#confirmPassword').val();
            
            if (!currentPassword || !newPassword || !confirmPassword) {
                showToast('error', 'Please fill all fields');
                return;
            }
            
            if (newPassword !== confirmPassword) {
                showToast('error', 'New passwords do not match');
                return;
            }
            
            if (!/^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/.test(newPassword)) {
                showToast('error', 'Password must be at least 8 characters with 1 number');
                return;
            }
            
            $.ajax({
                url: `${API_BASE_URL}/api/user/update_password`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ 
                    current_password: currentPassword,
                    new_password: newPassword 
                }),
                xhrFields: { withCredentials: true },
                success: function(data) {
                    showToast('success', 'Password updated successfully');
                    
                    $('#currentPassword, #newPassword, #confirmPassword').val('');
                    
                    setTimeout(() => closeModal('profileModal'), 1500);
                },
                error: function(xhr) {
                    showToast('error', xhr.responseJSON?.error || 'Failed to update password');
                }
            });
        });
    }

    // Profile Tabs
    $('.tab-btn').click(function(e) {
        e.preventDefault();
        
        $('.tab-btn').removeClass('text-blue-500 border-b-2 border-blue-500')
                     .addClass('text-gray-600 dark:text-gray-400');
        
        $(this).addClass('text-blue-500 border-b-2 border-blue-500')
               .removeClass('text-gray-600 dark:text-gray-400');
        
        $('.tab-content').addClass('hidden');
        $(`#${$(this).data('tab')}`).removeClass('hidden');
        
        gsap.from(`#${$(this).data('tab')}`, { 
            opacity: 0, 
            x: 20, 
            duration: 0.4 
        });
    });

    // Modal Controls
    $('#loginButton, #login-prompt-btn, #signup-cta-btn').click(function(e) {
        e.preventDefault();
        openModal('loginModal');
    });

    $('#signupButton, #signup-btn').click(function(e) {
        e.preventDefault();
        openModal('signupModal');
    });

    $('#profileBtn').click(function(e) {
        e.preventDefault();
        
        if (isAuthenticated) {
            openModal('profileModal');
        } else {
            openModal('loginModal');
        }
    });

    // Logout
    $('#logoutBtn').click(function(e) {
        e.preventDefault();
        
        $.ajax({
            url: `${API_BASE_URL}/api/auth/logout`,
            method: 'POST',
            xhrFields: { withCredentials: true },
            success: function() {
                isAuthenticated = false;
                checkAuthStatus();
                showToast('success', 'Logged out successfully');
                
                // Close profile modal if open
                closeModal('profileModal');
            },
            error: function(xhr) {
                showToast('error', xhr.responseJSON?.error || 'Logout failed');
            }
        });
    });

    // Pricing Plans
    $('.btn-plan-free, .btn-plan-pro, .btn-plan-enterprise').click(function(e) {
        e.preventDefault();
        
        if (!isAuthenticated) {
            openModal('loginModal');
            showToast('error', 'Please log in to select a plan');
            return;
        }

        const currentPlan = $('#dropdownPlan').text();
        const newPlan = $(this).hasClass('btn-plan-free') ? 'Free' :
                       $(this).hasClass('btn-plan-pro') ? 'Pro' : 'Enterprise';

        if (currentPlan === newPlan) {
            showToast('warning', `You are already on the ${newPlan} plan`);
            return;
        }

        if (newPlan === 'Enterprise') {
            showToast('info', 'Please contact support for Enterprise plan details');
            window.location.href = 'mailto:support@skytts.com';
            return;
        }

        if (confirm(`Are you sure you want to switch to the ${newPlan} plan?`)) {
            $.ajax({
                url: `${API_BASE_URL}/api/user/update_plan`,
                method: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ plan: newPlan }),
                xhrFields: { withCredentials: true },
                success: function(data) {
                    showToast('success', `Plan upgraded to ${newPlan}!`);
                    
                    gsap.from('#dropdownPlan', { 
                        scale: 0.8, 
                        opacity: 0, 
                        duration: 0.6 
                    });
                    
                    checkAuthStatus();
                },
                error: function(xhr) {
                    showToast('error', xhr.responseJSON?.error || 'Failed to update plan');
                }
            });
        }
    });

    // Character Count
    function updateCharCount() {
        const text = $('#tts-text').val();
        const count = text.length;
        
        $('#charCount').text(count);
        
        if (count > parseInt($('#charLimit').text())) {
            $('#tts-text').val(text.substring(0, parseInt($('#charLimit').text())));
            showToast('error', 'Character limit exceeded');
        }
    }

    $('#tts-text').on('input', updateCharCount);

    // Toast Notification
    function showToast(type, message) {
        const toastId = `toast-${Date.now()}`;
        const toast = $('<div>')
            .attr('id', toastId)
            .addClass(`toast fixed top-6 right-6 p-5 rounded-xl shadow-2xl text-white z-50 max-w-md border border-opacity-30 flex items-start justify-between`)
            .css({
                'background-color': type === 'success' ? '#10b981' : 
                                  type === 'error' ? '#ef4444' : 
                                  type === 'warning' ? '#f59e0b' : 
                                  type === 'info' ? '#3b82f6' : '#64748b',
                'border-color': type === 'success' ? 'rgba(16,185,129,0.6)' : 
                                type === 'error' ? 'rgba(239,68,68,0.6)' : 
                                type === 'warning' ? 'rgba(245,158,11,0.6)' : 
                                type === 'info' ? 'rgba(59,130,246,0.6)' : 'rgba(100,116,139,0.6)'
            })
            .html(`
                <div class="flex items-start">
                    <i class="fas fa-${type === 'success' ? 'check-circle' : 
                                      type === 'error' ? 'exclamation-circle' : 
                                      type === 'warning' ? 'exclamation-triangle' : 
                                      'info-circle'} mt-0.5 mr-3 text-lg"></i>
                    <div>
                        <p class="font-medium">${type.charAt(0).toUpperCase() + type.slice(1)}</p>
                        <p class="text-sm opacity-90">${message}</p>
                    </div>
                </div>
                <button class="toast-close ml-4 text-white hover:text-gray-200 transition-colors" data-toast-id="${toastId}">
                    <i class="fas fa-times"></i>
                </button>
            `);
        
        $('body').append(toast);
        
        gsap.fromTo(toast, 
            { opacity: 0, y: -30, scale: 0.9 },
            { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'back.out(1.5)' }
        );
        
        setTimeout(() => {
            gsap.to(toast, {
                opacity: 0,
                y: -30,
                scale: 0.9,
                duration: 0.4,
                onComplete: () => toast.remove()
            });
        }, 5000);

        $(document).on('click', `.toast-close[data-toast-id="${toastId}"]`, function() {
            gsap.to(`#${toastId}`, {
                opacity: 0,
                y: -30,
                scale: 0.9,
                duration: 0.4,
                onComplete: () => $(`#${toastId}`).remove()
            });
        });
    }

    // Accessibility
    $(document).keydown(function(e) {
        if (e.key === 'Escape') {
            $('.modal.show').each(function() {
                closeModal(this.id);
            });
        }
    });

    $('.nav-link').attr('tabindex', '0').on('keypress', function(e) {
        if (e.key === 'Enter') {
            $(this).trigger('click');
        }
    });

    // Initialize the app
    initApp();
});