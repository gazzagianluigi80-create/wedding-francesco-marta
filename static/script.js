// Upload con progress + preview
const form = document.getElementById('uploadForm');
if (form) {
  const input = document.getElementById('photos');
  const preview = document.getElementById('preview');
  input.addEventListener('change', () => {
    preview.innerHTML = '';
    [...input.files].slice(0, 12).forEach(f => {
      const img = document.createElement('img');
      img.src = URL.createObjectURL(f);
      preview.appendChild(img);
    });
  });
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const bar = document.getElementById('bar');
    const prog = document.getElementById('progress');
    const status = document.getElementById('status');
    prog.classList.remove('hidden');
    const xhr = new XMLHttpRequest();
    xhr.open('POST', form.action || window.location.pathname);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) bar.style.width = Math.round(ev.loaded / ev.total * 100) + '%';
    };
    xhr.onload = () => {
      try {
        const r = JSON.parse(xhr.responseText);
        if (r.ok) {
          status.textContent = `Grazie! ${r.count} foto caricate. 💛`;
          form.reset(); preview.innerHTML = ''; bar.style.width = '0';
          const a = document.createElement('p');
          a.innerHTML = '<a href="/gallery">Vedi la galleria →</a> · <a href="/upload">Carica altre foto</a>';
          status.appendChild(a);
        } else status.textContent = 'Errore durante il caricamento.';
      } catch { window.location.reload(); }
    };
    xhr.onerror = () => { status.textContent = 'Errore di rete. Riprova.'; };
    xhr.send(new FormData(form));
  });
}

// Galleria: polling ogni 10s + filtro + lightbox
let galleryTimer = null;
function initGallery(initialFilter) {
  const grid = document.getElementById('grid');
  if (!grid) return;
  const filter = document.getElementById('filter');
  const count = document.getElementById('count');
  const lb = document.getElementById('lightbox');
  if (initialFilter) filter.value = initialFilter;
  filter.addEventListener('change', load);

  async function load() {
    const q = filter.value ? '?momento=' + encodeURIComponent(filter.value) : '';
    let res;
    try {
      res = await fetch('/api/photos' + q);
    } catch {
      grid.innerHTML = '<p class="muted">Errore di rete. Ricarica la pagina.</p>';
      return;
    }
    if (res.status === 401) { window.location.href = '/upload?next=/gallery'; return; }
    if (!res.ok) { grid.innerHTML = '<p class="muted">Errore nel caricamento. Ricarica.</p>'; return; }
    let data;
    try {
      data = await res.json();
    } catch {
      window.location.href = '/upload?next=/gallery'; return;
    }
    count.textContent = data.total;
    grid.innerHTML = '';
    if (!data.photos.length) {
      grid.innerHTML = '<p class="muted">Nessuna foto ancora. Sii il primo a <a href="/upload">caricarne una</a>!</p>';
      return;
    }
    data.photos.forEach(p => {
      const fig = document.createElement('figure');
      const img = document.createElement('img');
      img.loading = 'lazy';
      img.src = '/uploads/' + encodeURIComponent(p.filename);
      img.alt = p.caption || 'Foto matrimonio';
      const cap = document.createElement('figcaption');
      cap.textContent = (p.name ? p.name + ' · ' : '') + (p.momento || '');
      fig.appendChild(img); fig.appendChild(cap);
      fig.onclick = () => {
        document.getElementById('lb-img').src = img.src;
        document.getElementById('lb-name').textContent = p.name || 'Anonimo';
        document.getElementById('lb-cap').textContent = p.caption || (p.momento || '');
        document.getElementById('lb-date').textContent = (p.datetime || '').replace('T', ' ');
        const del = document.getElementById('lb-del');
        if (del) del.action = '/admin/delete/' + encodeURIComponent(p.filename);
        lb.classList.remove('hidden');
      };
      grid.appendChild(fig);
    });
  }
  document.getElementById('close').onclick = () => lb.classList.add('hidden');
  lb.onclick = (e) => { if (e.target === lb) lb.classList.add('hidden'); };
  load();
  clearInterval(galleryTimer);
  galleryTimer = setInterval(load, 10000);
}
