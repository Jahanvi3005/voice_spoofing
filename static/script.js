// script.js

document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM Content Loaded. Initializing app...');

    // --- Global/Top-level elements for login status and navbar ---
    const openLoginModalBtn = document.getElementById('open-login-modal-btn');
    const loggedInInfo = document.getElementById('logged-in-info');
    const userEmailDisplay = document.getElementById('user-email-display');
    const logoutBtn = document.getElementById('logout-btn');
    const userIdDisplay = document.getElementById('user-id-display');

    // Global variable to track login status
    let isUserLoggedIn = false;

    // Attach listener for the main navbar login button
    if (openLoginModalBtn) {
        openLoginModalBtn.addEventListener('click', () => {
            console.log('Navbar Login Button Clicked.');
            const loginModal = document.getElementById('login-modal');
            if (loginModal) {
                loginModal.classList.remove('hidden');
                const modalMessage = document.getElementById('modal-message');
                if (modalMessage) modalMessage.classList.add('hidden'); // Hide message on open
                console.log('Login modal opened.');
            } else {
                console.error('Error: Login modal element not found when main login button clicked.');
            }
        });
    } else {
        console.warn('Warning: openLoginModalBtn not found.');
    }


    // --- Navbar Toggle for Mobile ---
    const navbarToggleBtn = document.getElementById('navbar-toggle-btn');
    const navbarLinks = document.getElementById('navbar-links');

    if (navbarToggleBtn && navbarLinks) {
        navbarToggleBtn.addEventListener('click', () => {
            console.log('Navbar Toggle Button Clicked.');
            navbarLinks.classList.toggle('hidden');
            navbarLinks.classList.toggle('flex'); // Ensure it becomes flex when active
        });
    } else {
        console.warn('Warning: Navbar toggle elements not found (navbarToggleBtn or navbarLinks).');
    }

    // --- Smooth Scrolling for Navigation Links ---
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            console.log(`Smooth scrolling to: ${targetId}`);
            document.querySelector(targetId).scrollIntoView({
                behavior: 'smooth'
            });
            // Close mobile nav after clicking a link
            if (navbarLinks && !navbarLinks.classList.contains('hidden')) {
                navbarLinks.classList.add('hidden');
                navbarLinks.classList.remove('flex');
            }
        });
    });

    // --- Scroll Progress Bar ---
    const scrollProgressBar = document.getElementById('scroll-progress-bar');
    if (scrollProgressBar) {
        window.addEventListener('scroll', () => {
            const totalHeight = document.body.scrollHeight - window.innerHeight;
            const progress = (window.scrollY / totalHeight) * 100;
            scrollProgressBar.style.width = progress + '%';
        });
    } else {
        console.warn('Warning: Scroll progress bar element not found.');
    }

    // --- Theme Toggle ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            console.log('Theme Toggle Button Clicked.');
            document.body.classList.toggle('dark-mode');
            // Save theme preference to localStorage
            if (document.body.classList.contains('dark-mode')) {
                localStorage.setItem('theme', 'dark');
            } else {
                localStorage.setItem('theme', 'light');
            }
            // Re-embed Twitter timeline to update its theme
            // embedTwitterTimeline(); // Removed as Twitter feed is replaced by news
        });
    } else {
        console.warn('Warning: Theme toggle button not found.');
    }

    // Apply saved theme preference on load
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }

    // --- Message Box Utility ---
    function showMessageBox(message, type = 'info', duration = 3000) {
        const messageBox = document.getElementById('message-box');
        if (!messageBox) {
            console.error('Error: Message box element not found.');
            return;
        }

        messageBox.textContent = message;
        messageBox.className = 'fixed bottom-4 right-4 text-white px-6 py-3 rounded-lg shadow-lg transition-all duration-300';

        switch (type) {
            case 'success':
                messageBox.classList.add('bg-green-600');
                break;
            case 'error':
                messageBox.classList.add('bg-red-600');
                break;
            case 'warning':
                messageBox.classList.add('bg-yellow-600');
                break;
            default:
                messageBox.classList.add('bg-gray-700');
                break;
        }

        messageBox.classList.remove('hidden');
        messageBox.classList.add('block', 'opacity-100', 'translate-y-0');

        setTimeout(() => {
            messageBox.classList.remove('opacity-100', 'translate-y-0');
            messageBox.classList.add('opacity-0', 'translate-y-4');
            setTimeout(() => {
                messageBox.classList.remove('block');
                messageBox.classList.add('hidden');
            }, 300); // Wait for fade out transition
        }, duration);
        console.log(`Message Box displayed: ${message} (${type})`);
    }
    window.showMessageBox = showMessageBox; // Make it globally accessible

    // --- Copy Email to Clipboard ---
    const copyEmailBtn = document.getElementById('copy-email-btn');
    const contactEmailSpan = document.getElementById('contact-email');

    if (copyEmailBtn && contactEmailSpan) {
        copyEmailBtn.addEventListener('click', () => {
            const email = contactEmailSpan.textContent;
            const tempInput = document.createElement('input');
            document.body.appendChild(tempInput);
            tempInput.value = email;
            tempInput.select();
            document.execCommand('copy');
            document.body.removeChild(tempInput);
            showMessageBox('Email copied to clipboard!', 'success');
            console.log('Email copied to clipboard.');
        });
    } else {
        console.warn('Warning: Copy email button or contact email span not found.');
    }

    // --- Dynamic Loading of Partials (Login Modal) ---
    async function loadPartial(placeholderId, partialPath) {
        const placeholder = document.getElementById(placeholderId);
        if (placeholder) {
            try {
                console.log(`Attempting to load partial: ${partialPath} into ${placeholderId}`);
                const response = await fetch(partialPath);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const html = await response.text();
                placeholder.innerHTML = html;
                console.log(`Partial ${partialPath} loaded successfully into ${placeholderId}`);
                return true; // Indicate successful load
            } catch (error) {
                console.error(`Failed to load partial ${partialPath}:`, error);
                showMessageBox(`Failed to load a part of the page: ${partialPath}`, 'error');
                return false; // Indicate failed load
            }
        } else {
            console.error(`Error: Placeholder element '${placeholderId}' not found for partial '${partialPath}'.`);
            return false;
        }
    }

    // Load Login Modal
    loadPartial('login-modal-placeholder', '/static/partials/login.html').then(loaded => {
        if (loaded) {
            console.log('Login modal partial loaded. Initializing login modal...');
            initLoginModal();
            checkUserLoginStatus(); // Check status after modal is loaded
        } else {
            console.error('Login modal partial failed to load. Login functionality may be impaired.');
        }
    });

    // --- Login/Registration Modal Logic ---
    function initLoginModal() {
        const loginModal = document.getElementById('login-modal');
        const closeLoginModalBtn = document.getElementById('close-login-modal-btn');
        const loginForm = document.getElementById('login-form');
        const registerForm = document.getElementById('register-form');
        const showRegisterFormLink = document.getElementById('show-register-form');
        const showLoginFormLink = document.getElementById('show-login-form');
        const modalTitle = document.getElementById('modal-title');
        const modalMessage = document.getElementById('modal-message');

        if (!loginModal || !closeLoginModalBtn || !loginForm || !registerForm || !showRegisterFormLink || !showLoginFormLink || !modalTitle || !modalMessage) {
            console.error('Error: One or more login modal elements not found after partial load. Login/Register functionality will not work.');
            return;
        }
        console.log('All login modal elements found. Attaching listeners.');

        closeLoginModalBtn.addEventListener('click', () => {
            loginModal.classList.add('hidden');
            console.log('Login modal closed by button.');
        });

        // Close modal if clicked outside content
        loginModal.addEventListener('click', (e) => {
            if (e.target === loginModal) {
                loginModal.classList.add('hidden');
                console.log('Login modal closed by clicking outside.');
            }
        });

        showRegisterFormLink.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('Showing register form.');
            loginForm.classList.add('hidden');
            registerForm.classList.remove('hidden');
            modalTitle.textContent = 'Register';
            modalMessage.classList.add('hidden');
        });

        showLoginFormLink.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('Showing login form.');
            registerForm.classList.add('hidden');
            loginForm.classList.remove('hidden');
            modalTitle.textContent = 'Login / Register';
            modalMessage.classList.add('hidden');
        });

        // Login Logic
        const loginSubmitBtn = document.getElementById('login-submit');
        if (loginSubmitBtn) {
            loginSubmitBtn.addEventListener('click', async () => {
                const email = document.getElementById('login-email').value;
                const password = document.getElementById('login-password').value;
                const currentModalMessage = modalMessage;
                currentModalMessage.classList.remove('hidden', 'text-green-600', 'text-red-600');
                currentModalMessage.classList.add('text-gray-500');
                currentModalMessage.textContent = 'Logging in...';
                console.log('Attempting login for:', email);

                try {
                    const response = await fetch('/api/login', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password })
                    });
                    const data = await response.json();
                    if (response.ok) {
                        currentModalMessage.textContent = data.message;
                        currentModalMessage.classList.remove('text-gray-500');
                        currentModalMessage.classList.add('text-green-600');
                        showMessageBox('Login successful!', 'success');
                        console.log('Login successful for:', email);
                        setTimeout(() => {
                            loginModal.classList.add('hidden');
                            checkUserLoginStatus();
                        }, 1000);
                    } else {
                        currentModalMessage.textContent = data.message || 'Login failed.';
                        currentModalMessage.classList.remove('text-gray-500');
                        currentModalMessage.classList.add('text-red-600');
                        showMessageBox(data.message || 'Login failed.', 'error');
                        console.error('Login failed:', data.message);
                    }
                } catch (error) {
                    console.error('Login fetch error:', error);
                    currentModalMessage.textContent = 'An error occurred. Please try again.';
                    currentModalMessage.classList.remove('text-gray-500');
                    currentModalMessage.classList.add('text-red-600');
                    showMessageBox('An error occurred during login.', 'error');
                }
            });
        } else {
            console.error('Error: Login submit button not found.');
        }


        // Register Logic
        const registerSubmitBtn = document.getElementById('register-submit');
        if (registerSubmitBtn) {
            registerSubmitBtn.addEventListener('click', async () => {
                const email = document.getElementById('register-email').value;
                const password = document.getElementById('register-password').value;
                const confirmPassword = document.getElementById('register-confirm-password').value;
                const currentModalMessage = modalMessage;
                currentModalMessage.classList.remove('hidden', 'text-green-600', 'text-red-600');
                currentModalMessage.classList.add('text-gray-500');
                currentModalMessage.textContent = 'Registering...';
                console.log('Attempting registration for:', email);

                if (password !== confirmPassword) {
                    currentModalMessage.textContent = 'Passwords do not match.';
                    currentModalMessage.classList.remove('text-gray-500');
                    currentModalMessage.classList.add('text-red-600');
                    showMessageBox('Passwords do not match.', 'error');
                    console.warn('Registration failed: Passwords do not match.');
                    return;
                }

                try {
                    const response = await fetch('/api/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, password })
                    });
                    const data = await response.json();
                    if (response.ok) {
                        currentModalMessage.textContent = data.message;
                        currentModalMessage.classList.remove('text-gray-500');
                        currentModalMessage.classList.add('text-green-600');
                        showMessageBox('Registration successful! Please log in.', 'success');
                        console.log('Registration successful for:', email);
                        setTimeout(() => {
                            showLoginFormLink.click(); // Switch back to login form
                            currentModalMessage.classList.add('hidden');
                        }, 1500);
                    } else {
                        currentModalMessage.textContent = data.message || 'Registration failed.';
                        currentModalMessage.classList.remove('text-gray-500');
                        currentModalMessage.classList.add('text-red-600');
                        showMessageBox(data.message || 'Registration failed.', 'error');
                        console.error('Registration failed:', data.message);
                    }
                } catch (error) {
                    console.error('Registration fetch error:', error);
                    currentModalMessage.textContent = 'An error occurred. Please try again.';
                    currentModalMessage.classList.remove('text-gray-500');
                    currentModalMessage.classList.add('text-red-600');
                    showMessageBox('An error occurred during registration.', 'error');
                }
            });
        } else {
            console.error('Error: Register submit button not found.');
        }
    }

    // --- User Login Status Check and Display ---
    async function checkUserLoginStatus() {
        console.log('Checking user login status...');
        try {
            const response = await fetch('/api/current_user');
            const data = await response.json();
            if (data.user_email) {
                isUserLoggedIn = true;
                if (userEmailDisplay) userEmailDisplay.textContent = data.user_email;
                if (loggedInInfo) loggedInInfo.classList.remove('hidden');
                if (openLoginModalBtn) openLoginModalBtn.classList.add('hidden');
                if (userIdDisplay) userIdDisplay.textContent = `Logged in as: ${data.user_email}`;
                fetchAnalysisHistory(); // Fetch history if logged in
                console.log('User is logged in:', data.user_email);
            } else {
                isUserLoggedIn = false;
                if (userEmailDisplay) userEmailDisplay.textContent = '';
                if (loggedInInfo) loggedInInfo.classList.add('hidden');
                if (openLoginModalBtn) openLoginModalBtn.classList.remove('hidden');
                if (userIdDisplay) userIdDisplay.textContent = '';
                const analysisHistoryList = document.getElementById('analysis-history-list');
                if (analysisHistoryList) {
                    analysisHistoryList.innerHTML = '<li class="text-center text-gray-500 dark:text-gray-400">Log in to view your analysis history.</li>';
                }
                console.log('User is not logged in.');
            }

            // Attach logout listener here, after logoutBtn is guaranteed to exist
            if (logoutBtn) {
                logoutBtn.removeEventListener('click', handleLogout); // Prevent duplicate listeners
                logoutBtn.addEventListener('click', handleLogout);
            } else {
                console.warn('Warning: Logout button not found.');
            }
        } catch (error) {
            console.error('Error checking login status:', error);
            isUserLoggedIn = false; // Ensure state is correctly set even on error
            if (userEmailDisplay) userEmailDisplay.textContent = '';
            if (loggedInInfo) loggedInInfo.classList.add('hidden');
            if (openLoginModalBtn) openLoginModalBtn.classList.remove('hidden');
            if (userIdDisplay) userIdDisplay.textContent = '';
            showMessageBox('Failed to verify login status. Please refresh.', 'error');
        }
        updateAnalyzeButtonState(); // Update button state after login status is known
    }

    async function handleLogout() {
        console.log('Logout button clicked.');
        try {
            const response = await fetch('/api/logout', { method: 'POST' });
            const data = await response.json();
            if (response.ok) {
                showMessageBox('Logged out successfully!', 'success');
                console.log('Logout successful.');
                checkUserLoginStatus();
            } else {
                showMessageBox(data.message || 'Logout failed.', 'error');
                console.error('Logout failed:', data.message);
            }
        } catch (error) {
            console.error('Logout fetch error:', error);
            showMessageBox('An error occurred during logout.', 'error');
        }
    }


    // --- Voice Analysis Section Logic ---
    const audioFileInput = document.getElementById('audio-file-input');
    const fileNameDisplay = document.getElementById('file-name-display');
    const fileStatusContainer = document.getElementById('file-status-container');
    const clearFileBtn = document.getElementById('clear-file-btn');
    const analyzeVoiceBtn = document.getElementById('analyze-voice-btn');
    const analysisLoadingSpinner = document.getElementById('analysis-loading-spinner');
    const analysisResultsDiv = document.getElementById('analysis-results');
    const resultText = document.getElementById('result-text');
    const confidenceScore = document.getElementById('confidence-score');
    const analysisMessage = document.getElementById('analysis-message');

    let selectedAudioFile = null; // To store the file object
    let recordedAudioBlob = null; // To store recorded audio blob

    // Enable/disable analyze button based on file selection/recording
    function updateAnalyzeButtonState() {
        if (analyzeVoiceBtn) {
            if (isUserLoggedIn && (selectedAudioFile || recordedAudioBlob)) {
                analyzeVoiceBtn.disabled = false;
                analyzeVoiceBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                console.log('Analyze button enabled.');
            } else {
                analyzeVoiceBtn.disabled = true;
                analyzeVoiceBtn.classList.add('opacity-50', 'cursor-not-allowed');
                console.log('Analyze button disabled. User logged in:', isUserLoggedIn, 'File selected:', !!selectedAudioFile, 'Recorded audio:', !!recordedAudioBlob);
            }
        } else {
            console.warn('Warning: Analyze voice button not found.');
        }
    }

    if (audioFileInput) {
        audioFileInput.addEventListener('change', (event) => {
            console.log('Audio file input changed. Current login status:', isUserLoggedIn);
            if (!isUserLoggedIn) {
                event.target.value = ''; // Clear selected file
                showMessageBox('Please log in to upload audio.', 'warning');
                const loginModal = document.getElementById('login-modal');
                if (loginModal) {
                    loginModal.classList.remove('hidden');
                    console.log('Login modal opened due to unauthenticated upload attempt.');
                } else {
                    console.error('Error: Login modal element not found when trying to open for unauthenticated upload.');
                }
                return;
            }
            if (event.target.files.length > 0) {
                selectedAudioFile = event.target.files[0];
                if (fileNameDisplay) fileNameDisplay.textContent = selectedAudioFile.name;
                if (fileStatusContainer) fileStatusContainer.classList.remove('hidden');
                
                // Clear any existing recording when a file is uploaded
                recordedAudioBlob = null;
                if (audioPlayback) audioPlayback.src = '';
                if (audioPlayback) audioPlayback.classList.add('hidden');
                if (recordAudioBtn) recordAudioBtn.textContent = 'Start Recording';
                if (recordingStatus) recordingStatus.classList.add('hidden');
                if (playRecordingBtn) playRecordingBtn.classList.add('hidden');
                if (clearRecordingBtn) clearRecordingBtn.classList.add('hidden');
                
                console.log('Audio file selected:', selectedAudioFile.name);
            } else {
                selectedAudioFile = null;
                if (fileNameDisplay) fileNameDisplay.textContent = '';
                if (fileStatusContainer) fileStatusContainer.classList.add('hidden');
                console.log('Audio file selection cleared.');
            }
            updateAnalyzeButtonState();
        });
    } else {
        console.warn('Warning: Audio file input not found.');
    }

    if (clearFileBtn) {
        clearFileBtn.addEventListener('click', () => {
            if (audioFileInput) audioFileInput.value = '';
            selectedAudioFile = null;
            if (fileNameDisplay) fileNameDisplay.textContent = '';
            if (fileStatusContainer) fileStatusContainer.classList.add('hidden');
            updateAnalyzeButtonState();
            console.log('File selection cleared by button.');
        });
    } else {
        console.warn('Warning: Clear file button not found.');
    }

    // --- Audio Recording Logic ---
    const recordAudioBtn = document.getElementById('record-audio-btn');
    const stopRecordingBtn = document.getElementById('stop-recording-btn');
    const playRecordingBtn = document.getElementById('play-recording-btn');
    const clearRecordingBtn = document.getElementById('clear-recording-btn');
    const recordingStatus = document.getElementById('recording-status');
    const recordingTimer = document.getElementById('recording-timer');
    const audioPlayback = document.getElementById('audio-playback');

    let mediaRecorder;
    let audioChunks = [];
    let timerInterval;
    let seconds = 0;

    function startTimer() {
        seconds = 0;
        if (recordingTimer) recordingTimer.textContent = '00:00';
        timerInterval = setInterval(() => {
            seconds++;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            if (recordingTimer) recordingTimer.textContent = `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
        }, 1000);
    }

    function stopTimer() {
        clearInterval(timerInterval);
    }

    if (recordAudioBtn) {
        recordAudioBtn.addEventListener('click', async () => {
            console.log('Record audio button clicked. Current login status:', isUserLoggedIn);
            if (!isUserLoggedIn) {
                showMessageBox('Please log in to record audio.', 'warning');
                const loginModal = document.getElementById('login-modal');
                if (loginModal) {
                    loginModal.classList.remove('hidden');
                    console.log('Login modal opened due to unauthenticated record attempt.');
                } else {
                    console.error('Error: Login modal element not found when trying to open for unauthenticated record.');
                }
                return;
            }
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                recordedAudioBlob = null; // Clear previous recording

                mediaRecorder.ondataavailable = event => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    recordedAudioBlob = new Blob(audioChunks, { type: 'audio/wav' }); // or 'audio/webm'
                    const audioUrl = URL.createObjectURL(recordedAudioBlob);
                    if (audioPlayback) audioPlayback.src = audioUrl;
                    if (audioPlayback) audioPlayback.classList.remove('hidden');
                    if (playRecordingBtn) playRecordingBtn.classList.remove('hidden');
                    if (clearRecordingBtn) clearRecordingBtn.classList.remove('hidden');
                    updateAnalyzeButtonState();
                    // Stop all tracks in the stream
                    stream.getTracks().forEach(track => track.stop());
                    console.log('Recording stopped. Audio blob created.');
                };

                mediaRecorder.start();
                if (recordAudioBtn) {
                    recordAudioBtn.textContent = 'Recording...';
                    recordAudioBtn.disabled = true;
                }
                if (stopRecordingBtn) stopRecordingBtn.classList.remove('hidden');
                if (playRecordingBtn) playRecordingBtn.classList.add('hidden');
                if (clearRecordingBtn) clearRecordingBtn.classList.add('hidden');
                if (recordingStatus) recordingStatus.classList.remove('hidden');
                startTimer();
                showMessageBox('Recording started!', 'info');
                console.log('Microphone access granted. Recording started.');
            } catch (err) {
                console.error('Error accessing microphone:', err);
                showMessageBox('Could not access microphone. Please check permissions.', 'error');
            }
        });
    } else {
        console.warn('Warning: Record audio button not found.');
    }

    if (stopRecordingBtn) {
        stopRecordingBtn.addEventListener('click', () => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                mediaRecorder.stop();
                stopTimer();
                if (recordAudioBtn) {
                    recordAudioBtn.textContent = 'Start Recording';
                    recordAudioBtn.disabled = false;
                }
                if (stopRecordingBtn) stopRecordingBtn.classList.add('hidden');
                if (recordingStatus) recordingStatus.classList.add('hidden');
                showMessageBox('Recording stopped.', 'info');
                console.log('Recording stopped by user.');
            }
        });
    } else {
        console.warn('Warning: Stop recording button not found.');
    }

    if (playRecordingBtn) {
        playRecordingBtn.addEventListener('click', () => {
            if (audioPlayback && audioPlayback.src) {
                audioPlayback.play();
                showMessageBox('Playing recording...', 'info');
                console.log('Playing recorded audio.');
            } else {
                console.warn('No audio to play.');
            }
        });
    } else {
        console.warn('Warning: Play recording button not found.');
    }

    if (clearRecordingBtn) {
        clearRecordingBtn.addEventListener('click', () => {
            recordedAudioBlob = null;
            if (audioPlayback) audioPlayback.src = '';
            if (audioPlayback) audioPlayback.classList.add('hidden');
            if (playRecordingBtn) playRecordingBtn.classList.add('hidden');
            if (clearRecordingBtn) clearRecordingBtn.classList.add('hidden');
            updateAnalyzeButtonState();
            showMessageBox('Recording cleared.', 'info');
            console.log('Recorded audio cleared.');
        });
    } else {
        console.warn('Warning: Clear recording button not found.');
    }

    // --- Analyze Voice Button Click ---
    if (analyzeVoiceBtn) {
        analyzeVoiceBtn.addEventListener('click', async () => {
            let audioToAnalyze = null;

            if (selectedAudioFile) {
                audioToAnalyze = selectedAudioFile;
                console.log('Analyzing selected file:', selectedAudioFile.name);
            } else if (recordedAudioBlob) {
                audioToAnalyze = recordedAudioBlob;
                console.log('Analyzing recorded audio.');
            }

            if (!audioToAnalyze) {
                showMessageBox('Please upload an audio file or record your voice first.', 'warning');
                console.warn('Analysis attempted without audio file.');
                return;
            }

            // Show loading spinner
            if (analysisLoadingSpinner) analysisLoadingSpinner.classList.remove('hidden');
            if (analyzeVoiceBtn) {
                analyzeVoiceBtn.disabled = true;
                analyzeVoiceBtn.classList.add('opacity-50', 'cursor-not-allowed');
            }
            if (analysisResultsDiv) analysisResultsDiv.classList.add('hidden'); // Hide previous results

            const formData = new FormData();
            formData.append('audio', audioToAnalyze);

            try {
                const response = await fetch('/api/analysis', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    if (resultText) resultText.textContent = `Result: ${data.result.toUpperCase()}`;
                    if (confidenceScore) confidenceScore.textContent = `Confidence: ${data.confidence}%`;
                    if (analysisMessage) analysisMessage.textContent = data.message;

                    // Set text color based on result
                    if (resultText) {
                        if (data.result === 'spoofed') {
                            resultText.classList.remove('text-green-600');
                            resultText.classList.add('text-red-600');
                        } else {
                            resultText.classList.remove('text-red-600');
                            resultText.classList.add('text-green-600');
                        }
                    }

                    // Update Chart
                    updateSpoofingChart(data.confidence, data.result);

                    if (analysisResultsDiv) analysisResultsDiv.classList.remove('hidden');
                    showMessageBox('Analysis complete!', 'success');
                    console.log('Analysis successful:', data);
                    fetchAnalysisHistory(); // Refresh history after new analysis
                } else {
                    showMessageBox(data.error || 'Voice analysis failed.', 'error');
                    console.error('Analysis API error:', data.error);
                }
            } catch (error) {
                console.error('Fetch error during analysis:', error);
                showMessageBox('An error occurred during analysis. Please try again.', 'error');
            } finally {
                if (analysisLoadingSpinner) analysisLoadingSpinner.classList.add('hidden');
                if (analyzeVoiceBtn) {
                    analyzeVoiceBtn.disabled = false;
                    analyzeVoiceBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            }
        });
    } else {
        console.warn('Warning: Analyze voice button not found.');
    }

    // --- Chart.js Initialization and Update ---
    let spoofingChartInstance;

    function updateSpoofingChart(confidence, resultType) {
        const ctx = document.getElementById('spoofingChart');
        if (!ctx) {
            console.error('Error: Chart canvas element not found.');
            return;
        }
        const genuineValue = resultType === 'genuine' ? confidence : (100 - confidence);
        const spoofedValue = resultType === 'spoofed' ? confidence : (100 - confidence);

        const chartData = {
            labels: ['Genuine', 'Spoofed'],
            datasets: [{
                data: [genuineValue, spoofedValue],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.8)', // Green for Genuine
                    'rgba(255, 99, 132, 0.8)'  // Red for Spoofed
                ],
                borderColor: [
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 99, 132, 1)'
                ],
                borderWidth: 1
            }]
        };

        const chartOptions = {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    labels: {
                        color: document.body.classList.contains('dark-mode') ? '#e0e0e0' : '#333333'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed !== null) {
                                label += context.parsed + '%';
                            }
                            return label;
                        }
                    }
                }
            }
        };

        if (spoofingChartInstance) {
            spoofingChartInstance.data = chartData;
            spoofingChartInstance.options = chartOptions; // Update options too
            spoofingChartInstance.update();
            console.log('Chart updated.');
        } else {
            spoofingChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: chartData,
                options: chartOptions
            });
            console.log('Chart initialized.');
        }
    }

    // --- Analysis History Fetching ---
    async function fetchAnalysisHistory() {
        const analysisHistoryList = document.getElementById('analysis-history-list');
        if (!analysisHistoryList) {
            console.warn('Warning: Analysis history list element not found.');
            return;
        }
        console.log('Fetching analysis history...');

        try {
            const response = await fetch('/api/analyses');
            const data = await response.json();

            if (response.ok) {
                if (data.analyses && data.analyses.length > 0) {
                    analysisHistoryList.innerHTML = ''; // Clear existing list items
                    data.analyses.forEach(analysis => {
                        const listItem = document.createElement('li');
                        listItem.className = 'p-3 rounded-md flex justify-between items-center';
                        listItem.classList.add(analysis.isSpoofed ? 'bg-red-100 dark:bg-red-900' : 'bg-green-100 dark:bg-green-900');
                        listItem.innerHTML = `
                            <span class="font-medium text-gray-800 dark:text-gray-200">${analysis.fileName}</span>
                            <span class="text-sm ${analysis.isSpoofed ? 'text-red-700 dark:text-red-300' : 'text-green-700 dark:text-green-300'}">
                                ${analysis.isSpoofed ? 'Spoofed' : 'Genuine'} (${analysis.confidence}%)
                            </span>
                            <span class="text-xs text-gray-500 dark:text-gray-400">${new Date(analysis.timestamp).toLocaleString()}</span>
                        `;
                        analysisHistoryList.appendChild(listItem);
                    });
                    console.log(`Loaded ${data.analyses.length} analysis history items.`);
                } else {
                    analysisHistoryList.innerHTML = '<li class="text-center text-gray-500 dark:text-gray-400">No analysis history found.</li>';
                    console.log('No analysis history found.');
                }
            } else {
                analysisHistoryList.innerHTML = `<li class="text-center text-red-500 dark:text-red-400">${data.message || 'Failed to load history.'}</li>`;
                console.error('Failed to load analysis history:', data.message);
            }
        } catch (error) {
            console.error('Error fetching analysis history:', error);
            analysisHistoryList.innerHTML = '<li class="text-center text-red-500 dark:text-red-400">Error loading history.</li>';
            showMessageBox('Error loading analysis history.', 'error');
        }
    }

    // --- News Fetching Logic (Reverted from Twitter Embed) ---
    async function fetchNews() {
        const newsContainer = document.getElementById('news-articles-container');
        if (!newsContainer) {
            console.warn('Warning: News articles container not found.');
            return;
        }

        newsContainer.innerHTML = '<p class="text-center text-gray-500 dark:text-gray-400">Loading latest news...</p>';
        console.log('Fetching news articles...');

        try {
            const response = await fetch('/api/news');
            const data = await response.json();

            if (response.ok && data.articles && data.articles.length > 0) {
                newsContainer.innerHTML = ''; // Clear loading message
                data.articles.forEach(article => {
                    const articleElement = document.createElement('div');
                    articleElement.className = 'w-full max-w-2xl mx-auto p-4 transition-all duration-300 transform hover:scale-105';
                    articleElement.innerHTML = `
                        <h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">${article.title}</h3>
                        <p class="text-gray-700 dark:text-gray-300 text-sm mb-3">${article.description}</p>
                        <a href="${article.url}" target="_blank" rel="noopener noreferrer" class="text-blue-600 hover:underline text-sm font-medium">Read More &rarr;</a>
                        ${article.source ? `<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Source: ${article.source}</p>` : ''}
                        ${article.publishedAt ? `<p class="text-xs text-gray-500 dark:text-gray-400">Published: ${new Date(article.publishedAt).toLocaleDateString()}</p>` : ''}
                    `;
                    newsContainer.appendChild(articleElement);
                });
                console.log(`Loaded ${data.articles.length} news articles.`);
            } else {
                newsContainer.innerHTML = '<p class="text-center text-red-500 dark:text-red-400">Failed to load news. Please try again later.</p>';
                console.error('Error fetching news:', data.message || 'Unknown error');
                showMessageBox('Failed to load news.', 'error');
            }
        } catch (error) {
            console.error('Fetch error during news retrieval:', error);
            newsContainer.innerHTML = '<p class="text-center text-red-500 dark:text-red-400">An error occurred while fetching news.</p>';
            showMessageBox('An error occurred while fetching news.', 'error');
        }
    }

    // --- News Toggle Button Logic (Reverted to News Section) ---
    const newsToggleBtn = document.getElementById('news-toggle-btn');
    if (newsToggleBtn) {
        newsToggleBtn.addEventListener('click', () => {
            console.log('News Toggle Button Clicked (for Latest News).');
            // Smooth scroll to the news section
            const newsSection = document.getElementById('news');
            if (newsSection) {
                newsSection.scrollIntoView({
                    behavior: 'smooth'
                });
                console.log('Scrolled to news section.');
            } else {
                console.warn('Warning: News section element not found for scrolling.');
            }
        });
    } else {
        console.warn('Warning: News toggle button not found.');
    }

    // --- FAQ Accordion Logic ---
    function initFaqAccordion() {
        const faqItems = document.querySelectorAll('.faq-item');

        faqItems.forEach(item => {
            const question = item.querySelector('.faq-question');
            const answer = item.querySelector('.faq-answer');
            const icon = item.querySelector('.faq-question i');

            if (question && answer && icon) {
                question.addEventListener('click', () => {
                    // Toggle visibility of the answer
                    answer.classList.toggle('hidden');
                    // Toggle the icon
                    if (answer.classList.contains('hidden')) {
                        icon.classList.remove('fa-minus');
                        icon.classList.add('fa-plus');
                    } else {
                        icon.classList.remove('fa-plus');
                        icon.classList.add('fa-minus');
                    }
                });
            } else {
                console.warn('Warning: Missing elements in FAQ item (question, answer, or icon).');
            }
        });
        console.log('FAQ accordion initialized.');
    }


    // --- Initializations on DOMContentLoaded ---
    updateAnalyzeButtonState(); // Set initial state of analyze button
    fetchNews(); // Fetch news when the page loads
    initFaqAccordion(); // Initialize FAQ accordion
});