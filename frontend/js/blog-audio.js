/**
 * Academic Comeback Blog — Smart Audio Player (Client-Side Speech Engine)
 * Instant, zero-bandwidth audio reader using browser Web Speech API.
 * Features:
 * - Intelligent formula & symbol cleaning (LaTeX, arrows, currency, abbreviations)
 * - Phrase-level rhythmic chunking ensuring crystal-clear enunciation at all speeds
 * - Calibrated speed rate curve (1.0x, 1.25x, 1.5x, 2.0x) preventing phonetic degradation
 * - Modern neural voice prioritization (eliminating mechanical desktop distortion)
 * - Cancellation queue hygiene preventing overlapping audio and runaway skip loops
 */
(function() {
  'use strict';

  // Calibrated speed levels for Web Speech API:
  // In Web Speech API, a raw rate of 2.0 pushes desktop synthesizers past 400 WPM, causing
  // severe consonant clipping and unintelligible distortion ("gibberish").
  // Mapping 2.0x to 1.48 produces a genuine ~270 WPM (matching YouTube/Audible 2x),
  // keeping every word articulate and clear while slightly lowering pitch to eliminate chipmunk screech.
  var SPEED_LEVELS = [
    { label: '1.0x', rate: 1.00, pitch: 1.00 },
    { label: '1.25x', rate: 1.15, pitch: 1.00 },
    { label: '1.5x', rate: 1.30, pitch: 0.98 },
    { label: '2.0x', rate: 1.48, pitch: 0.95 }
  ];

  function cleanTextForSpeech(text) {
    if (!text) return '';
    var cleaned = text;

    // 1. Decode HTML entities
    cleaned = cleaned
      .replace(/&nbsp;/g, ' ')
      .replace(/&amp;/g, ' and ')
      .replace(/&rarr;/g, ' leads to ')
      .replace(/&larr;/g, ' comes from ')
      .replace(/&quot;/g, ' ')
      .replace(/&#39;/g, ' ')
      .replace(/&lt;/g, ' less than ')
      .replace(/&gt;/g, ' greater than ');

    // 2. LaTeX & Mathematical formulas
    // Convert fractions: \frac{numerator}{denominator} -> numerator divided by denominator
    cleaned = cleaned.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '$1 divided by $2');
    cleaned = cleaned.replace(/\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g, function(_, num, den) {
      var n = num.replace(/\\text\{([^{}]+)\}/g, '$1');
      var d = den.replace(/\\text\{([^{}]+)\}/g, '$1');
      return n.trim() + ' divided by ' + d.trim();
    });

    // Math symbols, relational operators & arrows
    cleaned = cleaned
      .replace(/\\longrightarrow|\\rightarrow|➔|—>|->|=>|⇒/g, ' leads to ')
      .replace(/\\longleftarrow|\\leftarrow|<-|<=|⇐/g, ' comes from ')
      .replace(/\\ll/g, ' is much less than ')
      .replace(/\\gg/g, ' is much greater than ')
      .replace(/\\approx/g, ' is approximately ')
      .replace(/\\times|\\cdot/g, ' times ')
      .replace(/\\pm/g, ' plus or minus ')
      .replace(/\\neq/g, ' does not equal ')
      .replace(/\\leq/g, ' is less than or equal to ')
      .replace(/\\geq/g, ' is greater than or equal to ')
      .replace(/\\quad/g, ' ');

    // Clean remaining LaTeX commands: \text{...}, \mathbf{...}, \mathrm{...}
    cleaned = cleaned.replace(/\\(?:text|mathbf|mathrm|mathit)\{([^{}]+)\}/g, '$1');
    // Strip $$ and $ math delimiters
    cleaned = cleaned.replace(/\$\$|\$/g, ' ');
    // Strip any remaining backslash TeX commands
    cleaned = cleaned.replace(/\\[a-zA-Z]+/g, ' ');

    // 3. Nigerian Currency & Percentages
    cleaned = cleaned.replace(/₦\s*([0-9,]+(?:\.[0-9]+)?)/g, '$1 Naira');
    cleaned = cleaned.replace(/₦/g, ' Naira ');
    cleaned = cleaned.replace(/%/g, ' percent ');

    // 4. Academic Classifications & Ratios
    cleaned = cleaned.replace(/\b2:1\b/g, 'Two-One');
    cleaned = cleaned.replace(/\b2:2\b/g, 'Two-Two');
    cleaned = cleaned.replace(/\b1st\b/gi, 'First');
    cleaned = cleaned.replace(/\b2nd\b/gi, 'Second');
    cleaned = cleaned.replace(/\b3rd\b/gi, 'Third');

    // 5. Nigerian University Nomenclature & Acronyms (spelled out for crisp phonetic delivery)
    cleaned = cleaned
      .replace(/\bCGPA\b/g, 'C G P A')
      .replace(/\bSGPA\b/g, 'S G P A')
      .replace(/\bGPA\b/g, 'G P A')
      .replace(/\bTDB\b/g, 'Till Daybreak')
      .replace(/\bGST\b/g, 'G S T')
      .replace(/\bCA\b/g, 'C A')
      .replace(/\bNUC\b/g, 'N U C')
      .replace(/\bUNN\b/g, 'U N N')
      .replace(/\bOAU\b/g, 'O A U')
      .replace(/\bUNILAG\b/g, 'UNILAG')
      .replace(/\bFUTA\b/g, 'FUTA')
      .replace(/\bJAMB\b/g, 'JAMB')
      .replace(/\bWAEC\b/g, 'WAEC')
      .replace(/\bASUU\b/g, 'ASUU');

    // 6. Strip emojis and visual icons
    cleaned = cleaned.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '');

    // 7. Markdown & Links
    cleaned = cleaned.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    cleaned = cleaned.replace(/https?:\/\/\S+/g, '');
    cleaned = cleaned.replace(/\/blog\/[a-zA-Z0-9_\-\./]+/g, '');
    cleaned = cleaned.replace(/[#*_~`]/g, '');

    // 8. Clean dashes, brackets, quotes
    cleaned = cleaned
      .replace(/["'“”‘’]/g, '')
      .replace(/—/g, ', ')
      .replace(/–/g, ', ')
      .replace(/[{}\[\]\\]/g, ' ')
      .replace(/\.{2,}/g, '.')
      .replace(/\s+/g, ' ')
      .trim();

    return cleaned;
  }

  // Breaks sentences into digestible phrases (<= 110 characters).
  // This gives the TTS synthesizer micro-breaths, preventing words from blurring
  // into an unintelligible runaway stream at high speeds.
  function splitIntoPhrases(text) {
    if (!text) return [];
    var clean = text.trim();
    // Protect numbers like 4.70 or 2,000 from premature splitting
    var safeText = clean.replace(/(\d+)\.(\d+)/g, '$1___DEC___$2');
    safeText = safeText.replace(/(\d+),(\d+)/g, '$1___COMMA___$2');

    // Split on sentence boundaries (. ? !)
    var sentences = safeText.split(/(?<=[.!?])\s+(?=[A-Z0-9])/);
    var phrases = [];

    for (var i = 0; i < sentences.length; i++) {
      var sent = sentences[i].trim();
      if (!sent) continue;

      if (sent.length <= 110) {
        phrases.push(sent.replace(/___DEC___/g, '.').replace(/___COMMA___/g, ','));
      } else {
        // Break long sentences at natural punctuation pauses (commas, semicolons, dashes)
        var subParts = sent.split(/(?<=[,;:—–])\s+/);
        var acc = '';
        for (var j = 0; j < subParts.length; j++) {
          var part = subParts[j].trim();
          if (!part) continue;

          if (acc && (acc.length + part.length) > 100) {
            phrases.push(acc.replace(/___DEC___/g, '.').replace(/___COMMA___/g, ',').trim());
            acc = part;
          } else {
            acc = acc ? acc + ' ' + part : part;
          }
        }
        if (acc) {
          phrases.push(acc.replace(/___DEC___/g, '.').replace(/___COMMA___/g, ',').trim());
        }
      }
    }

    return phrases.length > 0 ? phrases : [clean];
  }

  function initBlogAudio() {
    var player = document.getElementById('article-audio-player');
    if (!player) return;

    // Idempotent initialization guard (prevents duplicate event listeners)
    if (player.getAttribute('data-audio-ready') === 'true') return;
    player.setAttribute('data-audio-ready', 'true');

    if (!('speechSynthesis' in window)) {
      player.style.display = 'none';
      return;
    }

    var playBtn = document.getElementById('audio-play-btn');
    var playIcon = document.getElementById('audio-play-icon');
    var playText = document.getElementById('audio-play-text');
    var statusText = document.getElementById('audio-status-text');
    var controls = document.getElementById('audio-controls');
    var progressBar = document.getElementById('audio-progress-bar');
    var speedBtn = document.getElementById('audio-speed-btn');
    var prevBtn = document.getElementById('audio-prev-btn');
    var nextBtn = document.getElementById('audio-next-btn');
    var stopBtn = document.getElementById('audio-stop-btn');

    var articleBody = document.querySelector('.article-body');
    if (!articleBody) return;

    // Collect readable leaf blocks: p, li, blockquote, h2, h3
    var rawBlocks = articleBody.querySelectorAll('p, li, blockquote, h2, h3');
    var tempBlocks = [];
    for (var i = 0; i < rawBlocks.length; i++) {
      var el = rawBlocks[i];
      if (el.closest('pre') || el.closest('table') || el.closest('.blog-cta-box') || el.closest('code')) {
        continue;
      }
      // Avoid parent-child duplication (skip container blockquotes or lis containing child blocks)
      if (el.querySelector('p, li, blockquote, h2, h3')) {
        continue;
      }

      var txt = (el.innerText || el.textContent || '').trim();
      if (txt.length >= 4) {
        tempBlocks.push(el);
      }
    }

    // Deduplicate consecutive blocks with identical text
    var blocks = [];
    var lastNormalizedText = '';
    for (var j = 0; j < tempBlocks.length; j++) {
      var normText = (tempBlocks[j].innerText || tempBlocks[j].textContent || '').trim().replace(/\s+/g, ' ');
      if (normText && normText !== lastNormalizedText) {
        blocks.push(tempBlocks[j]);
        lastNormalizedText = normText;
      }
    }

    if (blocks.length === 0) {
      player.style.display = 'none';
      return;
    }

    var currentIndex = 0;
    var currentPhraseIdx = 0;
    var currentBlockPhrases = null;
    var isPlaying = false;
    var isPaused = false;
    var speedIdx = 0;
    var sessionToken = 0;
    var consecutiveErrors = 0;
    var preferredVoice = null;
    var speedChangeTimer = null;
    var speakTimer = null;

    function selectBestVoice() {
      try {
        var voices = window.speechSynthesis.getVoices() || [];
        if (!voices.length) return null;

        var enVoices = [];
        for (var i = 0; i < voices.length; i++) {
          if (voices[i].lang && voices[i].lang.toLowerCase().indexOf('en') === 0) {
            enVoices.push(voices[i]);
          }
        }
        var candidateList = enVoices.length > 0 ? enVoices : voices;

        // 1. Try Nigerian English
        for (var n = 0; n < candidateList.length; n++) {
          if (candidateList[n].lang === 'en-NG') return candidateList[n];
        }

        // 2. High-Fidelity Neural / Natural / Online voices (Edge & Chrome)
        // These neural voices preserve clear formants at accelerated speeds without distortion
        var neuralKeywords = ['natural', 'online', 'neural', 'google', 'jenny', 'guy', 'aria', 'sonia', 'ryan', 'daniel'];
        for (var k = 0; k < neuralKeywords.length; k++) {
          for (var j = 0; j < candidateList.length; j++) {
            var name = (candidateList[j].name || '').toLowerCase();
            if (name.indexOf(neuralKeywords[k]) !== -1) {
              return candidateList[j];
            }
          }
        }

        // 3. Prefer non-desktop voices over legacy Windows SAPI concatenative voices
        var nonDesktop = candidateList.filter(function(v) {
          return (v.name || '').toLowerCase().indexOf('desktop') === -1;
        });
        if (nonDesktop.length > 0) return nonDesktop[0];

        // 4. Any English voice
        if (enVoices.length > 0) {
          return enVoices[0];
        }

        // Never fallback to a non-English voice for English text!
        return null;
      } catch (err) {
        return null;
      }
    }

    preferredVoice = selectBestVoice();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = function() {
        preferredVoice = selectBestVoice();
      };
    }

    function clearHighlight() {
      var highlighted = articleBody.querySelectorAll('.audio-active-reading');
      for (var m = 0; m < highlighted.length; m++) {
        highlighted[m].classList.remove('audio-active-reading');
      }
    }

    function highlightCurrent(idx) {
      clearHighlight();
      if (blocks[idx]) {
        var targetEl = blocks[idx].closest('blockquote') || blocks[idx];
        targetEl.classList.add('audio-active-reading');
        var rect = targetEl.getBoundingClientRect();
        var inView = (rect.top >= 70 && rect.bottom <= (window.innerHeight - 70));
        if (!inView) {
          targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }

    function updateProgressUI() {
      var pct = Math.round(((currentIndex) / blocks.length) * 100);
      if (progressBar) progressBar.style.width = pct + '%';
      if (statusText) statusText.textContent = 'Section ' + (currentIndex + 1) + ' of ' + blocks.length;
    }

    function speakCurrentPhrase() {
      if (!isPlaying || isPaused) return;

      if (currentIndex >= blocks.length) {
        stopAudio();
        if (statusText) statusText.textContent = 'Completed';
        return;
      }

      // Initialize phrases for the current block if needed
      if (!currentBlockPhrases || currentBlockPhrases.length === 0) {
        var rawText = (blocks[currentIndex].innerText || blocks[currentIndex].textContent || '').trim();
        var cleanedText = cleanTextForSpeech(rawText);
        currentBlockPhrases = splitIntoPhrases(cleanedText);
        currentPhraseIdx = 0;

        if (currentBlockPhrases.length === 0) {
          currentIndex++;
          speakCurrentPhrase();
          return;
        }

        updateProgressUI();
        highlightCurrent(currentIndex);
      }

      // Check if we finished all phrases in the current block
      if (currentPhraseIdx >= currentBlockPhrases.length) {
        currentIndex++;
        currentBlockPhrases = null;
        currentPhraseIdx = 0;
        setTimeout(function() {
          if (isPlaying && !isPaused) {
            speakCurrentPhrase();
          }
        }, 50);
        return;
      }

      var textToSpeak = currentBlockPhrases[currentPhraseIdx];
      var thisToken = ++sessionToken;
      var curSpeed = SPEED_LEVELS[speedIdx];

      // Refresh voice dynamically if it became available
      if (!preferredVoice) {
        preferredVoice = selectBestVoice();
      }

      try {
        window.speechSynthesis.cancel();
      } catch(e) {}

      var utter = new SpeechSynthesisUtterance(textToSpeak);
      if (preferredVoice) {
        utter.voice = preferredVoice;
        utter.lang = preferredVoice.lang;
      } else {
        utter.lang = 'en-US';
      }

      // Apply calibrated rate and formant-preserving pitch
      utter.rate = curSpeed.rate;
      utter.pitch = curSpeed.pitch;

      utter.onend = function() {
        if (thisToken !== sessionToken || !isPlaying || isPaused) return;
        consecutiveErrors = 0;
        currentPhraseIdx++;
        // 40ms inter-phrase micro-pause allows hardware buffer to settle and phonemes to breathe
        setTimeout(function() {
          if (thisToken === sessionToken && isPlaying && !isPaused) {
            speakCurrentPhrase();
          }
        }, 40);
      };

      utter.onerror = function(evt) {
        if (thisToken !== sessionToken || !isPlaying || isPaused) return;
        if (evt.error === 'interrupted' || evt.error === 'canceled') return;

        console.warn('Speech synthesis note on block ' + currentIndex + ':', evt.error);
        consecutiveErrors++;
        if (consecutiveErrors >= 5) {
          stopAudio();
          if (statusText) statusText.textContent = 'Audio reader paused';
          return;
        }

        currentPhraseIdx++;
        setTimeout(function() {
          if (thisToken === sessionToken && isPlaying && !isPaused) {
            speakCurrentPhrase();
          }
        }, 150);
      };

      // 80ms delay gives browser audio hardware adequate time to clear before dispatching next utterance
      clearTimeout(speakTimer);
      speakTimer = setTimeout(function() {
        if (thisToken === sessionToken && isPlaying && !isPaused) {
          try {
            window.speechSynthesis.speak(utter);
          } catch(err) {
            console.warn('Speech synthesis speak failed:', err);
          }
        }
      }, 70);
    }

    function startAudio() {
      isPlaying = true;
      isPaused = false;
      consecutiveErrors = 0;
      preferredVoice = selectBestVoice();

      if (controls) controls.style.display = 'flex';
      if (playIcon) playIcon.className = 'bi bi-pause-fill';
      if (playText) playText.textContent = 'Pause';
      if (playBtn) playBtn.classList.add('playing');

      speakCurrentPhrase();
    }

    function pauseAudio() {
      isPaused = true;
      sessionToken++;
      clearTimeout(speakTimer);
      clearTimeout(speedChangeTimer);

      try {
        window.speechSynthesis.pause();
      } catch(e) {}

      setTimeout(function() {
        if (isPaused) {
          try {
            window.speechSynthesis.cancel();
          } catch(e) {}
        }
      }, 200);

      if (playIcon) playIcon.className = 'bi bi-play-fill';
      if (playText) playText.textContent = 'Resume';
      if (statusText) statusText.textContent = 'Paused';
    }

    function resumeAudio() {
      isPaused = false;
      isPlaying = true;

      if (playIcon) playIcon.className = 'bi bi-pause-fill';
      if (playText) playText.textContent = 'Pause';
      if (statusText) statusText.textContent = 'Section ' + (currentIndex + 1) + ' of ' + blocks.length;

      try {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
          setTimeout(function() {
            if (!window.speechSynthesis.speaking && isPlaying && !isPaused) {
              speakCurrentPhrase();
            }
          }, 150);
        } else {
          speakCurrentPhrase();
        }
      } catch(e) {
        speakCurrentPhrase();
      }
    }

    function stopAudio() {
      isPlaying = false;
      isPaused = false;
      sessionToken++;
      clearTimeout(speakTimer);
      clearTimeout(speedChangeTimer);

      try {
        window.speechSynthesis.cancel();
      } catch(e) {}

      clearHighlight();
      currentIndex = 0;
      currentPhraseIdx = 0;
      currentBlockPhrases = null;

      if (progressBar) progressBar.style.width = '0%';
      if (playIcon) playIcon.className = 'bi bi-play-fill';
      if (playText) playText.textContent = 'Listen to article';
      if (playBtn) playBtn.classList.remove('playing');
      if (controls) controls.style.display = 'none';
      if (statusText) statusText.textContent = 'Click to play';
    }

    if (playBtn) {
      playBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (!isPlaying) {
          startAudio();
        } else if (isPaused) {
          resumeAudio();
        } else {
          pauseAudio();
        }
      });
    }

    if (speedBtn) {
      speedBtn.addEventListener('click', function(e) {
        e.preventDefault();
        speedIdx = (speedIdx + 1) % SPEED_LEVELS.length;
        var chosen = SPEED_LEVELS[speedIdx];
        speedBtn.textContent = chosen.label;

        // Debounced restart: prevents rapid-click collisions when user clicks multiple times
        if (isPlaying && !isPaused) {
          clearTimeout(speedChangeTimer);
          clearTimeout(speakTimer);
          sessionToken++;
          try {
            window.speechSynthesis.cancel();
          } catch(err) {}

          speedChangeTimer = setTimeout(function() {
            if (isPlaying && !isPaused) {
              speakCurrentPhrase();
            }
          }, 100);
        }
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (currentIndex > 0) {
          currentIndex--;
          currentBlockPhrases = null;
          currentPhraseIdx = 0;
          sessionToken++;
          clearTimeout(speakTimer);
          try { window.speechSynthesis.cancel(); } catch(err) {}

          if (isPlaying && !isPaused) {
            setTimeout(speakCurrentPhrase, 60);
          } else {
            highlightCurrent(currentIndex);
            updateProgressUI();
          }
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (currentIndex < blocks.length - 1) {
          currentIndex++;
          currentBlockPhrases = null;
          currentPhraseIdx = 0;
          sessionToken++;
          clearTimeout(speakTimer);
          try { window.speechSynthesis.cancel(); } catch(err) {}

          if (isPlaying && !isPaused) {
            setTimeout(speakCurrentPhrase, 60);
          } else {
            highlightCurrent(currentIndex);
            updateProgressUI();
          }
        }
      });
    }

    if (stopBtn) {
      stopBtn.addEventListener('click', function(e) {
        e.preventDefault();
        stopAudio();
      });
    }

    // Cancel speech on page navigation
    window.addEventListener('beforeunload', function() {
      try {
        window.speechSynthesis.cancel();
      } catch(e) {}
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBlogAudio);
  } else {
    initBlogAudio();
  }
})();
