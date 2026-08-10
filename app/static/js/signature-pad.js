(function () {
  function initSignaturePad(container) {
    const canvas = container.querySelector('canvas');
    const targetId = container.dataset.target;
    const hidden = document.getElementById(targetId);
    const clearButton = container.querySelector('[data-clear-signature]');
    if (!canvas || !hidden) return;

    const context = canvas.getContext('2d');
    let drawing = false;
    let hasInk = false;

    function resize() {
      const saved = hasInk ? canvas.toDataURL('image/png') : null;
      const ratio = Math.max(window.devicePixelRatio || 1, 1);
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(Math.floor(rect.width * ratio), 1);
      canvas.height = Math.max(Math.floor(rect.height * ratio), 1);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.lineWidth = 2.2;
      context.lineCap = 'round';
      context.lineJoin = 'round';
      context.strokeStyle = '#111827';
      if (saved) {
        const image = new Image();
        image.onload = () => context.drawImage(image, 0, 0, rect.width, rect.height);
        image.src = saved;
      }
    }

    function point(event) {
      const rect = canvas.getBoundingClientRect();
      return { x: event.clientX - rect.left, y: event.clientY - rect.top };
    }
    function start(event) {
      drawing = true;
      const current = point(event);
      context.beginPath();
      context.moveTo(current.x, current.y);
      canvas.setPointerCapture(event.pointerId);
    }
    function move(event) {
      if (!drawing) return;
      const current = point(event);
      context.lineTo(current.x, current.y);
      context.stroke();
      hasInk = true;
      event.preventDefault();
    }
    function end(event) {
      if (!drawing) return;
      drawing = false;
      if (hasInk) hidden.value = canvas.toDataURL('image/png');
      try { canvas.releasePointerCapture(event.pointerId); } catch (_) {}
    }
    function clear() {
      context.clearRect(0, 0, canvas.width, canvas.height);
      hidden.value = '';
      hasInk = false;
    }

    resize();
    window.addEventListener('resize', resize);
    canvas.addEventListener('pointerdown', start);
    canvas.addEventListener('pointermove', move);
    canvas.addEventListener('pointerup', end);
    canvas.addEventListener('pointercancel', end);
    clearButton && clearButton.addEventListener('click', clear);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-signature-pad]').forEach(initSignaturePad);
  });
})();
