/**
 * FinTrack UPI Dashboard Controller
 * Real-time analytics, Chart.js integrations, live SMS/Email simulator, and ledger controller.
 */

const state = {
  page: 1,
  limit: 15,
  sortBy: 'transaction_date',
  order: 'DESC',
  search: '',
  category: '',
  type: '',
  startDate: '',
  endDate: '',
  charts: {
    category: null,
    monthly: null
  }
};

const CATEGORY_ICONS = {
  'Food & Dining': '🍔',
  'Groceries & Essentials': '🛒',
  'Shopping & E-Commerce': '🛍️',
  'Travel & Commute': '🚗',
  'Health & Medical': '🏥',
  'Bills & Utilities': '⚡',
  'Entertainment & OTT': '🎬',
  'Investments & Finance': '📈',
  'Salary / Income': '💼',
  'Transfers & Personal': '💸',
  'Other': '🏷️'
};

const CATEGORY_COLORS = [
  '#6366F1', '#EC4899', '#10B981', '#F59E0B', '#3B82F6', 
  '#8B5CF6', '#14B8A6', '#F97316', '#06B6D4', '#84CC16'
];

const PRESETS = {
  salary: `Dear Rohit Sharma, 
This is an automated notification from Corporate Payroll Services. Your salary for the pay period 01-Jul-2026 to 31-Jul-2026 has been successfully processed and credited via Electronic Fund Transfer (EFT). 

--- TRANSACTION SUMMARY ---
Employee Name: Rohit Sharma
Payment Mode: Direct Deposit / NeFT
Value Date: 31-Jul-2026
Transaction Reference: HDFCR5202607310084321
Status: CREDITED 

--- DESTINATION ACCOUNT ---
Bank Name: HDFC Bank Ltd
Account Number: *******5432

--- DISBURSEMENT BREAKDOWN ---
Gross Earnings: ₹1,25,000.00
Total Deductions (Tax & Statutory): ₹18,400.00
Net Amount Deposited: ₹1,06,600.00 

Sincerely,
Global Payroll & HR Operations
TechCorp India Private Limited`,

  reliance: `Transaction Alert: Spend of INR 3,499.00 on your Card ending 1234 at RELIANCE DIGITAL - VAPI on 18-Aug-2026 04:38 AM. Avl Bal: INR 54,200.00. Ref No: REL88349210.`,

  amazon: `Alert: Debit Transaction for Account ******1234
Amount: INR 2,499.00
Merchant Name: AMZN Mktp US
Date & Time: 18-Aug-2026 04:25 AM
Reference: AMZ987654321`,

  swiggy: `Dear UPI user, A/c *2263 debited by Rs. 385.00 on 14-Feb-2025 13:20:00 transfer to Swiggy Ref: 504512345678.`,

  blinkit: `Your A/c ending 1722 is debited for Rs 1250.00 on 15-Feb-2025 at Blinkit Grocery. UPI txn id 504612349999.`,

  uber: `Rs. 450.00 debited from your account on 16-02-2025 18:00:00 at Uber India. UPI/504789123456.`,

  netflix: `INR 250.00 has been debited from your A/c no. XX172263 on 07-02-2025 19:30:20 at PUR/Netflix Subscription/1029384756.`
};

// Initialize Dashboard on DOM Load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  loadCategories();
  loadStats();
  loadTransactions();

  // Keyboard shortcut: Focus search on "/"
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
      e.preventDefault();
      document.getElementById('searchInput').focus();
    }
  });
});

