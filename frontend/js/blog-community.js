/**
 * Scale Group Blog Community & Reader Engagement Engine
 * Handles:
 * 1. Reader Email Login & Session Management
 * 2. Article Comments ("Share what you liked about the blog")
 * 3. Topic Request Submission & Community Upvoting
 */

(function () {
  'use strict';

  var STORAGE_KEY = 'scale_reader_user';

  // ── Session Helpers ────────────────────────────────────────────────────────
  function getReader() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function setReader(user) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } catch (e) {}
    updateHeaderUI();
    updateCommentFormUI();
  }

  function clearReader() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {}
    updateHeaderUI();
    updateCommentFormUI();
  }

  // ── Header Profile Indicator ──────────────────────────────────────────────
  function updateHeaderUI() {
    var reader = getReader();
    var navs = document.querySelectorAll('.global-nav');
    var drawers = document.querySelectorAll('.global-drawer__links');

    // Desktop Nav
    navs.forEach(function (nav) {
      var existingBtn = nav.querySelector('.reader-auth-btn');
      if (existingBtn) existingBtn.remove();

      var btn = document.createElement('a');
      btn.className = 'global-nav__link reader-auth-btn';
      btn.href = 'javascript:void(0)';

      if (reader && reader.email) {
        var displayName = reader.name ? reader.name.split(' ')[0] : reader.email.split('@')[0];
        btn.innerHTML = '<i class="bi bi-person-circle" style="color:var(--gold,#d4a63a)"></i> ' + escapeHtml(displayName);
        btn.title = 'Logged in as ' + escapeHtml(reader.email) + ' — Click to Sign Out';
        btn.onclick = function () {
          if (confirm('Signed in as ' + reader.email + '.\n\nDo you want to sign out?')) {
            clearReader();
            alert('You have signed out.');
          }
        };
      } else {
        btn.innerHTML = '<i class="bi bi-box-arrow-in-right"></i> Sign In';
        btn.onclick = function () {
          window.openReaderLoginModal();
        };
      }
      nav.appendChild(btn);
    });

    // Mobile Drawer
    drawers.forEach(function (drawer) {
      var existingDrawerBtn = drawer.querySelector('.reader-drawer-auth');
      if (existingDrawerBtn) existingDrawerBtn.remove();

      var item = document.createElement('div');
      item.className = 'reader-drawer-auth';
      item.style.cssText = 'padding: 14px 16px; margin-top: 10px; background: rgba(255,255,255,0.04); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08);';

      if (reader && reader.email) {
        item.innerHTML = '<div style="display:flex; justify-content:space-between; align-items:center;">' +
          '<div><div style="font-size:0.75rem; color:#94a3b8;">LOGGED IN READER</div><strong style="color:#fff; font-size:0.9rem;"><i class="bi bi-person-circle" style="color:#f3c659"></i> ' + escapeHtml(reader.name || reader.email) + '</strong></div>' +
          '<button type="button" class="btn-logout" style="background:transparent; border:1px solid rgba(255,255,255,0.2); color:#f87171; font-size:0.75rem; padding:4px 10px; border-radius:6px; cursor:pointer;">Sign Out</button>' +
          '</div>';
        var logoutBtn = item.querySelector('.btn-logout');
        if (logoutBtn) {
          logoutBtn.onclick = function () {
            clearReader();
            alert('Signed out successfully.');
          };
        }
      } else {
        item.innerHTML = '<div style="display:flex; justify-content:space-between; align-items:center;">' +
          '<div><strong style="color:#fff; font-size:0.9rem;">Reader Account</strong><div style="font-size:0.75rem; color:#94a3b8;">Log in to leave comments & suggest topics</div></div>' +
          '<button type="button" class="btn-login-drawer" style="background:linear-gradient(135deg,#c9973a,#f3c659); color:#000; border:none; font-weight:800; font-size:0.78rem; padding:6px 14px; border-radius:8px; cursor:pointer;">Sign In</button>' +
          '</div>';
        var loginBtn = item.querySelector('.btn-login-drawer');
        if (loginBtn) {
          loginBtn.onclick = function () {
            if (window.closeGlobalDrawer) window.closeGlobalDrawer();
            window.openReaderLoginModal();
          };
        }
      }
      drawer.appendChild(item);
    });
  }

  // ── Global Login Modal ────────────────────────────────────────────────────
  function createLoginModal() {
    if (document.getElementById('reader-login-modal')) return;

    var modalHtml = '' +
      '<div id="reader-login-modal" class="comm-modal-backdrop" style="display:none;">' +
      '  <div class="comm-modal">' +
      '    <button class="comm-modal-close" onclick="window.closeReaderLoginModal()">&times;</button>' +
      '    <div class="comm-modal-header">' +
      '      <span class="comm-badge"><i class="bi bi-mortarboard-fill"></i> SCALE GROUP COMMUNITY</span>' +
      '      <h3 style="margin:8px 0 6px 0; color:#fff; font-size:1.4rem; font-weight:800;">Log In with Your Email</h3>' +
      '      <p style="color:#94a3b8; font-size:0.88rem; margin:0 0 18px 0; line-height:1.45;">' +
      '        Join over 4,200+ Nigerian students. Leave comments, share your takeaways, and vote on upcoming study guides.' +
      '      </p>' +
      '    </div>' +
      '    <form id="reader-login-form" onsubmit="window.handleReaderLoginSubmit(event)">' +
      '      <div style="margin-bottom:14px; text-align:left;">' +
      '        <label style="display:block; font-size:0.8rem; font-weight:700; color:#cbd5e1; margin-bottom:6px;">Your Email Address <span style="color:#f87171">*</span></label>' +
      '        <input type="email" id="modal-reader-email" required placeholder="e.g. yourname@gmail.com" ' +
      '          style="width:100%; box-sizing:border-box; background:#161922; border:1px solid #2a2e3d; color:#fff; padding:12px 14px; border-radius:10px; font-size:0.95rem;">' +
      '      </div>' +
      '      <div style="margin-bottom:14px; text-align:left;">' +
      '        <label style="display:block; font-size:0.8rem; font-weight:700; color:#cbd5e1; margin-bottom:6px;">Your Name or Campus Alias</label>' +
      '        <input type="text" id="modal-reader-name" placeholder="e.g. David / Chinedu (UNILAG)" ' +
      '          style="width:100%; box-sizing:border-box; background:#161922; border:1px solid #2a2e3d; color:#fff; padding:12px 14px; border-radius:10px; font-size:0.95rem;">' +
      '      </div>' +
      '      <div id="modal-login-error" style="display:none; color:#f87171; font-size:0.82rem; margin-bottom:12px; text-align:left;"></div>' +
      '      <button type="submit" id="modal-login-btn" ' +
      '        style="width:100%; background:linear-gradient(135deg,#c9973a,#f3c659); color:#0c0e14; border:none; padding:14px; border-radius:10px; font-weight:800; font-size:0.95rem; cursor:pointer;">' +
      '        Continue to Scale Group &rarr;' +
      '      </button>' +
      '    </form>' +
      '    <div style="margin-top:14px; font-size:0.75rem; color:#64748b;">' +
      '      🔒 No spam, ever. Your email stays secure with Scale Group.' +
      '    </div>' +
      '  </div>' +
      '</div>';

    document.body.insertAdjacentHTML('beforeend', modalHtml);
  }

  window.openReaderLoginModal = function (callback) {
    createLoginModal();
    window._readerAuthCallback = callback;
    var modal = document.getElementById('reader-login-modal');
    if (modal) {
      modal.style.display = 'flex';
      var emailInp = document.getElementById('modal-reader-email');
      if (emailInp) emailInp.focus();
    }
  };

  window.closeReaderLoginModal = function () {
    var modal = document.getElementById('reader-login-modal');
    if (modal) modal.style.display = 'none';
  };

  window.handleReaderLoginSubmit = async function (e) {
    e.preventDefault();
    var email = document.getElementById('modal-reader-email').value.trim();
    var name = document.getElementById('modal-reader-name').value.trim();
    var btn = document.getElementById('modal-login-btn');
    var err = document.getElementById('modal-login-error');

    if (!email) return;

    btn.disabled = true;
    btn.textContent = 'Signing in...';
    err.style.display = 'none';

    try {
      var res = await fetch('/api/blog/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email, name: name })
      });
      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');

      setReader({
        email: data.user.email,
        name: data.user.name,
        token: data.token,
        school: data.user.school
      });

      window.closeReaderLoginModal();
      if (typeof window._readerAuthCallback === 'function') {
        window._readerAuthCallback(data.user);
        window._readerAuthCallback = null;
      }
    } catch (error) {
      err.textContent = error.message || 'Unable to sign in. Please try again.';
      err.style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Continue to Scale Group \u2192';
    }
  };

  // ── Article Comments UI & Operations ───────────────────────────────────────
  function updateCommentFormUI() {
    var reader = getReader();
    var userBadge = document.getElementById('comment-author-badge');
    var guestFields = document.getElementById('comment-guest-fields');

    if (userBadge && guestFields) {
      if (reader && reader.email) {
        userBadge.style.display = 'flex';
        guestFields.style.display = 'none';
        userBadge.innerHTML = '<i class="bi bi-person-check-fill" style="color:#4ade80"></i> ' +
          '<span>Posting as <strong>' + escapeHtml(reader.name || reader.email) + '</strong> (' + escapeHtml(reader.email) + ')</span> ' +
          '<button type="button" onclick="window.logoutReader()" style="background:none; border:none; color:#f3c659; font-size:0.75rem; text-decoration:underline; cursor:pointer; margin-left:8px;">Switch</button>';
      } else {
        userBadge.style.display = 'none';
        guestFields.style.display = 'grid';
      }
    }
  }

  window.logoutReader = function () {
    clearReader();
    updateCommentFormUI();
  };

  window.switchCommunityTab = function (tabName) {
    document.querySelectorAll('.comm-tab').forEach(function (btn) {
      btn.classList.toggle('active', btn.getAttribute('data-target') === tabName);
    });
    var commentsPane = document.getElementById('tab-pane-comments');
    var topicsPane = document.getElementById('tab-pane-topics');
    if (commentsPane && topicsPane) {
      commentsPane.style.display = tabName === 'tab-comments' ? 'block' : 'none';
      topicsPane.style.display = tabName === 'tab-topics' ? 'block' : 'none';
    }
  };

  async function loadComments(slug) {
    var list = document.getElementById('comments-list');
    if (!list) return;

    try {
      var url = slug ? '/api/blog/comments?slug=' + encodeURIComponent(slug) : '/api/blog/comments';
      var res = await fetch(url);
      var data = await res.json();
      var comments = data.comments || [];

      var countBadges = document.querySelectorAll('.comment-count-badge');
      countBadges.forEach(function (b) { b.textContent = comments.length; });

      if (comments.length === 0) {
        list.innerHTML = '<div style="text-align:center; padding:32px 16px; color:#94a3b8; background:rgba(255,255,255,0.02); border-radius:12px; border:1px dashed rgba(255,255,255,0.08);">' +
          '<i class="bi bi-chat-quote" style="font-size:2rem; color:var(--gold,#d4a63a); display:block; margin-bottom:8px;"></i>' +
          '<strong>Be the first to share what you liked about this guide!</strong>' +
          '<p style="font-size:0.85rem; margin:4px 0 0 0;">Did this study method or campus advice help you? Leave your feedback above.</p>' +
          '</div>';
        return;
      }

      list.innerHTML = comments.map(function (c) {
        var initial = (c.author_name || 'R').charAt(0).toUpperCase();
        var dateFormatted = c.created_at ? new Date(c.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : 'Recently';

        return '' +
          '<div class="comment-card">' +
          '  <div class="comment-card__header">' +
          '    <div class="comment-card__avatar">' + initial + '</div>' +
          '    <div class="comment-card__meta">' +
          '      <strong class="comment-card__name">' + escapeHtml(c.author_name || 'Reader') + '</strong>' +
          (c.school ? ' <span class="comment-card__school"><i class="bi bi-geo-alt"></i> ' + escapeHtml(c.school) + '</span>' : '') +
          '      <span class="comment-card__date">' + dateFormatted + '</span>' +
          '    </div>' +
          '    <div class="comment-card__badge"><i class="bi bi-heart-fill" style="color:#f43f5e; font-size:0.8rem"></i> Liked: ' + escapeHtml(c.what_liked || 'Practical Tips') + '</div>' +
          '  </div>' +
          '  <div class="comment-card__body">' + escapeHtml(c.content) + '</div>' +
          '</div>';
      }).join('');
    } catch (e) {
      list.innerHTML = '<div style="color:#f87171; font-size:0.85rem; padding:12px;">Unable to load reader comments. Please check your connection.</div>';
    }
  }

  window.submitBlogComment = async function (e) {
    e.preventDefault();
    var reader = getReader();
    var slug = document.getElementById('comment-slug') ? document.getElementById('comment-slug').value : '';
    var articleTitle = document.getElementById('comment-article-title') ? document.getElementById('comment-article-title').value : 'Study Guide';
    var whatLiked = document.getElementById('comment-what-liked').value.trim();
    var content = document.getElementById('comment-content').value.trim();
    var btn = document.getElementById('comment-submit-btn');
    var status = document.getElementById('comment-status');

    var email = reader ? reader.email : (document.getElementById('guest-email') ? document.getElementById('guest-email').value.trim() : '');
    var name = reader ? reader.name : (document.getElementById('guest-name') ? document.getElementById('guest-name').value.trim() : '');
    var school = reader ? reader.school : (document.getElementById('guest-school') ? document.getElementById('guest-school').value.trim() : '');

    if (!email) {
      window.openReaderLoginModal(function () {
        window.submitBlogComment(e);
      });
      return;
    }

    if (!content) {
      alert('Please enter your comment or takeaway.');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-inline"></span> Posting...';
    status.style.display = 'none';

    try {
      var res = await fetch('/api/blog/comments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': reader && reader.token ? 'Bearer ' + reader.token : ''
        },
        body: JSON.stringify({
          slug: slug,
          article_title: articleTitle,
          what_liked: whatLiked,
          content: content,
          email: email,
          name: name,
          school: school
        })
      });

      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error posting comment');

      if (!reader) {
        setReader({ email: email, name: name, school: school });
      }

      document.getElementById('comment-content').value = '';
      status.style.color = '#4ade80';
      status.textContent = '✨ Thank you! Your feedback has been shared with the community.';
      status.style.display = 'block';

      loadComments(slug);
    } catch (err) {
      status.style.color = '#f87171';
      status.textContent = err.message || 'Failed to submit comment. Please try again.';
      status.style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-send-fill"></i> Post Takeaway &rarr;';
    }
  };

  // ── Topic Requests & Upvoting ──────────────────────────────────────────────
  async function loadTopics(category) {
    var list = document.getElementById('topics-list');
    if (!list) return;

    try {
      var url = category && category !== 'All' ? '/api/blog/topics?category=' + encodeURIComponent(category) : '/api/blog/topics';
      var res = await fetch(url);
      var data = await res.json();
      var topics = data.topics || [];

      if (topics.length === 0) {
        list.innerHTML = '<div style="text-align:center; padding:24px 16px; color:#94a3b8;">No suggested topics found in this category yet. Be the first to suggest one!</div>';
        return;
      }

      list.innerHTML = topics.map(function (t) {
        var statusColor = '#94a3b8';
        if (t.status === 'In Writing') statusColor = '#f5c862';
        if (t.status === 'Planned') statusColor = '#38bdf8';
        if (t.status === 'Published') statusColor = '#4ade80';

        return '' +
          '<div class="topic-card" id="topic-card-' + t.id + '">' +
          '  <div class="topic-card__vote-col">' +
          '    <button type="button" class="topic-vote-btn" onclick="window.voteTopic(\'' + t.id + '\')" title="Upvote this topic">' +
          '      <i class="bi bi-caret-up-fill"></i>' +
          '      <span class="topic-vote-count" id="vote-count-' + t.id + '">' + (t.votes || 1) + '</span>' +
          '    </button>' +
          '  </div>' +
          '  <div class="topic-card__content">' +
          '    <div class="topic-card__top">' +
          '      <span class="topic-cat-pill">' + escapeHtml(t.category || 'Academics') + '</span>' +
          '      <span class="topic-status-pill" style="color:' + statusColor + '; border-color:' + statusColor + '22; background:' + statusColor + '12;">' +
          '        <i class="bi bi-circle-fill" style="font-size:0.5rem"></i> ' + escapeHtml(t.status || 'Community Request') +
          '      </span>' +
          '    </div>' +
          '    <h4 class="topic-card__title">' + escapeHtml(t.title) + '</h4>' +
          '    <p class="topic-card__why">' + escapeHtml(t.why_needed) + '</p>' +
          '    <div class="topic-card__footer">' +
          '      <span>Requested by <strong>' + escapeHtml(t.author_name || 'Anonymous Student') + '</strong></span>' +
          '    </div>' +
          '  </div>' +
          '</div>';
      }).join('');
    } catch (e) {
      list.innerHTML = '<div style="color:#f87171; font-size:0.85rem; padding:12px;">Unable to load suggested topics.</div>';
    }
  }

  window.submitTopicRequest = async function (e) {
    e.preventDefault();
    var reader = getReader();
    var title = document.getElementById('topic-title').value.trim();
    var category = document.getElementById('topic-category').value;
    var why = document.getElementById('topic-why').value.trim();
    var btn = document.getElementById('topic-submit-btn');
    var status = document.getElementById('topic-status');

    var email = reader ? reader.email : (document.getElementById('topic-guest-email') ? document.getElementById('topic-guest-email').value.trim() : '');
    var name = reader ? reader.name : (document.getElementById('topic-guest-name') ? document.getElementById('topic-guest-name').value.trim() : '');

    if (!email) {
      window.openReaderLoginModal(function () {
        window.submitTopicRequest(e);
      });
      return;
    }

    if (!title || !why) {
      alert('Please fill out the topic title and explanation.');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-inline"></span> Submitting...';
    status.style.display = 'none';

    try {
      var res = await fetch('/api/blog/topics', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': reader && reader.token ? 'Bearer ' + reader.token : ''
        },
        body: JSON.stringify({
          title: title,
          category: category,
          why_needed: why,
          email: email,
          name: name
        })
      });

      var data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error submitting topic');

      if (!reader) {
        setReader({ email: email, name: name });
      }

      document.getElementById('topic-title').value = '';
      document.getElementById('topic-why').value = '';
      status.style.color = '#4ade80';
      status.textContent = '🚀 Topic added to the community roadmap! It is now open for votes.';
      status.style.display = 'block';

      loadTopics();
    } catch (err) {
      status.style.color = '#f87171';
      status.textContent = err.message || 'Failed to submit topic. Please try again.';
      status.style.display = 'block';
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-lightbulb-fill"></i> Submit Topic Request &rarr;';
    }
  };

  window.voteTopic = async function (topicId) {
    var countEl = document.getElementById('vote-count-' + topicId);
    var reader = getReader();
    var email = reader ? reader.email : 'guest';

    try {
      var res = await fetch('/api/blog/topics/' + encodeURIComponent(topicId) + '/vote', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': reader && reader.token ? 'Bearer ' + reader.token : ''
        },
        body: JSON.stringify({ email: email })
      });
      var data = await res.json();
      if (res.ok && countEl) {
        countEl.textContent = data.votes;
        var btn = countEl.closest('.topic-vote-btn');
        if (btn) btn.classList.add('voted');
      }
    } catch (e) {
      console.warn('Vote error:', e);
    }
  };

  // Helper
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // ── Initialization ────────────────────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', function () {
    updateHeaderUI();
    createLoginModal();

    var slugEl = document.getElementById('comment-slug');
    var slug = slugEl ? slugEl.value : null;

    if (document.getElementById('comments-list')) {
      loadComments(slug);
      updateCommentFormUI();
    }

    if (document.getElementById('topics-list')) {
      loadTopics();
    }
  });

})();
