// stocks.js - Frontend logic for Fractional Shares Manager

document.addEventListener('DOMContentLoaded', () => {
  // Initialize date inputs to today's date
  const todayStr = new Date().toISOString().split('T')[0];
  const divDateInput = document.getElementById('dividend_date');
  if (divDateInput) {
    divDateInput.value = todayStr;
  }

  // Setup button event listeners to open modals
  setupModalButton('btnDepositWithdraw', 'modalDepositWithdraw');
  setupModalButton('btnDividend', 'modalDividend');
  setupModalButton('btnAddTrade', 'modalAddTrade');
  setupModalButton('btnSellTrade', 'modalSellTrade');
  setupModalButton('btnSettlement', 'modalSettlement');

  // Load initial data
  loadAllData();

  // Auto-fill stock code when a stock name is chosen
  ['addStockName', 'sellStockName'].forEach(id => {
    const nameInput = document.getElementById(id);
    if (nameInput) {
      nameInput.addEventListener('input', (e) => {
        const selectedName = e.target.value.trim();
        const codeInputId = id === 'addStockName' ? 'formAddTrade' : 'formSellTrade';
        const codeInput = document.querySelector(`#${codeInputId} input[name="stock_code"]`);
        if (codeInput && window.stockNameCodeMap && window.stockNameCodeMap.has(selectedName)) {
          codeInput.value = window.stockNameCodeMap.get(selectedName);
        }
      });
    }
  });

  // Initialize max visible trades settings
  const maxVisibleInput = document.getElementById('maxVisibleTradesInput');
  if (maxVisibleInput) {
    maxVisibleInput.value = localStorage.getItem('stocks_max_visible_trades') || '';
    maxVisibleInput.addEventListener('input', (e) => {
      const val = e.target.value.trim();
      if (val === '' || parseInt(val) > 0) {
        localStorage.setItem('stocks_max_visible_trades', val);
        if (window.lastLoadedTrades) {
          renderTradesAndCost(window.lastLoadedTrades);
        }
      }
    });
  }
});

// Helper to open a modal
function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.removeAttribute('hidden');
    // Ensure date inputs default to today when opening
    const dateInput = modal.querySelector('input[type="date"]');
    if (dateInput && !dateInput.value) {
      dateInput.value = new Date().toISOString().split('T')[0];
    }
  }
}

// Helper to close a modal and reset its form
function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) {
    modal.setAttribute('hidden', '');
    const form = modal.querySelector('form');
    if (form) {
      form.reset();
      // Restore add trade modal specific elements if resetting it
      if (id === 'modalAddTrade') {
        toggleAddTradeAmount(false);
      }
    }
  }
}

// Helper to assign click event to modal buttons
function setupModalButton(btnId, modalId) {
  const btn = document.getElementById(btnId);
  if (btn) {
    btn.addEventListener('click', () => openModal(modalId));
  }
}

// Toggle "Amount" field visibility/requirements in the Add Trade modal
function toggleAddTradeAmount(isDividend) {
  const groupAmount = document.getElementById('groupAddTradeAmount');
  const infoDividend = document.getElementById('infoAddTradeDividend');
  const amountInput = document.getElementById('addTradeAmount');

  if (isDividend) {
    groupAmount.style.display = 'none';
    amountInput.removeAttribute('required');
    amountInput.value = '0';
    infoDividend.style.display = 'block';
  } else {
    groupAmount.style.display = 'block';
    amountInput.setAttribute('required', '');
    amountInput.value = '';
    infoDividend.style.display = 'none';
  }
}

// Generic Form Submit Handler
async function handleFormSubmit(event, url, modalId) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const data = {};

  formData.forEach((value, key) => {
    data[key] = value;
  });

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errData = await response.json();
      throw new Error(errData.error || window.T.save_failed);
    }

    closeModal(modalId);
    loadAllData();
  } catch (error) {
    alert(error.message);
  }
}

// Load and render all dashboard contents
async function loadAllData() {
  try {
    // 1. Load Summary (4-7)
    const summaryRes = await fetch('/stocks/api/summary');
    if (!summaryRes.ok) throw new Error(window.T.load_failed);
    const summaryData = await summaryRes.json();
    renderSummary(summaryData);

    // 2. Load Trades & Cost (4-6)
    const tradesRes = await fetch('/stocks/api/trades');
    if (!tradesRes.ok) throw new Error(window.T.load_failed);
    const tradesData = await tradesRes.json();
    window.lastLoadedTrades = tradesData;
    renderTradesAndCost(tradesData);
  } catch (error) {
    console.error(error);
  }
}