// Format Indian Rupee currency with commas
function fmt(num) {
  if (num === null || num === undefined) return '0.00';
  return Number(num).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

// Fetch and Render Summary Statistics & Smart AI Insights
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (!data.success) return;

    const s = data.stats;

    // 1. Metric Cards
    document.getElementById('statTotalDebit').textContent = '₹' + fmt(s.total_debit);
    document.getElementById('statTotalCredit').textContent = '₹' + fmt(s.total_credit);
    
    const netEl = document.getElementById('statNetBalance');
    const isPos = s.net_balance >= 0;
    netEl.textContent = (isPos ? '+ ₹' : '- ₹') + fmt(Math.abs(s.net_balance));
    netEl.className = 'metric-value ' + (isPos ? 'credit' : 'debit');

    document.getElementById('statDebitCount').textContent = (s.debit_count || 0) + ' Debits';
    document.getElementById('statCreditCount').textContent = (s.credit_count || 0) + ' Credits';
    document.getElementById('statAvgDebit').textContent = 'Avg ₹' + fmt(s.avg_debit) + ' / txn';
    document.getElementById('statSavingsRate').textContent = (s.savings_rate || 0) + '% Retained';

    document.getElementById('statTopCategory').textContent = s.top_category || 'None';
    document.getElementById('statTopCatPct').textContent = (s.top_cat_pct || 0) + '% of spent';
    document.getElementById('statTopCatAmount').textContent = '₹' + fmt(s.top_cat_amount);
    document.getElementById('statTotalCount').textContent = s.total_count || 0;

    // 2. Smart AI Insight Banner
    if (s.smart_insight) {
      document.getElementById('smartInsightText').textContent = s.smart_insight;
    }
    if (s.health_score !== undefined) {
      document.getElementById('healthScoreVal').textContent = s.health_score;
      const badge = document.getElementById('healthStatusBadge');
      if (s.health_score >= 80) {
        badge.textContent = 'Optimal';
        badge.className = 'health-status-badge positive';
      } else if (s.health_score >= 50) {
        badge.textContent = 'Healthy';
        badge.className = 'health-status-badge positive';
      } else {
        badge.textContent = 'Attention';
        badge.className = 'health-status-badge warning';
      }
    }

    // 3. Render Visual Charts
    renderCategoryChart(s.category_breakdown);
    renderMonthlyChart(s.monthly_trends);

  } catch (err) {
    console.error('Failed to load summary stats:', err);
  }
}

// Render Doughnut Chart (Expense by Category)
function renderCategoryChart(breakdown) {
  const ctx = document.getElementById('categoryChart');
  const emptyState = document.getElementById('noChartData');
  if (!ctx) return;

  if (!breakdown || breakdown.length === 0) {
    ctx.style.display = 'none';
    if (emptyState) emptyState.style.display = 'flex';
    return;
  }

  ctx.style.display = 'block';
  if (emptyState) emptyState.style.display = 'none';

  if (state.charts.category) {
    state.charts.category.destroy();
  }

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const textColor = isDark ? '#94a3b8' : '#475569';

  state.charts.category = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: breakdown.map(b => b.category),
      datasets: [{
        data: breakdown.map(b => b.amount),
        backgroundColor: CATEGORY_COLORS.slice(0, breakdown.length),
        borderColor: isDark ? '#111827' : '#ffffff',
        borderWidth: 3,
        hoverOffset: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: textColor,
            font: { family: 'Inter', size: 12, weight: '500' },
            padding: 12,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        },
        tooltip: {
          backgroundColor: isDark ? '#1e293b' : '#0f172a',
          titleColor: '#fff',
          bodyColor: '#cbd5e1',
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: (ctx) => `  ${ctx.label}: ₹${fmt(ctx.raw)}`
          }
        }
      }
    }
  });
}

