(function () {
  const grid = document.querySelector('#catalog-grid');
  const cards = Array.from(document.querySelectorAll('.catalog-card[data-week]'));
  const search = document.querySelector('#guide-search');
  const filters = Array.from(document.querySelectorAll('.catalog-filter'));
  const resultCount = document.querySelector('#catalog-result-count');
  const showAll = document.querySelector('#show-all-guides');
  let activeFilter = 'All';
  let expanded = false;
  const requestedTopic = new URLSearchParams(window.location.search).get('topic');
  const topicFilters = {
    account: 'Account continuity',
    communication: 'Communication',
    scam: 'Scam defense',
    'home-network': 'Home network',
    device: 'Devices and accessibility',
    caregiver: 'Caregiver routines'
  };
  if (topicFilters[requestedTopic]) {
    activeFilter = topicFilters[requestedTopic];
    expanded = true;
  }

  function matches(card) {
    const query = search.value.trim().toLowerCase();
    const pillarMatch = activeFilter === 'All' || card.dataset.pillar === activeFilter;
    return pillarMatch && (!query || card.dataset.search.includes(query));
  }

  function update() {
    const matching = cards.filter(matches);
    cards.forEach(card => {
      const allowed = matches(card);
      const limited = !expanded && !search.value.trim() && activeFilter === 'All' && matching.indexOf(card) >= 6;
      card.hidden = !allowed || limited;
    });
    const visible = matching.filter(card => !card.hidden).length;
    resultCount.textContent = expanded || search.value.trim() || activeFilter !== 'All'
      ? `${matching.length} guide${matching.length === 1 ? '' : 's'} found.`
      : `Showing ${visible} recommended guides. Search or choose a topic for more.`;
    showAll.hidden = expanded || Boolean(search.value.trim()) || activeFilter !== 'All';
    grid.classList.toggle('catalog-collapsed', !expanded);
  }

  filters.forEach(button => button.addEventListener('click', () => {
    activeFilter = button.dataset.filter;
    filters.forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    update();
  }));
  filters.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === activeFilter)));
  search.addEventListener('input', update);
  showAll.addEventListener('click', () => { expanded = true; update(); });

  fetch('/assets/weekly-editorial.json', {cache: 'force-cache'})
    .then(response => response.ok ? response.json() : null)
    .then(payload => {
      if (!payload?.topics?.length) return;
      const today = new Intl.DateTimeFormat('en-CA', {timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit'}).format(new Date());
      const topic = payload.topics.find(item => item.starts_on <= today && today <= item.ends_on) || payload.topics[0];
      document.querySelector('#current-guide-title').textContent = `Week ${topic.week}: ${topic.title}`;
      document.querySelector('#current-guide-copy').textContent = topic.positioning;
      document.querySelector('#current-guide-link').href = topic.companion_path;
    })
    .catch(() => {});
  update();
}());
