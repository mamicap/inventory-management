<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.subtitle') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-header">
          <label for="restock-budget" class="budget-label">{{ t('restocking.budgetLabel') }}</label>
          <div class="budget-amount">{{ formatMoney(budget) }}</div>
        </div>
        <input
          id="restock-budget"
          v-model.number="budget"
          type="range"
          min="0"
          :max="maxBudget"
          :step="budgetStep"
          class="budget-slider"
          :disabled="maxBudget === 0"
        />
        <div class="budget-scale">
          <span>{{ formatMoney(0) }}</span>
          <span>{{ formatMoney(maxBudget) }}</span>
        </div>

        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-label">{{ t('restocking.availableBudget') }}</div>
            <div class="summary-value">{{ formatMoney(budget) }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">{{ t('restocking.selectedTotal') }}</div>
            <div class="summary-value">{{ formatMoney(selectedTotal) }}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">{{ t('restocking.remainingBudget') }}</div>
            <div :class="['summary-value', { negative: remainingBudget < 0 }]">{{ formatMoney(remainingBudget) }}</div>
          </div>
        </div>
      </div>

      <div v-if="submitError" class="message message-error" role="alert">{{ submitError }}</div>
      <div v-if="successOrder" class="message message-success" role="status">
        <strong>{{ t('restocking.successTitle') }}</strong>
        <span>
          {{ t('restocking.successMessage', {
            orderNumber: successOrder.order_number,
            days: successOrder.lead_time_days,
            date: formatDate(successOrder.expected_delivery)
          }) }}
        </span>
        <router-link to="/orders" class="message-link">{{ t('restocking.viewOrders') }}</router-link>
      </div>

      <div class="card">
        <div class="card-header actions-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ recommendations.length }})</h3>
          <button
            type="button"
            class="place-order-btn"
            :disabled="selectedLines.length === 0 || submitting"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="recommendations.length === 0" class="empty-state">
          {{ t('restocking.empty') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th class="col-check">{{ t('restocking.table.include') }}</th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.name') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.currentStock') }}</th>
                <th class="num">{{ t('restocking.table.forecastDemand') }}</th>
                <th class="num">{{ t('restocking.table.orderQty') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.sku">
                <td class="col-check">
                  <input
                    type="checkbox"
                    :checked="!!selection[rec.sku]"
                    :aria-label="rec.sku"
                    @change="toggleLine(rec.sku, $event.target.checked)"
                  />
                </td>
                <td><strong>{{ rec.sku }}</strong></td>
                <td>{{ translateProductName(rec.name) }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ t(`trends.${rec.trend}`) }}</span>
                </td>
                <td class="num">{{ rec.onHand.toLocaleString() }}</td>
                <td class="num">{{ rec.forecast.toLocaleString() }}</td>
                <td class="num"><strong>{{ rec.shortfall.toLocaleString() }}</strong></td>
                <td class="num">{{ formatMoney(rec.unitCost, 2) }}</td>
                <td class="num"><strong>{{ formatMoney(rec.lineTotal, 2) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

const roundCents = (n) => Math.round(n * 100) / 100

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale, translateProductName } = useI18n()

    const currencySymbol = computed(() => (currentCurrency.value === 'JPY' ? '¥' : '$'))

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const inventoryItems = ref([])

    const budget = ref(0)
    // Selection state keyed by sku: { [sku]: boolean }
    const selection = ref({})
    const submitting = ref(false)
    const submitError = ref(null)
    const successOrder = ref(null)

    // Join forecasts to inventory; keep only items whose forecasted demand exceeds stock
    const shortfalls = computed(() => {
      const bySku = new Map(inventoryItems.value.map(item => [item.sku, item]))
      const result = []
      for (const f of forecasts.value) {
        const item = bySku.get(f.item_sku)
        if (!item) continue
        const shortfall = Math.max(0, f.forecasted_demand - item.quantity_on_hand)
        if (shortfall <= 0) continue
        result.push({
          sku: item.sku,
          name: item.name,
          trend: f.trend,
          onHand: item.quantity_on_hand,
          forecast: f.forecasted_demand,
          shortfall,
          unitCost: item.unit_cost,
          lineTotal: roundCents(shortfall * item.unit_cost)
        })
      }
      return result.sort((a, b) => b.shortfall - a.shortfall)
    })

    const totalShortfallCost = computed(() =>
      shortfalls.value.reduce((sum, r) => sum + r.lineTotal, 0)
    )

    // Slider granularity scales with the magnitude of the total cost
    const budgetStep = computed(() => {
      const total = totalShortfallCost.value
      if (total <= 0) return 1
      return Math.max(1, Math.pow(10, Math.floor(Math.log10(total)) - 1))
    })

    const maxBudget = computed(() =>
      Math.ceil(totalShortfallCost.value / budgetStep.value) * budgetStep.value
    )

    // Greedy rule: walk shortfalls from largest to smallest and add each WHOLE line
    // (quantity = shortfall) only if it fits the remaining budget; lines that do not
    // fit are skipped and the walk continues, so smaller lines can still be added.
    const recommendations = computed(() => {
      let remaining = budget.value
      const picked = []
      for (const line of shortfalls.value) {
        if (line.lineTotal <= remaining) {
          picked.push(line)
          remaining = roundCents(remaining - line.lineTotal)
        }
      }
      return picked
    })

    // Reset selection whenever the recommendation set changes so new lines default to included
    watch(recommendations, (recs) => {
      const next = {}
      recs.forEach(r => { next[r.sku] = true })
      selection.value = next
    })

    const selectedLines = computed(() =>
      recommendations.value.filter(r => selection.value[r.sku])
    )

    const selectedTotal = computed(() =>
      roundCents(selectedLines.value.reduce((sum, r) => sum + r.lineTotal, 0))
    )

    const remainingBudget = computed(() => roundCents(budget.value - selectedTotal.value))

    const toggleLine = (sku, checked) => {
      selection.value = { ...selection.value, [sku]: checked }
    }

    const formatMoney = (value, decimals = 0) =>
      `${currencySymbol.value}${Number(value).toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      })}`

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
    }

    const loadData = async () => {
      try {
        loading.value = true
        error.value = null
        const [forecastData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory()
        ])
        forecasts.value = forecastData
        inventoryItems.value = inventoryData
        // Default budget: roughly 40% of the maximum, snapped to the slider step
        budget.value = Math.round((maxBudget.value * 0.4) / budgetStep.value) * budgetStep.value
      } catch (err) {
        error.value = 'Failed to load restocking data: ' + err.message
      } finally {
        loading.value = false
      }
    }

    const placeOrder = async () => {
      if (selectedLines.value.length === 0 || submitting.value) return
      submitting.value = true
      submitError.value = null
      successOrder.value = null
      try {
        const order = await api.createRestockingOrder({
          budget: budget.value,
          lines: selectedLines.value.map(r => ({ sku: r.sku, quantity: r.shortfall }))
        })
        successOrder.value = order
        // Clear selection so the same lines are not submitted twice
        const cleared = {}
        recommendations.value.forEach(r => { cleared[r.sku] = false })
        selection.value = cleared
      } catch (err) {
        const detail = err.response?.data?.detail
        submitError.value = typeof detail === 'string' && detail ? detail : t('restocking.errorSubmit')
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      budget,
      budgetStep,
      maxBudget,
      recommendations,
      selection,
      selectedLines,
      selectedTotal,
      remainingBudget,
      submitting,
      submitError,
      successOrder,
      toggleLine,
      placeOrder,
      formatMoney,
      formatDate,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 0.75rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-amount {
  font-size: 1.75rem;
  font-weight: 700;
  color: #0f172a;
}

.budget-slider {
  width: 100%;
  accent-color: #3b82f6;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.summary-label {
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 600;
}

.summary-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin-top: 0.25rem;
}

.summary-value.negative {
  color: #dc2626;
}

.actions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.place-order-btn {
  background: #0f172a;
  color: white;
  border: 1px solid #0f172a;
  border-radius: 6px;
  padding: 0.5rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.place-order-btn:hover:not(:disabled) {
  background: #1e293b;
}

.place-order-btn:disabled {
  background: #e2e8f0;
  border-color: #e2e8f0;
  color: #94a3b8;
  cursor: not-allowed;
}

.message {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem;
  padding: 0.875rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
  font-size: 0.875rem;
}

.message-success {
  background: #d1fae5;
  border: 1px solid #10b981;
  color: #065f46;
}

.message-error {
  background: #fee2e2;
  border: 1px solid #ef4444;
  color: #991b1b;
}

.message-link {
  color: #2563eb;
  font-weight: 600;
  text-decoration: underline;
}

.empty-state {
  padding: 2rem 1.5rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

.col-check {
  width: 64px;
  text-align: center;
}

.num {
  text-align: right;
}
</style>
