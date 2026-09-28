/**
 * Academic Comeback Blog — Smart Audio Player (Client-Side Speech Engine)
 * Instant, zero-bandwidth audio reader using browser Web Speech API.
 */
(function() {
  'use strict';

  function initBlogAudio() {
    var player = document.getElementById('article-audio-player');
    if (!player) return;

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
      // CRITICAL FIX: Avoid parent-child duplication (e.g. <blockquote> containing <p>, or <li> containing <p>)
      // If this element contains child readable blocks, skip the parent container so only the children are read!
      if (el.querySelector('p, li, blockquote, h2, h3')) {
        continue;
      }

      var txt = (el.innerText || el.textContent || '').trim();
      if (txt.length >= 4) {
        tempBlocks.push(el);
      }
    }

    // Secondary safety: Deduplicate any consecutive blocks that have identical text
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
    var isPlaying = false;
    var isPaused = false;
    var currentRate = 1.0;
    var rates = [1.0, 1.25, 1.5, 2.0];
    var rateIdx = 0;
    var activeUtterance = null;
    var preferredVoice = null;

    function selectBestVoice() {
      try {
        var voices = window.speechSynthesis.getVoices() || [];
        if (!voices.length) return null;

        // 1. Try Nigerian English
        for (var i = 0; i < voices.length; i++) {
          if (voices[i].lang === 'en-NG') return voices[i];
        }
        // 2. Try British English natural/neural
        for (var j = 0; j < voices.length; j++) {
          var v = voices[j];
          if (v.lang === 'en-GB' && (v.name.indexOf('Natural') !== -1 || v.name.indexOf('Google') !== -1 || v.name.indexOf('Daniel') !== -1)) {
            return v;
          }
        }
        // 3. Try standard English natural
        for (var k = 0; k < voices.length; k++) {
          var ve = voices[k];
          if (ve.lang.indexOf('en') === 0 && (ve.name.indexOf('Natural') !== -1 || ve.name.indexOf('Google') !== -1)) {
            return ve;
          }
        }
        // 4. Any English
        for (var l = 0; l < voices.length; l++) {
          if (voices[l].lang.indexOf('en') === 0) return voices[l];
        }
        return voices[0];
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
        // Highlight the parent blockquote if inside one, otherwise the element itself
        var targetEl = blocks[idx].closest('blockquote') || blocks[idx];
        targetEl.classList.add('audio-active-reading');
        var rect = targetEl.getBoundingClientRect();
        var inView = (rect.top >= 60 && rect.bottom <= (window.innerHeight - 60));
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

    function speakCurrentBlock() {
      if (currentIndex >= blocks.length) {
        stopAudio();
        if (statusText) statusText.textContent = 'Completed';
        return;
      }

      updateProgressUI();
      highlightCurrent(currentIndex);

      var blockText = (blocks[currentIndex].innerText || blocks[currentIndex].textContent || '').trim();
      
      // Clean up common markdown artifacts
      blockText = blockText.replace(/[#*_~`]/g, '').replace(/\s+/g, ' ');

      try {
        window.speechSynthesis.cancel();
      } catch(e) {}

      activeUtterance = new SpeechSynthesisUtterance(blockText);
      if (preferredVoice) {
        activeUtterance.voice = preferredVoice;
      }
      activeUtterance.rate = currentRate;
      activeUtterance.pitch = 1.0;

      activeUtterance.onend = function() {
        if (isPlaying && !isPaused) {
          currentIndex++;
          speakCurrentBlock();
        }
      };

      activeUtterance.onerror = function(evt) {
        if (evt.error !== 'interrupted' && evt.error !== 'canceled') {
          if (isPlaying && !isPaused) {
            currentIndex++;
            speakCurrentBlock();
          }
        }
      };

      try {
        window.speechSynthesis.speak(activeUtterance);
      } catch(e) {
        console.warn('Speech synthesis speak failed:', e);
      }
    }

    function startAudio() {
      isPlaying = true;
      isPaused = false;
      if (controls) controls.style.display = 'flex';
      if (playIcon) playIcon.className = 'bi bi-pause-fill';
      if (playText) playText.textContent = 'Pause';
      if (playBtn) playBtn.classList.add('playing');
      speakCurrentBlock();
    }

    function pauseAudio() {
      isPaused = true;
      try {
        window.speechSynthesis.pause();
      } catch(e) {}
      if (playIcon) playIcon.className = 'bi bi-play-fill';
      if (playText) playText.textContent = 'Resume';
      if (statusText) statusText.textContent = 'Paused';
    }

    function resumeAudio() {
      isPaused = false;
      if (playIcon) playIcon.className = 'bi bi-pause-fill';
      if (playText) playText.textContent = 'Pause';
      if (statusText) statusText.textContent = 'Section ' + (currentIndex + 1) + ' of ' + blocks.length;

      try {
        if (window.speechSynthesis.paused) {
          window.speechSynthesis.resume();
        } else {
          speakCurrentBlock();
        }
      } catch(e) {
        speakCurrentBlock();
      }
    }

    function stopAudio() {
      isPlaying = false;
      isPaused = false;
      try {
        window.speechSynthesis.cancel();
      } catch(e) {}
      clearHighlight();
      currentIndex = 0;
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
        rateIdx = (rateIdx + 1) % rates.length;
        currentRate = rates[rateIdx];
        speedBtn.textContent = currentRate.toFixed(currentRate % 1 === 0 ? 1 : 2) + 'x';
        if (isPlaying && !isPaused) {
          speakCurrentBlock();
        }
      });
    }

    if (prevBtn) {
      prevBtn.addEventListener('click', function(e) {
        e.preventDefault();
        if (currentIndex > 0) {
          currentIndex--;
          if (isPlaying && !isPaused) {
            speakCurrentBlock();
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
          if (isPlaying && !isPaused) {
            speakCurrentBlock();
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
