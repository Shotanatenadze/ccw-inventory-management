<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click="close">
        <div class="modal-container success-modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">{{ t('restocking.success.title') }}</h3>
            <button class="close-button" @click="close">×</button>
          </div>

          <div class="modal-body">
            <div class="success-message">
              <svg class="success-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              <div class="message-content">
                <h4>{{ t('restocking.success.message', { count: purchaseOrders.length }) }}</h4>
                <p class="total-cost">{{ t('restocking.success.totalCost') }}: {{ formatCurrency(totalCost) }}</p>
              </div>
            </div>

            <div class="orders-summary">
              <h4>{{ t('restocking.success.ordersCreated') }}</h4>
              <div class="orders-list">
                <div v-for="order in purchaseOrders" :key="order.id" class="order-item">
                  <div class="order-header">
                    <span class="order-id">{{ order.id }}</span>
                    <span class="order-status">{{ t(`purchaseOrder.status.${order.status}`) }}</span>
                  </div>
                  <div class="order-details">
                    <div class="order-info">
                      <span class="item-details">
                        <strong>{{ extractSkuFromNotes(order.notes) }}</strong> - {{ order.quantity }} {{ t('common.units') }}
                      </span>
                      <span class="supplier">{{ order.supplier_name }}</span>
                    </div>
                    <div class="order-cost">{{ formatCurrency(order.quantity * order.unit_cost) }}</div>
                  </div>
                  <div class="delivery-info">
                    <span class="delivery-date">
                      {{ t('restocking.success.expectedDelivery') }}: {{ formatDate(order.expected_delivery_date) }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div class="next-steps">
              <h4>{{ t('restocking.success.nextSteps') }}</h4>
              <ul>
                <li>{{ t('restocking.success.step1') }}</li>
                <li>{{ t('restocking.success.step2') }}</li>
                <li>{{ t('restocking.success.step3') }}</li>
              </ul>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="close">
              {{ t('common.close') }}
            </button>
            <button class="btn-primary" @click="viewOrders">
              {{ t('restocking.success.viewOrders') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { useRouter } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import { formatCurrency } from '../utils/currency'

export default {
  name: 'RestockingSuccessModal',
  props: {
    isOpen: {
      type: Boolean,
      default: false
    },
    purchaseOrders: {
      type: Array,
      default: () => []
    },
    totalCost: {
      type: Number,
      default: 0
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const { t } = useI18n()
    const router = useRouter()

    const close = () => {
      emit('close')
    }

    const extractSkuFromNotes = (notes) => {
      if (!notes) return 'Unknown SKU'
      // Extract SKU from notes format: "Budget-based restock for {SKU} (Priority: {score})"
      const match = notes.match(/for\s+([A-Z0-9-]+)\s+\(Priority/)
      return match ? match[1] : 'Unknown SKU'
    }

    const formatDate = (dateString) => {
      if (!dateString) return 'TBD'
      try {
        const date = new Date(dateString)
        return date.toLocaleDateString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric'
        })
      } catch {
        return 'TBD'
      }
    }

    const viewOrders = () => {
      // Navigate to orders page to see the purchase orders
      close()
      router.push('/orders')
    }

    return {
      close,
      extractSkuFromNotes,
      formatDate,
      viewOrders,
      formatCurrency,
      t
    }
  }
}
</script>

<style scoped>
/* Modal Base Styles (following existing patterns) */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  padding: 1rem;
}

.success-modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 700px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #6b7280;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  transition: all 0.2s ease;
}

.close-button:hover {
  background: #f3f4f6;
  color: #374151;
}

.modal-body {
  padding: 1.5rem 2rem;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding: 1rem 2rem 1.5rem;
  border-top: 1px solid #e5e7eb;
}

/* Success Message Styles */
.success-message {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  border-radius: 12px;
  border: 1px solid #6ee7b7;
}

.success-icon {
  width: 48px;
  height: 48px;
  color: #059669;
  flex-shrink: 0;
}

.message-content h4 {
  color: #065f46;
  font-size: 1.125rem;
  margin-bottom: 0.5rem;
}

.total-cost {
  color: #047857;
  font-weight: 600;
  font-size: 1rem;
}

/* Orders Summary Styles */
.orders-summary {
  margin-bottom: 2rem;
}

.orders-summary h4 {
  color: #1e293b;
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 600;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.order-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 1rem;
  background: #f9fafb;
  transition: border-color 0.2s ease;
}

.order-item:hover {
  border-color: #d1d5db;
}

.order-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.order-id {
  font-family: 'Courier New', monospace;
  font-weight: 600;
  color: #3b82f6;
  font-size: 0.875rem;
}

.order-status {
  background: #dbeafe;
  color: #1e40af;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: capitalize;
}

.order-details {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.item-details {
  color: #1e293b;
  font-size: 0.875rem;
}

.supplier {
  color: #6b7280;
  font-size: 0.75rem;
}

.order-cost {
  font-weight: 600;
  color: #059669;
  font-size: 1rem;
}

.delivery-info {
  padding-top: 0.5rem;
  border-top: 1px solid #e5e7eb;
}

.delivery-date {
  color: #6b7280;
  font-size: 0.75rem;
}

/* Next Steps Styles */
.next-steps {
  background: #f1f5f9;
  border-radius: 8px;
  padding: 1.5rem;
  border: 1px solid #cbd5e1;
}

.next-steps h4 {
  color: #1e293b;
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 600;
}

.next-steps ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.next-steps li {
  position: relative;
  padding-left: 1.5rem;
  margin-bottom: 0.75rem;
  color: #475569;
  font-size: 0.875rem;
  line-height: 1.5;
}

.next-steps li:before {
  content: '•';
  position: absolute;
  left: 0;
  top: 0;
  color: #3b82f6;
  font-weight: bold;
}

.next-steps li:last-child {
  margin-bottom: 0;
}

/* Button Styles */
.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.btn-secondary {
  background: #6b7280;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.btn-secondary:hover {
  background: #4b5563;
}

/* Modal Transition Animations */
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from, .modal-leave-to {
  opacity: 0;
}

.modal-enter-active .success-modal-container,
.modal-leave-active .success-modal-container {
  transition: transform 0.3s ease;
}

.modal-enter-from .success-modal-container {
  transform: scale(0.9) translateY(20px);
}

.modal-leave-to .success-modal-container {
  transform: scale(0.9) translateY(20px);
}

/* Responsive Design */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 0.5rem;
  }

  .success-modal-container {
    max-height: 95vh;
  }

  .modal-header,
  .modal-body,
  .modal-footer {
    padding-left: 1rem;
    padding-right: 1rem;
  }

  .success-message {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .order-details {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .order-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }

  .modal-footer {
    flex-direction: column;
    gap: 0.75rem;
  }
}
</style>