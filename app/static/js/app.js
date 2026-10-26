async function apiRequest(url, options) {
  const response = await fetch(url, {
    credentials: 'same-origin',
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options && options.headers),
    },
  });
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error(`The server returned an invalid response (${response.status}).`);
  }
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || `Request failed (${response.status}).`);
  }
  return payload;
}

function showFormMessage(form, message, type) {
  let alert = form.querySelector('[data-api-message]');
  if (!alert) {
    alert = document.createElement('div');
    alert.dataset.apiMessage = '';
    alert.setAttribute('role', 'alert');
    form.prepend(alert);
  }
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
}

function jobCard(job, detailUrl, savedJobUrl, isCandidate) {
  const column = document.createElement('div');
  column.className = 'col';
  const article = document.createElement('article');
  article.className = 'card job-card';
  const body = document.createElement('div');
  body.className = 'card-body';

  const heading = document.createElement('div');
  heading.className = 'd-flex justify-content-between align-items-start w-100 gap-2';
  const titleGroup = document.createElement('div');
  const title = document.createElement('h2');
  title.className = 'job-title';
  title.textContent = job.title || 'Untitled role';
  const company = document.createElement('p');
  company.className = 'job-company';
  company.textContent = job.company_name || 'Company';
  titleGroup.append(title, company);
  heading.append(titleGroup);
  if (job.match) {
    const match = document.createElement('span');
    match.className = 'status-pill';
    match.textContent = `${job.match.score}% match`;
    heading.append(match);
  }
  body.append(heading);

  const meta = document.createElement('div');
  meta.className = 'job-meta';
  [job.location || 'Location not specified', job.work_mode, job.employment_type]
    .filter(Boolean)
    .forEach((value) => {
      const item = document.createElement('span');
      item.textContent = value.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
      meta.append(item);
    });
  body.append(meta);

  if (job.salary_min || job.salary_max) {
    const salary = document.createElement('p');
    salary.className = 'job-company';
    salary.textContent = `${job.salary_min || '—'} – ${job.salary_max || '—'} salary`;
    body.append(salary);
  }

  const skills = document.createElement('ul');
  skills.className = 'skill-list';
  (job.skills || []).slice(0, 4).forEach((value) => {
    const item = document.createElement('li');
    item.textContent = value;
    skills.append(item);
  });
  body.append(skills);

  const actions = document.createElement('div');
  actions.className = 'job-card-actions';
  const detailLink = document.createElement('a');
  detailLink.className = 'btn btn-primary btn-sm';
  detailLink.href = detailUrl.replace('__JOB_ID__', encodeURIComponent(job._id));
  detailLink.textContent = 'View details';
  actions.append(detailLink);
  if (isCandidate) {
    const form = document.createElement('form');
    form.dataset.apiUrl = savedJobUrl.replace('__JOB_ID__', encodeURIComponent(job._id));
    form.dataset.apiMethod = 'PUT';
    const button = document.createElement('button');
    button.type = 'submit';
    button.className = 'btn btn-outline-primary btn-sm save-button';
    button.textContent = 'Save';
    form.append(button);
    actions.append(form);
  }
  body.append(actions);
  article.append(body);
  column.append(article);
  return column;
}

async function loadJobSearch(form) {
  const result = document.getElementById('job-search-results');
  if (!result) return;
  const params = new URLSearchParams(new FormData(form));
  const sort = params.get('sort') || 'recent';
  params.delete('sort');
  params.delete('page');
  const query = params.toString();
  const url = `${form.dataset.apiSearch}${query ? `?${query}` : ''}`;
  result.setAttribute('aria-busy', 'true');
  try {
    const payload = await apiRequest(url);
    const jobs = payload.data || [];
    if (sort === 'salary_high') jobs.sort((a, b) => (b.salary_max || 0) - (a.salary_max || 0));
    if (sort === 'salary_low') jobs.sort((a, b) => (a.salary_min || 0) - (b.salary_min || 0));
    else if (sort === 'recent') jobs.sort((a, b) => (b.posted_date || b.created_at || '').localeCompare(a.posted_date || a.created_at || ''));

    const summary = document.createElement('div');
    summary.className = 'results-bar';
    const count = document.createElement('p');
    count.className = 'mb-0';
    const strongCount = document.createElement('strong');
    strongCount.textContent = String(jobs.length);
    count.append(strongCount, ` ${jobs.length === 1 ? 'role' : 'roles'}${query ? ' match your search' : ''}`);
    summary.append(count);

    const grid = document.createElement('div');
    grid.className = 'row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3';
    const detailUrl = result.dataset.jobDetailUrl;
    const savedJobUrl = result.dataset.savedJobUrl;
    const isCandidate = result.dataset.candidate === 'true';
    jobs.forEach((job) => grid.append(jobCard(job, detailUrl, savedJobUrl, isCandidate)));

    const empty = document.createElement('div');
    empty.className = 'empty-state';
    const emptyTitle = document.createElement('h2');
    emptyTitle.textContent = 'No jobs match your search';
    const emptyText = document.createElement('p');
    emptyText.textContent = 'Try changing your search or clearing filters to see more roles.';
    empty.append(emptyTitle, emptyText);
    result.replaceChildren(summary, jobs.length ? grid : empty);
    const current = new URL(window.location.href);
    current.search = new URLSearchParams(new FormData(form)).toString();
    window.history.replaceState({}, '', current);
  } catch (error) {
    showFormMessage(form, error.message, 'danger');
  } finally {
    result.removeAttribute('aria-busy');
  }
}

document.addEventListener('submit', async (event) => {
  const form = event.target.closest('form');
  if (!form) return;
  if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
    return;
  }
  if (form.dataset.apiSearch) {
    event.preventDefault();
    await loadJobSearch(form);
    return;
  }
  if (!form.dataset.apiUrl) return;

  event.preventDefault();
  const submitButton = form.querySelector('button[type="submit"]');
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.setAttribute('aria-busy', 'true');
  }
  try {
    const payload = await apiRequest(form.dataset.apiUrl, {
      method: form.dataset.apiMethod || 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(Object.fromEntries(new FormData(form).entries())),
    });
    if (form.dataset.apiRedirect) {
      window.location.assign(form.dataset.apiRedirect);
    } else if (payload.data && typeof payload.data.saved === 'boolean' && submitButton) {
      submitButton.textContent = payload.data.saved ? 'Unsave' : 'Save';
      showFormMessage(form, payload.data.saved ? 'Job saved.' : 'Job removed from your saved list.', 'success');
    } else {
      showFormMessage(form, payload.message || 'Saved successfully.', 'success');
    }
  } catch (error) {
    showFormMessage(form, error.message, 'danger');
  } finally {
    if (submitButton) {
      submitButton.disabled = false;
      submitButton.removeAttribute('aria-busy');
    }
  }
});

document.addEventListener('change', (event) => {
  if (event.target.matches('#sort')) {
    event.target.form.requestSubmit();
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const searchForm = document.querySelector('form[data-api-search].search-panel');
  if (searchForm) loadJobSearch(searchForm);
});
