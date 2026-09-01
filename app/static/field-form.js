(() => {
  const form = document.getElementById('fieldForm');
  if (!form) return;
  const draftKey = 'tsco-field-draft-v2';
  const DB_NAME = 'tsco-field-offline-v2';
  const STORE = 'submissions';
  const ignored = new Set(['photos', 'photo_kind']);
  const statusEl = document.getElementById('fieldSaveStatus');
  const queuePanel = document.getElementById('offlineQueuePanel');
  const receipt = document.getElementById('offlineReceipt');

  function openDb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, {keyPath:'id'});
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  async function allQueued() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }
  async function putQueued(item) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(item);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }
  async function removeQueued(id) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  const saveDraft = () => {
    const data = {};
    new FormData(form).forEach((value, key) => {
      if (!ignored.has(key) && typeof value === 'string') data[key] = value;
    });
    localStorage.setItem(draftKey, JSON.stringify(data));
    if (statusEl) statusEl.textContent = navigator.onLine ? 'Draft saved on this device.' : 'Offline draft saved on this device.';
  };
  const restoreDraft = () => {
    try {
      const data = JSON.parse(localStorage.getItem(draftKey) || '{}');
      Object.entries(data).forEach(([key, value]) => {
        const el = form.elements.namedItem(key);
        if (el && !el.value) el.value = value;
      });
    } catch (_) {}
  };
  restoreDraft();
  form.addEventListener('input', saveDraft);

  const client = document.getElementById('clientId');
  const filterOptions = (select) => {
    [...select.options].forEach((option, index) => {
      if (index === 0) return;
      option.hidden = client.value && option.dataset.client !== client.value;
    });
    if (select.selectedOptions[0]?.hidden) select.value = '';
  };
  client.addEventListener('change', () => {
    filterOptions(document.getElementById('quotationId'));
    filterOptions(document.getElementById('poId'));
    filterOptions(document.getElementById('existingAsset'));
  });

  document.getElementById('captureGps').addEventListener('click', () => {
    const status = document.getElementById('gpsStatus');
    if (!navigator.geolocation) { status.textContent = 'GPS not supported'; return; }
    status.textContent = 'Capturing high-accuracy GPS…';
    navigator.geolocation.getCurrentPosition((position) => {
      document.getElementById('gpsLat').value = position.coords.latitude.toFixed(7);
      document.getElementById('gpsLon').value = position.coords.longitude.toFixed(7);
      document.getElementById('gpsAcc').value = Math.round(position.coords.accuracy);
      status.textContent = `Captured ±${Math.round(position.coords.accuracy)} m`;
      saveDraft();
    }, (error) => status.textContent = `GPS failed: ${error.message}`, {enableHighAccuracy:true, timeout:20000, maximumAge:0});
  });

  document.getElementById('addPhoto').addEventListener('click', () => {
    const row = document.querySelector('.photo-row').cloneNode(true);
    row.querySelector('input').value = '';
    document.getElementById('photoRows').appendChild(row);
  });

  const localId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`);
  const offlineBarcode = () => `DMM-OFF-${new Date().toISOString().slice(0,10).replaceAll('-','')}-${Math.random().toString(36).slice(2,8).toUpperCase()}`;
  const fileToDataUrl = file => new Promise((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file);
  });
  async function collectPayload() {
    const fd = new FormData(form), fields = {};
    fd.forEach((v,k) => { if (typeof v === 'string' && k !== 'photo_kind') fields[k] = v; });
    const kinds = [...form.querySelectorAll('select[name=photo_kind]')].map(x => x.value);
    const inputs = [...form.querySelectorAll('input[name=photos]')];
    const photos = [];
    for (let i=0;i<inputs.length;i++) {
      const file = inputs[i].files?.[0];
      if (!file) continue;
      photos.push({kind:kinds[i] || 'General', name:file.name, type:file.type || 'image/jpeg', data:await fileToDataUrl(file)});
    }
    return {id:localId(), offline_barcode:offlineBarcode(), created_at:new Date().toISOString(), fields, photos, attempts:0};
  }
  function code39Svg(value) {
    const patterns = {'0':'nnnwwnwnn','1':'wnnwnnnnw','2':'nnwwnnnnw','3':'wnwwnnnnn','4':'nnnwwnnnw','5':'wnnwwnnnn','6':'nnwwwnnnn','7':'nnnwnnwnw','8':'wnnwnnwnn','9':'nnwwnnwnn','A':'wnnnnwnnw','B':'nnwnnwnnw','C':'wnwnnwnnn','D':'nnnnwwnnw','E':'wnnnwwnnn','F':'nnwnwwnnn','G':'nnnnnwwnw','H':'wnnnnwwnn','I':'nnwnnwwnn','J':'nnnnwwwnn','K':'wnnnnnnww','L':'nnwnnnnww','M':'wnwnnnnwn','N':'nnnnwnnww','O':'wnnnwnnwn','P':'nnwnwnnwn','Q':'nnnnnnwww','R':'wnnnnnwwn','S':'nnwnnnwwn','T':'nnnnwnwwn','U':'wwnnnnnnw','V':'nwwnnnnnw','W':'wwwnnnnnn','X':'nwnnwnnnw','Y':'wwnnwnnnn','Z':'nwwnwnnnn','-':'nwnnnnwnw','.':'wwnnnnwnn',' ':'nwwnnnwnn','*':'nwnnwnwnn'};
    const text = `*${value.toUpperCase().replace(/[^0-9A-Z.\- ]/g,'-')}*`; let x=10, bars='';
    for (const ch of text) { const pat=patterns[ch]||patterns['-']; for(let i=0;i<9;i++){const w=pat[i]==='w'?4:2;if(i%2===0)bars+=`<rect x="${x}" y="5" width="${w}" height="52"/>`;x+=w;}x+=2; }
    return `<svg viewBox="0 0 ${x+10} 65" width="100%" height="80" aria-label="Barcode ${value}">${bars}</svg>`;
  }
  function showOfflineReceipt(item) {
    receipt.hidden = false;
    receipt.innerHTML = `<span class="eyebrow">SAVED OFFLINE</span><h2>Local field record secured</h2><p>The official request number will be issued after synchronization. Use this barcode on the bottle now.</p><div style="max-width:620px;background:white;border:1px solid #dce5ec;border-radius:12px;padding:12px">${code39Svg(item.offline_barcode)}<div style="text-align:center;font-weight:900;letter-spacing:.08em">${item.offline_barcode}</div></div><div class="alert info">Keep the application installed and open it when a connection returns. The record and ${item.photos.length} photo(s) remain queued until the server confirms receipt.</div>`;
    receipt.scrollIntoView({behavior:'smooth'});
  }
  async function updateQueuePanel() {
    const items = await allQueued();
    if (!queuePanel) return;
    queuePanel.hidden = items.length === 0;
    if (items.length) queuePanel.innerHTML = `<b>${items.length} offline submission(s) waiting to synchronize.</b> ${navigator.onLine ? 'Synchronization will start automatically.' : 'Connect to the internet, then press Sync Offline Queue.'}`;
  }
  async function syncQueue() {
    if (!navigator.onLine) { if(statusEl)statusEl.textContent='Still offline — queued records remain safe.'; return; }
    const items = await allQueued();
    for (const item of items) {
      try {
        if(statusEl)statusEl.textContent=`Synchronizing ${item.offline_barcode}…`;
        const res = await fetch('/field/offline-sync', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(item)});
        if (res.status === 401 || res.status === 403) throw new Error('Sign in again before synchronization.');
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'Synchronization failed');
        await removeQueued(item.id);
        if(statusEl)statusEl.textContent=`Synchronized ${data.request_number} successfully.`;
      } catch (error) {
        item.attempts=(item.attempts||0)+1; item.last_error=error.message; await putQueued(item);
        if(statusEl)statusEl.textContent=`Queue retained: ${error.message}`;
        break;
      }
    }
    await updateQueuePanel();
  }

  form.addEventListener('submit', async event => {
    if (navigator.onLine) { localStorage.removeItem(draftKey); return; }
    event.preventDefault();
    const submit = document.getElementById('submitSample'); submit.disabled = true; submit.textContent='Saving offline…';
    try {
      const item = await collectPayload();
      await putQueued(item); localStorage.removeItem(draftKey); showOfflineReceipt(item); await updateQueuePanel();
      if(statusEl)statusEl.textContent='Saved offline. Waiting for server synchronization.';
    } catch (error) { alert(`Could not save offline: ${error.message}`); }
    finally { submit.disabled=false; submit.textContent='Submit and Generate Barcode'; }
  });
  document.getElementById('syncOfflineNow')?.addEventListener('click', syncQueue);
  window.addEventListener('online', syncQueue);
  updateQueuePanel().then(()=>{ if(navigator.onLine)syncQueue(); });
})();