// Render 4-7: Investment and Profit Summary
function renderSummary(data) {
  document.getElementById('valInvested').innerText = formatCurrency(data.total_invested);
  document.getElementById('valDividends').innerText = formatCurrency(data.total_dividends);
  document.getElementById('valSellProfit').innerText = formatCurrency(data.total_sell_profit);
  document.getElementById('valBalance').innerText = formatCurrency(data.account_balance);

  const recentList = document.getElementById('recentFundsList');
  recentList.innerHTML = '';

  if (data.recent_funds && data.recent_funds.length > 0) {
    data.recent_funds.forEach(fund => {
      const item = document.createElement('div');
      item.className = 'recent-item';

      let typeStr = window.T[`type_${fund.type2}`] || fund.type2;
      let actionStr = window.T[`type_${fund.type1}`] || fund.type1;
      let prefix = fund.type1 === 'withdraw' ? '-' : '+';
      let displayAmount = `${prefix}${formatCurrency(fund.total_amount)}`;

      let detail = `${fund.date} [${actionStr} - ${typeStr}]`;
      if (fund.stock_name) {
        detail += ` (${fund.stock_name})`;
      }

      item.innerHTML = `
        <span>${detail} <strong>${displayAmount}</strong></span>
        <button class="btn-delete-item" onclick="deleteFundRecord(${fund.id})" title="Delete">&times;</button>
      `;
      recentList.appendChild(item);
    });
  } else {
    recentList.innerHTML = `<span class="text-muted">${window.T.no_recent_funds}</span>`;
  }
}

