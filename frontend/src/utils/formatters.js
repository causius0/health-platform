/**
 * Italian formatting utilities for dates and numbers.
 */

/**
 * Format date to Italian format (DD/MM/YYYY).
 * @param {string} isoDate - ISO format date string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
 * @returns {string} Formatted Italian date
 */
export function formatDateItalian(isoDate) {
  if (!isoDate) return 'N/A'

  try {
    // Handle dates with timestamps (YYYY-MM-DD HH:MM:SS.ssssss)
    const dateTimeParts = isoDate.split(' ')
    const datePart = dateTimeParts[0] // Get just the date portion

    const [year, month, day] = datePart.split('-')
    return `${day}/${month}/${year}`
  } catch (e) {
    return isoDate // Return original if parsing fails
  }
}

/**
 * Format number with Italian decimal comma.
 * @param {number} value - Numeric value
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted Italian number
 */
export function formatNumberItalian(value, decimals = 1) {
  if (value === null || value === undefined || isNaN(value)) return 'N/A'

  return value.toFixed(decimals).replace('.', ',')
}

/**
 * Format lab value with unit.
 * @param {string} value - Lab value
 * @param {string} unit - Unit
 * @returns {string} Formatted value with unit
 */
export function formatLabValue(value, unit) {
  if (!value) return 'N/A'
  if (!unit) return value

  // Try to parse as number for Italian formatting
  const numValue = parseFloat(value)
  if (!isNaN(numValue)) {
    return `${formatNumberItalian(numValue)} ${unit}`
  }

  return `${value} ${unit}`
}

/**
 * Translate condition to Italian.
 * @param {string} condition - Condition name
 * @returns {string} Italian condition name
 */
export function translateCondition(condition) {
  const translations = {
    'diabetes type 1': 'diabete tipo 1',
    'diabetes type 2': 'diabete tipo 2',
    'diabetes': 'diabete',
    'hypertension': 'ipertensione',
    'diabete tipo 2': 'diabete tipo 2',
    'diabete tipo 1': 'diabete tipo 1',
    'ipertensione': 'ipertensione'
  }

  const lowerCondition = condition.toLowerCase()
  return translations[lowerCondition] || condition
}

/**
 * Translate visit type to Italian.
 * @param {string} visitType - Visit type
 * @returns {string} Italian visit type
 */
export function translateVisitType(visitType) {
  const translations = {
    'controllo': 'Controllo',
    'urgenza': 'Urgenza',
    'followup': 'Follow-up'
  }

  return translations[visitType] || visitType
}
