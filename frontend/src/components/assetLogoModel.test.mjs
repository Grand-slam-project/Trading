import test from 'node:test'
import assert from 'node:assert/strict'

import { getAssetLogoUrl } from './assetLogoModel.js'

test('자산 유형별 로고 URL을 안정적으로 생성한다', () => {
  assert.equal(
    getAssetLogoUrl('BTC', 'CRYPTO'),
    'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/btc.png',
  )
  assert.equal(
    getAssetLogoUrl('aapl', 'STOCK'),
    'https://static.toss.im/png-icons/securities/icn-sec-fill-AAPL.png',
  )
  assert.equal(getAssetLogoUrl('', 'CRYPTO'), null)
})