// Render 4-6: Trades Table (Pivot style columns) & Cost Table
function renderTradesAndCost(trades) {
  const tradesContainer = document.getElementById('tradesContainer');
  const costTbody = document.getElementById('costTbody');

  // Populate datalist of existing stock names
  const datalist = document.getElementById('existingStockNames');
  if (datalist) {
    datalist.innerHTML = '';
    const nameMap = new Map();
    trades.forEach(t => {
      if (t.stock_name) {
        nameMap.set(t.stock_name.trim(), t.stock_code ? t.stock_code.trim() : '');
      }
    });
    nameMap.forEach((code, name) => {
      const option = document.createElement('option');
      option.value = name;
      datalist.appendChild(option);
    });
    window.stockNameCodeMap = nameMap;
  }

  tradesContainer.innerHTML = '';
  costTbody.innerHTML = '';

  if (trades.length === 0) {
    tradesContainer.innerHTML = `
      <div class="text-center text-muted" style="padding:24px;width:100%;background:var(--card);border:1px solid var(--border);border-radius:var(--radius-lg)">
        ${window.T.no_trades}
      </div>
    `;
    costTbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted" style="padding:24px">${window.T.no_cost}</td>
      </tr>
    `;
    return;
  }

  // 1. Group trades by stock (stock_name + ' (' + stock_code + ')')
  const grouped = {};
  trades.forEach(t => {
    const key = `${t.stock_name} (${t.stock_code})`;
    if (!grouped[key]) {
      grouped[key] = {
        name: t.stock_name,
        code: t.stock_code,
        list: []
      };
    }
    grouped[key].list.push(t);
  });

  // Sort groups alphabetically by stock name
  const sortedKeys = Object.keys(grouped).sort((a, b) => {
    return grouped[a].name.localeCompare(grouped[b].name, 'zh-Hant');
  });

  // Render columns for each stock
  sortedKeys.forEach(key => {
    const group = grouped[key];
    // Sort transactions within stock by date descending
    group.list.sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id);

    const columnCard = document.createElement('div');
    columnCard.className = 'summary-card';
    columnCard.id = 'trade-col-' + group.code.trim();
    columnCard.style.minWidth = '300px';
    columnCard.style.flex = '0 0 auto';

    let headerHtml = `
      <div style="font-weight:700; font-size:14px; margin-bottom:12px; border-bottom:1px solid var(--border); padding-bottom:6px; display:flex; justify-content:space-between">
        <span>${group.name} (${group.code})</span>
      </div>
    `;

    let rowsHtml = '';
    group.list.forEach(t => {
      let price = t.shares > 0 ? (t.total_amount / t.shares) : 0;
      let priceText = t.type === 'stock_dividend' ? '—' : formatCurrency(price);
      let sharesPrefix = t.type === 'sell' ? '-' : '+';
      let colorClass = t.type === 'buy' ? 'color-buy' : (t.type === 'sell' ? 'color-sell' : 'color-dividend');
      let typeText = window.T[`type_${t.type}`] || t.type;

      rowsHtml += `
        <tr>
          <td>${t.date}</td>
          <td class="${colorClass}">${sharesPrefix}${t.shares} (${typeText})</td>
          <td>${priceText}</td>
          <td style="text-align:right">
            <button class="btn-delete-item" onclick="deleteTradeRecord(${t.id})" title="Delete">&times;</button>
          </td>
        </tr>
      `;
    });

    const maxVisibleVal = localStorage.getItem('stocks_max_visible_trades') || '';
    const maxVisible = parseInt(maxVisibleVal);
    let scrollStyle = '';
    if (maxVisible > 0 && group.list.length > maxVisible) {
      // 表頭高度約 36px，每行高度約 36px
      const maxHeight = 36 + maxVisible * 36;
      scrollStyle = `style="max-height: ${maxHeight}px;"`;
    }

    const tableHtml = `
      <div class="trades-table-wrapper" ${scrollStyle}>
        <table class="records-table" style="font-size:11.5px; width:100%">
          <thead>
            <tr>
              <th>Date</th>
              <th>Qty</th>
              <th>Price</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
      </div>
    `;

    columnCard.innerHTML = headerHtml + tableHtml;
    tradesContainer.appendChild(columnCard);
  });

  // 2. Calculate and render Holdings Cost Table (4-6 下半部)
  // Formula: Buy: accumulate shares & total_amount
  //          Stock Dividend: accumulate shares (amount is 0)
  //          Sell: subtract shares & (total_amount / 1.06)
  const costRows = [];
  sortedKeys.forEach(key => {
    const group = grouped[key];
    let totalShares = 0;
    let totalCost = 0;

    group.list.forEach(t => {
      if (t.type === 'buy') {
        totalShares += t.shares;
        totalCost += t.total_amount;
      } else if (t.type === 'stock_dividend') {
        totalShares += t.shares;
      } else if (t.type === 'sell') {
        totalShares -= t.shares;
        totalCost -= (t.total_amount / 1.06);
      }
    });

    // Check if there are active holdings
    if (totalShares > 0) {
      let avgCost = totalShares > 0 ? (totalCost / totalShares) : 0;
      costRows.push({
        name: group.name,
        code: group.code,
        shares: totalShares,
        cost: totalCost,
        avgCost: avgCost
      });
    }
  });

  let totalStockCost = 0;
  if (costRows.length > 0) {
    costRows.forEach(row => {
      totalStockCost += row.cost;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>
          <a href="javascript:void(0)" onclick="scrollToStockColumn('${row.code.trim()}')" style="color: var(--accent); text-decoration: none; font-weight: 700; cursor: pointer;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">
            ${row.name} (${row.code})
          </a>
        </td>
        <td>${row.shares}</td>
        <td>${formatCurrency(row.cost, true)}</td>
        <td>${formatCurrency(row.avgCost)}</td>
      `;
      costTbody.appendChild(tr);
    });
  } else {
    costTbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted" style="padding:24px">${window.T.no_cost}</td>
      </tr>
    `;
  }

  const valTotalStockCost = document.getElementById('valTotalStockCost');
  if (valTotalStockCost) {
    valTotalStockCost.innerText = formatCurrency(totalStockCost, true);
  }
}

// Delete action for a trade record
async function deleteTradeRecord(id) {
  if (!confirm(window.T.delete_failed.replace('：', '?'))) return;
  try {
    const res = await fetch(`/stocks/api/trades/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(window.T.delete_failed);
    loadAllData();
  } catch (error) {
    alert(error.message);
  }
}

// Delete action for a fund record
async function deleteFundRecord(id) {
  if (!confirm(window.T.delete_failed.replace('：', '?'))) return;
  try {
    const res = await fetch(`/stocks/api/funds/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(window.T.delete_failed);
    loadAllData();
  } catch (error) {
    alert(error.message);
  }
}

// Helper: Format number into currency display (rounding to 2 decimals if needed, or integers)
function formatCurrency(val, forceInt = false) {
  const num = parseFloat(val);
  if (isNaN(num)) return '$0';
  
  if (forceInt) {
    return '$' + Math.round(num).toLocaleString();
  }
  
  // Format as integer if no decimal part, otherwise round to 2 decimals
  if (num % 1 === 0) {
    return '$' + num.toLocaleString();
  }
  return '$' + num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Helper: Scroll horizontally to a specific stock column card and flash highlight it
function scrollToStockColumn(code) {
  const element = document.getElementById('trade-col-' + code);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
    
    // Smooth transition flash highlight
    element.style.transition = 'border-color 0.25s, background-color 0.25s';
    element.style.borderColor = 'var(--accent)';
    element.style.backgroundColor = 'var(--accent-dim)';
    
    setTimeout(() => {
      element.style.borderColor = '';
      element.style.backgroundColor = '';
    }, 1200);
  }
}
