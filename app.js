(() => {
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
  const art = (species, index) => `<div class="style-art quadrant-${index + 1}"><img src="assets/${species}-styles.png" alt="${styles[index][1]} ${species} illustration" loading="lazy"><span class="style-letter">${styles[index][0]}</span></div>`;
  function renderStyles(species) {
    $('#styleCards').innerHTML = styles.map((item, index) => `<article class="style-card">${art(species, index)}<h3>${item[1]}</h3><p>${item[2]}</p></article>`).join('');
  }
  renderStyles('cat');
  document.querySelectorAll('[data-example]').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('[data-example]').forEach(item => {
      item.classList.toggle('active', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    });
    renderStyles(button.dataset.example);
  }));
  function setProgress(index) {
    document.querySelectorAll('.progress li').forEach((item, i) => item.classList.toggle('current', index === i));
  }
  function resetResult() {
    sampleStage = 0;
    $('#sampleStyles').hidden = true;
    $('#checkoutPanel').hidden = true;
    $('#watermark').hidden = true;
    $('#resultCanvas').hidden = false;
    $('#resultCanvas').classList.toggle('photo', Boolean(photo));
    $('#resultImage').src = photo ? objectUrl : `assets/${pet}-grid.png`;
    $('#resultImage').alt = photo ? 'Your selected pet photo' : `Sample ${pet} sticker pack`;
    $('#resultLabel').textContent = photo ? 'YOUR PHOTO' : 'A LITTLE INSPIRATION';
    $('#resultTitle').textContent = photo ? 'A lovely place to start.' : 'Their face. Your new favorite reply.';
    $('#resultDescription').textContent = photo ? 'Your photo is selected and stays in this browser until generation is available.' : 'Nine little ways to say hello, thank you, or “I need a hug.”';
    $('#previewButton').innerHTML = 'Create my free preview <span>↗</span>';
    setProgress(0);
  }
  document.querySelectorAll('[data-pet]').forEach(button => button.addEventListener('click', () => {
    pet = button.dataset.pet;
    document.querySelectorAll('[data-pet]').forEach(item => {
      item.classList.toggle('active', item === button);
      item.setAttribute('aria-pressed', String(item === button));
    });
    resetResult();
  }));
  async function selectPhoto(file) {
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      $('#formStatus').textContent = 'Please choose a JPG, PNG or WebP photo.'; return;
    }
    if (file.size > 10 * 1024 * 1024) {
      $('#formStatus').textContent = 'Please choose a photo smaller than 10 MB.'; return;
    }
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.src = url;
    try { await image.decode(); } catch {
      URL.revokeObjectURL(url); $('#formStatus').textContent = 'We couldn’t read that image. Please try another photo.'; return;
    }
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    objectUrl = url; photo = file;
    $('#uploadBox strong').textContent = file.name;
    $('#formStatus').textContent = 'Photo selected. You can replace it anytime before creating a preview.';
    resetResult();
  }
  $('#photoInput').addEventListener('change', e => selectPhoto(e.target.files[0]));
  ['dragenter', 'dragover'].forEach(name => $('#uploadBox').addEventListener(name, e => { e.preventDefault(); $('#uploadBox').classList.add('dragging'); }));
  ['dragleave', 'drop'].forEach(name => $('#uploadBox').addEventListener(name, e => { e.preventDefault(); $('#uploadBox').classList.remove('dragging'); }));
  $('#uploadBox').addEventListener('drop', e => selectPhoto(e.dataTransfer.files[0]));
  function showSampleStyles() {
    sampleStage = 1; style = 'A';
    $('#resultCanvas').hidden = true; $('#checkoutPanel').hidden = true;
    $('#sampleStyles').hidden = false;
    $('#sampleStyles').innerHTML = styles.map((item, index) => `<button type="button" data-style="${item[0]}" aria-pressed="${index === 0}" class="${index === 0 ? 'active' : ''}">${art(pet,index)}<span>${item[0]} · ${item[1]}</span></button>`).join('');
    $('#sampleStyles').querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
      style = button.dataset.style;
      $('#sampleStyles').querySelectorAll('button').forEach(item => { item.classList.toggle('active', item === button); item.setAttribute('aria-pressed', String(item === button)); });
    }));
    $('#resultLabel').textContent = 'EXPLORE THE SAMPLE · FOUR STYLES';
    $('#resultTitle').textContent = 'Which one feels like them?';
    $('#resultDescription').textContent = 'These are the supplied sample illustrations. Your own preview will show your pet.';
    $('#previewButton').innerHTML = 'See a sample nine-sticker pack <span>↗</span>';
    setProgress(1);
  }
  $('#sampleButton').addEventListener('click', showSampleStyles);
  $('#previewButton').addEventListener('click', () => {
    if (sampleStage === 1) {
      sampleStage = 2;
      $('#sampleStyles').hidden = true; $('#resultCanvas').hidden = false;
      $('#resultCanvas').classList.remove('photo');
      $('#resultImage').src = `assets/${pet}-grid.png`;
      $('#resultImage').alt = `Supplied sample ${pet} nine-sticker pack`;
      $('#watermark').hidden = false; $('#checkoutPanel').hidden = false;
      $('#resultLabel').textContent = 'SAMPLE PACK · WATERMARKED PREVIEW';
      $('#resultTitle').textContent = 'Nine little reasons to smile.';
      $('#resultDescription').textContent = `You selected style ${style}. This is the supplied sample pack, shown to illustrate the final preview.`;
      $('#previewButton').innerHTML = 'Back to my photo <span>↗</span>';
      setProgress(2); return;
    }
    if (sampleStage === 2) { resetResult(); return; }
    if (!photo) { $('#photoInput').click(); return; }
    $('#formStatus').textContent = 'Custom previews are coming soon. Your photo has not been uploaded or charged.';
  });
  window.addEventListener('beforeunload', () => { if (objectUrl) URL.revokeObjectURL(objectUrl); });
})();
