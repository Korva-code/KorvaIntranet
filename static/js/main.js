/* ═══════════════════════════════════════════════════════════════
   INTRANET — JavaScript principal
   ═══════════════════════════════════════════════════════════════ */

/* ── Toast global — disponible en todos los formularios ──────
   Uso: mostrarToast('success' | 'danger' | 'warning' | 'info', 'Mensaje')
   ─────────────────────────────────────────────────────────── */
/* ── Modal de confirmación global ────────────────────────────
   Uso: confirmarAccion(mensaje, onConfirm)
        confirmarAccion(mensaje, onConfirm, { titulo, tipo, txtBtn })
   tipo: 'warning' (default) | 'danger' | 'primary' | 'success'
   ─────────────────────────────────────────────────────────── */
function confirmarAccion(mensaje, onConfirm, opciones) {
  const { titulo = 'Confirmar acción', tipo = 'warning', txtBtn = 'Confirmar' } = opciones || {};

  const estilos = {
    warning: { bg: '#fef3c7', color: '#d97706', icon: 'bi-exclamation-triangle-fill', btn: 'btn-warning'  },
    danger:  { bg: '#fee2e2', color: '#dc2626', icon: 'bi-x-octagon-fill',            btn: 'btn-danger'   },
    primary: { bg: '#dbeafe', color: '#2563eb', icon: 'bi-question-circle-fill',      btn: 'btn-primary'  },
    success: { bg: '#dcfce7', color: '#16a34a', icon: 'bi-check-circle-fill',         btn: 'btn-success'  },
  };
  const e = estilos[tipo] || estilos.warning;

  document.getElementById('mdcTitulo').textContent        = titulo;
  document.getElementById('mdcMensaje').textContent       = mensaje;
  document.getElementById('mdcIconWrap').style.background = e.bg;
  const ic = document.getElementById('mdcIcon');
  ic.className = `bi ${e.icon} fs-5`;
  ic.style.color = e.color;

  // Reemplazar botón para limpiar handlers anteriores
  const btnViejo = document.getElementById('mdcBtnOk');
  const btnNuevo = btnViejo.cloneNode(true);
  btnNuevo.className = `btn ${e.btn} btn-sm px-3`;
  btnNuevo.innerHTML = `<i class="bi bi-check-lg me-1"></i>${txtBtn}`;
  btnViejo.parentNode.replaceChild(btnNuevo, btnViejo);

  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modalConfirmar'));
  btnNuevo.addEventListener('click', () => { modal.hide(); onConfirm(); });
  modal.show();
}

function mostrarToast(tipo, msg) {
  const iconos = {
    success: 'bi-check-circle-fill',
    danger:  'bi-x-circle-fill',
    warning: 'bi-exclamation-triangle-fill',
    info:    'bi-info-circle-fill',
  };

  let cont = document.getElementById('intranetToastContainer');
  if (!cont) {
    cont = document.createElement('div');
    cont.id = 'intranetToastContainer';
    document.body.appendChild(cont);
  }

  const icono = iconos[tipo] || 'bi-info-circle-fill';
  const texto = String(msg ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const el = document.createElement('div');
  el.className = `intranet-toast toast-${tipo}`;
  el.innerHTML = `
    <i class="bi ${icono} intranet-toast-icon"></i>
    <span class="intranet-toast-msg">${texto}</span>
    <button class="intranet-toast-close" onclick="this.closest('.intranet-toast').remove()" title="Cerrar">
      <i class="bi bi-x-lg"></i>
    </button>`;

  cont.appendChild(el);

  // Auto-cerrar a los 4 s con animación de salida
  setTimeout(() => {
    el.classList.add('hiding');
    setTimeout(() => el.remove(), 300);
  }, 4000);
}

(function () {
  'use strict';

  // ── Sidebar toggle ────────────────────────────────────────────
  const sidebarToggleBtn = document.getElementById('sidebarToggle');
  const sidebar          = document.getElementById('sidebar');
  const overlay          = document.getElementById('sidebarOverlay');
  const mainContent      = document.getElementById('mainContent');
  const COLLAPSED_KEY    = 'sidebar_collapsed';
  const isMobile         = () => window.innerWidth < 992;

  function setSidebarState(collapsed) {
    if (isMobile()) {
      sidebar.classList.toggle('open', !collapsed);
      overlay.classList.toggle('active', !collapsed);
      document.body.classList.remove('sidebar-collapsed');
    } else {
      document.body.classList.toggle('sidebar-collapsed', collapsed);
      localStorage.setItem(COLLAPSED_KEY, collapsed ? '1' : '0');
    }
  }

  // Restore saved state on desktop
  if (!isMobile() && localStorage.getItem(COLLAPSED_KEY) === '1') {
    document.body.classList.add('sidebar-collapsed');
  }

  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener('click', () => {
      if (isMobile()) {
        const isOpen = sidebar.classList.contains('open');
        setSidebarState(isOpen);          // toggle: open→close or close→open
      } else {
        const collapsed = document.body.classList.contains('sidebar-collapsed');
        setSidebarState(!collapsed);
      }
    });
  }

  if (overlay) {
    overlay.addEventListener('click', () => setSidebarState(true));
  }

  window.addEventListener('resize', () => {
    if (!isMobile()) {
      sidebar.classList.remove('open');
      overlay.classList.remove('active');
      if (localStorage.getItem(COLLAPSED_KEY) === '1') {
        document.body.classList.add('sidebar-collapsed');
      }
    }
  });


  // ── Reloj y fecha en taskbar / breadcrumb ─────────────────────
  function pad(n) { return String(n).padStart(2, '0'); }

  function updateDateTime() {
    const now = new Date();
    const days   = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
    const months = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
    const dateStr = `${days[now.getDay()]}, ${pad(now.getDate())} ${months[now.getMonth()]} ${now.getFullYear()}`;
    const timeStr = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

    const dateEl = document.getElementById('currentDate');
    const timeEl = document.getElementById('currentTime');
    const yearEl = document.getElementById('currentYear');

    if (dateEl) dateEl.textContent = dateStr;
    if (timeEl) timeEl.textContent = timeStr;
    if (yearEl) yearEl.textContent = now.getFullYear();
  }

  updateDateTime();
  setInterval(updateDateTime, 1000);


  // ── Auto-dismiss flash alerts ──────────────────────────────────
  document.querySelectorAll('.alert.fade.show').forEach(el => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });


  // ── Tooltip initialization ────────────────────────────────────
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el, { placement: 'right' });
  });

})();
