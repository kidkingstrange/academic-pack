/**
 * Dynamic Customer Reviews Widget for Academic Comeback Landing Pages.
 * Handles fetching aggregate summary, rendering verified review cards,
 * image lightboxes, and "Load More" pagination.
 */
(function () {
  let currentOffset = 0;
  const batchSize = 6;
  let totalReviews = 0;

  function renderStars(rating) {
    let starsHtml = '';
    for (let i = 1; i <= 5; i++) {
      if (i <= rating) {
        starsHtml += '<i class="bi bi-star-fill" style="color: #f3c659; margin-right: 2px;"></i>';
      } else {
        starsHtml += '<i class="bi bi-star" style="color: rgba(255,255,255,0.2); margin-right: 2px;"></i>';
      }
    }
    return starsHtml;
  }

  function formatDate(isoStr) {
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch (e) {
      return 'Verified Buyer';
    }
  }

  async function loadSummary(container) {
    try {
      const res = await fetch('/api/reviews/summary');
      if (!res.ok) return;
      const data = await res.json();
      totalReviews = data.total_reviews || 0;

      const summaryHtml = `
        <div class="reviews-summary-bar" style="background: linear-gradient(135deg, #131826 0%, #0c0e14 100%); border: 1px solid rgba(212, 166, 58, 0.25); border-radius: 16px; padding: 24px; margin-bottom: 28px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
          <div style="font-size: 2.4rem; font-weight: 900; color: #fff; line-height: 1; margin-bottom: 6px;">
            ${data.average_rating} <span style="font-size: 1.2rem; color: #f3c659;">/ 5.0</span>
          </div>
          <div style="font-size: 1.2rem; margin-bottom: 8px;">
            ${renderStars(Math.round(data.average_rating))}
          </div>
          <p style="margin: 0; font-size: 0.9rem; color: #94a3b8;">
            Based on <strong style="color: #fff;">${totalReviews} verified student reviews</strong> across Nigerian universities &amp; high-stakes exam takers.
          </p>
        </div>
      `;
      container.insertAdjacentHTML('afterbegin', summaryHtml);
    } catch (e) {
      console.warn('Reviews summary fetch error:', e);
    }
  }

  async function loadReviewsBatch(gridContainer, loadMoreBtn) {
    if (loadMoreBtn) {
      loadMoreBtn.disabled = true;
      loadMoreBtn.textContent = 'Loading reviews...';
    }

    try {
      const res = await fetch(`/api/reviews?approved=true&limit=${batchSize}&offset=${currentOffset}&sort=-date`);
      if (!res.ok) throw new Error('Failed to load reviews');
      const data = await res.json();

      if (data.reviews.length === 0 && currentOffset === 0) {
        gridContainer.innerHTML = '<p style="text-align:center; color:#94a3b8; grid-column:1/-1;">No reviews posted yet. Be the first to share your experience!</p>';
        if (loadMoreBtn) loadMoreBtn.style.display = 'none';
        return;
      }

      data.reviews.forEach((r) => {
        const card = document.createElement('div');
        card.className = 'review-widget-card';
        card.style.cssText = 'background: #121622; border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; text-align: left; transition: transform 0.2s, border-color 0.2s;';
        
        const photoHtml = r.photo_url
          ? `<div style="margin-top: 14px;"><img src="${r.photo_url}" alt="Review photo" style="max-height: 100px; border-radius: 8px; border: 1px solid rgba(212,166,58,0.3); cursor: pointer;" onclick="window.open('${r.photo_url}', '_blank')"></div>`
          : '';

        card.innerHTML = `
          <div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
              <div>${renderStars(r.rating)}</div>
              <span style="font-size: 0.75rem; color: #64748b;">${formatDate(r.date)}</span>
            </div>
            <p style="font-size: 0.9rem; color: #e2e8f0; line-height: 1.6; margin: 0 0 12px; font-style: italic;">
              "${r.text}"
            </p>
            ${photoHtml}
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 12px;">
            <div style="width: 32px; height: 32px; border-radius: 50%; background: rgba(212,166,58,0.15); color: #f3c659; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem;">
              ${r.name ? r.name.charAt(0).toUpperCase() : 'S'}
            </div>
            <div>
              <strong style="font-size: 0.85rem; color: #fff; display: block;">${r.name || 'Verified Student'}</strong>
              <span style="font-size: 0.75rem; color: #4ade80;"><i class="bi bi-patch-check-fill"></i> Verified Buyer</span>
            </div>
          </div>
        `;
        gridContainer.appendChild(card);
      });

      currentOffset += data.reviews.length;

      if (loadMoreBtn) {
        loadMoreBtn.disabled = false;
        loadMoreBtn.textContent = 'Load More Reviews ↓';
        if (!data.has_more) {
          loadMoreBtn.style.display = 'none';
        }
      }
    } catch (err) {
      console.warn('Reviews batch error:', err);
      if (loadMoreBtn) {
        loadMoreBtn.disabled = false;
        loadMoreBtn.textContent = 'Load More Reviews ↓';
      }
    }
  }

  window.initReviewsWidget = function (containerId = 'reviews-widget-container') {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';
    loadSummary(container);

    const grid = document.createElement('div');
    grid.className = 'reviews-widget-grid';
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px;';
    container.appendChild(grid);

    const btnWrapper = document.createElement('div');
    btnWrapper.style.cssText = 'text-align: center; margin-top: 16px;';
    const loadMoreBtn = document.createElement('button');
    loadMoreBtn.className = 'btn-load-more-reviews';
    loadMoreBtn.textContent = 'Load More Reviews ↓';
    loadMoreBtn.style.cssText = 'background: rgba(255,255,255,0.06); border: 1px solid rgba(212,166,58,0.3); color: #f3c659; font-size: 0.88rem; font-weight: 700; padding: 10px 24px; border-radius: 50px; cursor: pointer; transition: all 0.2s;';
    loadMoreBtn.addEventListener('click', () => loadReviewsBatch(grid, loadMoreBtn));
    btnWrapper.appendChild(loadMoreBtn);
    container.appendChild(btnWrapper);

    loadReviewsBatch(grid, loadMoreBtn);
  };
})();
