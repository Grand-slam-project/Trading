export function getAssetLogoUrl(symbol, assetType) {
  if (!symbol) return null

  const cleanSymbol = String(symbol).trim()
  if (!cleanSymbol) return null

  const upperType = String(assetType || '').toUpperCase()

  if (upperType === 'CRYPTO') {
    return `https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/${cleanSymbol.toLowerCase()}.png`
  }

  return `https://static.toss.im/png-icons/securities/icn-sec-fill-${cleanSymbol.toUpperCase()}.png`
}
