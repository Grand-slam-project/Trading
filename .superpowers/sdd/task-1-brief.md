### Task 1: 학습 유니버스 3분리

**Files:**
- Modify: `ml/data/reference/training_universes.json`
- Create: `tests/ml/test_training_universes.py`

**Interfaces:**
- Consumes: 기존 JSON 키 `stock_core_90`
- Produces:
  - JSON key `stock_kr_core_45: list[str]`
  - JSON key `stock_us_core_45: list[str]`

- [ ] **Step 1: Write the failing test**

Create `tests/ml/test_training_universes.py`:

```python
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UNIVERSE_PATH = PROJECT_ROOT / "ml" / "data" / "reference" / "training_universes.json"


def test_stock_core_90_is_split_into_kr_and_us_universes():
    payload = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))

    stock_core = payload["stock_core_90"]
    kr_core = payload["stock_kr_core_45"]
    us_core = payload["stock_us_core_45"]

    assert len(stock_core) == 90
    assert len(kr_core) == 45
    assert len(us_core) == 45
    assert kr_core + us_core == stock_core
    assert len(set(kr_core)) == 45
    assert len(set(us_core)) == 45
    assert set(kr_core).isdisjoint(set(us_core))
    assert all(symbol.isdigit() and len(symbol) == 6 for symbol in kr_core)
    assert all(not (symbol.isdigit() and len(symbol) == 6) for symbol in us_core)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/ml/test_training_universes.py -v
```

Expected: FAIL with `KeyError: 'stock_kr_core_45'`.

- [ ] **Step 3: Add split universes**

Modify `ml/data/reference/training_universes.json` so it contains these keys immediately after `stock_core_90`:

```json
  "stock_kr_core_45": [
    "005930", "000660", "035420", "035720", "005380", "000270", "051910", "068270", "373220", "006400",
    "207940", "105560", "055550", "086790", "012330", "028260", "066570", "096770", "003550", "034020",
    "011200", "010130", "017670", "009150", "018260", "010950", "032830", "042660", "000810", "316140",
    "035250", "251270", "361610", "018880", "329180", "259960", "352820", "138040", "267250", "302440",
    "005387", "090430", "271560", "034730", "097950"
  ],
  "stock_us_core_45": [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD", "AVGO", "LLY",
    "NFLX", "COST", "JPM", "V", "MA", "XOM", "UNH", "ORCL", "CRM", "ADBE",
    "QCOM", "INTC", "MU", "PLTR", "SMCI", "PANW", "ASML", "TSM", "UBER", "SHOP",
    "SNOW", "COIN", "SOFI", "ARM", "RDDT", "QQQ", "SPY", "DIA", "IWM", "SOXX",
    "XLK", "XLF", "XLE", "GLD", "TLT"
  ],
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python3 -m pytest tests/ml/test_training_universes.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add ml/data/reference/training_universes.json tests/ml/test_training_universes.py
git commit -m "feat: split stock training universes"
```

---

