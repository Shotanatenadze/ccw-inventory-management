<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <!-- Budget Input Form -->
    <div class="card budget-card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budgetPlanning') }}</h3>
      </div>
      <div class="budget-form">
        <div class="form-group">
          <label for="budget-input">{{ t('restocking.totalBudget') }}</label>
          <div class="input-container">
            <input
              id="budget-input"
              v-model.number="budgetAmount"
              type="number"
              :placeholder="t('restocking.enterBudget')"
              class="budget-input"
              min="0"
              step="100"
              @input="validateBudget"
              @change="validateBudget"
            />
            <span class="currency-symbol">{{ currencySymbol }}</span>
          </div>
          <div v-if="budgetError" class="error-message">{{ budgetError }}</div>
        </div>
        <button
          @click="calculateRecommendations"
          :disabled="!buttonEnabled"
          class="calculate-btn"
        >
          <span v-if="calculating">{{ t('restocking.calculating') }}...</span>
          <span v-else>{{ t('restocking.calculate') }}</span>
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="calculating" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('restocking.calculatingRecommendations') }}</p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="error-state">
      <h3>{{ t('common.error') }}</h3>
      <p>{{ error }}</p>
      <button @click="error = null" class="btn-secondary">{{ t('common.dismiss') }}</button>
    </div>

    <!-- Recommendations Results -->
    <div v-if="recommendations && !calculating" class="card recommendations-card">
      <div class="card-header">
        <h3 class="card-title">
          {{ t('restocking.recommendations') }} ({{ recommendations.items_covered }}/{{ recommendations.items_recommended }})
        </h3>
        <div class="budget-summary">
          <div class="budget-item">
            <span class="label">{{ t('restocking.allocated') }}:</span>
            <span class="value allocated">{{ formatCurrency(recommendations.budget_allocated) }}</span>
          </div>
          <div class="budget-item">
            <span class="label">{{ t('restocking.remaining') }}:</span>
            <span class="value remaining">{{ formatCurrency(recommendations.budget_remaining) }}</span>
          </div>
        </div>
      </div>

      <div v-if="editableRecommendations.length === 0" class="no-recommendations">
        <h4>{{ t('restocking.noItemsNeeded') }}</h4>
        <p>{{ t('restocking.allItemsStocked') }}</p>
      </div>

      <div v-else class="recommendations-container">
        <div class="table-container">
          <table class="recommendations-table">
            <thead>
              <tr>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.currentStock') }}</th>
                <th>{{ t('restocking.table.recommended') }}</th>
                <th>{{ t('restocking.table.allocated') }}</th>
                <th>{{ t('restocking.table.cost') }}</th>
                <th>{{ t('restocking.table.priority') }}</th>
                <th>{{ t('restocking.table.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in editableRecommendations" :key="item.item_id" class="recommendation-row">
                <td class="item-cell">
                  <div class="item-info">
                    <strong class="sku">{{ item.sku }}</strong>
                    <span class="name">{{ item.name }}</span>
                  </div>
                </td>
                <td class="stock-cell">
                  <span :class="{ 'low-stock': item.current_stock <= item.reorder_point }">
                    {{ item.current_stock }} / {{ item.reorder_point }}
                  </span>
                </td>
                <td class="recommended-cell">{{ item.recommended_quantity }}</td>
                <td class="allocated-cell">
                  <input
                    v-model.number="item.allocated_quantity"
                    type="number"
                    :min="0"
                    :max="calculateMaxQuantity(item)"
                    @input="updateItemCost(item)"
                    class="quantity-input"
                  />
                  <span v-if="item.is_partial" class="partial-label">{{ t('restocking.partial') }}</span>
                </td>
                <td class="cost-cell">{{ formatCurrency(item.total_cost) }}</td>
                <td class="priority-cell">
                  <div class="priority-score">{{ item.priority_score.toFixed(1) }}</div>
                  <div class="priority-indicators">
                    <span v-if="item.demand_trend" :class="`trend-${item.demand_trend}`">
                      {{ t(`restocking.trends.${item.demand_trend}`) }}
                    </span>
                    <span v-if="item.backlog_priority" :class="`priority-${item.backlog_priority}`">
                      {{ t(`restocking.priority.${item.backlog_priority}`) }}
                    </span>
                  </div>
                </td>
                <td class="actions-cell">
                  <button @click="removeItem(item)" class="remove-btn" :title="t('restocking.removeItem')">
                    ×
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="approval-section">
          <div class="approval-summary">
            <h4>{{ t('restocking.approvalSummary') }}</h4>
            <div class="summary-stats">
              <span>{{ t('restocking.itemsToOrder') }}: {{ editableRecommendations.length }}</span>
              <span>{{ t('restocking.totalCost') }}: {{ formatCurrency(totalCost) }}</span>
            </div>
          </div>
          <button
            @click="approveRecommendations"
            :disabled="!hasAllocatedItems || approving"
            class="approve-btn"
          >
            <span v-if="approving">{{ t('restocking.approving') }}...</span>
            <span v-else>{{ t('restocking.approve') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Success Modal -->
    <RestockingSuccessModal
      :is-open="showSuccessModal"
      :purchase-orders="createdOrders"
      :total-cost="totalApprovedCost"
      @close="showSuccessModal = false"
    />
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { useI18n } from '../composables/useI18n'
import { useFilters } from '../composables/useFilters'
import { formatCurrency } from '../utils/currency'
import { api } from '../api'
import RestockingSuccessModal from '../components/RestockingSuccessModal.vue'

export default {
  name: 'Restocking',
  components: {
    RestockingSuccessModal
  },
  setup() {
    const { t, currentCurrency } = useI18n()
    const { getCurrentFilters } = useFilters()

    // Reactive state
    const budgetAmount = ref(0)
    const budgetError = ref('')
    const calculating = ref(false)
    const approving = ref(false)
    const error = ref('')
    const recommendations = ref(null)
    const editableRecommendations = ref([])
    const showSuccessModal = ref(false)
    const createdOrders = ref([])
    const totalApprovedCost = ref(0)

    // Computed properties
    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const hasAllocatedItems = computed(() => {
      return editableRecommendations.value.some(item => item.allocated_quantity > 0)
    })

    const totalCost = computed(() => {
      return editableRecommendations.value.reduce((sum, item) => sum + item.total_cost, 0)
    })

    // Computed properties
    const buttonEnabled = computed(() => {
      return budgetAmount.value > 0 && !calculating.value && !budgetError.value
    })

    // Methods
    const validateBudget = () => {
      budgetError.value = ''
      if (budgetAmount.value < 0) {
        budgetError.value = t('restocking.errors.negativeBudget')
      } else if (budgetAmount.value === 0) {
        budgetError.value = t('restocking.errors.zeroBudget')
      }
    }

    const calculateRecommendations = async () => {
      if (!budgetAmount.value || budgetAmount.value <= 0) {
        budgetError.value = t('restocking.errors.invalidBudget')
        return
      }

      try {
        calculating.value = true
        error.value = ''

        const filters = getCurrentFilters()
        const request = {
          budget: budgetAmount.value,
          warehouse: filters.warehouse !== 'all' ? filters.warehouse : null,
          category: filters.category !== 'all' ? filters.category : null
        }

        const result = await api.calculateRestocking(request)
        recommendations.value = result
        editableRecommendations.value = [...result.recommendations]

      } catch (err) {
        console.error('Error calculating restocking:', err)
        error.value = t('restocking.errors.calculationFailed')
      } finally {
        calculating.value = false
      }
    }

    const calculateMaxQuantity = (item) => {
      // Maximum quantity based on remaining budget + current allocation
      const remainingBudget = budgetAmount.value - totalCost.value + item.total_cost
      return Math.floor(remainingBudget / item.unit_cost)
    }

    const updateItemCost = (item) => {
      if (item.allocated_quantity < 0) {
        item.allocated_quantity = 0
      }

      const maxQuantity = calculateMaxQuantity(item)
      if (item.allocated_quantity > maxQuantity) {
        item.allocated_quantity = maxQuantity
      }

      item.total_cost = item.allocated_quantity * item.unit_cost
      item.is_partial = item.allocated_quantity < item.recommended_quantity
    }

    const removeItem = (itemToRemove) => {
      const index = editableRecommendations.value.findIndex(item => item.item_id === itemToRemove.item_id)
      if (index > -1) {
        editableRecommendations.value.splice(index, 1)
      }
    }

    const approveRecommendations = async () => {
      if (!hasAllocatedItems.value) return

      try {
        approving.value = true
        error.value = ''

        const itemsToApprove = editableRecommendations.value.filter(item => item.allocated_quantity > 0)
        const result = await api.approveRestocking(itemsToApprove)

        createdOrders.value = result.orders || []
        totalApprovedCost.value = totalCost.value
        showSuccessModal.value = true

        // Reset form after successful approval
        budgetAmount.value = null
        recommendations.value = null
        editableRecommendations.value = []

      } catch (err) {
        console.error('Error approving restocking:', err)
        error.value = t('restocking.errors.approvalFailed')
      } finally {
        approving.value = false
      }
    }

    return {
      // State
      budgetAmount,
      budgetError,
      calculating,
      approving,
      error,
      recommendations,
      editableRecommendations,
      showSuccessModal,
      createdOrders,
      totalApprovedCost,

      // Computed
      currencySymbol,
      hasAllocatedItems,
      totalCost,
      buttonEnabled,

      // Methods
      validateBudget,
      calculateRecommendations,
      calculateMaxQuantity,
      updateItemCost,
      removeItem,
      approveRecommendations,
      formatCurrency,
      t
    }
  }
}
</script>

<style scoped>
.restocking {
  padding: 1.5rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h2 {
  color: #1e293b;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.page-header p {
  color: #64748b;
  font-size: 1.1rem;
}

/* Budget Form Styles */
.budget-card {
  margin-bottom: 2rem;
}

.budget-form {
  display: flex;
  gap: 1.5rem;
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-group {
  flex: 1;
  min-width: 250px;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #374151;
}

.input-container {
  position: relative;
}

.budget-input {
  width: 100%;
  padding: 0.75rem 3rem 0.75rem 0.75rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.budget-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.currency-symbol {
  position: absolute;
  right: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  font-weight: 500;
  color: #6b7280;
}

.calculate-btn {
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 140px;
}

.calculate-btn:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
}

.calculate-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
}

.error-message {
  margin-top: 0.5rem;
  color: #ef4444;
  font-size: 0.875rem;
}

/* Loading and Error States */
.loading-state {
  text-align: center;
  padding: 3rem 1.5rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top: 4px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-state {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 1.5rem;
  text-align: center;
  margin: 2rem 0;
}

.error-state h3 {
  color: #dc2626;
  margin-bottom: 0.5rem;
}

.error-state p {
  color: #7f1d1d;
  margin-bottom: 1rem;
}

/* Recommendations Card */
.recommendations-card {
  margin-bottom: 2rem;
}

.budget-summary {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}

.budget-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.budget-item .label {
  color: #6b7280;
  font-size: 0.875rem;
}

.budget-item .value {
  font-weight: 600;
  font-size: 1rem;
}

.value.allocated {
  color: #059669;
}

.value.remaining {
  color: #7c2d12;
}

/* No Recommendations */
.no-recommendations {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}

/* Recommendations Table */
.recommendations-container {
  margin-top: 1.5rem;
}

.table-container {
  overflow-x: auto;
  margin-bottom: 2rem;
}

.recommendations-table {
  width: 100%;
  border-collapse: collapse;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.recommendations-table th {
  background: #f8fafc;
  padding: 1rem 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #e5e7eb;
}

.recommendation-row {
  border-bottom: 1px solid #e5e7eb;
  transition: background-color 0.2s ease;
}

.recommendation-row:hover {
  background: #f9fafb;
}

.recommendations-table td {
  padding: 1rem 0.75rem;
  vertical-align: middle;
}

.item-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.sku {
  font-weight: 600;
  color: #1e293b;
}

.name {
  color: #64748b;
  font-size: 0.875rem;
}

.low-stock {
  color: #dc2626;
  font-weight: 600;
}

.quantity-input {
  width: 80px;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  text-align: center;
}

.quantity-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.partial-label {
  display: block;
  font-size: 0.75rem;
  color: #f59e0b;
  margin-top: 0.25rem;
}

.priority-score {
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 0.25rem;
}

.priority-indicators {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.priority-indicators span {
  font-size: 0.75rem;
  padding: 0.125rem 0.5rem;
  border-radius: 12px;
  font-weight: 500;
}

.trend-increasing {
  background: #d1fae5;
  color: #065f46;
}

.trend-stable {
  background: #e0e7ff;
  color: #3730a3;
}

.trend-decreasing {
  background: #fef3c7;
  color: #92400e;
}

.priority-high {
  background: #fecaca;
  color: #7f1d1d;
}

.priority-medium {
  background: #fed7aa;
  color: #9a3412;
}

.priority-low {
  background: #e5e7eb;
  color: #374151;
}

.remove-btn {
  background: #ef4444;
  color: white;
  border: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.2s ease;
}

.remove-btn:hover {
  background: #dc2626;
  transform: scale(1.1);
}

/* Approval Section */
.approval-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.approval-summary h4 {
  margin-bottom: 0.5rem;
  color: #1e293b;
}

.summary-stats {
  display: flex;
  gap: 1.5rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.approve-btn {
  padding: 0.75rem 2rem;
  background: #059669;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 140px;
}

.approve-btn:hover:not(:disabled) {
  background: #047857;
  transform: translateY(-1px);
}

.approve-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  padding: 0.5rem 1rem;
  background: #6b7280;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.btn-secondary:hover {
  background: #4b5563;
}

/* Responsive Design */
@media (max-width: 768px) {
  .restocking {
    padding: 1rem;
  }

  .budget-form {
    flex-direction: column;
    align-items: stretch;
  }

  .budget-summary {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .approval-section {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }

  .summary-stats {
    flex-direction: column;
    gap: 0.5rem;
  }

  .recommendations-table {
    font-size: 0.875rem;
  }

  .recommendations-table th,
  .recommendations-table td {
    padding: 0.75rem 0.5rem;
  }
}
</style>