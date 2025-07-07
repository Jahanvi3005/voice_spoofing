document.addEventListener('DOMContentLoaded', () => {
    // --- Common Elements (present on multiple pages via base.html) ---
    const htmlElement = document.documentElement; 
    const themeToggle = document.getElementById('themeToggle'); 
    const languageSelect = document.getElementById('languageSelect'); 

    // --- Elements specific to home.html (check for existence before adding listeners) ---
    const audioFile = document.getElementById('audioFile');
    const recordButton = document.getElementById('recordButton');
    const stopButton = document.getElementById('stopButton');
    const recordingStatus = document.getElementById('recordingStatus');
    const analyzeButton = document.getElementById('analyzeButton');
    const audioPlayback = document.getElementById('audioPlayback');
    const verdictOutput = document.getElementById('verdictOutput'); 
    const confGenuine = document.getElementById('confGenuine');     
    const confSpoofed = document.getElementById('confSpoofed');     
    const loadingIndicator = document.getElementById('loadingIndicator'); 
    const clearButton = document.getElementById('clearButton');     
    const dropZone = document.getElementById('dropZone'); 
    const downloadAudioButton = document.getElementById('downloadAudioButton');
    const playbackSpeedSelect = document.getElementById('playbackSpeedSelect');


    let mediaRecorder; 
    let audioChunks = []; 
    let recordedAudioBlob = null; 

    // --- Elements specific to account.html (check for existence) ---
    const savePreferencesButton = document.getElementById('savePreferencesButton');
    const themeDropdown = document.getElementById('preferredModeSelect');
    const languageDropdown = document.getElementById('preferredLanguageSelect');
    const currentThemeDisplay = document.getElementById('currentThemeDisplay');
    const currentLanguageDisplay = document.getElementById('currentLanguageDisplay');

    // --- Sidebar Toggle Logic (from base.html's original script part) ---
    const hamburgerButton = document.getElementById('hamburgerButton');
    const sidebarOverlay = document.getElementById('sidebarOverlay');

    if (hamburgerButton) {
        hamburgerButton.addEventListener('click', () => {
            htmlElement.classList.toggle('sidebar-open');
        });
    }

    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', () => {
            htmlElement.classList.remove('sidebar-open');
        });
    }


    // --- Language Translation Logic (Client-side) ---
    // This object contains only translations for text that is dynamically
    // generated or updated by JavaScript. All other static text in HTML
    // is translated by the Flask backend using Jinja2.
    const CLIENT_TRANSLATIONS = {
        'file_selected': {'en': 'File selected:', 'hi': 'फ़ाइल चुनी गई:'},
        'not_audio_file': {'en': 'Please drop an audio file.', 'hi': 'कृपया एक ऑडियो फ़ाइल गिराएँ।'},
        'not_audio_file_uploaded': {'en': 'Please upload an audio file.', 'hi': 'कृपया एक ऑडियो फ़ाइल अपलोड करें।'},
        'no_audio_provided': {'en': 'Please provide audio first (upload or record).', 'hi': 'पहले ऑडियो प्रदान करें (अपलोड करें या रिकॉर्ड करें)।'},
        'network_error': {'en': 'Network Error', 'hi': 'नेटवर्क त्रुटि'},
        'genuine': {'en': 'Genuine', 'hi': 'वास्तविक'},
        'spoofed': {'en': 'Spoofed', 'hi': 'स्पूफ़ेड'},
        'no_analysis_yet': {'en': 'No analysis yet.', 'hi': 'अभी तक कोई विश्लेषण नहीं हुआ है।'},
        'analyzing_audio': {'en': 'Analyzing audio...', 'hi': 'ऑडियो का विश्लेषण हो रहा है...'},
        'recording_status_recording': {'en': 'Recording...', 'hi': 'रिकॉर्डिंग हो रही है...'},
        'recording_status_stop_prompt': {'en': 'Recording (Click to stop)', 'hi': 'रिकॉर्डिंग (रोकने के लिए क्लिक करें)'},
        'recording_status_finished': {'en': 'Recording finished. Ready for analysis.', 'hi': 'रिकॉर्डिंग समाप्त। विश्लेषण के लिए तैयार।'},
        'mic_error': {'en': 'Error accessing microphone. Please ensure permissions are granted.', 'hi': 'माइक्रोफ़ोन तक पहुंचने में त्रुटि। कृपया सुनिश्चित करें कि अनुमतियाँ दी गई हैं।'},
        'no_audio_to_download': {'en': 'No audio to download.', 'hi': 'डाउनलोड करने के लिए कोई ऑडियो नहीं है।'},
    };
    
    window.getClientText = (key) => { 
        const currentLang = htmlElement.lang || 'en';
        return CLIENT_TRANSLATIONS[key]?.[currentLang] || CLIENT_TRANSLATIONS[key]?.['en'] || key;
    };


    // --- Theme Toggle Logic (for header toggle) ---
    if (themeToggle) { 
        themeToggle.addEventListener('click', async () => {
            htmlElement.classList.add('transition'); // Add transition to html element
            let newMode;
            if (htmlElement.classList.contains('dark')) {
                htmlElement.classList.remove('dark');
                newMode = 'light';
            } else {
                htmlElement.classList.add('dark');
                newMode = 'dark';
            }

            try {
                const response = await fetch('/update_preferences', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ preferred_mode: newMode })
                });
                const data = await response.json();
                if (!data.success) {
                    console.error('Failed to save theme preference to DB:', data.message);
                }
            } catch (error) {
                console.error('Network error saving theme preference:', error);
            } finally {
                setTimeout(() => {
                    htmlElement.classList.remove('transition');
                }, 750);
            }
        });
    }

    // --- Language Selector Logic (for header dropdown) ---
    if (languageSelect) {
        languageSelect.addEventListener('change', async () => {
            const newLanguage = languageSelect.value;
            try {
                const response = await fetch('/update_preferences', { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ preferred_language: newLanguage })
                });
                const data = await response.json();
                if (data.success) {
                    console.log('Language preference saved to DB successfully!');
                    window.location.reload(); 
                } else {
                    alert('Failed to update language preference: ' + data.message);
                }
            } catch (error) {
                console.error('Network error updating language preference:', error);
                alert('An error occurred while updating language preference.');
            }
        });
    }

    // --- Logic for Account Page (Save Preferences Button) ---
    if (savePreferencesButton && themeDropdown && languageDropdown) {
        savePreferencesButton.addEventListener('click', async () => {
            console.log('Save Preferences button clicked.');
            const preferredMode = themeDropdown.value;
            const preferredLanguage = languageDropdown.value;
            
            console.log('Attempting to save preferences:', { preferredMode, preferredLanguage });

            try {
                const response = await fetch('/update_preferences', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        preferred_mode: preferredMode,
                        preferred_language: preferredLanguage
                    })
                });
                const data = await response.json();
                console.log('Server response for save preferences:', data);
                console.log('Response status:', response.status);

                if (response.ok && data.success) {
                    alert('Preferences saved successfully!');
                    if (currentThemeDisplay) {
                        currentThemeDisplay.textContent = preferredMode.charAt(0).toUpperCase() + preferredMode.slice(1);
                    }
                    if (currentLanguageDisplay) {
                        currentLanguageDisplay.textContent = preferredLanguage.charAt(0).toUpperCase() + preferredLanguage.slice(1);
                    }
                    
                    if (preferredMode === 'dark') {
                        htmlElement.classList.add('dark');
                    } else {
                        htmlElement.classList.remove('dark');
                    }

                    if (htmlElement.lang !== preferredLanguage) {
                        setTimeout(() => window.location.reload(), 100); 
                    }
                } else {
                    alert('Failed to save preferences: ' + (data.message || `Server responded with status ${response.status}.`));
                }
            } catch (error) {
                console.error('Error saving preferences:', error);
                alert('An error occurred while saving preferences. Check console for details.');
            }
        });
    }

    // --- Home page specific logic (Audio recording/upload/analysis) ---
    if (analyzeButton && recordButton && stopButton && audioFile && clearButton && verdictOutput && confGenuine && confSpoofed && loadingIndicator && dropZone) {
        
        function enableAnalyzeButton() {
            analyzeButton.disabled = false;
            analyzeButton.classList.remove('bg-gray-400', 'cursor-not-allowed');
            analyzeButton.classList.add('bg-emerald-600', 'hover:bg-emerald-700', 'cursor-pointer');
        }

        function disableAnalyzeButton() {
            analyzeButton.disabled = true;
            analyzeButton.classList.remove('bg-emerald-600', 'hover:bg-emerald-700', 'cursor-pointer');
            analyzeButton.classList.add('bg-gray-400', 'cursor-not-allowed');
        }

        function clearResults() {
            verdictOutput.textContent = window.getClientText('no_analysis_yet');
            verdictOutput.className = 'text-center text-2xl font-extrabold p-4 rounded-lg bg-gray-100 dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-600 mb-4 min-h-[70px] flex items-center justify-center shadow-md';
            confGenuine.textContent = 'N/A';
            confSpoofed.textContent = 'N/A';
            audioPlayback.src = '';
            audioFile.value = ''; 
            recordedAudioBlob = null; 
            recordingStatus.textContent = ''; 
            loadingIndicator.classList.add('hidden');
            disableAnalyzeButton(); 
            stopRecording(); 
            if (document.getElementById('fileSelectedDisplay')) {
                document.getElementById('fileSelectedDisplay').textContent = ''; 
            }
            if (downloadAudioButton) downloadAudioButton.disabled = true;
            if (playbackSpeedSelect) playbackSpeedSelect.disabled = true;
            if (audioPlayback) audioPlayback.playbackRate = 1.0;
        }

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault(); 
            dropZone.classList.add('border-indigo-500', 'bg-gray-50', 'dark:bg-gray-700');
            dropZone.classList.remove('border-dashed');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-indigo-500', 'bg-gray-50', 'dark:bg-gray-700');
            dropZone.classList.add('border-dashed');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('border-indigo-500', 'bg-gray-50', 'dark:bg-gray-700');
            dropZone.classList.add('border-dashed');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const firstFile = files[0];
                if (!firstFile.type.startsWith('audio/')) {
                    alert(window.getClientText('not_audio_file'));
                    return;
                }
                audioFile.files = files;
                audioFile.dispatchEvent(new Event('change', { bubbles: true })); 
            }
        });

        audioFile.addEventListener('change', (event) => {
            const file = event.target.files[0]; 
            if (file) {
                if (!file.type.startsWith('audio/')) {
                    alert(window.getClientText('not_audio_file_uploaded'));
                    event.target.value = ''; 
                    recordedAudioBlob = null;
                    audioPlayback.src = '';
                    disableAnalyzeButton();
                    if (downloadAudioButton) downloadAudioButton.disabled = true;
                    if (playbackSpeedSelect) playbackSpeedSelect.disabled = true;
                    return;
                }

                clearResults(); 

                recordedAudioBlob = file; 
                audioPlayback.src = URL.createObjectURL(file);
                audioPlayback.load();
                enableAnalyzeButton();
                if (document.getElementById('fileSelectedDisplay')) {
                    document.getElementById('fileSelectedDisplay').textContent = `${window.getClientText('file_selected')} ${file.name}`;
                }
                recordingStatus.textContent = ''; 
                if (downloadAudioButton) downloadAudioButton.disabled = false;
                if (playbackSpeedSelect) playbackSpeedSelect.disabled = false;

            } else {
                recordedAudioBlob = null;
                audioPlayback.src = '';
                if (document.getElementById('fileSelectedDisplay')) {
                    document.getElementById('fileSelectedDisplay').textContent = '';
                }
                disableAnalyzeButton();
                if (downloadAudioButton) downloadAudioButton.disabled = true;
                if (playbackSpeedSelect) playbackSpeedSelect.disabled = true;
            }
        });

        recordButton.addEventListener('click', async () => {
            clearResults(); 

            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                
                let options = {};
                if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
                    options = { mimeType: 'audio/webm;codecs=opus' };
                } else if (MediaRecorder.isTypeSupported('audio/webm')) {
                    options = { mimeType: 'audio/webm' };
                } else if (MediaRecorder.isTypeSupported('audio/wav')) {
                    options = { mimeType: 'audio/wav' };
                } else {
                    console.warn('No preferred MIME type for MediaRecorder found. Falling back to browser default.');
                }

                mediaRecorder = new MediaRecorder(stream, options); 
                audioChunks = []; 

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data); 
                };

                mediaRecorder.onstop = () => {
                    const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
                    
                    recordedAudioBlob = blob; 
                    audioPlayback.src = URL.createObjectURL(blob);
                    audioPlayback.load();
                    
                    enableAnalyzeButton(); 
                    recordingStatus.textContent = window.getClientText('recording_status_finished');
                    recordButton.innerHTML = `<i class="fas fa-microphone mr-2"></i> ${window.getClientText('start_recording_btn')}`;
                    recordButton.disabled = false; 
                    stopButton.disabled = true;
                    recordButton.classList.remove('active'); 
                    if (downloadAudioButton) downloadAudioButton.disabled = false;
                    if (playbackSpeedSelect) playbackSpeedSelect.disabled = false;
                };

                mediaRecorder.start(); 
                recordingStatus.textContent = window.getClientText('recording_status_recording');
                recordButton.innerHTML = `<i class="fas fa-microphone mr-2"></i> ${window.getClientText('recording_status_stop_prompt')}`;
                recordButton.disabled = true; 
                stopButton.disabled = false;
                recordButton.classList.add('active'); 
                disableAnalyzeButton(); 
                
                if (document.getElementById('fileSelectedDisplay')) {
                    document.getElementById('fileSelectedDisplay').textContent = ''; 
                }
                if (downloadAudioButton) downloadAudioButton.disabled = true;
                if (playbackSpeedSelect) playbackSpeedSelect.disabled = true;

            } catch (err) {
                console.error('Error accessing microphone:', err);
                recordingStatus.textContent = window.getClientText('mic_error');
                recordButton.disabled = false;
                stopButton.disabled = true;
                recordButton.classList.remove('active');
                disableAnalyzeButton();
                if (downloadAudioButton) downloadAudioButton.disabled = true;
                if (playbackSpeedSelect) playbackSpeedSelect.disabled = true;
            }
        });

        stopButton.addEventListener('click', () => {
            stopRecording();
        });

        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop(); 
                mediaRecorder.stream.getTracks().forEach(track => track.stop()); 
                recordButton.disabled = false; 
                stopButton.disabled = true; 
            }
        }

        analyzeButton.addEventListener('click', async () => {
            if (!recordedAudioBlob) {
                verdictOutput.textContent = window.getClientText('no_audio_provided');
                verdictOutput.className = 'text-center text-2xl font-extrabold p-4 rounded-lg bg-rose-100 border-2 border-rose-400 text-rose-700 mb-4 min-h-[70px] flex items-center justify-center shadow-md';
                return;
            }

            loadingIndicator.classList.remove('hidden');
            disableAnalyzeButton();
            verdictOutput.textContent = window.getClientText('analyzing_audio');
            verdictOutput.className = 'text-center text-2xl font-extrabold p-4 rounded-lg bg-gray-100 dark:bg-gray-700 border-2 border-gray-300 dark:border-gray-600 text-indigo-600 mb-4 min-h-[70px] flex items-center justify-center shadow-md';
            confGenuine.textContent = 'Analyzing...';
            confSpoofed.textContent = 'Analyzing...';

            const formData = new FormData();
            const fileName = audioFile.files && audioFile.files[0] ? audioFile.files[0].name : `recorded_audio.${recordedAudioBlob.type.split('/')[1] || 'webm'}`;
            formData.append('audio', recordedAudioBlob, fileName); 

            try {
                const response = await fetch('/predict', {
                    method: 'POST',
                    body: formData,
                });

                const data = await response.json();

                loadingIndicator.classList.add('hidden');
                enableAnalyzeButton(); 

                if (response.ok) { 
                    if (data.redirect_to) {
                        window.location.href = data.redirect_to; 
                    } else {
                        verdictOutput.textContent = data.verdict;
                        // Use original verdict text (English) to check for 'Spoofed' for styling consistency
                        if (data.verdict_en && data.verdict_en.includes('Spoofed')) { 
                            verdictOutput.className = 'text-center text-2xl font-extrabold p-4 rounded-lg bg-rose-100 border-2 border-rose-400 text-rose-700 mb-4 min-h-[70px] flex items-center justify-center shadow-md'; 
                        } else {
                            verdictOutput.className = 'text-center text-2xl font-extrabold p-4 rounded-lg bg-emerald-100 border-2 border-emerald-400 text-emerald-700 mb-4 min-h-[70px] flex items-center justify-center shadow-md'; 
                        }
                        confGenuine.textContent = (data.confidence.Genuine * 100).toFixed(2) + '%';
                        confSpoofed.textContent = (data.confidence.Spoofed * 100).toFixed(2) + '%';
                    }

                } else { 
                    verdictOutput.textContent = `${window.getClientText('network_error')}: ${data.error || 'Unknown error'}`;
                    verdictOutput.className = 'text-center text-2xl font-extrabold p-4 rounded-lg bg-rose-100 border-2 border-rose-400 text-rose-700 mb-4 min-h-[70px] flex items-center justify-center shadow-md'; 
                    confGenuine.textContent = 'N/A';
                    confSpoofed.textContent = 'N/A';
                }

            } catch (error) { 
                console.error('Network or fetch error:', error);
                loadingIndicator.classList.add('hidden');
                enableAnalyzeButton();
                verdictOutput.textContent = `${window.getClientText('network_error')}: ${error.message}.`;
                verdictOutput.className = 'text-center text-2xl font-extrabold p-4 rounded-lg bg-rose-100 border-2 border-rose-400 text-rose-700 mb-4 min-h-[70px] flex items-center justify-center shadow-md'; 
                confGenuine.textContent = 'N/A';
                confSpoofed.textContent = 'N/A';
            }
        });

        clearButton.addEventListener('click', clearResults);

        // --- New: Download Audio Button Logic ---
        if (downloadAudioButton) {
            downloadAudioButton.addEventListener('click', () => {
                if (recordedAudioBlob) {
                    const url = URL.createObjectURL(recordedAudioBlob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    const originalFileName = audioFile.files && audioFile.files[0] ? audioFile.files[0].name.split('.').slice(0, -1).join('.') : 'recorded_audio';
                    const fileExtension = recordedAudioBlob.type.split('/')[1] || 'webm';
                    a.download = `${originalFileName}.${fileExtension}`;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    document.body.removeChild(a);
                } else {
                    alert(window.getClientText('no_audio_to_download'));
                }
            });
            downloadAudioButton.disabled = true;
        }

        // --- New: Playback Speed Select Logic ---
        if (playbackSpeedSelect && audioPlayback) {
            playbackSpeedSelect.addEventListener('change', () => {
                audioPlayback.playbackRate = parseFloat(playbackSpeedSelect.value);
            });
            playbackSpeedSelect.disabled = true;
        }

        disableAnalyzeButton();
    }
});