// Render Monthly Trends Bar Chart (Credits vs Debits)
function renderMonthlyChart(trends) {
  const ctx = document.getElementById('monthlyChart');
  if (!ctx) return;

  if (state.charts.monthly) {
    state.charts.monthly.destroy();
  }

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';
  const textColor = isDark ? '#94a3b8' : '#475569';

  const labels = trends && trends.length > 0 ? trends.map(t => t.month) : ['Current'];
  const debits = trends && trends.length > 0 ? trends.map(t => t.debit) : [0];
  const credits = trends && trends.length > 0 ? trends.map(t => t.credit) : [0];

  state.charts.monthly = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Debits (Spent)',
          data: debits,
          backgroundColor: 'rgba(244, 63, 94, 0.85)',
          borderRadius: 6,
          borderSkipped: false
        },
        {
          label: 'Credits (Income)',
          data: credits,
          backgroundColor: 'rgba(16, 185, 129, 0.85)',
          borderRadius: 6,
          borderSkipped: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: isDark ? '#1e293b' : '#0f172a',
          titleColor: '#fff',
          bodyColor: '#cbd5e1',
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: (ctx) => `  ${ctx.dataset.label}: ₹${fmt(ctx.raw)}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { family: 'Inter', size: 11 } }
        },
        y: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { family: 'Inter', size: 11 },
            callback: (val) => '₹' + (val >= 1000 ? (val / 1000) + 'k' : val)
          }
        }
      }
    }
  });
}

// Fetch Paginated Ledger Transactions
async function loadTransactions() {
  const tbody = document.getElementById('transactionsTbody');
  tbody.innerHTML = `<tr><td colspan="7" class="loading-state"><div class="spinner"></div><span>Updating ledger...</span></td></tr>`;

  try {
    const params = new URLSearchParams({
      page: state.page,
      limit: state.limit,
      sort_by: state.sortBy,
      order: state.order,
      search: state.search,
      category: state.category,
      type: state.type,
      start_date: state.startDate,
      end_date: state.endDate,
      paginated: '1'
    });

    const res = await fetch(`/api/transactions?${params.toString()}`);
    const data = await res.json();

    if (data.success) {
      renderTable(data.data);
      renderPagination(data.pagination);
      document.getElementById('tableRecordCountBadge').textContent = `${data.pagination.total} Record${data.pagination.total === 1 ? '' : 's'}`;
    } else {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="color:var(--color-debit); padding:30px;">${data.error || 'Failed to load records'}</td></tr>`;
    }
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="color:var(--color-debit); padding:30px;">Error connecting to server.</td></tr>`;
  }
}

// Render Table Rows
function renderTable(txns) {
  const tbody = document.getElementById('transactionsTbody');
  tbody.innerHTML = '';

  if (!txns || txns.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="text-center" style="padding:40px; color:var(--text-tertiary);">No transactions found matching criteria.</td></tr>`;
    return;
  }

  txns.forEach(t => {
    const tr = document.createElement('tr');
    const icon = CATEGORY_ICONS[t.category] || '🏷️';
    const isDebit = t.transaction_type === 'Debit';
    const sign = isDebit ? '- ₹' : '+ ₹';
    const dateFormatted = formatDateString(t.transaction_date);

    tr.innerHTML = `
      <td>${dateFormatted}</td>
      <td class="cell-merchant">
        ${escapeHtml(t.merchant)}
        ${t.reference_id ? `<div class="ref-sub" onclick="copyRef('${escapeHtml(t.reference_id)}')" title="Click to copy Reference ID">Ref: ${escapeHtml(t.reference_id)}</div>` : ''}
      </td>
      <td>
        <span class="cell-cat-badge">
          <span>${icon}</span>
          <span>${escapeHtml(t.category)}</span>
        </span>
      </td>
      <td class="cell-amount text-right ${isDebit ? 'debit' : 'credit'}">
        ${sign}${fmt(t.amount)}
      </td>
      <td>
        <span class="cell-type ${isDebit ? 'debit' : 'credit'}">${t.transaction_type}</span>
      </td>
      <td class="cell-source">${t.source || 'Email'}</td>
      <td class="text-center">
        <button class="btn-delete" onclick="deleteTransaction(${t.id}, '${escapeHtml(t.merchant)}', ${t.amount})" title="Delete transaction">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function formatDateString(dtStr) {
  if (!dtStr) return '--';
  try {
    const d = new Date(dtStr.replace(' ', 'T'));
    if (isNaN(d.getTime())) return dtStr;
    return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) + ', ' +
           d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }).toLowerCase();
  } catch {
    return dtStr;
  }
}

function renderPagination(p) {
  const info = document.getElementById('paginationInfo');
  const indicator = document.getElementById('pageIndicator');
  const prevBtn = document.getElementById('prevPageBtn');
  const nextBtn = document.getElementById('nextPageBtn');

  const start = p.total === 0 ? 0 : (p.page - 1) * p.limit + 1;
  const end = Math.min(p.page * p.limit, p.total);
  info.textContent = `Showing records ${start} to ${end} of ${p.total}`;
  indicator.textContent = `Page ${p.page} of ${p.total_pages}`;

  prevBtn.disabled = p.page <= 1;
  nextBtn.disabled = p.page >= p.total_pages;
}

function prevPage() {
  if (state.page > 1) {
    state.page--;
    loadTransactions();
  }
}

function nextPage() {
  state.page++;
  loadTransactions();
}

// Sorting
function handleSort(col) {
  if (state.sortBy === col) {
    state.order = state.order === 'ASC' ? 'DESC' : 'ASC';
  } else {
    state.sortBy = col;
    state.order = 'DESC';
  }
  updateSortIndicators();
  state.page = 1;
  loadTransactions();
}

function updateSortIndicators() {
  ['thDate', 'thMerchant', 'thCategory', 'thAmount'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const arrow = el.querySelector('.sort-arrow');
    if (!arrow) return;
    
    const colMap = { thDate: 'transaction_date', thMerchant: 'merchant', thCategory: 'category', thAmount: 'amount' };
    if (state.sortBy === colMap[id]) {
      arrow.textContent = state.order === 'ASC' ? '▲' : '▼';
    } else {
      arrow.textContent = '';
    }
  });
}

// Search with Debounce
let searchTimeout = null;
function handleSearch(val) {
  clearTimeout(searchTimeout);
  document.getElementById('clearSearchBtn').style.display = val ? 'block' : 'none';
  searchTimeout = setTimeout(() => {
    state.search = val.trim();
    state.page = 1;
    loadTransactions();
  }, 300);
}

function clearSearch() {
  const input = document.getElementById('searchInput');
  input.value = '';
  document.getElementById('clearSearchBtn').style.display = 'none';
  state.search = '';
  state.page = 1;
  loadTransactions();
}

// Quick Type Filter Pills
function setQuickTypeFilter(type, btn) {
  document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  state.type = type;
  state.page = 1;
  loadTransactions();
}

function handleCategoryFilter(cat) {
  state.category = cat;
  state.page = 1;
  loadTransactions();
}

function clearAllFilters() {
  state.search = '';
  state.category = '';
  state.type = '';
  state.page = 1;

  document.getElementById('searchInput').value = '';
  document.getElementById('clearSearchBtn').style.display = 'none';
  document.getElementById('categoryFilter').value = '';
  
  document.querySelectorAll('.filter-pills .pill').forEach(p => p.classList.remove('active'));
  document.querySelector('.filter-pills .pill[data-filter=""]').classList.add('active');

  loadTransactions();
  toast('Filters reset', 'info');
}

// Categories Fetch
async function loadCategories() {
  try {
    const res = await fetch('/api/categories');
    const data = await res.json();
    if (!data.success) return;

    const filterSel = document.getElementById('categoryFilter');
    const modalSel = document.getElementById('modalCategory');

    data.categories.forEach(cat => {
      const opt = document.createElement('option');
      opt.value = cat;
      opt.textContent = `${CATEGORY_ICONS[cat] || '🏷️'} ${cat}`;
      filterSel.appendChild(opt);

      const modalOpt = document.createElement('option');
      modalOpt.value = cat;
      modalOpt.textContent = cat;
      modalSel.appendChild(modalOpt);
    });
  } catch (err) {
    console.error('Error loading categories:', err);
  }
}

// Delete Transaction
async function deleteTransaction(id, merchant, amount) {
  if (!confirm(`Delete transaction:\n${merchant} - ₹${fmt(amount)}?`)) return;

  try {
    const res = await fetch(`/api/transactions/${id}`, { method: 'DELETE' });
    const data = await res.json();

    if (data.success) {
      toast('Transaction deleted successfully', 'success');
      loadStats();
      loadTransactions();
    } else {
      toast(data.error || 'Failed to delete transaction', 'error');
    }
  } catch {
    toast('Server error deleting transaction', 'error');
  }
}

// Live IMAP Email & SMS Sync Trigger
async function triggerSync(source = 'email') {
  const syncBtn = document.getElementById('syncBtn');
  const syncText = document.getElementById('syncBtnText');
  
  syncBtn.classList.add('syncing');
  syncText.textContent = 'Syncing...';
  toast('Connecting to Gmail inbox & fetching transaction alerts...', 'info');

  try {
    const res = await fetch('/api/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source })
    });
    const data = await res.json();

    syncBtn.classList.remove('syncing');
    syncText.textContent = 'Refresh & Sync';

    if (data.success) {
      const added = data.results.email_saved || 0;
      if (added > 0) {
        toast(`Sync complete! Added ${added} new transaction${added === 1 ? '' : 's'}.`, 'success');
      } else {
        toast('Inbox up to date. No new unrecorded transactions.', 'info');
      }
      loadStats();
      loadTransactions();
    } else {
      toast(data.error || 'Sync encountered errors', 'error');
    }
  } catch {
    syncBtn.classList.remove('syncing');
    syncText.textContent = 'Refresh & Sync';
    toast('Error connecting to email sync service', 'error');
  }
}

// SMS / Alert Simulator Preset Loader
function loadPreset(key) {
  const text = PRESETS[key] || '';
  document.getElementById('smsInput').value = text;
  simulateParse(false);
}

function clearParser() {
  document.getElementById('smsInput').value = '';
  document.getElementById('parseResultBanner').style.display = 'none';
}

// Simulate / Test Parse SMS Text
async function simulateParse(saveToDb = false) {
  const text = document.getElementById('smsInput').value.trim();
  if (!text) {
    toast('Please enter or paste an alert message', 'error');
    return;
  }

  try {
    const res = await fetch('/api/parse-sms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, save: saveToDb })
    });
    const data = await res.json();

    if (data.success && data.parsed) {
      const p = data.parsed;
      const banner = document.getElementById('parseResultBanner');
      banner.style.display = 'block';

      document.getElementById('parsedAmount').textContent = '₹' + fmt(p.amount);
      document.getElementById('parsedMerchant').textContent = p.merchant || 'Unknown';
      document.getElementById('parsedCategory').textContent = p.category || 'Other';
      document.getElementById('parsedDate').textContent = p.transaction_date || '--';
      document.getElementById('parsedRef').textContent = p.reference_id || 'N/A';
      document.getElementById('parsedAccount').textContent = p.account || 'N/A';
      
      const badge = document.getElementById('parsedTypeBadge');
      badge.textContent = p.transaction_type;
      badge.className = 'badge ' + (p.transaction_type === 'Credit' ? 'badge-credit' : 'badge-debit');

      if (saveToDb) {
        if (data.saved) {
          toast(`Saved: ${p.merchant} (₹${fmt(p.amount)})`, 'success');
          loadStats();
          loadTransactions();
        } else {
          toast(data.save_message || 'Duplicate transaction skipped', 'info');
        }
      }
    } else {
      toast(data.error || 'Could not parse message', 'error');
    }
  } catch {
    toast('Server error during parsing', 'error');
  }
}

// Add Manual Transaction Modal
function openAddModal() {
  document.getElementById('addTransactionModal').classList.add('active');
  document.getElementById('modalMerchant').focus();
}

function closeAddModal() {
  document.getElementById('addTransactionModal').classList.remove('active');
  document.getElementById('addTransactionForm').reset();
}

async function handleAddTransaction(e) {
  e.preventDefault();
  const payload = {
    merchant: document.getElementById('modalMerchant').value.trim(),
    amount: parseFloat(document.getElementById('modalAmount').value),
    transaction_type: document.getElementById('modalType').value,
    category: document.getElementById('modalCategory').value,
    transaction_date: document.getElementById('modalDate').value.trim() || undefined,
    reference_id: document.getElementById('modalRef').value.trim() || undefined,
    source: 'Manual'
  };

  try {
    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (data.success) {
      toast('Transaction saved successfully', 'success');
      closeAddModal();
      loadStats();
      loadTransactions();
    } else {
      toast(data.error || 'Failed to save', 'error');
    }
  } catch {
    toast('Server error saving transaction', 'error');
  }
}

// Copy Reference ID with Tooltip Toast
function copyRef(ref) {
  navigator.clipboard.writeText(ref).then(() => {
    toast(`Copied Reference: ${ref}`, 'info');
  }).catch(() => {
    toast(`Ref: ${ref}`, 'info');
  });
}

// Toast Notifications
function toast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const div = document.createElement('div');
  div.className = `toast ${type}`;
  div.textContent = msg;
  container.appendChild(div);

  setTimeout(() => {
    div.style.opacity = '0';
    div.style.transform = 'translateY(10px)';
    div.style.transition = 'all 0.3s ease';
    setTimeout(() => div.remove(), 300);
  }, 3500);
}

// Theme Controller (Dark / Light)
function initTheme() {
  const saved = localStorage.getItem('fintrack_theme') || 'dark';
  setTheme(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  setTheme(next);
}

function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('fintrack_theme', theme);

  const isDark = theme === 'dark';
  document.getElementById('themeLabel').textContent = isDark ? 'Light Mode' : 'Dark Mode';
  document.querySelector('.icon-moon').style.display = isDark ? 'inline' : 'none';
  document.querySelector('.icon-sun').style.display = isDark ? 'none' : 'inline';

  // Redraw charts with updated theme palette
  loadStats();
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (window.innerWidth <= 860) {
    sidebar.classList.toggle('open');
  } else {
    sidebar.classList.toggle('collapsed');
    document.body.classList.toggle('sidebar-collapsed');
    setTimeout(() => window.dispatchEvent(new Event('resize')), 260);
  }
}

function scrollToSection(id) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[m]);
}
