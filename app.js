/**
 * File purpose:
 * - Client-side UI behavior for the My Pet Stickers static V1 landing page.
 *
 * Major functions:
 * - Hero cat/dog scrapbook carousel with autoplay and mobile swipe.
 * - Pet type selection and local image validation/preview.
 * - Sample four-style selector and sample nine-sticker pack flow.
 * - Progress, watermark, and demo checkout state updates.
 *
 * Last modification:
 * - 【MODIFIED】 Added responsive carousel behavior and simplified the page logic for the compact pet-studio layout.
 */

(() => {
  // 【MODIFIED】 Fixed V1 style catalog shared by the sample style picker.
  const styles = [
    ['A', 'Soft Kawaii Chibi', 'Rounded paws, a little bigger eyes, and an extra dose of sweetness.'],
    ['B', 'Bold Cartoon Sticker', 'Confident outlines and expressive shapes that pop in every chat.'],
    ['C', 'Cute Semi-Realistic', 'Their familiar face and beautiful markings, softly illustrated.'],
    ['D', 'Storybook Watercolor', 'Gentle brushstrokes and the warmth of a favorite picture book.']
  ];

  const $ = (selector) => document.querySelector(selector);

  let pet = 'cat';
  let photo = null;
  let objectUrl = null;
  let sampleStage = 0;
  let style = 'A';

  // 【MODIFIED】 Hero carousel state is kept local to this module.
  let heroSlide = 0;
  let heroTimer = null;
  let heroResumeTimer = null;
  let touchStartX = null;

  /**
   * Function responsibility:
   * - Build one visual quadrant from the supplied 2×2 style reference image.
   * Input:
   * - species: "cat" or "dog".
   * - index: zero-based quadrant index.
   * Output / side effects:
   * - Returns HTML only; does not mutate global state or DOM.
   */
  function art(species, index) {
    return `<div class="style-art quadrant-${index + 1}">
      <img src="assets/${species}-styles.png" alt="${styles[index][1]} ${species} illustration" loading="lazy">
      <span class="style-letter">${styles[index][0]}</span>
    </div>`;
  }

  /**
   * Function responsibility:
   * - Highlight one progress step in the creator workflow.
   * Input:
   * - index: zero-based progress step.
   * Output / side effects:
   * - Updates .progress DOM classes only.
   */
  function setProgress(index) {
    document.querySelectorAll('.progress li').forEach((item, i) => {
      item.classList.toggle('current', index === i);
    });
  }

  /**
   * Function responsibility:
   * - Render the requested hero carousel slide and accessibility state.
   * Input:
   * - index: requested slide index.
   * - isManual: whether a user action initiated the change.
   * Output / side effects:
   * - Updates hero slide visibility, carousel dots, and carousel timing.
   */
  function showHeroSlide(index, isManual = false) {
    const slides = [...document.querySelectorAll('.carousel-slide')];
    const dots = [...document.querySelectorAll('[data-carousel-dot]')];
    if (!slides.length) return;

    heroSlide = (index + slides.length) % slides.length;

    slides.forEach((slide, i) => {
      const active = i === heroSlide;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
    });

    dots.forEach((dot, i) => {
      const active = i === heroSlide;
      dot.classList.toggle('is-active', active);
      dot.setAttribute('aria-selected', String(active));
    });

    if (isManual) pauseHeroAutoplay(12000);
  }

  /**
   * Function responsibility:
   * - Stop existing hero carousel timers.
   * Input:
   * - resumeAfterMs: optional delay before autoplay restarts.
   * Output / side effects:
   * - Clears and optionally schedules module-level carousel timers.
   */
  function pauseHeroAutoplay(resumeAfterMs = 0) {
    if (heroTimer) {
      window.clearInterval(heroTimer);
      heroTimer = null;
    }

    if (heroResumeTimer) {
      window.clearTimeout(heroResumeTimer);
      heroResumeTimer = null;
    }

    if (resumeAfterMs > 0 && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      heroResumeTimer = window.setTimeout(startHeroAutoplay, resumeAfterMs);
    }
  }

  /**
   * Function responsibility:
   * - Start the six-second hero sample rotation.
   * Input:
   * - None.
   * Output / side effects:
   * - Creates one module-level interval unless reduced motion is requested.
   */
  function startHeroAutoplay() {
    if (!$('#heroCarousel') || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    pauseHeroAutoplay();
    heroTimer = window.setInterval(() => showHeroSlide(heroSlide + 1, false), 6000);
  }

  /**
   * Function responsibility:
   * - Configure buttons, hover/focus pause, and swipe behavior for the hero carousel.
   * Input:
   * - None.
   * Output / side effects:
   * - Adds event listeners to hero carousel DOM and starts autoplay.
   */
  function initHeroCarousel() {
    const carousel = $('#heroCarousel');
    if (!carousel) return;

    $('#heroPrev')?.addEventListener('click', () => showHeroSlide(heroSlide - 1, true));
    $('#heroNext')?.addEventListener('click', () => showHeroSlide(heroSlide + 1, true));

    document.querySelectorAll('[data-carousel-dot]').forEach((dot) => {
      dot.addEventListener('click', () => showHeroSlide(Number(dot.dataset.carouselDot), true));
    });

    carousel.addEventListener('mouseenter', () => pauseHeroAutoplay());
    carousel.addEventListener('mouseleave', startHeroAutoplay);
    carousel.addEventListener('focusin', () => pauseHeroAutoplay());
    carousel.addEventListener('focusout', startHeroAutoplay);

    carousel.addEventListener('touchstart', (event) => {
      touchStartX = event.changedTouches[0]?.clientX ?? null;
    }, { passive: true });

    carousel.addEventListener('touchend', (event) => {
      if (touchStartX === null) return;
      const touchEndX = event.changedTouches[0]?.clientX ?? touchStartX;
      const delta = touchEndX - touchStartX;
      touchStartX = null;
      if (Math.abs(delta) < 45) return;
      showHeroSlide(heroSlide + (delta < 0 ? 1 : -1), true);
    }, { passive: true });

    showHeroSlide(0, false);
    startHeroAutoplay();
  }

  /**
   * Function responsibility:
   * - Restore the creator result panel to the selected pet/photo starting state.
   * Input:
   * - None; reads module-level pet/photo/objectUrl.
   * Output / side effects:
   * - Resets creator DOM, sample state, watermark, checkout and progress.
   */
  function resetResult() {
    sampleStage = 0;

    const sampleStyles = $('#sampleStyles');
    const checkoutPanel = $('#checkoutPanel');
    const watermark = $('#watermark');
    const resultCanvas = $('#resultCanvas');
    const resultImage = $('#resultImage');
    const previewButton = $('#previewButton');

    if (!sampleStyles || !checkoutPanel || !watermark || !resultCanvas || !resultImage || !previewButton) return;

    sampleStyles.hidden = true;
    checkoutPanel.hidden = true;
    watermark.hidden = true;
    resultCanvas.hidden = false;
    resultCanvas.classList.toggle('photo', Boolean(photo));

    resultImage.src = photo ? objectUrl : `assets/${pet}-grid.png`;
    resultImage.alt = photo ? 'Your selected pet photo' : `Sample ${pet} sticker pack`;

    if ($('#resultLabel')) $('#resultLabel').textContent = photo ? 'YOUR PHOTO' : 'A LITTLE INSPIRATION';
    if ($('#resultTitle')) $('#resultTitle').textContent = photo ? 'A lovely place to start.' : 'Their face. Your new favorite reply.';
    if ($('#resultDescription')) {
      $('#resultDescription').textContent = photo
        ? 'Your photo is selected and stays in this browser until generation is available.'
        : 'Nine little ways to say hello, thank you, or “I need a hug.”';
    }

    previewButton.innerHTML = 'Create my free preview <span>↗</span>';
    setProgress(0);
  }

  /**
   * Function responsibility:
   * - Validate and locally preview a user-selected pet photo.
   * Input:
   * - file: File object from input or drag-and-drop.
   * Output / side effects:
   * - Updates module-level photo/objectUrl and creator DOM; no upload occurs.
   */
  async function selectPhoto(file) {
    if (!file) return;
    const status = $('#formStatus');

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      if (status) status.textContent = 'Please choose a JPG, PNG or WebP photo.';
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      if (status) status.textContent = 'Please choose a photo smaller than 10 MB.';
      return;
    }

    const url = URL.createObjectURL(file);
    const image = new Image();
    image.src = url;

    try {
      await image.decode();
    } catch {
      URL.revokeObjectURL(url);
      if (status) status.textContent = 'We couldn’t read that image. Please try another photo.';
      return;
    }

    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = url;
    photo = file;

    const uploadTitle = $('#uploadBox strong');
    if (uploadTitle) uploadTitle.textContent = file.name;
    if (status) status.textContent = 'Photo selected. You can replace it anytime before creating a preview.';
    resetResult();
  }

  /**
   * Function responsibility:
   * - Render the four fixed art styles in the sample workflow.
   * Input:
   * - None; reads module-level pet.
   * Output / side effects:
   * - Populates #sampleStyles, updates creator labels, progress and sample stage.
   */
  function showSampleStyles() {
    const sampleStyles = $('#sampleStyles');
    const resultCanvas = $('#resultCanvas');
    const checkoutPanel = $('#checkoutPanel');
    if (!sampleStyles || !resultCanvas || !checkoutPanel) return;

    sampleStage = 1;
    style = 'A';
    resultCanvas.hidden = true;
    checkoutPanel.hidden = true;
    sampleStyles.hidden = false;

    sampleStyles.innerHTML = styles.map((item, index) => `
      <button type="button" data-style="${item[0]}" aria-pressed="${index === 0}" class="${index === 0 ? 'active' : ''}">
        ${art(pet, index)}
        <span>${item[0]} · ${item[1]}</span>
      </button>
    `).join('');

    sampleStyles.querySelectorAll('button').forEach((button) => {
      button.addEventListener('click', () => {
        style = button.dataset.style;
        sampleStyles.querySelectorAll('button').forEach((item) => {
          const active = item === button;
          item.classList.toggle('active', active);
          item.setAttribute('aria-pressed', String(active));
        });
      });
    });

    $('#resultLabel').textContent = 'EXPLORE THE SAMPLE · FOUR STYLES';
    $('#resultTitle').textContent = 'Which one feels like them?';
    $('#resultDescription').textContent = 'These sample styles show how the same pet can feel different without losing their identity.';
    $('#previewButton').innerHTML = 'See a sample nine-sticker pack <span>↗</span>';
    setProgress(1);
  }

  /**
   * Function responsibility:
   * - Configure creator pet toggles, local upload, drag/drop and demo sample controls.
   * Input:
   * - None.
   * Output / side effects:
   * - Adds event listeners and updates the creator DOM/module state.
   */
  function initCreator() {
    document.querySelectorAll('[data-pet]').forEach((button) => {
      button.addEventListener('click', () => {
        pet = button.dataset.pet;
        document.querySelectorAll('[data-pet]').forEach((item) => {
          const active = item === button;
          item.classList.toggle('active', active);
          item.setAttribute('aria-pressed', String(active));
        });
        resetResult();
      });
    });

    $('#photoInput')?.addEventListener('change', (event) => selectPhoto(event.target.files[0]));

    const uploadBox = $('#uploadBox');
    if (uploadBox) {
      ['dragenter', 'dragover'].forEach((name) => {
        uploadBox.addEventListener(name, (event) => {
          event.preventDefault();
          uploadBox.classList.add('dragging');
        });
      });

      ['dragleave', 'drop'].forEach((name) => {
        uploadBox.addEventListener(name, (event) => {
          event.preventDefault();
          uploadBox.classList.remove('dragging');
        });
      });

      uploadBox.addEventListener('drop', (event) => selectPhoto(event.dataTransfer.files[0]));
    }

    $('#sampleButton')?.addEventListener('click', showSampleStyles);

    $('#previewButton')?.addEventListener('click', () => {
      if (sampleStage === 1) {
        sampleStage = 2;
        $('#sampleStyles').hidden = true;
        $('#resultCanvas').hidden = false;
        $('#resultCanvas').classList.remove('photo');
        $('#resultImage').src = `assets/${pet}-grid.png`;
        $('#resultImage').alt = `Supplied sample ${pet} nine-sticker pack`;
        $('#watermark').hidden = false;
        $('#checkoutPanel').hidden = false;
        $('#resultLabel').textContent = 'SAMPLE PACK · WATERMARKED PREVIEW';
        $('#resultTitle').textContent = 'Nine little reasons to smile.';
        $('#resultDescription').textContent = `You selected style ${style}. This sample shows the final pack stage before payment.`;
        $('#previewButton').innerHTML = 'Back to my photo <span>↗</span>';
        setProgress(2);
        return;
      }

      if (sampleStage === 2) {
        resetResult();
        return;
      }

      if (!photo) {
        $('#photoInput')?.click();
        return;
      }

      const status = $('#formStatus');
      if (status) status.textContent = 'Custom previews are coming soon. Your photo has not been uploaded or charged.';
    });
  }

  // 【MODIFIED】 Initialize independent UI features after the document has been parsed.
  initHeroCarousel();
  initCreator();
  resetResult();

  // 【MODIFIED】 Revoke the local object URL when leaving the page to avoid leaking browser memory.
  window.addEventListener('beforeunload', () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
  });
})();
