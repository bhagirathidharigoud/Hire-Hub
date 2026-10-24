document.addEventListener('submit', function (event) {
  const form = event.target.closest('form[data-confirm]');
  if (form && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
    return;
  }
  const searchForm = event.target.closest('.search-panel');
  if (searchForm) {
    const button = searchForm.querySelector('button[type="submit"]');
    if (button) {
      button.disabled = true;
      button.textContent = 'Searching…';
      button.setAttribute('aria-busy', 'true');
    }
  }
});
